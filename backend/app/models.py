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
    id: str
    categories: list[str]
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


class KnowledgeGraphEntity(BaseModel):
    id: str
    name: str
    categories: list[str]


class Evidence(BaseModel):
    edgeId: str | None
    primaryKnowledgeSource: str | None
    providedBy: list[str]
    sourceDataset: str | None
    references: list[str]
    maxPhaseForIndication: float | None
    attributes: dict[str, Any]


class GraphFact(BaseModel):
    subject: KnowledgeGraphEntity
    predicate: str
    object: KnowledgeGraphEntity
    evidence: Evidence


class GraphRetrievalResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]
    relation: ExtractedRelation
    relationships: list[RelationshipCandidate]
    facts: list[GraphFact]


class GroundingContextResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]
    relation: ExtractedRelation
    relationships: list[RelationshipCandidate]
    facts: list[GraphFact]
    context: str


class AugmentedPromptResponse(
    GroundingContextResponse
):
    hasEvidence: bool
    augmentedPrompt: str