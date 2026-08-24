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
            coalesce(r.predicate, r.relation, type(r)) AS relationship,
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
                WHEN n.id IS NOT NULL
                    AND toLower(n.id) = toLower($entity) THEN 1.0
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
        WITH DISTINCT coalesce(
            r.predicate,
            r.relation,
            type(r)
        ) AS relationship
        WHERE relationship IS NOT NULL
        RETURN relationship
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
          AND (
              type(r) = $relationship
              OR r.predicate = $relationship
              OR r.relation = $relationship
          )

        RETURN
            elementId(source) AS sourceId,
            labels(source) AS sourceLabels,
            source.name AS source,
            coalesce(
                r.predicate,
                r.relation,
                type(r)
            ) AS relationship,
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
          AND (
              type(r) = $relationship
              OR r.predicate = $relationship
              OR r.relation = $relationship
          )

        RETURN
            elementId(source) AS sourceId,
            labels(source) AS sourceLabels,
            source.name AS source,
            coalesce(
                r.predicate,
                r.relation,
                type(r)
            ) AS relationship,
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

    def clear_graph(self):
        query = """
        MATCH (n)
        DETACH DELETE n
        """

        with self.driver.session() as session:
            session.run(query).consume()

    def ensure_kg_constraints(self):
        query = """
        CREATE CONSTRAINT kg_entity_id IF NOT EXISTS
        FOR (n:KGEntity)
        REQUIRE n.id IS UNIQUE
        """

        with self.driver.session() as session:
            session.run(query).consume()

    def upsert_kg_nodes(self, rows: list[dict]):
        query = """
        UNWIND $rows AS row

        MERGE (n:KGEntity {id: row.id})

        SET n.name = row.name,
            n.categories = row.categories,
            n.aliases = row.aliases,
            n.providedBy = row.providedBy

        SET n += row.properties

        RETURN count(n) AS count
        """

        with self.driver.session() as session:
            result = session.run(query, rows=rows)
            record = result.single()
            return record["count"] if record else 0

    def upsert_kg_edges(self, rows: list[dict]):
        query = """
        UNWIND $rows AS row

        MATCH (source:KGEntity {id: row.subject})
        MATCH (target:KGEntity {id: row.object})

        MERGE (source)-[r:KG_RELATION {
            edgeKey: row.edgeKey
        }]->(target)

        SET r.predicate = row.predicate,
            r.relation = row.relation,
            r.providedBy = row.providedBy

        SET r += row.properties

        RETURN count(r) AS count
        """

        with self.driver.session() as session:
            result = session.run(query, rows=rows)
            record = result.single()
            return record["count"] if record else 0