import re


class PropositionGuard:
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_VERIFIABLE = "NOT_VERIFIABLE_WITH_CURRENT_KG"

    NEGATION_PATTERN = (
        r"(?:"
        r"does not"
        r"|do not"
        r"|did not"
        r"|doesn t"
        r"|don t"
        r"|didn t"
        r"|cannot"
        r"|can not"
        r"|can t"
        r"|could not"
        r"|couldn t"
        r"|may not"
        r"|might not"
        r"|will not"
        r"|won t"
        r"|would not"
        r"|wouldn t"
        r"|should not"
        r"|shouldn t"
        r"|never"
        r")"
    )

    CAUSE_LANGUAGE = (
        "cause",
        "caused by",
        "causative",
        "responsible for",
        "result from",
        "results from",
        "resulted from",
        "due to",
        "attributable to",
    )

    TRANSMISSION_LANGUAGE = (
        "spread",
        "spreads",
        "transmit",
        "transmits",
        "transmitted",
        "transmission",
        "airborne",
        "aerosol",
        "aerosols",
        "respiratory particle",
        "respiratory particles",
        "droplet",
        "droplets",
        "close contact",
        "face to face",
        "indoor",
        "indoors",
        "surface",
        "surfaces",
        "fomite",
        "foodborne",
        "food borne",
        "saliva",
        "spit",
        "spitting",
    )

    TRANSMISSION_IMPORTANCE = (
        "major route",
        "main route",
        "primary route",
        "dominant route",
        "minor route",
        "common route",
        "rare route",
        "important route",
        "major way",
        "main way",
        "primary way",
        "dominant way",
    )

    def cause_decision(
        self,
        text: str,
        entities: list[dict],
        facts: list[dict],
    ):
        cause_facts = [
            fact
            for fact in facts
            if self._is_cause_predicate(
                fact.get(
                    "predicate",
                    "",
                )
            )
        ]

        if not cause_facts:
            return None

        normalized = self._normalize(
            text
        )

        assertion = (
            self._cause_assertion(
                normalized
            )
        )

        if assertion is None:
            if self._has_cause_language(
                normalized
            ):
                return None

            return self._decision(
                status=self.NOT_VERIFIABLE,
                reason=(
                    "Retrieved causal evidence "
                    "does not correspond to a "
                    "causal proposition expressed "
                    "by this claim."
                ),
                evidence_count=0,
                clear_facts=True,
            )

        claimed_cause = assertion[
            "cause"
        ]

        evidence_subjects = [
            self._normalize(
                fact.get(
                    "subject",
                    {},
                ).get(
                    "name",
                    "",
                )
            )
            for fact in cause_facts
            if fact.get(
                "subject",
                {},
            ).get(
                "name"
            )
        ]

        if self._cause_matches_evidence(
            claimed_cause,
            evidence_subjects,
        ):
            return None

        if self._cause_is_linked(
            claimed_cause,
            entities,
        ):
            return self._decision(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The claimed alternative cause "
                    "maps to a known knowledge graph "
                    "concept, but the retrieved "
                    "causal evidence does not "
                    "establish the asserted positive "
                    "or negative relationship."
                ),
                evidence_count=0,
                clear_facts=True,
            )

        return self._decision(
            status=self.NOT_VERIFIABLE,
            reason=(
                "The claim names an alternative "
                "cause that cannot be linked to a "
                "supported cause proposition in the "
                "current knowledge graph."
            ),
            evidence_count=0,
            clear_facts=True,
        )

    def transmission_decision(
        self,
        text: str,
        facts: list[dict],
    ):
        transmission_facts = [
            fact
            for fact in facts
            if self._is_transmission_predicate(
                fact.get(
                    "predicate",
                    "",
                )
            )
        ]

        if not transmission_facts:
            return None

        normalized = self._normalize(
            text
        )

        if self._exclusive_claim(
            normalized
        ):
            return None

        if not self._has_transmission_language(
            normalized
        ):
            return self._decision(
                status=self.NOT_VERIFIABLE,
                reason=(
                    "Retrieved transmission "
                    "evidence does not correspond "
                    "to a transmission proposition "
                    "expressed by this claim."
                ),
                evidence_count=0,
                clear_facts=True,
            )

        targets = (
            self._transmission_targets(
                normalized
            )
        )

        evidence_objects = [
            self._normalize(
                fact.get(
                    "object",
                    {},
                ).get(
                    "name",
                    "",
                )
            )
            for fact in transmission_facts
            if fact.get(
                "object",
                {},
            ).get(
                "name"
            )
        ]

        if any(
            phrase in normalized
            for phrase
            in self.TRANSMISSION_IMPORTANCE
        ):
            targets_match = (
                bool(targets)
                and all(
                    self._transmission_target_matches(
                        target,
                        evidence_objects,
                    )
                    for target
                    in targets
                )
            )

            return self._decision(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The knowledge graph represents "
                    "transmission routes and risk "
                    "contexts, but does not establish "
                    "the claim's ranking of a route "
                    "as major, minor, primary, or "
                    "otherwise dominant."
                ),
                evidence_count=(
                    len(
                        transmission_facts
                    )
                    if targets_match
                    else 0
                ),
                clear_facts=(
                    not targets_match
                ),
            )

        if targets:
            unmatched = [
                target
                for target
                in targets
                if not self._transmission_target_matches(
                    target,
                    evidence_objects,
                )
            ]

            if unmatched:
                return self._decision(
                    status=(
                        self.INSUFFICIENT_EVIDENCE
                    ),
                    reason=(
                        "Transmission evidence was "
                        "retrieved, but it does not "
                        "directly represent the "
                        "specific route asserted by "
                        "the claim."
                    ),
                    evidence_count=0,
                    clear_facts=True,
                )

            if self._is_negated_claim(
                normalized
            ):
                return self._decision(
                    status=self.CONTRADICTED,
                    reason=(
                        "The claim negates a "
                        "specific transmission route "
                        "that is directly represented "
                        "by the retrieved evidence."
                    ),
                    evidence_count=len(
                        transmission_facts
                    ),
                    clear_facts=False,
                )

            return None

        if self._is_negated_claim(
            normalized
        ):
            if self._generic_transmission_negation(
                normalized
            ):
                return self._decision(
                    status=self.CONTRADICTED,
                    reason=(
                        "The claim broadly negates "
                        "SARS-CoV-2 transmission, "
                        "while the retrieved evidence "
                        "represents supported "
                        "transmission routes."
                    ),
                    evidence_count=len(
                        transmission_facts
                    ),
                    clear_facts=False,
                )

            return self._decision(
                status=(
                    self.INSUFFICIENT_EVIDENCE
                ),
                reason=(
                    "The claim contains a negative "
                    "transmission statement, but the "
                    "retrieved evidence does not "
                    "identify the same specific "
                    "route strongly enough to treat "
                    "the propositions as direct "
                    "contradictions."
                ),
                evidence_count=0,
                clear_facts=True,
            )

        return None

    def _cause_assertion(
        self,
        text: str,
    ):
        passive_patterns = (
            (
                r"\bcovid(?: 19)? "
                r"(?:is|was) "
                r"(?P<neg>not )?"
                r"caused by "
                r"(?P<cause>.+)$"
            ),
            (
                r"\bcovid(?: 19)? "
                r"(?:is|was) "
                r"(?P<neg>not )?"
                r"due to "
                r"(?P<cause>.+)$"
            ),
            (
                r"\bcovid(?: 19)? "
                r"(?:results?|resulted) "
                r"from "
                r"(?P<cause>.+)$"
            ),
            (
                r"(?:the )?cause of "
                r"covid(?: 19)? "
                r"(?:is|was) "
                r"(?P<neg>not )?"
                r"(?P<cause>.+)$"
            ),
        )

        for pattern in passive_patterns:
            match = re.search(
                pattern,
                text,
            )

            if match:
                return {
                    "cause": (
                        match.group(
                            "cause"
                        ).strip()
                    ),
                    "negated": bool(
                        match.groupdict()
                        .get(
                            "neg"
                        )
                    ),
                }

        active_pattern = re.search(
            (
                r"^(?P<cause>.+?) "
                r"(?:(?P<neg>"
                + self.NEGATION_PATTERN
                + r") )?"
                r"causes? "
                r"covid(?: 19)?\b"
            ),
            text,
        )

        if active_pattern:
            return {
                "cause": (
                    active_pattern.group(
                        "cause"
                    ).strip()
                ),
                "negated": bool(
                    active_pattern.group(
                        "neg"
                    )
                ),
            }

        responsible_pattern = re.search(
            (
                r"^(?P<cause>.+?) "
                r"(?:(?P<neg>"
                + self.NEGATION_PATTERN
                + r") )?"
                r"(?:is )?responsible for "
                r"covid(?: 19)?\b"
            ),
            text,
        )

        if responsible_pattern:
            return {
                "cause": (
                    responsible_pattern.group(
                        "cause"
                    ).strip()
                ),
                "negated": bool(
                    responsible_pattern.group(
                        "neg"
                    )
                ),
            }

        return None

    def _cause_matches_evidence(
        self,
        cause: str,
        evidence_subjects: list[str],
    ):
        if not evidence_subjects:
            return False

        if self._canonical_cause_reference(
            cause
        ):
            return any(
                self._canonical_cause_reference(
                    subject
                )
                for subject
                in evidence_subjects
            )

        if self._generic_virus_reference(
            cause
        ):
            return any(
                self._canonical_cause_reference(
                    subject
                )
                for subject
                in evidence_subjects
            )

        normalized_cause = (
            self._normalize(
                cause
            )
        )

        if not normalized_cause:
            return False

        return any(
            (
                normalized_cause
                == subject
                or (
                    len(
                        normalized_cause
                    ) >= 5
                    and normalized_cause
                    in subject
                )
                or (
                    len(
                        subject
                    ) >= 5
                    and subject
                    in normalized_cause
                )
            )
            for subject
            in evidence_subjects
        )

    def _cause_is_linked(
        self,
        cause: str,
        entities: list[dict],
    ):
        normalized_cause = (
            self._normalize(
                cause
            )
        )

        if not normalized_cause:
            return False

        for entity in entities:
            candidates = entity.get(
                "candidates"
            ) or []

            if not candidates:
                continue

            names = [
                entity.get(
                    "text",
                    "",
                )
            ]

            for candidate in candidates:
                names.append(
                    candidate.get(
                        "name",
                        "",
                    )
                )

                names.extend(
                    candidate.get(
                        "aliases",
                        [],
                    )
                    or []
                )

            for name in names:
                normalized_name = (
                    self._normalize(
                        str(name)
                    )
                )

                if not normalized_name:
                    continue

                if (
                    normalized_name
                    == normalized_cause
                    or normalized_name
                    in normalized_cause
                    or normalized_cause
                    in normalized_name
                ):
                    return True

        return False

    def _canonical_cause_reference(
        self,
        text: str,
    ):
        normalized = self._normalize(
            text
        )

        return any(
            value in normalized
            for value in (
                "sars cov 2",
                (
                    "severe acute respiratory "
                    "syndrome coronavirus 2"
                ),
            )
        )

    def _generic_virus_reference(
        self,
        text: str,
    ):
        normalized = self._normalize(
            text
        )

        return normalized in {
            "virus",
            "a virus",
            "the virus",
            "coronavirus",
            "a coronavirus",
            "the coronavirus",
            "sars coronavirus",
        }

    def _has_cause_language(
        self,
        text: str,
    ):
        return any(
            value in text
            for value
            in self.CAUSE_LANGUAGE
        )

    def _is_cause_predicate(
        self,
        predicate: str,
    ):
        normalized = self._normalize(
            predicate
        )

        return (
            normalized == "causes"
            or normalized.endswith(
                " causes"
            )
        )

    def _is_transmission_predicate(
        self,
        predicate: str,
    ):
        normalized = self._normalize(
            predicate
        )

        return (
            "transmitted via"
            in normalized
            or (
                "transmission risk context"
                in normalized
            )
        )

    def _has_transmission_language(
        self,
        text: str,
    ):
        return any(
            value in text
            for value
            in self.TRANSMISSION_LANGUAGE
        )

    def _transmission_targets(
        self,
        text: str,
    ):
        targets = []

        if any(
            value in text
            for value in (
                "airborne",
                "through the air",
                "aerosol",
                "aerosols",
                "respiratory particle",
                "respiratory particles",
                "droplet",
                "droplets",
            )
        ):
            targets.append(
                "respiratory_particles"
            )

        if any(
            value in text
            for value in (
                "surface",
                "surfaces",
                "fomite",
                "fomites",
            )
        ):
            targets.append(
                "surface_contact"
            )

        if any(
            value in text
            for value in (
                "close contact",
                "face to face",
                "face-to-face",
            )
        ):
            targets.append(
                "close_contact"
            )

        if any(
            value in text
            for value in (
                "indoor",
                "indoors",
                "closed indoor",
                "closed space",
                "closed spaces",
            )
        ):
            targets.append(
                "indoor_space"
            )

        if any(
            value in text
            for value in (
                "food",
                "foodborne",
                "food borne",
                "eating",
                "ingestion",
                "ingest",
            )
        ):
            targets.append(
                "food_ingestion"
            )

        if any(
            value in text
            for value in (
                "saliva",
                "spit",
                "spitting",
            )
        ):
            targets.append(
                "saliva"
            )

        return list(
            dict.fromkeys(
                targets
            )
        )

    def _transmission_target_matches(
        self,
        target: str,
        evidence_objects: list[str],
    ):
        if target == "respiratory_particles":
            return any(
                (
                    "respiratory particle"
                    in value
                    or "respiratory particles"
                    in value
                )
                for value
                in evidence_objects
            )

        if target == "surface_contact":
            return any(
                (
                    "contaminated surface"
                    in value
                    or "surface contact"
                    in value
                )
                for value
                in evidence_objects
            )

        if target == "close_contact":
            return any(
                "close contact"
                in value
                for value
                in evidence_objects
            )

        if target == "indoor_space":
            return any(
                (
                    "indoor"
                    in value
                    or "closed space"
                    in value
                )
                for value
                in evidence_objects
            )

        if target == "food_ingestion":
            return any(
                (
                    "food"
                    in value
                    or "ingest"
                    in value
                )
                for value
                in evidence_objects
            )

        if target == "saliva":
            return any(
                (
                    "saliva"
                    in value
                    or "spit"
                    in value
                )
                for value
                in evidence_objects
            )

        return False

    def _generic_transmission_negation(
        self,
        text: str,
    ):
        subject = (
            r"(?:"
            r"covid(?: 19)?"
            r"|sars cov 2"
            r"|severe acute respiratory "
            r"syndrome coronavirus 2"
            r")"
        )

        return bool(
            re.search(
                (
                    r"\b"
                    + subject
                    + r"\b.*\b"
                    + self.NEGATION_PATTERN
                    + r"\b.*\b"
                    r"(?:spread|transmit|transmission)"
                ),
                text,
            )
            or re.search(
                (
                    r"\b"
                    + subject
                    + r"\b.*\b"
                    r"not transmissible\b"
                ),
                text,
            )
        )

    def _exclusive_claim(
        self,
        text: str,
    ):
        return any(
            re.search(
                (
                    r"\b"
                    + re.escape(
                        value
                    )
                    + r"\b"
                ),
                text,
            )
            is not None
            for value in (
                "only",
                "solely",
                "exclusively",
            )
        )

    def _is_negated_claim(
        self,
        text: str,
    ):
        return bool(
            re.search(
                (
                    r"\bnot\b"
                    r"|\bnever\b"
                    r"|\bcannot\b"
                    r"|\bcan not\b"
                    r"|n t\b"
                ),
                text,
            )
        )

    def _decision(
        self,
        status: str,
        reason: str,
        evidence_count: int,
        clear_facts: bool,
    ):
        return {
            "status": status,
            "reason": reason,
            "evidenceCount": evidence_count,
            "clearFacts": clear_facts,
        }

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