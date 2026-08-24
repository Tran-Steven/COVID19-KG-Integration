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

    def find_entity_candidates(self, entity: str, limit: int = 5):
        query = """
        MATCH (n)
        WHERE n.name IS NOT NULL

        WITH n,
            CASE
                WHEN toLower(n.name) = toLower($entity) THEN 1.0
                WHEN any(
                    alias IN coalesce(n.aliases, [])
                    WHERE toLower(alias) = toLower($entity)
                ) THEN 0.95
                WHEN toLower(n.name) CONTAINS toLower($entity) THEN 0.75
                WHEN toLower($entity) CONTAINS toLower(n.name) THEN 0.70
                ELSE 0.0
            END AS score

        WHERE score > 0

        RETURN
            elementId(n) AS graphId,
            labels(n) AS labels,
            n.name AS name,
            coalesce(n.aliases, []) AS aliases,
            score

        ORDER BY score DESC
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                entity=entity,
                limit=limit,
            )
            return [record.data() for record in result]

    def get_relationship_types(self):
        query = """
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) AS relationship
        ORDER BY relationship
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [record["relationship"] for record in result]

    def find_related_facts(
        self,
        graph_id: str,
        relationship: str,
        limit: int = 20,
    ):
        query = """
        MATCH (source)-[r]-(target)
        WHERE elementId(source) = $graphId
          AND type(r) = $relationship

        RETURN
            elementId(source) AS sourceId,
            labels(source) AS sourceLabels,
            source.name AS source,
            type(r) AS relationship,
            elementId(target) AS targetId,
            labels(target) AS targetLabels,
            target.name AS target,
            properties(r) AS relationshipProperties

        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                graphId=graph_id,
                relationship=relationship,
                limit=limit,
            )
            return [record.data() for record in result]

    def find_relationship_between_entities(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        limit: int = 20,
    ):
        query = """
        MATCH (source)-[r]-(target)
        WHERE elementId(source) = $sourceId
          AND elementId(target) = $targetId
          AND type(r) = $relationship

        RETURN
            elementId(source) AS sourceId,
            labels(source) AS sourceLabels,
            source.name AS source,
            type(r) AS relationship,
            elementId(target) AS targetId,
            labels(target) AS targetLabels,
            target.name AS target,
            properties(r) AS relationshipProperties

        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                sourceId=source_id,
                targetId=target_id,
                relationship=relationship,
                limit=limit,
            )
            return [record.data() for record in result]