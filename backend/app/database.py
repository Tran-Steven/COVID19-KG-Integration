import os

from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv(
                "NEO4J_URI",
                "bolt://neo4j:7687",
            ),
            auth=(
                os.getenv(
                    "NEO4J_USERNAME",
                    "neo4j",
                ),
                os.getenv(
                    "NEO4J_PASSWORD",
                    "cvkgdemo",
                ),
            ),
        )

    def close(self):
        self.driver.close()

    def get_entity_terms(self):
        query = """
        MATCH (n:KGEntity)

        WHERE NOT any(
            category IN coalesce(
                n.categories,
                []
            )
            WHERE category IN [
                "biolink:Event",
                "biolink:InformationContentEntity"
            ]
        )

        RETURN
            n.id AS id,
            n.name AS name,
            coalesce(
                n.aliases,
                []
            ) AS aliases

        ORDER BY n.id
        """

        with self.driver.session() as session:
            result = session.run(query)

            return [record.data() for record in result]

    def get_entity_context(
        self,
        entity: str,
    ):
        query = """
        MATCH (n:KGEntity)

        WHERE toLower(n.name) = toLower($entity)

        OPTIONAL MATCH
            (n)-[r:KG_RELATION]-(connected:KGEntity)

        RETURN
            n.id AS entityId,
            n.name AS entity,
            coalesce(
                n.categories,
                []
            ) AS entityCategories,
            coalesce(
                r.semantic_role,
                r.predicate,
                r.relation
            ) AS relationship,
            connected.id AS connectedEntityId,
            connected.name AS connectedEntity,
            coalesce(
                connected.categories,
                []
            ) AS connectedCategories
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                entity=entity,
            )

            return [record.data() for record in result]

    def find_history_events(
        self,
        event_type: str,
        limit: int = 10,
    ):
        query = """
        MATCH (event:KGEntity)

        WHERE event.event_type = $eventType

        RETURN
            event.id AS eventId,
            event.name AS eventName,
            event.event_type AS eventType,
            event.event_date_start AS dateStart,
            event.event_date_end AS dateEnd,
            event.source_text AS sourceText,
            event.source_url AS sourceUrl,
            event.source_links AS sourceLinks,
            null AS semanticRole,
            null AS relatedEntityId,
            null AS relatedEntityName,
            [] AS relatedEntityCategories

        ORDER BY
            event.event_date_start,
            event.id

        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                eventType=event_type,
                limit=limit,
            )

            return [record.data() for record in result]

    def find_history_event_relations(
        self,
        event_type: str,
        semantic_role: str,
        limit: int = 10,
    ):
        query = """
        MATCH (event:KGEntity)
            -[r:KG_RELATION]->
            (related:KGEntity)

        WHERE event.event_type = $eventType
          AND r.semantic_role = $semanticRole

        RETURN
            event.id AS eventId,
            event.name AS eventName,
            event.event_type AS eventType,
            event.event_date_start AS dateStart,
            event.event_date_end AS dateEnd,
            event.source_text AS sourceText,
            event.source_url AS sourceUrl,
            event.source_links AS sourceLinks,
            r.semantic_role AS semanticRole,
            related.id AS relatedEntityId,
            related.name AS relatedEntityName,
            coalesce(
                related.categories,
                []
            ) AS relatedEntityCategories

        ORDER BY
            event.event_date_start,
            event.id,
            related.id

        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                eventType=event_type,
                semanticRole=semantic_role,
                limit=limit,
            )

            return [record.data() for record in result]

    def find_entity_candidates(
        self,
        entity: str,
        limit: int = 5,
    ):
        query = """
        MATCH (n:KGEntity)

        WHERE n.name IS NOT NULL
          AND NOT any(
              category IN coalesce(
                  n.categories,
                  []
              )
              WHERE category IN [
                  "biolink:Event",
                  "biolink:InformationContentEntity"
              ]
          )

        WITH n,
            CASE
                WHEN toLower(n.name) = toLower($entity)
                    THEN 1.0
                WHEN n.id IS NOT NULL
                    AND toLower(n.id) = toLower($entity)
                    THEN 1.0
                WHEN any(
                    alias IN coalesce(
                        n.aliases,
                        []
                    )
                    WHERE toLower(alias)
                        = toLower($entity)
                )
                    THEN 0.95
                WHEN toLower(n.name)
                    CONTAINS toLower($entity)
                    THEN 0.75
                WHEN toLower($entity)
                    CONTAINS toLower(n.name)
                    THEN 0.70
                ELSE 0.0
            END AS score

        WHERE score > 0

        RETURN
            n.id AS id,
            coalesce(
                n.categories,
                []
            ) AS categories,
            n.name AS name,
            coalesce(
                n.aliases,
                []
            ) AS aliases,
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
        MATCH ()-[r:KG_RELATION]->()

        WITH DISTINCT
            r.predicate AS relationship

        WHERE relationship IS NOT NULL

        RETURN relationship
        ORDER BY relationship
        """

        with self.driver.session() as session:
            result = session.run(query)

            return [record["relationship"] for record in result]

    def find_related_facts(
        self,
        entity_id: str,
        relationship: str,
        limit: int = 20,
    ):
        query = """
        MATCH (entity:KGEntity {
            id: $entityId
        })

        CALL {
            WITH entity

            MATCH
                (entity)
                -[r:KG_RELATION]->
                (target:KGEntity)

            WHERE r.predicate = $relationship
               OR r.relation = $relationship

            RETURN
                entity AS subject,
                r,
                target AS object

            UNION ALL

            WITH entity

            MATCH
                (subject:KGEntity)
                -[r:KG_RELATION]->
                (entity)

            WHERE r.predicate = $relationship
               OR r.relation = $relationship

            RETURN
                subject,
                r,
                entity AS object
        }

        RETURN
            subject.id AS subjectId,
            subject.name AS subject,
            coalesce(
                subject.categories,
                []
            ) AS subjectCategories,
            r.predicate AS predicate,
            object.id AS objectId,
            object.name AS object,
            coalesce(
                object.categories,
                []
            ) AS objectCategories,
            properties(r)
                AS relationshipProperties

        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                entityId=entity_id,
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
        MATCH (first:KGEntity {
            id: $sourceId
        })

        MATCH (second:KGEntity {
            id: $targetId
        })

        CALL {
            WITH first, second

            MATCH
                (first)
                -[r:KG_RELATION]->
                (second)

            WHERE r.predicate = $relationship
               OR r.relation = $relationship

            RETURN
                first AS subject,
                r,
                second AS object

            UNION ALL

            WITH first, second

            MATCH
                (second)
                -[r:KG_RELATION]->
                (first)

            WHERE r.predicate = $relationship
               OR r.relation = $relationship

            RETURN
                second AS subject,
                r,
                first AS object
        }

        RETURN
            subject.id AS subjectId,
            subject.name AS subject,
            coalesce(
                subject.categories,
                []
            ) AS subjectCategories,
            r.predicate AS predicate,
            object.id AS objectId,
            object.name AS object,
            coalesce(
                object.categories,
                []
            ) AS objectCategories,
            properties(r)
                AS relationshipProperties

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

    def find_semantic_facts(
        self,
        semantic_roles: list[str],
        subject_ids: list[str] | None = None,
        object_ids: list[str] | None = None,
        limit: int = 50,
    ):
        query = """
        MATCH
            (subject:KGEntity)
            -[r:KG_RELATION]->
            (object:KGEntity)

        WHERE r.semantic_role IN $semanticRoles
          AND (
              size($subjectIds) = 0
              OR subject.id IN $subjectIds
          )
          AND (
              size($objectIds) = 0
              OR object.id IN $objectIds
          )

        RETURN
            subject.id AS subjectId,
            subject.name AS subject,
            coalesce(
                subject.categories,
                []
            ) AS subjectCategories,
            r.semantic_role AS predicate,
            object.id AS objectId,
            object.name AS object,
            coalesce(
                object.categories,
                []
            ) AS objectCategories,
            properties(r)
                AS relationshipProperties

        ORDER BY
            r.semantic_role,
            coalesce(
                r.source_date,
                ""
            ) DESC,
            subject.id,
            object.id,
            r.id

        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                semanticRoles=semantic_roles,
                subjectIds=(subject_ids or []),
                objectIds=(object_ids or []),
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
        CREATE CONSTRAINT
            kg_entity_id
            IF NOT EXISTS

        FOR (n:KGEntity)

        REQUIRE n.id IS UNIQUE
        """

        with self.driver.session() as session:
            session.run(query).consume()

    def upsert_kg_nodes(
        self,
        rows: list[dict],
    ):
        query = """
        UNWIND $rows AS row

        MERGE (n:KGEntity {
            id: row.id
        })

        SET
            n.name = row.name,
            n.categories = row.categories,
            n.aliases = row.aliases,
            n.providedBy = row.providedBy

        SET n += row.properties

        RETURN count(n) AS count
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                rows=rows,
            )

            record = result.single()

            return record["count"] if record else 0

    def upsert_kg_edges(
        self,
        rows: list[dict],
    ):
        query = """
        UNWIND $rows AS row

        MATCH (source:KGEntity {
            id: row.subject
        })

        MATCH (target:KGEntity {
            id: row.object
        })

        MERGE
            (source)
            -[r:KG_RELATION {
                edgeKey: row.edgeKey
            }]->
            (target)

        SET
            r.id = row.id,
            r.predicate = row.predicate,
            r.relation = row.relation,
            r.providedBy = row.providedBy

        SET r += row.properties

        RETURN count(r) AS count
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                rows=rows,
            )

            record = result.single()

            return record["count"] if record else 0
