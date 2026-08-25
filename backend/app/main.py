from contextlib import asynccontextmanager

import spacy
from fastapi import FastAPI

from app.augmentation.context_builder import GroundingContextBuilder
from app.augmentation.prompt_augmenter import PromptAugmenter
from app.database import Neo4jClient
from app.interpretation.ambiguity_detector import AmbiguityDetector
from app.interpretation.direction_resolver import DirectionResolver
from app.interpretation.history_intent_resolver import HistoryIntentResolver
from app.interpretation.outcome_resolver import OutcomeResolver
from app.interpretation.relation_intent_resolver import RelationIntentResolver
from app.interpretation.semantic_interpreter import SemanticInterpreter
from app.models import (
    AugmentedPromptResponse,
    EntityLinkingResponse,
    EntityRequest,
    GraphRetrievalResponse,
    GroundingContextResponse,
    InterpretationResponse,
    NLPAnalysisResponse,
    NLPRequest,
    NLPResponse,
    RelationResponse,
)
from app.nlp.entity_extractor import EntityExtractor
from app.nlp.entity_linker import EntityLinker
from app.nlp.kg_entity_matcher import KGEntityMatcher
from app.nlp.relation_extractor import RelationExtractor
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.history_retriever import HistoryRetriever
from app.retrieval.relationship_resolver import RelationshipResolver


nlp = spacy.load("en_core_web_sm")

neo4j_client = Neo4jClient()

kg_entity_matcher = KGEntityMatcher(
    nlp,
    neo4j_client,
)

entity_extractor = EntityExtractor(
    nlp,
    kg_entity_matcher,
)

entity_linker = EntityLinker(
    neo4j_client
)

relation_extractor = RelationExtractor(
    nlp
)

relationship_resolver = RelationshipResolver(
    neo4j_client,
    nlp,
)

outcome_resolver = OutcomeResolver()

relation_intent_resolver = (
    RelationIntentResolver()
)

semantic_interpreter = (
    SemanticInterpreter()
)

direction_resolver = (
    DirectionResolver(
        nlp
    )
)

ambiguity_detector = AmbiguityDetector()

history_intent_resolver = (
    HistoryIntentResolver()
)

graph_retriever = GraphRetriever(
    neo4j_client,
    entity_linker,
    relationship_resolver,
)

history_retriever = (
    HistoryRetriever(
        neo4j_client,
        history_intent_resolver,
    )
)

grounding_context_builder = (
    GroundingContextBuilder()
)

prompt_augmenter = PromptAugmenter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    neo4j_client.close()


app = FastAPI(
    title="COVID-19 KG Integration API",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/kg/entity")
def entity_context(
    request: EntityRequest,
):
    context = (
        neo4j_client
        .get_entity_context(
            request.entity
        )
    )

    return {
        "entity": request.entity,
        "context": context,
    }


@app.post(
    "/nlp/entities",
    response_model=NLPResponse,
)
def extract_entities(
    request: NLPRequest,
):
    entities = entity_extractor.extract(
        request.text
    )

    return {
        "text": request.text,
        "entities": entities,
    }


@app.post(
    "/nlp/link",
    response_model=EntityLinkingResponse,
)
def link_entities(
    request: NLPRequest,
):
    extracted_entities = (
        entity_extractor.extract(
            request.text
        )
    )

    linked_entities = []

    for entity in extracted_entities:
        candidates = entity_linker.link(
            entity["text"]
        )

        linked_entities.append(
            {
                **entity,
                "candidates": candidates,
            }
        )

    return {
        "text": request.text,
        "entities": linked_entities,
    }


@app.post(
    "/nlp/relation",
    response_model=RelationResponse,
)
def extract_relation(
    request: NLPRequest,
):
    relation = relation_extractor.extract(
        request.text
    )

    return {
        "text": request.text,
        "relation": relation,
    }


@app.post(
    "/nlp/analyze",
    response_model=NLPAnalysisResponse,
)
def analyze_text(
    request: NLPRequest,
):
    extracted_entities = (
        entity_extractor.extract(
            request.text
        )
    )

    relation = relation_extractor.extract(
        request.text
    )

    linked_entities = []

    for entity in extracted_entities:
        candidates = entity_linker.link(
            entity["text"]
        )

        linked_entities.append(
            {
                **entity,
                "candidates": candidates,
            }
        )

    return {
        "text": request.text,
        "entities": linked_entities,
        "relation": relation,
    }


@app.post("/nlp/semantic")
def inspect_semantics(
    request: NLPRequest,
):
    return {
        "text": request.text,
        "intentCandidates": (
            semantic_interpreter
            .rank_intents(
                request.text
            )
        ),
        "outcomeCandidates": (
            semantic_interpreter
            .rank_outcomes(
                request.text
            )
        ),
        "directionCandidates": (
            semantic_interpreter
            .rank_directions(
                request.text
            )
        ),
    }


@app.post(
    "/nlp/interpret",
    response_model=InterpretationResponse,
)
def interpret_query(
    request: NLPRequest,
):
    relation = relation_extractor.extract(
        request.text
    )

    outcomes = outcome_resolver.resolve(
        request.text
    )

    direction = direction_resolver.resolve(
        request.text
    )

    rule_intent = (
        relation_intent_resolver.resolve(
            text=request.text,
            extracted_relation=relation[
                "text"
            ],
        )
    )

    relation_intent = rule_intent

    if (
        not outcomes
        and direction is not None
    ):
        semantic_outcome = (
            semantic_interpreter
            .resolve_outcome(
                request.text
            )
        )

        if semantic_outcome:
            outcomes = [
                semantic_outcome
            ]

    if (
        direction is not None
        and outcomes
        and rule_intent["intent"]
        in {
            "unknown",
            "treatment",
            "risk_modifier",
            "broad_effect",
        }
    ):
        relation_intent = {
            "intent": "risk_modifier",
            "direction": direction,
            "matchedText": None,
            "specific": True,
            "method": "composed",
            "score": None,
        }

    if (
        relation_intent["intent"]
        == "unknown"
    ):
        semantic_intent = (
            semantic_interpreter
            .resolve_intent(
                request.text
            )
        )

        if semantic_intent:
            relation_intent = (
                semantic_intent
            )
        else:
            relation_intent = {
                **relation_intent,
                "method": "none",
            }

    if (
        not outcomes
        and relation_intent["intent"]
        in {
            "risk_modifier",
            "association",
        }
    ):
        semantic_outcome = (
            semantic_interpreter
            .resolve_outcome(
                request.text
            )
        )

        if semantic_outcome:
            outcomes = [
                semantic_outcome
            ]

    if (
        direction is None
        and outcomes
        and rule_intent["intent"]
        in {
            "unknown",
            "treatment",
            "risk_modifier",
            "broad_effect",
        }
    ):
        semantic_direction = (
            semantic_interpreter
            .resolve_direction(
                request.text
            )
        )

        if semantic_direction:
            direction = (
                semantic_direction[
                    "direction"
                ]
            )

    if (
        direction is not None
        and outcomes
        and rule_intent["intent"]
        in {
            "unknown",
            "treatment",
            "risk_modifier",
            "broad_effect",
        }
    ):
        relation_intent = {
            "intent": "risk_modifier",
            "direction": direction,
            "matchedText": None,
            "specific": True,
            "method": "composed",
            "score": None,
        }

    if (
        relation_intent["intent"]
        == "risk_modifier"
        and relation_intent[
            "direction"
        ] is None
        and direction is not None
    ):
        relation_intent[
            "direction"
        ] = direction

    interpretation = (
        ambiguity_detector.detect(
            text=request.text,
            relation=relation["text"],
            outcomes=outcomes,
            resolved_intent=relation_intent[
                "intent"
            ],
        )
    )

    interpretation[
        "relationIntent"
    ] = relation_intent

    return {
        "text": request.text,
        "relation": relation,
        "interpretation": interpretation,
    }


def retrieve(
    text: str,
):
    history_interpretation = (
        history_intent_resolver.resolve(
            text
        )
    )

    relation = relation_extractor.extract(
        text
    )

    if history_interpretation is not None:
        history = history_retriever.retrieve(
            text
        )

        return {
            "text": text,
            "verificationType": "history",
            "entities": [],
            "relation": relation,
            "relationships": [],
            "facts": [],
            "history": history,
        }

    extracted_entities = (
        entity_extractor.extract(
            text
        )
    )

    retrieval = graph_retriever.retrieve(
        entities=extracted_entities,
        relation=relation["text"],
    )

    return {
        "text": text,
        "verificationType": (
            "relationship"
        ),
        "entities": retrieval["entities"],
        "relation": relation,
        "relationships": retrieval[
            "relationships"
        ],
        "facts": retrieval["facts"],
        "history": None,
    }


def ground(
    text: str,
):
    retrieval = retrieve(
        text
    )

    if (
        retrieval[
            "verificationType"
        ]
        == "history"
    ):
        context = (
            grounding_context_builder
            .build_history(
                text=retrieval["text"],
                history=retrieval[
                    "history"
                ],
            )
        )
    else:
        context = (
            grounding_context_builder
            .build(
                text=retrieval["text"],
                entities=retrieval[
                    "entities"
                ],
                relation=retrieval[
                    "relation"
                ],
                relationships=retrieval[
                    "relationships"
                ],
                facts=retrieval[
                    "facts"
                ],
            )
        )

    return {
        **retrieval,
        "context": context,
    }


@app.post(
    "/kg/retrieve",
    response_model=GraphRetrievalResponse,
)
def retrieve_graph_context(
    request: NLPRequest,
):
    return retrieve(
        request.text
    )


@app.post("/kg/history")
def retrieve_history(
    request: NLPRequest,
):
    return history_retriever.retrieve(
        request.text
    )


@app.post(
    "/kg/context",
    response_model=GroundingContextResponse,
)
def build_grounding_context(
    request: NLPRequest,
):
    return ground(
        request.text
    )


@app.post(
    "/kg/augment",
    response_model=AugmentedPromptResponse,
)
def augment_prompt(
    request: NLPRequest,
):
    grounding = ground(
        request.text
    )

    history = grounding.get(
        "history"
    )

    has_history_evidence = bool(
        history
        and history.get(
            "evidence"
        )
    )

    has_evidence = (
        bool(
            grounding["facts"]
        )
        or has_history_evidence
    )

    augmented_prompt = (
        prompt_augmenter.build(
            text=request.text,
            context=grounding[
                "context"
            ],
            has_evidence=has_evidence,
        )
    )

    return {
        **grounding,
        "hasEvidence": has_evidence,
        "augmentedPrompt": (
            augmented_prompt
        ),
    }