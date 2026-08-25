import re


class VerificationResolver:
    SUPPORTED = "SUPPORTED"

    CONTRADICTED = (
        "CONTRADICTED"
    )

    INSUFFICIENT_EVIDENCE = (
        "INSUFFICIENT_EVIDENCE"
    )

    NOT_VERIFIABLE = (
        "NOT_VERIFIABLE_WITH_CURRENT_KG"
    )

    VALID_STATUSES = {
        SUPPORTED,
        CONTRADICTED,
        INSUFFICIENT_EVIDENCE,
        NOT_VERIFIABLE,
    }

    def resolve(
        self,
        text: str,
        verification_type: str,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
        history: dict | None,
    ):
        if verification_type == "history":
            return self._history_result(
                history
            )

        if verification_type == "who":
            return self._who_result(
                text=text,
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
                reason=(
                    "No supported history "
                    "interpretation was resolved."
                ),
                evidence_count=0,
                method="history",
            )

        status = history.get(
            "status"
        )

        evidence = history.get(
            "evidence",
            [],
        )

        if status in self.VALID_STATUSES:
            return self._result(
                status=status,
                reason=(
                    self._history_reason(
                        status
                    )
                ),
                evidence_count=len(
                    evidence
                ),
                method="history",
            )

        if evidence:
            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "Matching source-backed "
                    "historical evidence was "
                    "retrieved."
                ),
                evidence_count=len(
                    evidence
                ),
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

    def _who_result(
        self,
        text: str,
        facts: list[dict],
    ):
        if not facts:
            return self._result(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The query maps to a WHO "
                    "verification relation, but "
                    "no matching WHO evidence "
                    "was retrieved."
                ),
                evidence_count=0,
                method="who_semantic",
            )

        roles = {
            fact.get(
                "predicate"
            )
            for fact in facts
        }

        if (
            "origin_hypothesis_assessment"
            in roles
            or "overall_origin_status"
            in roles
        ):
            return self._origin_result(
                text=text,
                facts=facts,
            )

        if self._has_explicit_contradiction(
            facts
        ):
            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "Retrieved WHO evidence "
                    "explicitly contradicts the "
                    "requested claim."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        if self._is_negated_claim(
            text
        ):
            return self._result(
                status=self.CONTRADICTED,
                reason=(
                    "The query asserts the "
                    "negation of a relation that "
                    "is directly supported by "
                    "retrieved WHO evidence."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        return self._result(
            status=self.SUPPORTED,
            reason=(
                "Matching WHO evidence "
                "directly supports the "
                "requested semantic relation."
            ),
            evidence_count=len(
                facts
            ),
            method="who_semantic",
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

        if self._deliberate_origin_query(
            normalized
        ):
            if (
                "no_scientific_evidence_"
                "supporting_over_natural_processes"
                in assessments
            ):
                return self._result(
                    status=(
                        self.INSUFFICIENT_EVIDENCE
                    ),
                    reason=(
                        "WHO SAGO reports no "
                        "scientific evidence "
                        "supporting deliberate "
                        "laboratory manipulation "
                        "over natural processes, "
                        "while the overall origin "
                        "remains inconclusive."
                    ),
                    evidence_count=len(
                        facts
                    ),
                    method="who_semantic",
                )

        if self._laboratory_origin_query(
            normalized
        ):
            if (
                "cannot_be_ruled_out_or_"
                "proven_with_available_"
                "information"
                in assessments
            ):
                return self._result(
                    status=(
                        self.INSUFFICIENT_EVIDENCE
                    ),
                    reason=(
                        "WHO SAGO states that a "
                        "laboratory-related event "
                        "cannot be ruled out or "
                        "proven with the available "
                        "information."
                    ),
                    evidence_count=len(
                        facts
                    ),
                    method="who_semantic",
                )

        if self._cold_chain_query(
            normalized
        ):
            if (
                "no_additional_evidence_"
                "supporting"
                in assessments
            ):
                return self._result(
                    status=(
                        self.INSUFFICIENT_EVIDENCE
                    ),
                    reason=(
                        "WHO SAGO reports no "
                        "additional evidence "
                        "supporting the cold-chain "
                        "hypothesis."
                    ),
                    evidence_count=len(
                        facts
                    ),
                    method="who_semantic",
                )

        if self._zoonotic_origin_query(
            normalized
        ):
            if (
                "best_supported_by_available_"
                "scientific_data"
                in assessments
            ):
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
                    evidence_count=len(
                        facts
                    ),
                    method="who_semantic",
                )

        if (
            "inconclusive_pending_additional_"
            "information_or_scientific_data"
            in assessments
        ):
            return self._result(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "WHO SAGO can evaluate the "
                    "origin question, but its "
                    "overall assessment remains "
                    "inconclusive pending "
                    "additional information or "
                    "scientific data."
                ),
                evidence_count=len(
                    facts
                ),
                method="who_semantic",
            )

        return self._result(
            status=(
                self.INSUFFICIENT_EVIDENCE
            ),
            reason=(
                "Origin evidence was retrieved, "
                "but it does not establish a "
                "definitive origin conclusion."
            ),
            evidence_count=len(
                facts
            ),
            method="who_semantic",
        )

    def _relationship_result(
        self,
        text: str,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
    ):
        if facts:
            if self._has_explicit_contradiction(
                facts
            ):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "Retrieved knowledge graph "
                        "evidence explicitly "
                        "contradicts the requested "
                        "claim."
                    ),
                    evidence_count=len(
                        facts
                    ),
                    method="relationship",
                )

            if self._is_negated_claim(
                text
            ):
                return self._result(
                    status=self.CONTRADICTED,
                    reason=(
                        "The query asserts the "
                        "negation of a relation "
                        "that is directly supported "
                        "by retrieved knowledge "
                        "graph evidence."
                    ),
                    evidence_count=len(
                        facts
                    ),
                    method="relationship",
                )

            return self._result(
                status=self.SUPPORTED,
                reason=(
                    "Matching knowledge graph "
                    "evidence directly supports "
                    "the requested relationship."
                ),
                evidence_count=len(
                    facts
                ),
                method="relationship",
            )

        has_linked_entity = any(
            entity.get(
                "candidates"
            )
            for entity in entities
        )

        if (
            not has_linked_entity
            or not relationships
        ):
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
            status=(
                self.INSUFFICIENT_EVIDENCE
            ),
            reason=(
                "The query maps to known "
                "knowledge graph concepts and a "
                "supported relationship, but no "
                "matching evidence was found."
            ),
            evidence_count=0,
            method="relationship",
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
            attributes = (
                fact.get(
                    "evidence",
                    {}
                )
                .get(
                    "attributes",
                    {},
                )
            )

            for key in (
                "verification_stance",
                "evidence_stance",
                "stance",
                "verification_status",
            ):
                value = attributes.get(
                    key
                )

                if value is None:
                    continue

                normalized = (
                    self._normalize(
                        str(value)
                    )
                )

                if (
                    normalized
                    in contradiction_values
                ):
                    return True

        return False

    def _assessment(
        self,
        fact: dict,
    ):
        return (
            fact.get(
                "evidence",
                {}
            )
            .get(
                "attributes",
                {},
            )
            .get(
                "assessment"
            )
        )

    def _is_negated_claim(
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
            )
        )

    def _cold_chain_query(
        self,
        text: str,
    ):
        return (
            "cold chain"
            in text
        )

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
            return (
                "Source-backed historical "
                "evidence contradicts the "
                "requested claim."
            )

        if (
            status
            == self.INSUFFICIENT_EVIDENCE
        ):
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
            r"[^a-z0-9\s]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

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