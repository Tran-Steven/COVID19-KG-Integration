from typing import Any

from pydantic import BaseModel


class EntityRequest(BaseModel):
    entity: str


class NLPRequest(BaseModel):
    text: str


class ExtractedEntity(BaseModel):
    text: str
    type: str
    start: int
    end: int


class NLPResponse(BaseModel):
    text: str
    entities: list[ExtractedEntity]


class GraphEntityCandidate(BaseModel):
    graphId: str
    labels: list[str]
    name: str
    aliases: list[str]
    score: float


class LinkedEntity(BaseModel):
    text: str
    type: str
    start: int
    end: int
    candidates: list[GraphEntityCandidate]


class EntityLinkingResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]


class ExtractedRelation(BaseModel):
    text: str | None
    normalized: str | None
    root: str | None


class RelationResponse(BaseModel):
    text: str
    relation: ExtractedRelation


class NLPAnalysisResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]
    relation: ExtractedRelation


class RelationshipCandidate(BaseModel):
    relationship: str
    normalized: str
    score: float


class GraphFact(BaseModel):
    sourceId: str
    sourceLabels: list[str]
    source: str
    relationship: str
    targetId: str
    targetLabels: list[str]
    target: str
    relationshipProperties: dict[str, Any]


class GraphRetrievalResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]
    relation: ExtractedRelation
    relationships: list[RelationshipCandidate]
    facts: list[GraphFact]