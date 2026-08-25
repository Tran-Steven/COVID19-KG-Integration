from contextlib import (
    asynccontextmanager,
)

import spacy
from fastapi import FastAPI

from app.augmentation.context_builder import (
    GroundingContextBuilder,
)
from app.augmentation.prompt_augmenter import (
    PromptAugmenter,
)
from app.augmentation.who_context_builder import (
    WhoGroundingContextBuilder,
)
from app.database import Neo4jClient
from app.interpretation.ambiguity_detector import (
    AmbiguityDetector,
)
from app.interpretation.confidence_scorer import (
    ConfidenceScorer,
)
from app.interpretation.direction_resolver import (
    DirectionResolver,
)
from app.interpretation.history_intent_resolver import (
    HistoryIntentResolver,
)
from app.interpretation.outcome_resolver import (
    OutcomeResolver,
)
from app.interpretation.relation_intent_resolver import (
    RelationIntentResolver,
)
from app.interpretation.response_verification_aggregator import (
    ResponseVerificationAggregator,
)
from app.interpretation.semantic_interpreter import (
    SemanticInterpreter,
)
from app.interpretation.verification_resolver import (
    VerificationResolver,
)
from app.interpretation.who_intent_resolver import (
    WhoIntentResolver,
)
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
    ResponseVerificationRequest,
    ResponseVerificationResponse,
)
from app.nlp.entity_extractor import (
    EntityExtractor,
)
from app.nlp.entity_linker import (
    EntityLinker,
)
from app.nlp.kg_entity_matcher import (
    KGEntityMatcher,
)
from app.nlp.relation_extractor import (
    RelationExtractor,
)
from app.nlp.response_claim_extractor import (
    ResponseClaimExtractor,
)
from app.retrieval.graph_retriever import (
    GraphRetriever,
)
from app.retrieval.history_retriever import (
    HistoryRetriever,
)
from app.retrieval.relationship_resolver import (
    RelationshipResolver,
)
from app.retrieval.who_retriever import (
    WhoRetriever,
)


nlp = spacy.load(
    "en_core_web_sm"
)

neo4j_client = Neo4jClient()

kg_entity_matcher = (
    KGEntityMatcher(
        nlp,
        neo4j_client,
    )
)

entity_extractor = (
    EntityExtractor(
        nlp,
        kg_entity_matcher,
    )
)

entity_linker = (
    EntityLinker(
        neo4j_client
    )
)

relation_extractor = (
    RelationExtractor(
        nlp
    )
)

response_claim_extractor = (
    ResponseClaimExtractor(
        nlp
    )
)

response_verification_aggregator = (
    ResponseVerificationAggregator()
)

relationship_resolver = (
    RelationshipResolver(
        neo4j_client,
        nlp,
    )
)

outcome_resolver = (
    OutcomeResolver()
)

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

ambiguity_detector = (
    AmbiguityDetector()
)

history_intent_resolver = (
    HistoryIntentResolver()
)

who_intent_resolver = (
    WhoIntentResolver()
)

verification_resolver = (
    VerificationResolver()
)

confidence_scorer = (
    ConfidenceScorer()
)

graph_retriever = (
    GraphRetriever(
        neo4j_client,
        entity_linker,
        relationship_resolver,
    )
)

history_retriever = (
    HistoryRetriever(
        neo4j_client,
        history_intent_resolver,
    )
)

who_retriever = (
    WhoRetriever(
        neo4j_client,
        who_intent_resolver,
    )
)

grounding_context_builder = (
    GroundingContextBuilder()
)

who_grounding_context_builder = (
    WhoGroundingContextBuilder()
)

prompt_augmenter = (
    PromptAugmenter()
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    yield

    neo4j_client.close()


app = FastAPI(
    title=(
        "COVID-19 KG "
        "Integration API"
    ),
    lifespan=lifespan,
)


@app.get(
    "/health"
)
def health():
    return {
        "status": "ok"
    }


@app.post(
    "/kg/entity"
)
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


def link_extracted_entities(
    entities: list[dict],
):
    linked_entities = []

    for entity in entities:
        candidates = (
            entity_linker.link(
                entity["text"]
            )
        )

        linked_entities.append(
            {
                **entity,
                "candidates": candidates,
            }
        )

    return linked_entities


def finalize_retrieval(
    retrieval: dict,
):
    verification = (
        verification_resolver.resolve(
            text=retrieval[
                "text"
            ],
            verification_type=(
                retrieval[
                    "verificationType"
                ]
            ),
            entities=retrieval[
                "entities"
            ],
            relationships=retrieval[
                "relationships"
            ],
            facts=retrieval[
                "facts"
            ],
            history=retrieval.get(
                "history"
            ),
        )
    )

    verification[
        "confidence"
    ] = (
        confidence_scorer.score(
            verification_type=(
                retrieval[
                    "verificationType"
                ]
            ),
            verification=verification,
            entities=retrieval[
                "entities"
            ],
            relationships=retrieval[
                "relationships"
            ],
            facts=retrieval[
                "facts"
            ],
            history=retrieval.get(
                "history"
            ),
        )
    )

    retrieval[
        "verification"
    ] = verification

    return retrieval


def has_covid_context(
    text: str,
):
    normalized = (
        text.lower()
        .replace(
            "_",
            " ",
        )
    )

    return any(
        value in normalized
        for value in (
            "covid",
            "sars-cov-2",
            "sars cov 2",
            (
                "coronavirus "
                "disease 2019"
            ),
        )
    )


def contextualize_claim(
    text: str,
    context_text: str | None,
):
    if not context_text:
        return None

    if has_covid_context(
        text
    ):
        return None

    if not has_covid_context(
        context_text
    ):
        return None

    return (
        f"{text} "
        f"Question context: "
        f"{context_text}"
    )


@app.post(
    "/nlp/entities",
    response_model=NLPResponse,
)
def extract_entities(
    request: NLPRequest,
):
    entities = (
        entity_extractor.extract(
            request.text
        )
    )

    return {
        "text": request.text,
        "entities": entities,
    }


@app.post(
    "/nlp/link",
    response_model=(
        EntityLinkingResponse
    ),
)
def link_entities(
    request: NLPRequest,
):
    extracted_entities = (
        entity_extractor.extract(
            request.text
        )
    )

    return {
        "text": request.text,
        "entities": (
            link_extracted_entities(
                extracted_entities
            )
        ),
    }


@app.post(
    "/nlp/relation",
    response_model=RelationResponse,
)
def extract_relation(
    request: NLPRequest,
):
    relation = (
        relation_extractor.extract(
            request.text
        )
    )

    return {
        "text": request.text,
        "relation": relation,
    }


@app.post(
    "/nlp/analyze",
    response_model=(
        NLPAnalysisResponse
    ),
)
def analyze_text(
    request: NLPRequest,
):
    extracted_entities = (
        entity_extractor.extract(
            request.text
        )
    )

    relation = (
        relation_extractor.extract(
            request.text
        )
    )

    linked_entities = (
        link_extracted_entities(
            extracted_entities
        )
    )

    return {
        "text": request.text,
        "entities": linked_entities,
        "relation": relation,
    }


@app.post(
    "/nlp/semantic"
)
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
    response_model=(
        InterpretationResponse
    ),
)
def interpret_query(
    request: NLPRequest,
):
    relation = (
        relation_extractor.extract(
            request.text
        )
    )

    outcomes = (
        outcome_resolver.resolve(
            request.text
        )
    )

    direction = (
        direction_resolver.resolve(
            request.text
        )
    )

    rule_intent = (
        relation_intent_resolver
        .resolve(
            text=request.text,
            extracted_relation=(
                relation["text"]
            ),
        )
    )

    relation_intent = (
        rule_intent
    )

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
        and rule_intent[
            "intent"
        ]
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
        relation_intent[
            "intent"
        ]
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
        and relation_intent[
            "intent"
        ]
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
        and rule_intent[
            "intent"
        ]
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
        and rule_intent[
            "intent"
        ]
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
        relation_intent[
            "intent"
        ]
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
            relation=relation[
                "text"
            ],
            outcomes=outcomes,
            resolved_intent=(
                relation_intent[
                    "intent"
                ]
            ),
        )
    )

    interpretation[
        "relationIntent"
    ] = relation_intent

    return {
        "text": request.text,
        "relation": relation,
        "interpretation": (
            interpretation
        ),
    }


def retrieve(
    text: str,
    context_text: str | None = None,
):
    relation = (
        relation_extractor.extract(
            text
        )
    )

    history_interpretation = (
        history_intent_resolver
        .resolve(
            text
        )
    )

    history_routing_text = (
        text
    )

    contextual_text = (
        contextualize_claim(
            text,
            context_text,
        )
    )

    if (
        history_interpretation
        is None
        and contextual_text
    ):
        contextual_history = (
            history_intent_resolver
            .resolve(
                contextual_text
            )
        )

        if contextual_history is not None:
            history_interpretation = (
                contextual_history
            )

            history_routing_text = (
                contextual_text
            )

    if (
        history_interpretation
        is not None
    ):
        history = (
            history_retriever.retrieve(
                history_routing_text
            )
        )

        return finalize_retrieval(
            {
                "text": text,
                "verificationType": (
                    "history"
                ),
                "entities": [],
                "relation": relation,
                "relationships": [],
                "facts": [],
                "history": history,
            }
        )

    who_interpretation = (
        who_intent_resolver.resolve(
            text
        )
    )

    if (
        who_interpretation is None
        and contextual_text
    ):
        who_interpretation = (
            who_intent_resolver.resolve(
                contextual_text
            )
        )

    if (
        who_interpretation
        is not None
    ):
        extracted_entities = (
            entity_extractor.extract(
                text
            )
        )

        linked_entities = (
            link_extracted_entities(
                extracted_entities
            )
        )

        who = (
            who_retriever.retrieve(
                text,
                interpretation=(
                    who_interpretation
                ),
            )
        )

        return finalize_retrieval(
            {
                "text": text,
                "verificationType": (
                    "who"
                ),
                "entities": (
                    linked_entities
                ),
                "relation": relation,
                "relationships": (
                    who[
                        "relationships"
                    ]
                ),
                "facts": (
                    who[
                        "facts"
                    ]
                ),
                "history": None,
            }
        )

    extracted_entities = (
        entity_extractor.extract(
            text
        )
    )

    retrieval = (
        graph_retriever.retrieve(
            entities=(
                extracted_entities
            ),
            relation=relation[
                "text"
            ],
        )
    )

    return finalize_retrieval(
        {
            "text": text,
            "verificationType": (
                "relationship"
            ),
            "entities": retrieval[
                "entities"
            ],
            "relation": relation,
            "relationships": retrieval[
                "relationships"
            ],
            "facts": retrieval[
                "facts"
            ],
            "history": None,
        }
    )


def verify_response_claim(
    question: str,
    claim: dict,
):
    direct = retrieve(
        claim[
            "text"
        ]
    )

    direct_status = (
        direct[
            "verification"
        ][
            "status"
        ]
    )

    retry_with_context = (
        direct_status
        in {
            (
                "NOT_VERIFIABLE_"
                "WITH_CURRENT_KG"
            ),
            "INSUFFICIENT_EVIDENCE",
        }
    )

    if not retry_with_context:
        return {
            **claim,
            "extractionMethod": (
                claim[
                    "method"
                ]
            ),
            "usedQuestionContext": (
                False
            ),
            "retrieval": direct,
        }

    contextual = retrieve(
        claim[
            "text"
        ],
        context_text=question,
    )

    contextual_status = (
        contextual[
            "verification"
        ][
            "status"
        ]
    )

    contextual_route = (
        contextual[
            "verificationType"
        ]
    )

    use_contextual = (
        contextual_status
        != (
            "NOT_VERIFIABLE_"
            "WITH_CURRENT_KG"
        )
        and (
            contextual_route
            in {
                "history",
                "who",
            }
            or direct_status
            == (
                "NOT_VERIFIABLE_"
                "WITH_CURRENT_KG"
            )
        )
    )

    retrieval = (
        contextual
        if use_contextual
        else direct
    )

    return {
        **claim,
        "extractionMethod": (
            claim[
                "method"
            ]
        ),
        "usedQuestionContext": (
            use_contextual
        ),
        "retrieval": retrieval,
    }


def verification_context(
    verification: dict,
):
    confidence = verification[
        "confidence"
    ]

    lines = [
        "VERIFICATION RESULT",
        (
            "status="
            f"{verification['status']}"
        ),
        (
            "evidence_count="
            f"{verification['evidenceCount']}"
        ),
        (
            "method="
            f"{verification['method']}"
        ),
        (
            "reason="
            f"{verification['reason']}"
        ),
        (
            "confidence_score="
            f"{confidence['score']}"
        ),
        (
            "confidence_level="
            f"{confidence['level']}"
        ),
        (
            "confidence_target="
            f"{confidence['target']}"
        ),
        (
            "confidence_calibrated="
            f"{str(confidence['calibrated']).lower()}"
        ),
    ]

    for name, value in (
        confidence[
            "components"
        ].items()
    ):
        lines.append(
            (
                "confidence_component_"
                f"{name}={value}"
            )
        )

    return "\n".join(
        lines
    )


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
                text=retrieval[
                    "text"
                ],
                history=retrieval[
                    "history"
                ],
            )
        )

    elif (
        retrieval[
            "verificationType"
        ]
        == "who"
    ):
        context = (
            who_grounding_context_builder
            .build(
                text=retrieval[
                    "text"
                ],
                entities=retrieval[
                    "entities"
                ],
                relationships=(
                    retrieval[
                        "relationships"
                    ]
                ),
                facts=retrieval[
                    "facts"
                ],
            )
        )

    else:
        context = (
            grounding_context_builder
            .build(
                text=retrieval[
                    "text"
                ],
                entities=retrieval[
                    "entities"
                ],
                relation=retrieval[
                    "relation"
                ],
                relationships=(
                    retrieval[
                        "relationships"
                    ]
                ),
                facts=retrieval[
                    "facts"
                ],
            )
        )

    context = "\n\n".join(
        [
            verification_context(
                retrieval[
                    "verification"
                ]
            ),
            context,
        ]
    )

    return {
        **retrieval,
        "context": context,
    }


@app.post(
    "/kg/retrieve",
    response_model=(
        GraphRetrievalResponse
    ),
)
def retrieve_graph_context(
    request: NLPRequest,
):
    return retrieve(
        request.text
    )


@app.post(
    "/kg/verify-response",
    response_model=(
        ResponseVerificationResponse
    ),
)
def verify_response(
    request: ResponseVerificationRequest,
):
    extracted_claims = (
        response_claim_extractor
        .extract(
            request.response
        )
    )

    verified_claims = [
        verify_response_claim(
            request.question,
            claim,
        )
        for claim
        in extracted_claims
    ]

    summary = (
        response_verification_aggregator
        .summarize(
            verified_claims
        )
    )

    return {
        "question": request.question,
        "response": request.response,
        "claimCount": len(
            verified_claims
        ),
        "summary": summary,
        "claims": verified_claims,
    }


@app.post(
    "/kg/history"
)
def retrieve_history(
    request: NLPRequest,
):
    return (
        history_retriever.retrieve(
            request.text
        )
    )


@app.post(
    "/kg/context",
    response_model=(
        GroundingContextResponse
    ),
)
def build_grounding_context(
    request: NLPRequest,
):
    return ground(
        request.text
    )


@app.post(
    "/kg/augment",
    response_model=(
        AugmentedPromptResponse
    ),
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
            grounding[
                "facts"
            ]
        )
        or has_history_evidence
    )

    augmented_prompt = (
        prompt_augmenter.build(
            text=request.text,
            context=grounding[
                "context"
            ],
            has_evidence=(
                has_evidence
            ),
        )
    )

    return {
        **grounding,
        "hasEvidence": (
            has_evidence
        ),
        "augmentedPrompt": (
            augmented_prompt
        ),
    }