from datetime import date, datetime, timezone


class ConfidenceScorer:
    WEIGHTS = {
        "evidenceCoverage": 0.20,
        "provenanceCompleteness": 0.15,
        "relationCertainty": 0.15,
        "entityLinkCertainty": 0.15,
        "evidenceAgreement": 0.15,
        "sourceDiversity": 0.15,
        "recency": 0.05,
    }

    TEMPORAL_ROLES = {
        "global_public_health_risk_level",
        "variant_of_interest",
        "variant_under_monitoring",
    }

    NOT_VERIFIABLE = (
        "NOT_VERIFIABLE_WITH_CURRENT_KG"
    )

    INSUFFICIENT_EVIDENCE = (
        "INSUFFICIENT_EVIDENCE"
    )

    def score(
        self,
        verification_type: str,
        verification: dict,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
        history: dict | None,
    ):
        components = {
            "evidenceCoverage": (
                self._evidence_coverage(
                    facts,
                    history,
                )
            ),
            "provenanceCompleteness": (
                self._provenance_completeness(
                    facts,
                    history,
                )
            ),
            "relationCertainty": (
                self._relation_certainty(
                    verification_type,
                    relationships,
                )
            ),
            "entityLinkCertainty": (
                self._entity_link_certainty(
                    verification_type,
                    entities,
                )
            ),
            "evidenceAgreement": (
                self._evidence_agreement(
                    facts,
                    history,
                )
            ),
            "sourceDiversity": (
                self._source_diversity(
                    facts,
                    history,
                )
            ),
            "recency": (
                self._recency(
                    relationships,
                    facts,
                )
            ),
        }

        raw_score = sum(
            components[name]
            * self.WEIGHTS[name]
            for name
            in self.WEIGHTS
        )

        status = verification[
            "status"
        ]

        if (
            status
            == self.NOT_VERIFIABLE
        ):
            raw_score = min(
                raw_score,
                0.45,
            )

        if (
            status
            == self.INSUFFICIENT_EVIDENCE
            and not facts
            and not self._history_evidence(
                history
            )
        ):
            raw_score = min(
                raw_score,
                0.60,
            )

        final_score = round(
            min(
                max(
                    raw_score,
                    0.0,
                ),
                0.99,
            ),
            3,
        )

        return {
            "score": final_score,
            "level": self._level(
                final_score
            ),
            "target": (
                "verification_outcome"
            ),
            "calibrated": False,
            "components": {
                key: round(
                    value,
                    3,
                )
                for key, value
                in components.items()
            },
            "weights": dict(
                self.WEIGHTS
            ),
            "explanation": (
                "Heuristic evidence-grounding "
                "confidence for the verification "
                "outcome. It is not a probability "
                "that the claim is factually true "
                "and has not yet been empirically "
                "calibrated."
            ),
        }

    def _evidence_coverage(
        self,
        facts: list[dict],
        history: dict | None,
    ):
        count = len(
            self._evidence_ids(
                facts,
                history,
            )
        )

        if count == 0:
            return 0.0

        if count == 1:
            return 0.75

        if count == 2:
            return 0.90

        return 1.0

    def _provenance_completeness(
        self,
        facts: list[dict],
        history: dict | None,
    ):
        scores = []

        for fact in facts:
            evidence = fact.get(
                "evidence",
                {},
            )

            attributes = evidence.get(
                "attributes",
                {},
            )

            checks = [
                bool(
                    evidence.get(
                        "edgeId"
                    )
                ),
                bool(
                    evidence.get(
                        "primaryKnowledgeSource"
                    )
                    or evidence.get(
                        "sourceDataset"
                    )
                ),
                bool(
                    evidence.get(
                        "references"
                    )
                    or attributes.get(
                        "source_url"
                    )
                ),
                bool(
                    attributes.get(
                        "source_text"
                    )
                    or attributes.get(
                        "source_date"
                    )
                    or evidence.get(
                        "maxPhaseForIndication"
                    )
                    is not None
                ),
            ]

            scores.append(
                sum(
                    checks
                )
                / len(
                    checks
                )
            )

        for item in (
            self._history_evidence(
                history
            )
        ):
            checks = [
                bool(
                    item.get(
                        "eventId"
                    )
                ),
                bool(
                    item.get(
                        "sourceUrl"
                    )
                ),
                bool(
                    item.get(
                        "sourceText"
                    )
                ),
                bool(
                    item.get(
                        "dateStart"
                    )
                    or item.get(
                        "sourceLinks"
                    )
                ),
            ]

            scores.append(
                sum(
                    checks
                )
                / len(
                    checks
                )
            )

        if not scores:
            return 0.0

        return (
            sum(
                scores
            )
            / len(
                scores
            )
        )

    def _relation_certainty(
        self,
        verification_type: str,
        relationships: list[dict],
    ):
        if (
            verification_type
            == "history"
        ):
            return 1.0

        scores = [
            float(
                relationship.get(
                    "score",
                    0.0,
                )
            )
            for relationship
            in relationships
        ]

        if not scores:
            return 0.0

        return min(
            max(
                max(
                    scores
                ),
                0.0,
            ),
            1.0,
        )

    def _entity_link_certainty(
        self,
        verification_type: str,
        entities: list[dict],
    ):
        if not entities:
            if verification_type in {
                "history",
                "who",
            }:
                return 1.0

            return 0.0

        scores = []

        for entity in entities:
            candidates = entity.get(
                "candidates",
                [],
            )

            if not candidates:
                scores.append(
                    0.0
                )

                continue

            scores.append(
                float(
                    candidates[
                        0
                    ].get(
                        "score",
                        0.0,
                    )
                )
            )

        return min(
            max(
                sum(
                    scores
                )
                / len(
                    scores
                ),
                0.0,
            ),
            1.0,
        )

    def _evidence_agreement(
        self,
        facts: list[dict],
        history: dict | None,
    ):
        evidence_count = (
            len(
                facts
            )
            + len(
                self._history_evidence(
                    history
                )
            )
        )

        if evidence_count == 0:
            return 0.0

        stances = set()

        for fact in facts:
            attributes = (
                fact.get(
                    "evidence",
                    {},
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

                if value:
                    stances.add(
                        str(
                            value
                        )
                        .strip()
                        .lower()
                    )

        if not stances:
            return 1.0

        positive = {
            "supported",
            "supports",
            "support",
            "positive",
        }

        negative = {
            "contradicted",
            "contradicts",
            "contradiction",
            "refuted",
            "refutes",
            "negative",
        }

        if (
            stances
            & positive
            and stances
            & negative
        ):
            return 0.30

        return 1.0

    def _source_diversity(
        self,
        facts: list[dict],
        history: dict | None,
    ):
        sources = set()

        for fact in facts:
            evidence = fact.get(
                "evidence",
                {},
            )

            attributes = evidence.get(
                "attributes",
                {},
            )

            source = (
                attributes.get(
                    "source_id"
                )
                or attributes.get(
                    "source_url"
                )
                or evidence.get(
                    "primaryKnowledgeSource"
                )
                or evidence.get(
                    "sourceDataset"
                )
            )

            if source:
                sources.add(
                    str(
                        source
                    )
                )

        for item in (
            self._history_evidence(
                history
            )
        ):
            source = (
                item.get(
                    "sourceUrl"
                )
                or item.get(
                    "eventId"
                )
            )

            if source:
                sources.add(
                    str(
                        source
                    )
                )

        count = len(
            sources
        )

        if count == 0:
            return 0.0

        if count == 1:
            return 0.65

        if count == 2:
            return 0.85

        return 1.0

    def _recency(
        self,
        relationships: list[dict],
        facts: list[dict],
    ):
        roles = {
            relationship.get(
                "relationship"
            )
            for relationship
            in relationships
        }

        if not (
            roles
            & self.TEMPORAL_ROLES
        ):
            return 1.0

        dates = []

        for fact in facts:
            attributes = (
                fact.get(
                    "evidence",
                    {},
                )
                .get(
                    "attributes",
                    {},
                )
            )

            value = (
                attributes.get(
                    "as_of_date"
                )
                or attributes.get(
                    "source_date"
                )
            )

            parsed = (
                self._parse_date(
                    value
                )
            )

            if parsed is not None:
                dates.append(
                    parsed
                )

        if not dates:
            return 0.40

        latest = max(
            dates
        )

        today = datetime.now(
            timezone.utc
        ).date()

        age_days = max(
            (
                today
                - latest
            ).days,
            0,
        )

        if age_days <= 90:
            return 1.0

        if age_days <= 180:
            return 0.90

        if age_days <= 365:
            return 0.75

        if age_days <= 730:
            return 0.50

        return 0.25

    def _parse_date(
        self,
        value,
    ):
        if not value:
            return None

        try:
            return date.fromisoformat(
                str(
                    value
                )
                .strip()[
                    :10
                ]
            )

        except ValueError:
            return None

    def _evidence_ids(
        self,
        facts: list[dict],
        history: dict | None,
    ):
        identifiers = set()

        for index, fact in enumerate(
            facts
        ):
            edge_id = (
                fact.get(
                    "evidence",
                    {},
                )
                .get(
                    "edgeId"
                )
            )

            identifiers.add(
                edge_id
                or (
                    f"fact:"
                    f"{index}"
                )
            )

        for index, item in enumerate(
            self._history_evidence(
                history
            )
        ):
            identifiers.add(
                item.get(
                    "eventId"
                )
                or (
                    f"history:"
                    f"{index}"
                )
            )

        return identifiers

    def _history_evidence(
        self,
        history: dict | None,
    ):
        if not history:
            return []

        return history.get(
            "evidence",
            [],
        )

    def _level(
        self,
        score: float,
    ):
        if score >= 0.85:
            return "high"

        if score >= 0.65:
            return "medium"

        return "low"