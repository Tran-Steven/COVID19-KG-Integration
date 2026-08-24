from pydantic import BaseModel


class EntityRequest(BaseModel):
    entity: str