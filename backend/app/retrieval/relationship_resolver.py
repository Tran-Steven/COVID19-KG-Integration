import re

from spacy.language import Language

from app.database import Neo4jClient


class RelationshipResolver:
    RELATION_ALIASES = {
        "biolink:treats": [
            "treat",
            "treatment",
            "therapy",
            "therapeutic indication",
        ],
        "biolink:studied_to_treat": [
            "study",
            "studied",
            "study to treat",
            "studied to treat",
            "investigate",
            "investigated",
            "experimental treatment",
        ],
        "biolink:in_clinical_trials_for": [
            "clinical trial",
            "clinical trials",
            "trial",
            "trials",
            "tested in clinical trials",
        ],
        "biolink:has_phenotype": [
            "phenotype",
            "symptom",
            "symptoms",
            "sign",
            "signs",
            "manifestation",
        ],
        "biolink:model_of": [
            "model",
            "model of",
            "disease model",
        ],
        "biolink:related_to": [
            "relate",
            "related",
            "related to",
            "associate",
            "associated",
            "associated with",
            "association",
            "linked",
            "linked to",
        ],
        "biolink:subclass_of": [
            "subclass",
            "subclass of",
            "subtype",
            "type",
            "type of",
            "kind of",
            "form of",
        ],
    }

    def __init__(
        self,
        database: Neo4jClient,
        nlp: Language,
    ):
        self.database = database
        self.nlp = nlp

    def resolve(
        self,
        relation: str | None,
        limit: int = 5,
    ):
        if not relation:
            return []

        query_relation = self._normalize(
            relation
        )

        relationship_types = (
            self.database
            .get_relationship_types()
        )

        candidates = []

        for relationship_type in relationship_types:
            normalized_relationship = (
                self._normalize(
                    relationship_type
                )
            )

            score = self._relationship_score(
                query_relation,
                relationship_type,
                normalized_relationship,
            )

            if score > 0:
                candidates.append(
                    {
                        "relationship": relationship_type,
                        "normalized": normalized_relationship,
                        "score": score,
                    }
                )

        candidates.sort(
            key=lambda candidate: candidate["score"],
            reverse=True,
        )

        return candidates[:limit]

    def _relationship_score(
        self,
        query: str,
        relationship_type: str,
        normalized_relationship: str,
    ):
        scores = [
            self._score(
                query,
                normalized_relationship,
            )
        ]

        aliases = self.RELATION_ALIASES.get(
            relationship_type,
            [],
        )

        for alias in aliases:
            scores.append(
                self._score(
                    query,
                    self._normalize(alias),
                )
            )

        return max(scores)

    def _normalize(
        self,
        text: str,
    ):
        text = text.strip()

        if ":" in text and " " not in text:
            text = text.split(
                ":",
                1,
            )[1]

        text = re.sub(
            r"[_-]+",
            " ",
            text.lower(),
        )

        text = re.sub(
            r"[^a-z0-9\s]+",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        doc = self.nlp(text)

        return " ".join(
            token.lemma_.lower()
            for token in doc
            if not token.is_space
        )

    def _score(
        self,
        query: str,
        candidate: str,
    ):
        if query == candidate:
            return 1.0

        query_tokens = set(
            query.split()
        )

        candidate_tokens = set(
            candidate.split()
        )

        if (
            not query_tokens
            or not candidate_tokens
        ):
            return 0.0

        intersection = (
            query_tokens
            & candidate_tokens
        )

        union = (
            query_tokens
            | candidate_tokens
        )

        token_score = (
            len(intersection)
            / len(union)
        )

        if (
            query in candidate
            or candidate in query
        ):
            return max(
                token_score,
                0.8,
            )

        return token_score