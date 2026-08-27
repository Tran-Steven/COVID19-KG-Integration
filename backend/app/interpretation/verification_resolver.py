import re

from app.interpretation.proposition_guard import (
    PropositionGuard,
)
from app.interpretation.proposition_semantics import (
    PropositionSemantics,
)
from app.interpretation.verification_resolver_base import (
    VerificationResolver as BaseVerificationResolver,
)


class VerificationResolver(
    BaseVerificationResolver
):
    def __init__(
        self,
    ):
        super().__init__()

        self.semantics = (
            PropositionSemantics()
        )

        self.proposition_guard = (
            PropositionGuard()
        )

    def _who_result(
        self,
        text: str,
        entities: list[dict],
        facts: list[dict],
    ):
        if (
            self.semantics
            .is_no_additional_risk_claim(
                text
            )
        ):
            if (
                facts
                and self._facts_support_no_additional_risk(
                    facts
                )
            ):
                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "The claim matches WHO "
                        "evidence indicating no "
                        "additional public-health risk "
                        "for the referenced variant."
                    ),
                    evidence_count=len(
                        facts
                    ),
                    method="who_semantic",
                )

            return self._result(
                status=self.INSUFFICIENT_EVIDENCE,
                reason=(
                    "WHO variant evidence was retrieved, "
                    "but the current knowledge graph "
                    "does not contain evidence establishing "
                    "the claimed no-additional-risk "
                    "assessment."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        return super()._who_result(
            text=text,
            entities=entities,
            facts=facts,
        )

    def _origin_result(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(
            text
        )

        assessments = {
            self._assessment(
                fact
            )
            for fact in facts
            if self._assessment(
                fact
            )
        }

        overall_inconclusive = (
            "inconclusive_pending_additional_"
            "information_or_scientific_data"
            in assessments
        )

        lab_uncertain = (
            "cannot_be_ruled_out_or_"
            "proven_with_available_"
            "information"
            in assessments
        )

        zoonotic_supported = (
            "best_supported_by_available_"
            "scientific_data"
            in assessments
        )

        if (
            overall_inconclusive
            and self.semantics
            .is_origin_inconclusive(
                normalized
            )
        ):
            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "The claim matches WHO "
                    "SAGO's assessment that the "
                    "origin remains unresolved or "
                    "inconclusive."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        if (
            lab_uncertain
            and self.semantics
            .is_lab_uncertainty(
                normalized
            )
        ):
            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "The claim matches WHO "
                    "SAGO's assessment that a "
                    "laboratory-related event "
                    "cannot currently be ruled out "
                    "or proven with available "
                    "information."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        if (
            zoonotic_supported
            and any(
                value in normalized
                for value in (
                    "evidence favors zoonotic",
                    "evidence favours zoonotic",
                    "evidence favors an animal",
                    "evidence favours an animal",
                    "available evidence favors",
                    "available evidence favours",
                    "weight of available evidence favors",
                    "weight of available evidence favours",
                    "best supported",
                    "best supported scientific explanation",
                )
            )
            and not self.origin_qualifiers.is_certainty_overclaim(
                normalized
            )
        ):
            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "The claim matches WHO "
                    "SAGO's assessment that "
                    "zoonotic spillover is the "
                    "best-supported hypothesis "
                    "while the overall origin "
                    "remains unresolved."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        return super()._origin_result(
            text=text,
            facts=facts,
        )

    def _risk_result(
        self,
        text: str,
        facts: list[dict],
    ):
        claim_years = (
            self.semantics
            .explicit_years(
                text
            )
        )

        fact_years = (
            self._fact_source_years(
                facts
            )
        )

        if (
            claim_years
            and fact_years
            and not self.semantics
            .has_current_language(
                text
            )
            and max(
                claim_years
            )
            < max(
                fact_years
            )
        ):
            return self._result(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The claim refers to a "
                    "historical risk assessment, "
                    "while the retrieved WHO fact "
                    "represents a newer assessment. "
                    "A historical state is not "
                    "contradicted merely because "
                    "the current state differs."
                ),
                evidence_count=0,
                method="who_semantic",
            )

        return super()._risk_result(
            text=text,
            facts=facts,
        )

    def _vaccine_result(
        self,
        text: str,
        facts: list[dict],
    ):
        if (
            self.semantics
            .is_non_covid_vaccine(
                text
            )
        ):
            return self._result(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The claim refers to a "
                    "non-COVID vaccine, so "
                    "COVID-19 vaccination evidence "
                    "cannot be used as direct "
                    "support or contradiction."
                ),
                evidence_count=0,
                method="who_semantic",
            )

        if (
            self.semantics
            .is_absolute_limitation(
                text
            )
        ):
            return self._result(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The claim limits an absolute "
                    "vaccine-effect interpretation. "
                    "The current knowledge graph "
                    "represents protection "
                    "relationships but does not "
                    "model an absolute guarantee."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        return super()._vaccine_result(
            text=text,
            facts=facts,
        )

    def _relationship_result(
        self,
        text: str,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
    ):
        if (
            self.semantics
            .is_non_covid_vaccine(
                text
            )
            and facts
        ):
            return self._result(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "Retrieved vaccine evidence "
                    "does not establish the "
                    "asserted relationship for "
                    "the specific non-COVID "
                    "vaccine named in the claim."
                ),
                evidence_count=0,
                method="relationship",
            )

        return super()._relationship_result(
            text=text,
            entities=entities,
            relationships=relationships,
            facts=facts,
        )

    def _vaccine_targets(
        self,
        text: str,
    ):
        targets = (
            super()._vaccine_targets(
                text
            )
        )

        if (
            "infection"
            in targets
            and len(
                targets
            ) > 1
            and any(
                value in text
                for value in (
                    "rather than",
                    "although vaccinated",
                    "though vaccinated",
                    "while vaccinated",
                    "vaccinated people can still",
                    "vaccinated people may still",
                )
            )
        ):
            targets = [
                target
                for target in targets
                if target
                != "infection"
            ]

        return targets

    def _is_negated_claim(
        self,
        text: str,
    ):
        return (
            self.semantics
            .is_relation_negated(
                text
            )
        )

    def _is_unrelated_claim(
        self,
        text: str,
    ):
        normalized = self._normalize(
            text
        )

        if any(
            value in normalized
            for value in (
                "nothing to do with",
                "no connection between",
                "no connection to",
            )
        ):
            return True

        return super()._is_unrelated_claim(
            text
        )

    def _facts_support_no_additional_risk(
        self,
        facts: list[dict],
    ):
        evidence_text = (
            self._facts_text(
                facts
            )
        )

        return any(
            value in evidence_text
            for value in (
                "no additional public health risk",
                "does not pose additional public health risk",
                "does not appear to pose additional public health risk",
                "does not pose an additional public health risk",
                "does not appear to pose an additional public health risk",
            )
        )

    def _facts_text(
        self,
        facts: list[dict],
    ):
        values = []

        for fact in facts:
            values.append(
                str(
                    fact.get(
                        "predicate",
                        "",
                    )
                )
            )

            values.append(
                str(
                    fact.get(
                        "subject",
                        {},
                    ).get(
                        "name",
                        "",
                    )
                )
            )

            values.append(
                str(
                    fact.get(
                        "object",
                        {},
                    ).get(
                        "name",
                        "",
                    )
                )
            )

            attributes = (
                fact.get(
                    "evidence",
                    {},
                ).get(
                    "attributes",
                    {},
                )
            )

            for value in (
                attributes.values()
            ):
                if isinstance(
                    value,
                    (
                        str,
                        int,
                        float,
                        bool,
                    ),
                ):
                    values.append(
                        str(
                            value
                        )
                    )

        return self._normalize(
            " ".join(
                values
            )
        )

    def _fact_source_years(
        self,
        facts: list[dict],
    ):
        years = []

        for fact in facts:
            attributes = (
                fact.get(
                    "evidence",
                    {},
                ).get(
                    "attributes",
                    {},
                )
            )

            source_date = str(
                attributes.get(
                    "source_date",
                    "",
                )
            )

            match = re.search(
                r"\b((?:19|20)\d{2})\b",
                source_date,
            )

            if match:
                years.append(
                    int(
                        match.group(
                            1
                        )
                    )
                )

        return years