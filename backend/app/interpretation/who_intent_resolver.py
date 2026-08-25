import re


class WhoIntentResolver:
    COVID_ID = "MONDO:0100096"
    SARS_ID = "NCBITaxon:2697049"
    LONG_COVID_ID = "MONDO:0100320"

    VACCINATION_ID = (
        "covidkg:who:concept:"
        "covid-19-vaccination"
    )

    AIRBORNE_ID = (
        "covidkg:who:transmission:"
        "infectious-respiratory-particles"
    )

    SURFACE_ID = (
        "covidkg:who:transmission:"
        "contaminated-surface-contact-"
        "followed-by-touching-the-eyes-"
        "nose-or-mouth"
    )

    SEVERE_DISEASE_ID = (
        "covidkg:who:vaccine-outcome:"
        "severe-disease"
    )

    HOSPITALIZATION_ID = (
        "covidkg:who:vaccine-outcome:"
        "hospitalization"
    )

    DEATH_ID = (
        "covidkg:who:vaccine-outcome:"
        "death"
    )

    ORIGIN_STATUS_ID = (
        "covidkg:who:origin-status:"
        "origin-remains-inconclusive"
    )

    ZOONOTIC_ID = (
        "covidkg:who:origin-hypothesis:"
        "natural-zoonotic-spillover"
    )

    LAB_ID = (
        "covidkg:who:origin-hypothesis:"
        "accidental-laboratory-related-event"
    )

    COLD_CHAIN_ID = (
        "covidkg:who:origin-hypothesis:"
        "cold-chain-introduction-"
        "into-animal-markets"
    )

    DELIBERATE_ID = (
        "covidkg:who:origin-hypothesis:"
        "deliberate-laboratory-manipulation-"
        "followed-by-a-biosafety-breach"
    )

    def resolve(
        self,
        text: str,
    ):
        normalized = self._normalize(
            text
        )

        if self._origin_query(
            normalized
        ):
            return self._resolve_origin(
                normalized
            )

        if self._variant_query(
            normalized
        ):
            return self._resolve_variants(
                normalized
            )

        if self._vaccine_query(
            normalized
        ):
            object_ids = []

            if "severe" in normalized:
                object_ids.append(
                    self.SEVERE_DISEASE_ID
                )

            if "hospital" in normalized:
                object_ids.append(
                    self.HOSPITALIZATION_ID
                )

            if any(
                value in normalized
                for value in (
                    "death",
                    "die",
                    "mortality",
                )
            ):
                object_ids.append(
                    self.DEATH_ID
                )

            return {
                "intent": (
                    "vaccine_protection"
                ),
                "semanticRoles": [
                    "protects_against"
                ],
                "subjectIds": [
                    self.VACCINATION_ID
                ],
                "objectIds": object_ids,
                "matchedText": (
                    self._first_match(
                        normalized,
                        [
                            "covid vaccine",
                            "covid 19 vaccine",
                            "covid vaccination",
                            "covid 19 vaccination",
                            "vaccination against covid",
                            "vaccine against covid",
                        ],
                    )
                ),
                "method": "rule",
            }

        if self._long_covid_query(
            normalized
        ):
            return {
                "intent": (
                    "long_covid_outcome"
                ),
                "semanticRoles": [
                    (
                        "can_lead_to_"
                        "post_covid_condition"
                    )
                ],
                "subjectIds": [
                    self.COVID_ID
                ],
                "objectIds": [
                    self.LONG_COVID_ID
                ],
                "matchedText": (
                    self._first_match(
                        normalized,
                        [
                            "long covid",
                            "post covid condition",
                            "post covid effects",
                            "post covid effect",
                            "post covid symptoms",
                            "long term post covid",
                        ],
                    )
                ),
                "method": "rule",
            }

        if self._transmission_query(
            normalized
        ):
            roles = [
                "transmitted_via"
            ]

            object_ids = []

            if any(
                phrase in normalized
                for phrase in (
                    "airborne",
                    "through the air",
                    "respiratory particles",
                    "respiratory particle",
                    "aerosol",
                    "aerosols",
                )
            ):
                object_ids = [
                    self.AIRBORNE_ID
                ]

            elif any(
                phrase in normalized
                for phrase in (
                    "surface",
                    "surfaces",
                    "contaminated surface",
                )
            ):
                object_ids = [
                    self.SURFACE_ID
                ]

            else:
                roles.append(
                    (
                        "transmission_"
                        "risk_context"
                    )
                )

            return {
                "intent": "transmission",
                "semanticRoles": roles,
                "subjectIds": [
                    self.SARS_ID
                ],
                "objectIds": object_ids,
                "matchedText": (
                    self._first_match(
                        normalized,
                        [
                            "airborne",
                            "through the air",
                            "respiratory particles",
                            "aerosol",
                            "surface",
                            "surfaces",
                            "spread",
                            "transmit",
                            "transmission",
                            "catch",
                            "close contact",
                            "indoor",
                        ],
                    )
                ),
                "method": "rule",
            }

        if self._cause_query(
            normalized
        ):
            return {
                "intent": "cause",
                "semanticRoles": [
                    "causes"
                ],
                "subjectIds": [
                    self.SARS_ID
                ],
                "objectIds": [
                    self.COVID_ID
                ],
                "matchedText": (
                    self._first_match(
                        normalized,
                        [
                            "caused by",
                            "cause",
                            "responsible for",
                            "results from infection with",
                            "result from infection with",
                            "due to infection with",
                            "infection with",
                        ],
                    )
                ),
                "method": "rule",
            }

        if self._current_risk_query(
            normalized
        ):
            return {
                "intent": (
                    "current_global_risk"
                ),
                "semanticRoles": [
                    (
                        "global_public_health_"
                        "risk_level"
                    )
                ],
                "subjectIds": [
                    self.COVID_ID
                ],
                "objectIds": [],
                "matchedText": "risk",
                "method": "rule",
            }

        return None

    def _resolve_origin(
        self,
        text: str,
    ):
        object_ids = []

        if any(
            phrase in text
            for phrase in (
                "man made",
                "manmade",
                "engineered",
                "deliberate",
                "artificial",
                "created in a lab",
                "laboratory manipulation",
                "lab manipulation",
                "biosafety breach",
            )
        ):
            object_ids = [
                self.DELIBERATE_ID,
                self.ORIGIN_STATUS_ID,
            ]

        elif any(
            phrase in text
            for phrase in (
                "lab leak",
                "laboratory",
                "lab origin",
                "from a lab",
                "laboratory related",
                "lab related",
            )
        ):
            object_ids = [
                self.LAB_ID,
                self.ORIGIN_STATUS_ID,
            ]

        elif any(
            phrase in text
            for phrase in (
                "zoonotic",
                "animal origin",
                "from animals",
                "natural origin",
                "natural spillover",
                "zoonotic spillover",
            )
        ):
            object_ids = [
                self.ZOONOTIC_ID,
                self.ORIGIN_STATUS_ID,
            ]

        elif "cold chain" in text:
            object_ids = [
                self.COLD_CHAIN_ID,
                self.ORIGIN_STATUS_ID,
            ]

        return {
            "intent": "origin",
            "semanticRoles": [
                (
                    "origin_hypothesis_"
                    "assessment"
                ),
                "overall_origin_status",
            ],
            "subjectIds": [
                self.SARS_ID
            ],
            "objectIds": object_ids,
            "matchedText": (
                self._first_match(
                    text,
                    [
                        "origin",
                        "man made",
                        "manmade",
                        "engineered",
                        "lab leak",
                        "laboratory",
                        "zoonotic",
                        "natural spillover",
                        "cold chain",
                        "laboratory manipulation",
                        "biosafety breach",
                    ],
                )
            ),
            "method": "rule",
        }

    def _resolve_variants(
        self,
        text: str,
    ):
        if any(
            value in text
            for value in (
                "monitor",
                "monitoring",
                "under monitoring",
            )
        ):
            roles = [
                (
                    "variant_under_"
                    "monitoring"
                )
            ]

        elif any(
            value in text
            for value in (
                "variant of interest",
                "variants of interest",
                "voi",
            )
        ):
            roles = [
                "variant_of_interest"
            ]

        else:
            roles = [
                "variant_of_interest",
                (
                    "variant_under_"
                    "monitoring"
                ),
            ]

        return {
            "intent": "variants",
            "semanticRoles": roles,
            "subjectIds": [
                self.SARS_ID
            ],
            "objectIds": [],
            "matchedText": "variant",
            "method": "rule",
        }

    def _origin_query(
        self,
        text: str,
    ):
        origin_language = any(
            phrase in text
            for phrase in (
                "origin",
                "originate",
                "originated",
                "man made",
                "manmade",
                "engineered",
                "created in a lab",
                "lab leak",
                "lab origin",
                "from a lab",
                "laboratory origin",
                "laboratory related",
                "lab related",
                "laboratory manipulation",
                "lab manipulation",
                "deliberate laboratory",
                "biosafety breach",
                "zoonotic",
                "animal origin",
                "from animals",
                "natural origin",
                "natural spillover",
                "zoonotic spillover",
                "cold chain",
            )
        )

        return (
            origin_language
            and self._covid_context(
                text
            )
        )

    def _variant_query(
        self,
        text: str,
    ):
        return (
            "variant" in text
            and (
                self._covid_context(
                    text
                )
                or "monitor" in text
                or "interest" in text
                or "current" in text
            )
        )

    def _vaccine_query(
        self,
        text: str,
    ):
        vaccine = any(
            value in text
            for value in (
                "vaccine",
                "vaccination",
                "vaccinated",
            )
        )

        outcome = any(
            value in text
            for value in (
                "protect",
                "prevent",
                "reduce",
                "lower",
                "severe",
                "hospital",
                "death",
                "die",
                "mortality",
            )
        )

        return (
            vaccine
            and outcome
            and self._covid_vaccine_context(
                text
            )
            and not self._non_covid_vaccine_context(
                text
            )
        )

    def _covid_vaccine_context(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "covid vaccine",
                "covid 19 vaccine",
                "covid vaccination",
                "covid 19 vaccination",
                "covid vaccinated",
                "covid 19 vaccinated",
                "vaccine against covid",
                "vaccines against covid",
                "vaccination against covid",
                "vaccinated against covid",
            )
        )

    def _non_covid_vaccine_context(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "flu vaccine",
                "flu vaccines",
                "flu vaccination",
                "influenza vaccine",
                "influenza vaccines",
                "influenza vaccination",
                "measles vaccine",
                "measles vaccines",
                "measles vaccination",
                "polio vaccine",
                "polio vaccines",
                "polio vaccination",
            )
        )

    def _long_covid_query(
        self,
        text: str,
    ):
        long_covid = any(
            value in text
            for value in (
                "long covid",
                "post covid condition",
                "post covid effects",
                "post covid effect",
                "post covid symptoms",
                "long term post covid",
                "long term covid effects",
            )
        )

        relation = any(
            value in text
            for value in (
                "lead to",
                "cause",
                "result in",
                "develop",
                "get ",
                "follow",
                "following",
                "after",
            )
        )

        return (
            long_covid
            and relation
            and self._covid_context(
                text
            )
        )

    def _transmission_query(
        self,
        text: str,
    ):
        if not self._covid_context(
            text
        ):
            return False

        direct_relation = any(
            value in text
            for value in (
                "spread",
                "transmit",
                "transmission",
                "airborne",
                "through the air",
                "respiratory particle",
                "aerosol",
                "surface",
                "surfaces",
            )
        )

        risk_context = (
            "catch" in text
            and any(
                value in text
                for value in (
                    "indoor",
                    "indoors",
                    "shared space",
                    "shared spaces",
                    "close contact",
                    "crowded",
                    "ventilation",
                )
            )
        )

        return (
            direct_relation
            or risk_context
        )

    def _cause_query(
        self,
        text: str,
    ):
        if not self._covid_context(
            text
        ):
            return False

        causal_language = any(
            value in text
            for value in (
                "cause",
                "caused by",
                "responsible for",
                "results from infection with",
                "result from infection with",
                "due to infection with",
                "caused by infection with",
            )
        )

        sars_reference = any(
            value in text
            for value in (
                "sars cov 2",
                (
                    "severe acute respiratory "
                    "syndrome coronavirus 2"
                ),
            )
        )

        if (
            causal_language
            and sars_reference
        ):
            return True

        generic_patterns = (
            "what causes covid",
            "what cause covid",
            "what is covid caused by",
            "what causes coronavirus disease 2019",
            (
                "what is coronavirus disease "
                "2019 caused by"
            ),
            "which virus causes covid",
            "what virus causes covid",
            "virus that causes covid",
            "cause of covid",
            "which virus is responsible for covid",
            "what virus is responsible for covid",
            "virus responsible for covid",
        )

        if any(
            pattern in text
            for pattern
            in generic_patterns
        ):
            return True

        if any(
            value in text
            for value in (
                "covid is caused by",
                "covid 19 is caused by",
                "covid caused by",
                "covid 19 caused by",
            )
        ):
            return True

        return False

    def _current_risk_query(
        self,
        text: str,
    ):
        return (
            "risk" in text
            and any(
                value in text
                for value in (
                    "current",
                    "global",
                    "right now",
                    "today",
                    "now",
                )
            )
            and self._covid_context(
                text
            )
        )

    def _covid_context(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "covid",
                (
                    "coronavirus disease "
                    "2019"
                ),
                "sars cov 2",
                "chinese virus",
            )
        )

    def _normalize(
        self,
        text: str,
    ):
        text = text.lower()

        text = re.sub(
            r"[_/\-]+",
            " ",
            text,
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

        return text

    def _first_match(
        self,
        text: str,
        values: list[str],
    ):
        for value in values:
            if value in text:
                return value

        return None