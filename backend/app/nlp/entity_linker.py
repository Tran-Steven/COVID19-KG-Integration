from app.database import Neo4jClient


class EntityLinker:
    def __init__(self, database: Neo4jClient):
        self.database = database

    def link(self, entity: str, limit: int = 5):
        return self.database.find_entity_candidates(entity, limit)