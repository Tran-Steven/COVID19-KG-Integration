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