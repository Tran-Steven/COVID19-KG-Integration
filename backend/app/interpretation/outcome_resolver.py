import re


class OutcomeResolver:
    OUTCOME_ALIASES = {
        "infection": [
            "infection",
            "infected",
            "become infected",
            "getting infected",
            "get covid",
            "getting covid",
            "catch covid",
            "catching covid",
            "contract covid",
            "contracting covid",
        ],
        "severity": [
            "severity",
            "severe covid",
            "severe disease",
            "severe illness",
            "serious illness",
            "seriously ill",
            "make covid worse",
            "covid worse",
            "worse",
        ],
        "hospitalization": [
            "hospitalization",
            "hospitalisation",
            "hospitalized",
            "hospitalised",
            "hospital admission",
            "hospital admissions",
            "admitted to hospital",
            "admitted to the hospital",
            "go to the hospital",
        ],
        "mortality": [
            "mortality",
            "death",
            "deaths",
            "die",
            "dying",
            "fatality",
            "fatalities",
            "fatal",
        ],
    }

    def resolve(
        self,
        text: str,
    ):
        normalized_text = self._normalize(
            text
        )

        matches = []

        for outcome, aliases in (
            self.OUTCOME_ALIASES.items()
        ):
            best_match = None

            for alias in aliases:
                normalized_alias = (
                    self._normalize(
                        alias
                    )
                )

                position = self._find_phrase(
                    normalized_text,
                    normalized_alias,
                )

                if position is None:
                    continue

                candidate = {
                    "outcome": outcome,
                    "matchedText": alias,
                    "position": position,
                }

                if (
                    best_match is None
                    or candidate["position"]
                    < best_match["position"]
                ):
                    best_match = candidate

            if best_match:
                matches.append(
                    best_match
                )

        matches.sort(
            key=lambda match: match[
                "position"
            ]
        )

        return [
            {
                "outcome": match["outcome"],
                "matchedText": match[
                    "matchedText"
                ],
            }
            for match in matches
        ]

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

    def _find_phrase(
        self,
        text: str,
        phrase: str,
    ):
        match = re.search(
            rf"\b{re.escape(phrase)}\b",
            text,
        )

        if not match:
            return None

        return match.start()