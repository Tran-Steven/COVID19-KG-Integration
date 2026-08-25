class GroundingContextBuilder:
    def __init__(
        self,
        reference_limit: int = 8,
    ):
        self.reference_limit = reference_limit

    def build(
        self,
        text: str,
        entities: list[dict],
        relation: dict,
        relationships: list[dict],
        facts: list[dict],
    ):
        sections = [
            self._query_section(text),
            self._entity_section(entities),
            self._relation_section(
                relation,
                relationships,
            ),
            self._evidence_section(facts),
            self._rules_section(),
        ]

        return "\n\n".join(
            section
            for section in sections
            if section
        )

    def build_history(
        self,
        text: str,
        history: dict,
    ):
        sections = [
            self._query_section(text),
            self._history_interpretation_section(
                history
            ),
            self._history_answer_section(
                history
            ),
            self._history_evidence_section(
                history
            ),
            self._history_rules_section(),
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

            candidate = candidates[0]

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
                    (int, float),
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
                        f"link_score={score_text}",
                    ]
                )
            )

            found = True

        if not found:
            lines.append(
                "No entities were linked to the knowledge graph."
            )

        return "\n".join(lines)

    def _relation_section(
        self,
        relation: dict,
        relationships: list[dict],
    ):
        lines = [
            "INTERPRETED RELATION"
        ]

        relation_text = relation.get(
            "text"
        )

        if relation_text:
            lines.append(
                f"query_relation={relation_text}"
            )
        else:
            lines.append(
                "query_relation=unknown"
            )

        if relationships:
            best = relationships[0]

            lines.append(
                f"kg_predicate={best['relationship']}"
            )

            lines.append(
                f"relation_score={best['score']:.2f}"
            )
        else:
            lines.append(
                "kg_predicate=unresolved"
            )

        return "\n".join(lines)

    def _evidence_section(
        self,
        facts: list[dict],
    ):
        lines = [
            "KNOWLEDGE GRAPH EVIDENCE"
        ]

        if not facts:
            lines.append(
                "No matching knowledge graph evidence was retrieved."
            )

            return "\n".join(lines)

        for index, fact in enumerate(
            facts,
            start=1,
        ):
            subject = fact["subject"]
            object_entity = fact["object"]
            evidence = fact["evidence"]

            lines.append(
                " ".join(
                    [
                        f"[{index}]",
                        f"{subject['id']}",
                        f"{subject['name']}",
                        f"--{fact['predicate']}-->",
                        f"{object_entity['id']}",
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

            phase = evidence.get(
                "maxPhaseForIndication"
            )

            if phase is not None:
                lines.append(
                    f"max_phase_for_indication={phase}"
                )

            edge_id = evidence.get(
                "edgeId"
            )

            if edge_id:
                lines.append(
                    f"evidence_id={edge_id}"
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
                    + ", ".join(selected)
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

        return "\n".join(lines)

    def _history_interpretation_section(
        self,
        history: dict,
    ):
        lines = [
            "INTERPRETED HISTORY QUERY"
        ]

        interpretation = history.get(
            "interpretation"
        )

        if not interpretation:
            lines.append(
                "No supported history intent was resolved."
            )

            return "\n".join(lines)

        lines.append(
            "intent="
            f"{interpretation.get('intent')}"
        )

        lines.append(
            "canonical_subject="
            f"{interpretation.get('canonicalSubject')}"
        )

        lines.append(
            "event_type="
            f"{interpretation.get('eventType')}"
        )

        lines.append(
            "requested_field="
            f"{interpretation.get('requestedField')}"
        )

        semantic_role = (
            interpretation.get(
                "semanticRole"
            )
        )

        if semantic_role:
            lines.append(
                "semantic_role="
                f"{semantic_role}"
            )

        return "\n".join(lines)

    def _history_answer_section(
        self,
        history: dict,
    ):
        lines = [
            "RETRIEVED HISTORY RESULT"
        ]

        lines.append(
            "status="
            f"{history.get('status')}"
        )

        answer = history.get(
            "answer"
        )

        if not answer:
            lines.append(
                "No source-backed history result was retrieved."
            )

            return "\n".join(lines)

        lines.append(
            f"{answer.get('field')}="
            f"{answer.get('value')}"
        )

        qualification = (
            answer.get(
                "qualification"
            )
        )

        if qualification:
            lines.append(
                "qualification="
                f"{qualification}"
            )

        return "\n".join(lines)

    def _history_evidence_section(
        self,
        history: dict,
    ):
        lines = [
            "WHO HISTORY EVIDENCE"
        ]

        evidence = history.get(
            "evidence",
            [],
        )

        if not evidence:
            lines.append(
                "No matching WHO history evidence was retrieved."
            )

            return "\n".join(lines)

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            lines.append(
                f"[{index}] "
                f"{item.get('eventName')}"
            )

            event_id = item.get(
                "eventId"
            )

            if event_id:
                lines.append(
                    f"event_id={event_id}"
                )

            event_type = item.get(
                "eventType"
            )

            if event_type:
                lines.append(
                    f"event_type={event_type}"
                )

            date_start = item.get(
                "dateStart"
            )

            date_end = item.get(
                "dateEnd"
            )

            if date_start:
                if (
                    date_end
                    and date_end
                    != date_start
                ):
                    lines.append(
                        "date="
                        f"{date_start}..{date_end}"
                    )
                else:
                    lines.append(
                        f"date={date_start}"
                    )

            semantic_role = (
                item.get(
                    "semanticRole"
                )
            )

            if semantic_role:
                lines.append(
                    "semantic_role="
                    f"{semantic_role}"
                )

            related_name = (
                item.get(
                    "relatedEntityName"
                )
            )

            related_id = (
                item.get(
                    "relatedEntityId"
                )
            )

            if related_name:
                if related_id:
                    lines.append(
                        "related_entity="
                        f"{related_id} "
                        f"{related_name}"
                    )
                else:
                    lines.append(
                        "related_entity="
                        f"{related_name}"
                    )

            source_text = item.get(
                "sourceText"
            )

            if source_text:
                lines.append(
                    f"source_text={source_text}"
                )

            source_url = item.get(
                "sourceUrl"
            )

            if source_url:
                lines.append(
                    f"source={source_url}"
                )

            source_links = item.get(
                "sourceLinks",
                [],
            )

            if source_links:
                selected = source_links[
                    :self.reference_limit
                ]

                lines.append(
                    "source_links="
                    + ", ".join(
                        selected
                    )
                )

        return "\n".join(lines)

    def _rules_section(self):
        return "\n".join(
            [
                "GROUNDING RULES",
                "Use the knowledge graph evidence as external grounding for the response.",
                "Do not claim that the knowledge graph supports a statement unless a retrieved fact supports it.",
                "Do not convert clinical-trial evidence into an approved-treatment claim.",
                "Treat biolink:treats, biolink:in_clinical_trials_for, and biolink:studied_to_treat as different claims.",
                "If no relevant evidence was retrieved, state that the knowledge graph provides insufficient evidence for the requested relation.",
                "Preserve uncertainty and provenance when describing evidence.",
            ]
        )

    def _history_rules_section(self):
        return "\n".join(
            [
                "GROUNDING RULES",
                "Use the retrieved WHO event as source-backed historical evidence.",
                "Preserve the distinction between a reported outbreak event and biological identification of SARS-CoV-2.",
                "Do not rewrite reported_case_location as a universal first_found_in assertion.",
                "Do not strengthen the WHO source statement beyond what it explicitly says.",
                "Preserve the qualification attached to the retrieved result.",
                "Preserve source attribution when presenting the historical evidence.",
            ]
        )