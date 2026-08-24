from contextlib import asynccontextmanager

import spacy
from fastapi import FastAPI

from app.database import Neo4jClient
from app.models import (
    EntityLinkingResponse,
    EntityRequest,
    GraphRetrievalResponse,
    NLPAnalysisResponse,
    NLPRequest,
    NLPResponse,
    RelationResponse,
)
from app.nlp.entity_extractor import EntityExtractor
from app.nlp.entity_linker import EntityLinker
from app.nlp.relation_extractor import RelationExtractor
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.relationship_resolver import RelationshipResolver


nlp = spacy.load("en_core_web_sm")

neo4j_client = Neo4jClient()
entity_extractor = EntityExtractor(nlp)
entity_linker = EntityLinker(neo4j_client)
relation_extractor = RelationExtractor(nlp)
relationship_resolver = RelationshipResolver(
    neo4j_client,
    nlp,
)
graph_retriever = GraphRetriever(
    neo4j_client,
    entity_linker,
    relationship_resolver,
)


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
    return {"status": "ok"}


@app.post("/kg/entity")
def entity_context(request: EntityRequest):
    context = neo4j_client.get_entity_context(request.entity)

    return {
        "entity": request.entity,
        "context": context,
    }


@app.post("/nlp/entities", response_model=NLPResponse)
def extract_entities(request: NLPRequest):
    entities = entity_extractor.extract(request.text)

    return {
        "text": request.text,
        "entities": entities,
    }


@app.post("/nlp/link", response_model=EntityLinkingResponse)
def link_entities(request: NLPRequest):
    extracted_entities = entity_extractor.extract(request.text)

    linked_entities = []

    for entity in extracted_entities:
        candidates = entity_linker.link(entity["text"])

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


@app.post("/nlp/relation", response_model=RelationResponse)
def extract_relation(request: NLPRequest):
    relation = relation_extractor.extract(request.text)

    return {
        "text": request.text,
        "relation": relation,
    }


@app.post("/nlp/analyze", response_model=NLPAnalysisResponse)
def analyze_text(request: NLPRequest):
    extracted_entities = entity_extractor.extract(request.text)
    relation = relation_extractor.extract(request.text)

    linked_entities = []

    for entity in extracted_entities:
        candidates = entity_linker.link(entity["text"])

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


@app.post("/kg/retrieve", response_model=GraphRetrievalResponse)
def retrieve_graph_context(request: NLPRequest):
    extracted_entities = entity_extractor.extract(request.text)
    relation = relation_extractor.extract(request.text)

    retrieval = graph_retriever.retrieve(
        entities=extracted_entities,
        relation=relation["text"],
    )

    return {
        "text": request.text,
        "entities": retrieval["entities"],
        "relation": relation,
        "relationships": retrieval["relationships"],
        "facts": retrieval["facts"],
    }