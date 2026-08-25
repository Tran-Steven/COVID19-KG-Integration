import re


class AmbiguityDetector:
    OUTCOME_TERMS = {
        "chance": [
            "infection",
            "severity",
            "hospitalization",
            "mortality",
        ],
        "chances": [
            "infection",
            "severity",
            "hospitalization",
            "mortality",
        ],
        "risk": [
            "infection",
            "severity",
            "hospitalization",
            "mortality",
        ],
        "odds": [
            "infection",
            "severity",
            "hospitalization",
            "mortality",
        ],
        "outcome": [
            "severity",
            "hospitalization",
            "mortality",
        ],
        "outcomes": [
            "severity",
            "hospitalization",
            "mortality",
        ],
    }

    BROAD_RELATIONS = {
        "affect",
        "impact",
        "influence",
        "change",
    }

    def detect(
        self,
        text: str,
        relation: str | None,
    ):
        normalized_text = self._normalize(
            text
        )

        ambiguities = []

        for term, possibilities in (
            self.OUTCOME_TERMS.items()
        ):
            if self._contains_term(
                normalized_text,
                term,
            ):
                ambiguities.append(
                    {
                        "term": term,
                        "type": "outcome",
                        "possibleInterpretations": (
                            possibilities
                        ),
                    }
                )

        normalized_relation = (
            self._normalize(
                relation
            )
            if relation
            else None
        )

        broad_relation = (
            normalized_relation
            in self.BROAD_RELATIONS
        )

        return {
            "ambiguous": bool(
                ambiguities
            ),
            "broadRelation": broad_relation,
            "ambiguities": ambiguities,
        }

    def _normalize(
        self,
        text: str,
    ):
        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    def _contains_term(
        self,
        text: str,
        term: str,
    ):
        return bool(
            re.search(
                rf"\b{re.escape(term)}\b",
                text,
            )
        )