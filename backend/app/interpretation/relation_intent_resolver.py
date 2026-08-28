import re


class RelationIntentResolver:
    RULES = [
        {
            "intent": "risk_modifier",
            "direction": "increase",
            "specific": True,
            "phrases": [
                "increase risk",
                "increases risk",
                "increased risk",
                "raise risk",
                "raises risk",
                "higher risk",
                "more likely",
                "make covid worse",
                "makes covid worse",
                "make covid 19 worse",
                "makes covid 19 worse",
                "worsen covid",
                "worsens covid",
                "worsen covid 19",
                "worsens covid 19",
                "more severe",
                "increase severity",
                "increases severity",
            ],
        },
        {
            "intent": "risk_modifier",
            "direction": "decrease",
            "specific": True,
            "phrases": [
                "decrease risk",
                "decreases risk",
                "decreased risk",
                "lower risk",
                "lowers risk",
                "reduced risk",
                "reduce risk",
                "reduces risk",
                "less likely",
                "protect against",
                "protects against",
                "protect from",
                "protects from",
                "make covid less severe",
                "makes covid less severe",
                "make covid 19 less severe",
                "makes covid 19 less severe",
                "less severe",
                "decrease severity",
                "decreases severity",
                "reduce severity",
                "reduces severity",
            ],
        },
        {
            "intent": "treatment",
            "direction": None,
            "specific": True,
            "phrases": [
                "used to treat",
                "used for treating",
                "treat",
                "treats",
                "treated by",
                "treatment",
                "therapy",
                "therapeutic",
                "help with",
                "helps with",
            ],
        },
        {
            "intent": "causation",
            "direction": None,
            "specific": True,
            "phrases": [
                "cause",
                "causes",
                "caused by",
                "lead to",
                "leads to",
                "result in",
                "results in",
                "responsible for",
            ],
        },
        {
            "intent": "association",
            "direction": None,
            "specific": True,
            "phrases": [
                "associated with",
                "association with",
                "related to",
                "linked to",
                "correlated with",
                "correlate with",
                "connected to",
                "connection with",
            ],
        },
        {
            "intent": "clinical_study",
            "direction": None,
            "specific": True,
            "phrases": [
                "clinical trial",
                "clinical trials",
                "studied for",
                "studied to treat",
                "investigated for",
                "tested for",
            ],
        },
        {
            "intent": "phenotype",
            "direction": None,
            "specific": True,
            "phrases": [
                "symptom of",
                "symptoms of",
                "sign of",
                "signs of",
                "phenotype of",
                "manifestation of",
            ],
        },
        {
            "intent": "broad_effect",
            "direction": None,
            "specific": False,
            "phrases": [
                "affect",
                "affects",
                "affected by",
                "impact",
                "impacts",
                "influence",
                "influences",
                "change",
                "changes",
            ],
        },
    ]

    def resolve(
        self,
        text: str,
        extracted_relation: str | None,
    ):
        normalized_text = self._normalize(text)

        matches = []

        for rule_index, rule in enumerate(self.RULES):
            for phrase in rule["phrases"]:
                normalized_phrase = self._normalize(phrase)

                position = self._find_phrase(
                    normalized_text,
                    normalized_phrase,
                )

                if position is None:
                    continue

                matches.append(
                    {
                        "intent": rule["intent"],
                        "direction": rule["direction"],
                        "matchedText": phrase,
                        "specific": rule["specific"],
                        "position": position,
                        "phraseLength": len(normalized_phrase),
                        "ruleIndex": rule_index,
                    }
                )

        if matches:
            matches.sort(
                key=lambda match: (
                    -match["phraseLength"],
                    match["position"],
                    match["ruleIndex"],
                )
            )

            best = matches[0]

            return {
                "intent": best["intent"],
                "direction": best["direction"],
                "matchedText": best["matchedText"],
                "specific": best["specific"],
            }

        if extracted_relation:
            normalized_relation = self._normalize(extracted_relation)

            for rule in self.RULES:
                for phrase in rule["phrases"]:
                    if normalized_relation == self._normalize(phrase):
                        return {
                            "intent": rule["intent"],
                            "direction": rule["direction"],
                            "matchedText": (extracted_relation),
                            "specific": rule["specific"],
                        }

        return {
            "intent": "unknown",
            "direction": None,
            "matchedText": (extracted_relation),
            "specific": False,
        }

    def _normalize(
        self,
        text: str,
    ):
        text = text.lower()

        text = re.sub(
            r"[-_/]+",
            " ",
            text,
        )

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
