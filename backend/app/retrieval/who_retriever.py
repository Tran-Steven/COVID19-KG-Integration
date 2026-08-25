from app.database import Neo4jClient
from app.interpretation.who_intent_resolver import (
    WhoIntentResolver,
)
from app.retrieval.evidence_normalizer import (
    EvidenceNormalizer,
)


class WhoRetriever:
    def __init__(
        self,
        database: Neo4jClient,
        intent_resolver: WhoIntentResolver,
    ):
        self.database = database
        self.intent_resolver = intent_resolver

        self.evidence_normalizer = (
            EvidenceNormalizer()
        )

    def retrieve(
        self,
        text: str,
        interpretation: dict | None = None,
    ):
        interpretation = (
            interpretation
            or self.intent_resolver.resolve(
                text
            )
        )

        if interpretation is None:
            return None

        raw_facts = (
            self.database
            .find_semantic_facts(
                semantic_roles=interpretation[
                    "semanticRoles"
                ],
                subject_ids=interpretation[
                    "subjectIds"
                ],
                object_ids=interpretation[
                    "objectIds"
                ],
            )
        )

        facts = [
            self.evidence_normalizer
            .normalize_fact(
                fact
            )
            for fact in raw_facts
        ]

        relationships = [
            {
                "relationship": role,
                "normalized": role.replace(
                    "_",
                    " ",
                ),
                "score": 1.0,
            }
            for role
            in interpretation[
                "semanticRoles"
            ]
        ]

        return {
            "interpretation": interpretation,
            "relationships": relationships,
            "facts": facts,
        }