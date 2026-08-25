class WhoGroundingContextBuilder:
    def __init__(
        self,
        reference_limit: int = 8,
    ):
        self.reference_limit = (
            reference_limit
        )

    def build(
        self,
        text: str,
        entities: list[dict],
        relationships: list[dict],
        facts: list[dict],
    ):
        sections = [
            self._query_section(
                text
            ),
            self._entity_section(
                entities
            ),
            self._relationship_section(
                relationships
            ),
            self._evidence_section(
                facts
            ),
            self._rules_section(),
        ]

        return "\n\n".join(
            section
            for section in sections
            if section
        )

    def _query_section(
        self,
        text: str,
    ):
        return "\n".join(
            [
                "USER QUERY",
                text,
            ]
        )

    def _entity_section(
        self,
        entities: list[dict],
    ):
        lines = [
            "LINKED ENTITIES"
        ]

        found = False

        for entity in entities:
            candidates = entity.get(
                "candidates",
                [],
            )

            if not candidates:
                continue

            candidate = candidates[
                0
            ]

            categories = ", ".join(
                candidate.get(
                    "categories",
                    [],
                )
            )

            score = candidate.get(
                "score"
            )

            score_text = (
                f"{score:.2f}"
                if isinstance(
                    score,
                    (
                        int,
                        float,
                    ),
                )
                else "unknown"
            )

            lines.append(
                " | ".join(
                    [
                        entity["text"],
                        candidate["id"],
                        candidate["name"],
                        categories,
                        (
                            "link_score="
                            f"{score_text}"
                        ),
                    ]
                )
            )

            found = True

        if not found:
            lines.append(
                "No ordinary KG entities were required "
                "for this WHO evidence route."
            )

        return "\n".join(
            lines
        )

    def _relationship_section(
        self,
        relationships: list[dict],
    ):
        lines = [
            "WHO VERIFICATION RELATION"
        ]

        if not relationships:
            lines.append(
                "semantic_role=unresolved"
            )

            return "\n".join(
                lines
            )

        for relationship in relationships:
            lines.append(
                "semantic_role="
                f"{relationship['relationship']}"
            )

        return "\n".join(
            lines
        )

    def _evidence_section(
        self,
        facts: list[dict],
    ):
        lines = [
            "WHO KNOWLEDGE GRAPH EVIDENCE"
        ]

        if not facts:
            lines.append(
                "No matching WHO evidence "
                "was retrieved."
            )

            return "\n".join(
                lines
            )

        for index, fact in enumerate(
            facts,
            start=1,
        ):
            subject = fact[
                "subject"
            ]

            object_entity = fact[
                "object"
            ]

            evidence = fact[
                "evidence"
            ]

            attributes = evidence.get(
                "attributes",
                {},
            )

            lines.append(
                " ".join(
                    [
                        f"[{index}]",
                        subject["id"],
                        subject["name"],
                        (
                            "--"
                            f"{fact['predicate']}"
                            "-->"
                        ),
                        object_entity["id"],
                        object_entity["name"],
                    ]
                )
            )

            source = evidence.get(
                "primaryKnowledgeSource"
            )

            if source:
                lines.append(
                    f"source={source}"
                )

            dataset = evidence.get(
                "sourceDataset"
            )

            if dataset:
                lines.append(
                    f"dataset={dataset}"
                )

            source_id = attributes.get(
                "source_id"
            )

            if source_id:
                lines.append(
                    f"source_id={source_id}"
                )

            source_date = attributes.get(
                "source_date"
            )

            if source_date:
                lines.append(
                    f"source_date={source_date}"
                )

            source_section = (
                attributes.get(
                    "source_section"
                )
            )

            if source_section:
                lines.append(
                    "source_section="
                    f"{source_section}"
                )

            source_text = attributes.get(
                "source_text"
            )

            if source_text:
                lines.append(
                    f"source_text={source_text}"
                )

            source_url = attributes.get(
                "source_url"
            )

            if source_url:
                lines.append(
                    f"source_url={source_url}"
                )

            assessment = attributes.get(
                "assessment"
            )

            if assessment:
                lines.append(
                    f"assessment={assessment}"
                )

            as_of_date = attributes.get(
                "as_of_date"
            )

            if as_of_date:
                lines.append(
                    f"as_of_date={as_of_date}"
                )

            earliest = attributes.get(
                "earliest_documented_sample"
            )

            if earliest:
                lines.append(
                    "earliest_documented_sample="
                    f"{earliest}"
                )

            designation = attributes.get(
                "designation_date"
            )

            if designation:
                lines.append(
                    "designation_date="
                    f"{designation}"
                )

            references = evidence.get(
                "references",
                [],
            )

            if references:
                selected = references[
                    :self.reference_limit
                ]

                lines.append(
                    "references="
                    + ", ".join(
                        selected
                    )
                )

                remaining = (
                    len(references)
                    - len(selected)
                )

                if remaining > 0:
                    lines.append(
                        "additional_reference_count="
                        f"{remaining}"
                    )

        return "\n".join(
            lines
        )

    def _rules_section(self):
        return "\n".join(
            [
                "GROUNDING RULES",
                "Use the WHO source text and semantic role as the external grounding for the response.",
                "Do not strengthen a WHO statement beyond the wording preserved in the evidence.",
                "Preserve dates, qualifications, and uncertainty when they are present.",
                "For origin questions, distinguish evidence supporting a hypothesis from evidence that rules a hypothesis out.",
                "Do not convert an inconclusive origin assessment into a definitive claim.",
                "For current-risk and variant claims, preserve the source date because those facts can change over time.",
                "If no matching WHO evidence was retrieved, state that the WHO graph provides insufficient evidence for the requested claim.",
            ]
        )
