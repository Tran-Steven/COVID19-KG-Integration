import re

from app.interpretation.origin_qualifier_resolver import (
    OriginQualifierResolver,
)
from app.interpretation.proposition_guard import (
    PropositionGuard,
)
from app.interpretation.proposition_semantics import PropositionSemantics


class VerificationResolver:
    def __init__(
        self,
    ):
        self._init_core()

        self.semantics = PropositionSemantics()

        self.proposition_guard = PropositionGuard()

    def _who_result(
        self,
        text: str,
        entities: list[dict],
        facts: list[dict],
    ):
        if self.semantics.is_no_additional_risk_claim(text):
            if facts and self._facts_support_no_additional_risk(facts):
                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "The claim matches WHO "
                        "evidence indicating no "
                        "additional public-health risk "
                        "for the referenced variant."
                    ),
                    evidence_count=len(facts),
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
                evidence_count=len(facts),
                method="who_semantic",
            )

        if self.semantics.is_variant_tracking_rationale_claim(text):
            return self._result(
                status=self.INSUFFICIENT_EVIDENCE,
                reason=(
                    "WHO variant monitoring evidence "
                    "was retrieved, but the current "
                    "knowledge graph does not establish "
                    "the claimed rationale for why the "
                    "variant is being monitored."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._who_result_core(
            text=text,
            entities=entities,
            facts=facts,
        )

    def _origin_result(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(text)

        assessments = {
            self._assessment(fact) for fact in facts if self._assessment(fact)
        }

        overall_inconclusive = (
            "inconclusive_pending_additional_"
            "information_or_scientific_data" in assessments
        )

        lab_uncertain = (
            "cannot_be_ruled_out_or_proven_with_available_information" in assessments
        )

        zoonotic_supported = (
            "best_supported_by_available_scientific_data" in assessments
        )

        if overall_inconclusive and self.semantics.is_origin_inconclusive(text):
            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "The claim matches WHO "
                    "SAGO's assessment that the "
                    "origin remains unresolved or "
                    "inconclusive."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        if lab_uncertain and self.semantics.is_lab_uncertainty(text):
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
                evidence_count=len(facts),
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
            and not self.origin_qualifiers.is_certainty_overclaim(normalized)
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
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._origin_result_core(
            text=text,
            facts=facts,
        )

    def _risk_result(
        self,
        text: str,
        facts: list[dict],
    ):
        claim_years = self.semantics.explicit_years(text)

        fact_years = self._fact_source_years(facts)

        if (
            claim_years
            and fact_years
            and not self.semantics.has_current_language(text)
            and max(claim_years) < max(fact_years)
        ):
            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
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

        return self._risk_result_core(
            text=text,
            facts=facts,
        )

    def _vaccine_result(
        self,
        text: str,
        facts: list[dict],
    ):
        if self.semantics.is_non_covid_vaccine(text):
            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
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

        if self.semantics.is_absolute_limitation(text):
            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
                reason=(
                    "The claim limits an absolute "
                    "vaccine-effect interpretation. "
                    "The current knowledge graph "
                    "represents protection "
                    "relationships but does not "
                    "model an absolute guarantee."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._vaccine_result_core(
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
        if self.semantics.is_non_covid_vaccine(text) and facts:
            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
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

        return self._relationship_result_core(
            text=text,
            entities=entities,
            relationships=relationships,
            facts=facts,
        )

    def _vaccine_targets(
        self,
        text: str,
    ):
        targets = self._vaccine_targets_core(text)

        if (
            "infection" in targets
            and len(targets) > 1
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
            targets = [target for target in targets if target != "infection"]

        return targets

    def _is_negated_claim(
        self,
        text: str,
    ):
        return self.semantics.is_relation_negated(text)

    def _is_unrelated_claim(
        self,
        text: str,
    ):
        normalized = self._normalize(text)

        if any(
            value in normalized
            for value in (
                "nothing to do with",
                "no connection between",
                "no connection to",
            )
        ):
            return True

        return self._is_unrelated_claim_core(text)

    def _facts_support_no_additional_risk(
        self,
        facts: list[dict],
    ):
        evidence_text = self._facts_text(facts)

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

            attributes = fact.get(
                "evidence",
                {},
            ).get(
                "attributes",
                {},
            )

            for value in attributes.values():
                if isinstance(
                    value,
                    (
                        str,
                        int,
                        float,
                        bool,
                    ),
                ):
                    values.append(str(value))

        return self._normalize(" ".join(values))

    def _fact_source_years(
        self,
        facts: list[dict],
    ):
        years = []

        for fact in facts:
            attributes = fact.get(
                "evidence",
                {},
            ).get(
                "attributes",
                {},
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
                years.append(int(match.group(1)))

        return years

    SUPPORTED = "SUPPORTED"

    CONTRADICTED = "CONTRADICTED"

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

    NOT_VERIFIABLE = "NOT_VERIFIABLE_WITH_CURRENT_KG"

    VALID_STATUSES = {
        SUPPORTED,
        CONTRADICTED,
        INSUFFICIENT_EVIDENCE,
        NOT_VERIFIABLE,
    }

    def _init_core(
        self,
    ):
        self.origin_qualifiers = OriginQualifierResolver()

        self.proposition_guard = PropositionGuard()

    def resolve(
        self,
        text: str,
        verification_type: str,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
        history: dict | None,
    ):
        scoped = self.proposition_guard.scope_decision(text)

        if scoped is not None:
            return self._guard_result(
                scoped,
                verification_type,
            )

        if verification_type == "history":
            return self._history_result(history)

        if verification_type == "who":
            return self._who_result(
                text=text,
                entities=entities,
                facts=facts,
            )

        return self._relationship_result(
            text=text,
            entities=entities,
            relationships=relationships,
            facts=facts,
        )

    def _history_result(
        self,
        history: dict | None,
    ):
        if not history:
            return self._result(
                status=self.NOT_VERIFIABLE,
                reason=("No supported history interpretation was resolved."),
                evidence_count=0,
                method="history",
            )

        status = history.get("status")

        evidence = history.get(
            "evidence",
            [],
        )

        if status in self.VALID_STATUSES:
            return self._result(
                status=status,
                reason=(self._history_reason(status)),
                evidence_count=len(evidence),
                method="history",
            )

        if evidence:
            return self._result(
                status=self.SUPPORTED,
                reason=("Matching source-backed historical evidence was retrieved."),
                evidence_count=len(evidence),
                method="history",
            )

        return self._result(
            status=self.NOT_VERIFIABLE,
            reason=(
                "The requested historical "
                "claim is not verifiable with "
                "the current knowledge graph."
            ),
            evidence_count=0,
            method="history",
        )

    def _who_result_core(
        self,
        text: str,
        entities: list[dict],
        facts: list[dict],
    ):
        if not facts:
            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
                reason=(
                    "The query maps to a WHO "
                    "verification relation, but "
                    "no matching WHO evidence "
                    "was retrieved."
                ),
                evidence_count=0,
                method="who_semantic",
            )

        roles = {fact.get("predicate") for fact in facts}

        if "origin_hypothesis_assessment" in roles or "overall_origin_status" in roles:
            return self._origin_result(
                text=text,
                facts=facts,
            )

        if "global_public_health_risk_level" in roles:
            return self._risk_result(
                text=text,
                facts=facts,
            )

        if "causes" in roles:
            guarded = self.proposition_guard.cause_decision(
                text=text,
                entities=entities,
                facts=facts,
            )

            if guarded is not None:
                return self._guard_result(
                    guarded,
                    "who_semantic",
                )

            return self._cause_result(
                text=text,
                facts=facts,
            )

        if "protects_against" in roles:
            return self._vaccine_result(
                text=text,
                facts=facts,
            )

        if "transmitted_via" in roles:
            guarded = self.proposition_guard.transmission_decision(
                text=text,
                facts=facts,
            )

            if guarded is not None:
                return self._guard_result(
                    guarded,
                    "who_semantic",
                )

            return self._transmission_result(
                text=text,
                facts=facts,
            )

        if self._has_explicit_contradiction(facts):
            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "Retrieved WHO evidence explicitly contradicts the requested claim."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        if self._is_negated_claim(text):
            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "The query asserts the "
                    "negation of a relation that "
                    "is directly supported by "
                    "retrieved WHO evidence."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._result(
            status=self.SUPPORTED,
            reason=(
                "Matching WHO evidence "
                "directly supports the "
                "requested semantic relation."
            ),
            evidence_count=len(facts),
            method="who_semantic",
        )

    def _cause_result(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(text)

        if self._canonical_cause_reference(normalized) and self._is_negated_claim(text):
            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "WHO evidence identifies "
                    "SARS-CoV-2 as the virus "
                    "that causes COVID-19, while "
                    "the claim negates that "
                    "relationship."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        if self._is_question(text):
            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "WHO evidence identifies "
                    "SARS-CoV-2 as the virus "
                    "that causes COVID-19."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        claimed_cause = self._claimed_cause(normalized)

        if claimed_cause:
            if self._canonical_cause_reference(claimed_cause):
                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "The claimed cause "
                        "matches WHO evidence "
                        "identifying SARS-CoV-2 "
                        "as the cause of COVID-19."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            if self._generic_virus_reference(claimed_cause):
                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "The claim is compatible "
                        "with WHO evidence "
                        "identifying SARS-CoV-2 "
                        "as the virus that causes "
                        "COVID-19."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "The claim names a different "
                    "cause, while WHO evidence "
                    "identifies SARS-CoV-2 as "
                    "the virus that causes "
                    "COVID-19."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._result(
            status=self.SUPPORTED,
            reason=("Retrieved WHO evidence supports the modeled causal relationship."),
            evidence_count=len(facts),
            method="who_semantic",
        )

    def _risk_result_core(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(text)

        claimed_level = self._risk_level(normalized)

        evidence_text = " ".join(self._fact_object_names(facts))

        if claimed_level:
            if claimed_level in evidence_text:
                if self._is_negated_claim(text):
                    return self._result(
                        status=self.CONTRADICTED,
                        reason=(
                            "The claim negates "
                            f"the {claimed_level} "
                            "risk level represented "
                            "by the current WHO "
                            "assessment."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "The claimed current "
                        "risk level matches the "
                        "WHO risk assessment "
                        "represented in the "
                        "knowledge graph."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "The claimed current risk "
                    "level does not match the "
                    "WHO risk level represented "
                    "in the knowledge graph."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._result(
            status=self.SUPPORTED,
            reason=("Current WHO global public health risk evidence was retrieved."),
            evidence_count=len(facts),
            method="who_semantic",
        )

    def _vaccine_result_core(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(text)

        targets = self._vaccine_targets(normalized)

        evidence_objects = self._fact_object_names(facts)

        if self._absolute_positive_claim(normalized) and targets:
            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
                reason=(
                    "The claim makes an absolute "
                    "vaccine-effect statement "
                    "that is stronger than the "
                    "protective relationships "
                    "represented in the current "
                    "WHO knowledge graph."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        if targets:
            matched_targets = [
                target
                for target in targets
                if self._target_in_objects(
                    target,
                    evidence_objects,
                )
            ]

            if len(matched_targets) != len(targets):
                return self._result(
                    status=(self.INSUFFICIENT_EVIDENCE),
                    reason=(
                        "WHO vaccine evidence was "
                        "retrieved, but the "
                        "specific claimed outcome "
                        "is not represented by "
                        "the retrieved protection "
                        "relationships."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            if self._is_negated_claim(text):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "The claim negates a "
                        "vaccine-protection "
                        "relationship directly "
                        "represented by WHO "
                        "evidence."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "The claimed vaccine outcome "
                    "matches a protection "
                    "relationship represented by "
                    "WHO evidence."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        if self._is_negated_claim(text):
            return self._result(
                status=self.CONTRADICTED,
                reason=("The claim negates retrieved WHO vaccine-protection evidence."),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._result(
            status=self.SUPPORTED,
            reason=(
                "Retrieved WHO evidence "
                "supports the requested vaccine "
                "protection relationship."
            ),
            evidence_count=len(facts),
            method="who_semantic",
        )

    def _transmission_result(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(text)

        if self._exclusive_claim(normalized):
            transmitted_objects = {
                self._normalize(
                    fact.get(
                        "object",
                        {},
                    ).get(
                        "name",
                        "",
                    )
                )
                for fact in facts
                if (fact.get("predicate") == "transmitted_via")
                and fact.get(
                    "object",
                    {},
                ).get("name")
            }

            if len(transmitted_objects) > 1:
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "The claim says the "
                        "transmission route is "
                        "exclusive, but WHO "
                        "evidence in the graph "
                        "represents multiple "
                        "transmission routes."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
                reason=(
                    "The retrieved evidence "
                    "supports a transmission "
                    "route but does not establish "
                    "the claim's exclusivity."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        if self._is_negated_claim(text):
            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "The claim negates a "
                    "transmission relationship "
                    "directly represented by "
                    "WHO evidence."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._result(
            status=self.SUPPORTED,
            reason=(
                "The requested transmission "
                "relationship is represented "
                "by WHO evidence."
            ),
            evidence_count=len(facts),
            method="who_semantic",
        )

    def _origin_result_core(
        self,
        text: str,
        facts: list[dict],
    ):
        normalized = self._normalize(text)

        assessments = {
            self._assessment(fact) for fact in facts if self._assessment(fact)
        }

        if self.origin_qualifiers.is_inconclusive(normalized):
            if (
                "inconclusive_pending_additional_"
                "information_or_scientific_data" in assessments
            ):
                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "The claim matches WHO "
                        "SAGO's overall assessment "
                        "that the origin remains "
                        "inconclusive pending "
                        "additional information."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

        if self._deliberate_origin_query(normalized):
            if (
                "no_scientific_evidence_"
                "supporting_over_natural_processes" in assessments
            ):
                if self.origin_qualifiers.is_negative_support_claim(normalized):
                    return self._result(
                        status=self.SUPPORTED,
                        reason=(
                            "The claim matches the "
                            "absence of supporting "
                            "evidence represented by "
                            "WHO SAGO."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                if self.origin_qualifiers.is_positive_support_claim(normalized):
                    return self._result(
                        status=self.CONTRADICTED,
                        reason=(
                            "WHO SAGO reports no "
                            "scientific evidence "
                            "supporting deliberate "
                            "laboratory manipulation "
                            "over natural processes."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                return self._result(
                    status=(self.INSUFFICIENT_EVIDENCE),
                    reason=(
                        "WHO SAGO reports no "
                        "scientific evidence "
                        "supporting deliberate "
                        "laboratory manipulation "
                        "over natural processes, "
                        "while the overall origin "
                        "remains inconclusive."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

        if self._laboratory_origin_query(normalized):
            if (
                "cannot_be_ruled_out_or_"
                "proven_with_available_"
                "information" in assessments
            ):
                if self.origin_qualifiers.is_uncertain_lab_claim(normalized):
                    return self._result(
                        status=self.SUPPORTED,
                        reason=(
                            "The claim matches WHO "
                            "SAGO's assessment that "
                            "a laboratory-related "
                            "event cannot currently "
                            "be ruled out or proven "
                            "with available "
                            "information."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                if self.origin_qualifiers.is_ruled_out(normalized):
                    return self._result(
                        status=self.CONTRADICTED,
                        reason=(
                            "The claim says a "
                            "laboratory-related "
                            "origin has been ruled "
                            "out, while WHO SAGO "
                            "states that it cannot "
                            "currently be ruled out "
                            "or proven."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                return self._result(
                    status=(self.INSUFFICIENT_EVIDENCE),
                    reason=(
                        "WHO SAGO states that a "
                        "laboratory-related event "
                        "cannot be ruled out or "
                        "proven with the available "
                        "information."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

        if self._cold_chain_query(normalized):
            if "no_additional_evidence_supporting" in assessments:
                if self.origin_qualifiers.is_negative_support_claim(normalized):
                    return self._result(
                        status=self.SUPPORTED,
                        reason=(
                            "The claim matches WHO "
                            "SAGO's assessment that "
                            "no additional evidence "
                            "supports the cold-chain "
                            "hypothesis."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                if self.origin_qualifiers.is_positive_support_claim(normalized):
                    return self._result(
                        status=self.CONTRADICTED,
                        reason=(
                            "The claim asserts "
                            "support for the "
                            "cold-chain hypothesis, "
                            "while WHO SAGO reports "
                            "no additional evidence "
                            "supporting it."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                return self._result(
                    status=(self.INSUFFICIENT_EVIDENCE),
                    reason=(
                        "WHO SAGO reports no "
                        "additional evidence "
                        "supporting the cold-chain "
                        "hypothesis."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

        if self._zoonotic_origin_query(normalized):
            if "best_supported_by_available_scientific_data" in assessments:
                if self.origin_qualifiers.is_certainty_overclaim(normalized):
                    return self._result(
                        status=(self.INSUFFICIENT_EVIDENCE),
                        reason=(
                            "WHO SAGO identifies "
                            "zoonotic spillover as "
                            "the best-supported "
                            "hypothesis, but does "
                            "not establish it as a "
                            "conclusively proven "
                            "origin."
                        ),
                        evidence_count=len(facts),
                        method="who_semantic",
                    )

                return self._result(
                    status=self.SUPPORTED,
                    reason=(
                        "WHO SAGO identifies "
                        "zoonotic spillover as the "
                        "best-supported hypothesis "
                        "in the available "
                        "scientific data, while "
                        "the overall origin remains "
                        "inconclusive."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

        if (
            "inconclusive_pending_additional_"
            "information_or_scientific_data" in assessments
        ):
            if self.origin_qualifiers.is_broad_certainty_claim(normalized):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "The claim presents the "
                        "origin as conclusively "
                        "known, while WHO SAGO's "
                        "overall assessment "
                        "remains inconclusive."
                    ),
                    evidence_count=len(facts),
                    method="who_semantic",
                )

            return self._result(
                status=(self.INSUFFICIENT_EVIDENCE),
                reason=(
                    "WHO SAGO can evaluate the "
                    "origin question, but its "
                    "overall assessment remains "
                    "inconclusive pending "
                    "additional information or "
                    "scientific data."
                ),
                evidence_count=len(facts),
                method="who_semantic",
            )

        return self._result(
            status=(self.INSUFFICIENT_EVIDENCE),
            reason=(
                "Origin evidence was retrieved, "
                "but it does not establish a "
                "definitive origin conclusion."
            ),
            evidence_count=len(facts),
            method="who_semantic",
        )

    def _relationship_result_core(
        self,
        text: str,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
    ):
        if facts:
            guarded = self.proposition_guard.cause_decision(
                text=text,
                entities=entities,
                facts=facts,
            )

            if guarded is None:
                guarded = self.proposition_guard.transmission_decision(
                    text=text,
                    facts=facts,
                )

            if guarded is not None:
                return self._guard_result(
                    guarded,
                    "relationship",
                )

            if self._has_explicit_contradiction(facts):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "Retrieved knowledge graph "
                        "evidence explicitly "
                        "contradicts the requested "
                        "claim."
                    ),
                    evidence_count=len(facts),
                    method="relationship",
                )

            if self._is_unrelated_claim(text):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "The claim explicitly "
                        "denies a relationship "
                        "that is directly "
                        "supported by retrieved "
                        "knowledge graph evidence."
                    ),
                    evidence_count=len(facts),
                    method="relationship",
                )

            if self._is_negated_claim(text):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "The query asserts the "
                        "negation of a relation "
                        "that is directly supported "
                        "by retrieved knowledge "
                        "graph evidence."
                    ),
                    evidence_count=len(facts),
                    method="relationship",
                )

            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "Matching knowledge graph "
                    "evidence directly supports "
                    "the requested relationship."
                ),
                evidence_count=len(facts),
                method="relationship",
            )

        has_linked_entity = any(entity.get("candidates") for entity in entities)

        if not has_linked_entity or not relationships:
            return self._result(
                status=self.NOT_VERIFIABLE,
                reason=(
                    "The query could not be "
                    "mapped to both a supported "
                    "knowledge graph concept and "
                    "relationship."
                ),
                evidence_count=0,
                method="relationship",
            )

        return self._result(
            status=(self.INSUFFICIENT_EVIDENCE),
            reason=(
                "The query maps to known "
                "knowledge graph concepts and a "
                "supported relationship, but no "
                "matching evidence was found."
            ),
            evidence_count=0,
            method="relationship",
        )

    def _claimed_cause(
        self,
        text: str,
    ):
        patterns = (
            (
                r"\bcovid(?: 19)? "
                r"(?:is )?caused by "
                r"(.+)$"
            ),
            (
                r"\bcovid(?: 19)? "
                r"results? from infection with "
                r"(.+)$"
            ),
            (
                r"\bcovid(?: 19)? "
                r"is due to infection with "
                r"(.+)$"
            ),
            (
                r"^(.+?) "
                r"(?:does not )?"
                r"causes? "
                r"covid(?: 19)?\b"
            ),
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
            )

            if match:
                return match.group(1).strip()

        return None

    def _canonical_cause_reference(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "sars cov 2",
                ("severe acute respiratory syndrome coronavirus 2"),
            )
        )

    def _generic_virus_reference(
        self,
        text: str,
    ):
        normalized = text.strip()

        return normalized in {
            "virus",
            "a virus",
            "coronavirus",
            "a coronavirus",
            "the coronavirus",
        }

    def _risk_level(
        self,
        text: str,
    ):
        levels = (
            "very high",
            "high",
            "moderate",
            "low",
        )

        for level in levels:
            if re.search(
                (r"\b" + re.escape(level) + r"\b"),
                text,
            ):
                return level

        return None

    def _vaccine_targets_core(
        self,
        text: str,
    ):
        targets = []

        if "severe" in text:
            targets.append("severe disease")

        if "hospital" in text:
            targets.append("hospitalization")

        if any(
            value in text
            for value in (
                "death",
                "deaths",
                "die",
                "mortality",
            )
        ):
            targets.append("death")

        if any(
            value in text
            for value in (
                "infection",
                "infections",
                "infected",
            )
        ):
            targets.append("infection")

        if any(
            value in text
            for value in (
                "transmission",
                "spread",
            )
        ):
            targets.append("transmission")

        return targets

    def _target_in_objects(
        self,
        target: str,
        objects: list[str],
    ):
        if target == "severe disease":
            return any("severe disease" in value for value in objects)

        if target == "hospitalization":
            return any("hospital" in value for value in objects)

        if target == "death":
            return any(value == "death" or "death" in value for value in objects)

        return any(target in value for value in objects)

    def _fact_object_names(
        self,
        facts: list[dict],
    ):
        return [
            self._normalize(
                fact.get(
                    "object",
                    {},
                ).get(
                    "name",
                    "",
                )
            )
            for fact in facts
            if fact.get(
                "object",
                {},
            ).get("name")
        ]

    def _absolute_positive_claim(
        self,
        text: str,
    ):
        if self._is_negated_claim(text):
            return False

        return any(
            value in text
            for value in (
                "completely",
                "always",
                "guarantees",
                "guarantee",
                "100 percent",
                "fully prevent",
                "entirely prevent",
                "eliminates",
                "eliminate",
            )
        )

    def _exclusive_claim(
        self,
        text: str,
    ):
        return any(
            re.search(
                (r"\b" + re.escape(value) + r"\b"),
                text,
            )
            is not None
            for value in (
                "only",
                "solely",
                "exclusively",
            )
        )

    def _inconclusive_origin_claim(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "remains inconclusive",
                "remain inconclusive",
                "is inconclusive",
                "still inconclusive",
                "origin is unknown",
                "origin remains unknown",
            )
        )

    def _cannot_rule_out_claim(
        self,
        text: str,
    ):
        cannot = "cannot" in text or "can not" in text

        ruled_out = "ruled out" in text

        proven = "proven" in text or "proved" in text

        return cannot and ruled_out and proven

    def _ruled_out_claim(
        self,
        text: str,
    ):
        if "cannot" in text or "can not" in text:
            return False

        return any(
            value in text
            for value in (
                "ruled out",
                "excluded as an origin",
                "excluded as the origin",
                "impossible",
            )
        )

    def _positive_support_claim(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "better supported",
                "more strongly supported",
                "most strongly supported",
                "strongly supported",
                "well supported",
                "evidence supports",
                "evidence strongly supports",
                "supported than natural",
                "new evidence supports",
            )
        )

    def _certainty_overclaim(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "conclusively proven",
                "conclusively proved",
                "definitively proven",
                "definitively proved",
                "definite origin",
                "certain origin",
                "proven origin",
                "proved origin",
            )
        )

    def _broad_origin_certainty_claim(
        self,
        text: str,
    ):
        return self._certainty_overclaim(text) or any(
            value in text
            for value in (
                "know exactly how",
                "knows exactly how",
                "origin is known exactly",
                "origin is conclusively known",
                "origin has been conclusively proven",
                "origin has been definitively proven",
                "origin has been proven",
            )
        )

    def _has_explicit_contradiction(
        self,
        facts: list[dict],
    ):
        contradiction_values = {
            "contradicted",
            "contradicts",
            "contradiction",
            "refuted",
            "refutes",
            "negative",
        }

        for fact in facts:
            attributes = fact.get(
                "evidence",
                {},
            ).get(
                "attributes",
                {},
            )

            for key in (
                "verification_stance",
                "evidence_stance",
                "stance",
                "verification_status",
            ):
                value = attributes.get(key)

                if value is None:
                    continue

                normalized = self._normalize(str(value))

                if normalized in contradiction_values:
                    return True

        return False

    def _assessment(
        self,
        fact: dict,
    ):
        return (
            fact.get(
                "evidence",
                {},
            )
            .get(
                "attributes",
                {},
            )
            .get("assessment")
        )

    def _is_negated_claim_core(
        self,
        text: str,
    ):
        normalized = text.lower()

        return bool(
            re.search(
                (
                    r"\bnot\b"
                    r"|\bnever\b"
                    r"|\bcannot\b"
                    r"|n['’]t\b"
                ),
                normalized,
            )
        )

    def _is_unrelated_claim_core(
        self,
        text: str,
    ):
        normalized = self._normalize(text)

        return any(
            value in normalized
            for value in (
                "unrelated to",
                "not related to",
                "no relationship to",
                "no relation to",
            )
        )

    def _is_question(
        self,
        text: str,
    ):
        stripped = text.strip()

        if stripped.endswith("?"):
            return True

        normalized = self._normalize(stripped)

        return any(
            normalized.startswith(value)
            for value in (
                "what ",
                "which ",
                "who ",
                "when ",
                "where ",
                "why ",
                "how ",
                "can ",
                "could ",
                "does ",
                "do ",
                "did ",
                "is ",
                "are ",
                "was ",
                "were ",
            )
        )

    def _deliberate_origin_query(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
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
        )

    def _laboratory_origin_query(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "lab leak",
                "laboratory",
                "lab origin",
                "from a lab",
                "laboratory related",
                "lab related",
            )
        )

    def _cold_chain_query(
        self,
        text: str,
    ):
        return "cold chain" in text

    def _zoonotic_origin_query(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "zoonotic",
                "animal origin",
                "from animals",
                "natural origin",
                "natural spillover",
                "zoonotic spillover",
            )
        )

    def _history_reason(
        self,
        status: str,
    ):
        if status == self.SUPPORTED:
            return (
                "Matching source-backed "
                "historical evidence supports "
                "the requested result."
            )

        if status == self.CONTRADICTED:
            return "Source-backed historical evidence contradicts the requested claim."

        if status == self.INSUFFICIENT_EVIDENCE:
            return (
                "The history query is within "
                "scope, but the available "
                "evidence is insufficient."
            )

        return (
            "The requested historical claim "
            "cannot be verified with the "
            "current knowledge graph."
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

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    def _guard_result(
        self,
        decision: dict,
        method: str,
    ):
        result = self._result(
            status=decision["status"],
            reason=decision["reason"],
            evidence_count=decision["evidenceCount"],
            method=method,
        )

        if decision.get("clearFacts"):
            result["_clearFacts"] = True

        return result

    def _result(
        self,
        status: str,
        reason: str,
        evidence_count: int,
        method: str,
    ):
        return {
            "status": status,
            "reason": reason,
            "evidenceCount": evidence_count,
            "method": method,
        }
