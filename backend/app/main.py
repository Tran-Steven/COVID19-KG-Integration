from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Neo4jClient
from app.models import EntityRequest


neo4j_client = Neo4jClient()


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