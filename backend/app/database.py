import os

from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "cvkgdemo"),
            ),
        )

    def close(self):
        self.driver.close()

    def get_entity_context(self, entity: str):
        query = """
        MATCH (n)
        WHERE toLower(n.name) = toLower($entity)
        OPTIONAL MATCH (n)-[r]-(connected)
        RETURN
            labels(n) AS entityLabels,
            n.name AS entity,
            type(r) AS relationship,
            connected.name AS connectedEntity,
            labels(connected) AS connectedLabels
        """

        with self.driver.session() as session:
            result = session.run(query, entity=entity)
            return [record.data() for record in result]