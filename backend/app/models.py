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