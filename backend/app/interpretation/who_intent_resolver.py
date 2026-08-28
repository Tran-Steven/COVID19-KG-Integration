from app.interpretation.proposition_semantics import (
    PropositionSemantics,
)
from app.interpretation.who_intent_resolver_base import (
    WhoIntentResolver as BaseWhoIntentResolver,
)


class WhoIntentResolver(BaseWhoIntentResolver):
    def __init__(
        self,
    ):
        self.semantics = PropositionSemantics()

    def resolve(
        self,
        text: str,
    ):
        result = super().resolve(text)

        if not result:
            return result

        if result.get("intent") == "transmission":
            normalized = self._normalize(text)

            route_language = any(
                value in normalized
                for value in (
                    "through the air",
                    "respiratory particle",
                    "respiratory particles",
                    "aerosol",
                    "aerosols",
                    "droplet",
                    "droplets",
                )
            )

            context_language = any(
                value in normalized
                for value in (
                    "close contact",
                    "close or prolonged",
                    "prolonged contact",
                    "indoor",
                    "indoors",
                    "poorly ventilated",
                    "closed space",
                    "shared indoor",
                )
            )

            if route_language and context_language:
                result["semanticRoles"] = [
                    "transmitted_via",
                    "transmission_risk_context",
                ]

                result["objectIds"] = []

        return result

    def _origin_query(
        self,
        text: str,
    ):
        if super()._origin_query(text):
            return True

        return any(
            value in text
            for value in (
                "laboratory associated origin",
                "laboratory associated event",
                "lab associated origin",
                "lab associated event",
                "laboratory related origin",
                "laboratory related event",
                "lab related origin",
                "lab related event",
                "origin remains unresolved",
                "origin remains uncertain",
                "origin remains inconclusive",
                "precise origin",
                "exact origin",
                "zoonotic spillover",
            )
        )

    def _variant_query(
        self,
        text: str,
        raw_text: str,
    ):
        if super()._variant_query(
            text,
            raw_text,
        ):
            return True

        variant_reference = (
            self._has_variant_identifier(raw_text)
            or "variant" in text
            or "lineage" in text
        )

        surveillance = any(
            value in text
            for value in (
                "surveillance",
                "under surveillance",
                "surveilled",
                "continues surveillance",
            )
        )

        comparative_risk = "risk" in text and any(
            value in text
            for value in (
                "additional",
                "compared with",
                "compared to",
                "relative to",
                "greater",
                "higher",
                "lower",
                "increased",
                "reduced",
                "other circulating",
            )
        )

        return variant_reference and (surveillance or comparative_risk)

    def _cause_query(
        self,
        text: str,
    ):
        if super()._cause_query(text):
            return True

        incapacity = any(
            value in text
            for value in (
                "incapable of",
                "unable to",
            )
        )

        causal_action = any(
            value in text
            for value in (
                "produce",
                "producing",
                "cause",
                "causing",
                "give rise to",
                "giving rise to",
            )
        )

        return incapacity and causal_action and self._covid_context(text)

    def _non_covid_vaccine_context(
        self,
        text: str,
    ):
        if self.semantics.is_non_covid_vaccine(text):
            return True

        return super()._non_covid_vaccine_context(text)
