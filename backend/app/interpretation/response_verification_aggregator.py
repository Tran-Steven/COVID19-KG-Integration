class ResponseVerificationAggregator:
    SUPPORTED = "SUPPORTED"

    CONTRADICTED = "CONTRADICTED"

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

    NOT_VERIFIABLE = "NOT_VERIFIABLE_WITH_CURRENT_KG"

    MIXED = "MIXED"

    NO_FACTUAL_CLAIMS = "NO_FACTUAL_CLAIMS"

    def summarize(
        self,
        claims: list[dict],
    ):
        statuses = [claim["retrieval"]["verification"]["status"] for claim in claims]

        claim_count = len(statuses)

        supported_count = self._count(
            statuses,
            self.SUPPORTED,
        )

        contradicted_count = self._count(
            statuses,
            self.CONTRADICTED,
        )

        insufficient_count = self._count(
            statuses,
            self.INSUFFICIENT_EVIDENCE,
        )

        not_verifiable_count = self._count(
            statuses,
            self.NOT_VERIFIABLE,
        )

        verifiable_claim_count = claim_count - not_verifiable_count

        needs_attention_count = contradicted_count + insufficient_count

        supported_ratio = self._ratio(
            supported_count,
            claim_count,
        )

        coverage_ratio = self._ratio(
            verifiable_claim_count,
            claim_count,
        )

        grounding_score = supported_ratio

        status = self._overall_status(
            claim_count=(claim_count),
            supported_count=(supported_count),
            contradicted_count=(contradicted_count),
            insufficient_count=(insufficient_count),
            not_verifiable_count=(not_verifiable_count),
        )

        return {
            "status": status,
            "claimCount": (claim_count),
            "supportedCount": (supported_count),
            "contradictedCount": (contradicted_count),
            "insufficientEvidenceCount": (insufficient_count),
            "notVerifiableCount": (not_verifiable_count),
            "verifiableClaimCount": (verifiable_claim_count),
            "needsAttentionCount": (needs_attention_count),
            "supportedRatio": (supported_ratio),
            "coverageRatio": (coverage_ratio),
            "groundingScore": (grounding_score),
            "method": ("claim_status_aggregation"),
            "explanation": (
                "The grounding score is the "
                "fraction of extracted factual "
                "claims positively supported by "
                "the current knowledge graph. "
                "Unverifiable claims reduce "
                "coverage but do not by themselves "
                "make the overall response mixed. "
                "The grounding score is not a "
                "probability that the response is "
                "factually correct."
            ),
        }

    def _overall_status(
        self,
        claim_count: int,
        supported_count: int,
        contradicted_count: int,
        insufficient_count: int,
        not_verifiable_count: int,
    ):
        if claim_count == 0:
            return self.NO_FACTUAL_CLAIMS

        verifiable_count = claim_count - not_verifiable_count

        if verifiable_count == 0:
            return self.NOT_VERIFIABLE

        if supported_count > 0 and contradicted_count == 0 and insufficient_count == 0:
            return self.SUPPORTED

        if contradicted_count > 0 and supported_count == 0 and insufficient_count == 0:
            return self.CONTRADICTED

        if insufficient_count > 0 and supported_count == 0 and contradicted_count == 0:
            return self.INSUFFICIENT_EVIDENCE

        return self.MIXED

    def _count(
        self,
        statuses: list[str],
        status: str,
    ):
        return sum(1 for value in statuses if value == status)

    def _ratio(
        self,
        numerator: int,
        denominator: int,
    ):
        if denominator == 0:
            return None

        return round(
            numerator / denominator,
            3,
        )
