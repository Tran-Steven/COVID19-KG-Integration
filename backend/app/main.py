from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Neo4jClient
from app.models import EntityRequest, NLPRequest, NLPResponse
from app.nlp.entity_extractor import EntityExtractor


neo4j_client = Neo4jClient()
entity_extractor = EntityExtractor()


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