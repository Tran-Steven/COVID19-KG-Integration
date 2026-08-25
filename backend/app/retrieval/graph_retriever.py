from app.database import Neo4jClient
from app.nlp.entity_linker import EntityLinker
from app.retrieval.evidence_normalizer import EvidenceNormalizer
from app.retrieval.relationship_resolver import RelationshipResolver


class GraphRetriever:
    def __init__(
        self,
        database: Neo4jClient,
        entity_linker: EntityLinker,
        relationship_resolver: RelationshipResolver,
    ):
        self.database = database
        self.entity_linker = entity_linker
        self.relationship_resolver = (
            relationship_resolver
        )
        self.evidence_normalizer = (
            EvidenceNormalizer()
        )

    def retrieve(
        self,
        entities: list[dict],
        relation: str | None,
    ):
        linked_entities = []

        for entity in entities:
            candidates = (
                self.entity_linker.link(
                    entity["text"]
                )
            )

            linked_entities.append(
                {
                    **entity,
                    "candidates": candidates,
                }
            )

        relationship_candidates = (
            self.relationship_resolver.resolve(
                relation
            )
        )

        if (
            not linked_entities
            or not relationship_candidates
        ):
            return {
                "entities": linked_entities,
                "relationships": (
                    relationship_candidates
                ),
                "facts": [],
            }

        best_relationship = (
            relationship_candidates[0][
                "relationship"
            ]
        )

        entities_with_candidates = [
            entity
            for entity in linked_entities
            if entity["candidates"]
        ]

        if not entities_with_candidates:
            return {
                "entities": linked_entities,
                "relationships": (
                    relationship_candidates
                ),
                "facts": [],
            }

        if len(
            entities_with_candidates
        ) >= 2:
            raw_facts = (
                self._retrieve_between_entities(
                    entities_with_candidates,
                    best_relationship,
                )
            )
        else:
            raw_facts = (
                self._retrieve_from_entity(
                    entities_with_candidates[0],
                    best_relationship,
                )
            )

        facts = [
            self.evidence_normalizer
            .normalize_fact(fact)
            for fact in raw_facts
        ]

        return {
            "entities": linked_entities,
            "relationships": (
                relationship_candidates
            ),
            "facts": facts,
        }

    def _retrieve_from_entity(
        self,
        entity: dict,
        relationship: str,
    ):
        best_candidate = (
            entity["candidates"][0]
        )

        return (
            self.database
            .find_related_facts(
                entity_id=best_candidate[
                    "id"
                ],
                relationship=relationship,
            )
        )

    def _retrieve_between_entities(
        self,
        entities: list[dict],
        relationship: str,
    ):
        source_candidates = (
            entities[0]["candidates"]
        )

        target_candidates = (
            entities[1]["candidates"]
        )

        facts = []

        for source in source_candidates:
            for target in target_candidates:
                result = (
                    self.database
                    .find_relationship_between_entities(
                        source_id=source[
                            "id"
                        ],
                        target_id=target[
                            "id"
                        ],
                        relationship=relationship,
                    )
                )

                facts.extend(
                    result
                )

                if facts:
                    return facts

        return facts