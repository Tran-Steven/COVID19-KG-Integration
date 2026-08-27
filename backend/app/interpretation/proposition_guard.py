import re

from app.interpretation.proposition_guard_base import (
    PropositionGuard as BasePropositionGuard,
)
from app.interpretation.proposition_semantics import (
    PropositionSemantics,
)


class PropositionGuard(
    BasePropositionGuard
):
    def __init__(
        self,
    ):
        self.semantics = (
            PropositionSemantics()
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
            self._cause_assertion_extended(
                normalized
            )
        )

        if assertion is None:
            if self._has_cause_language(
                normalized
            ):
                return self._decision(
                    status=(
                        self.NOT_VERIFIABLE
                    ),
                    reason=(
                        "Causal evidence was "
                        "retrieved, but the claim "
                        "does not assert the same "
                        "COVID-19 causal proposition "
                        "represented by that evidence."
                    ),
                    evidence_count=0,
                    clear_facts=True,
                )

            return super().cause_decision(
                text=text,
                entities=entities,
                facts=facts,
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

        matches = (
            self._cause_matches_evidence(
                claimed_cause,
                evidence_subjects,
            )
        )

        if matches:
            if assertion[
                "negated"
            ]:
                return self._decision(
                    status=(
                        self.CONTRADICTED
                    ),
                    reason=(
                        "The claim negates the "
                        "SARS-CoV-2 causal "
                        "relationship directly "
                        "represented by WHO "
                        "evidence."
                    ),
                    evidence_count=len(
                        cause_facts
                    ),
                    clear_facts=False,
                )

            return None

        if assertion[
            "negated"
        ]:
            return self._decision(
                status=self.SUPPORTED,
                reason=(
                    "The claim rejects an "
                    "alternative causal attribution "
                    "while WHO evidence identifies "
                    "SARS-CoV-2 as the cause of "
                    "COVID-19."
                ),
                evidence_count=len(
                    cause_facts
                ),
                clear_facts=False,
            )

        return self._decision(
            status=self.CONTRADICTED,
            reason=(
                "The claim attributes COVID-19 "
                "to a different cause, while WHO "
                "evidence identifies SARS-CoV-2 "
                "as the cause of COVID-19."
            ),
            evidence_count=len(
                cause_facts
            ),
            clear_facts=False,
        )

    def _cause_assertion_extended(
        self,
        text: str,
    ):
        base = self._cause_assertion(
            text
        )

        if base is not None:
            return base

        patterns = (
            (
                (
                    r"^(?P<cause>.+?) "
                    r"(?:is )?incapable of "
                    r"(?:causing|producing|"
                    r"giving rise to) "
                    r"covid(?: 19)?\b"
                ),
                True,
            ),
            (
                (
                    r"^(?P<cause>.+?) "
                    r"(?:gives rise to|give rise to|"
                    r"produces|produce|"
                    r"underlies|underlie) "
                    r"covid(?: 19)?\b"
                ),
                False,
            ),
            (
                (
                    r"^(?P<cause>.+?) "
                    r"is the virus that causes "
                    r"covid(?: 19)?\b"
                ),
                False,
            ),
            (
                (
                    r"^covid(?: 19)? "
                    r"is the disease caused by "
                    r"(?P<cause>.+)$"
                ),
                False,
            ),
            (
                (
                    r"^(?P<cause>.+?) "
                    r"(?:is )?(?:the )?"
                    r"(?:etiologic|etiological|"
                    r"causative) agent "
                    r"(?:of|for) "
                    r"covid(?: 19)?\b"
                ),
                False,
            ),
            (
                (
                    r"^(?P<cause>.+?) "
                    r"(?:is )?(?:the )?"
                    r"pathogen responsible for "
                    r"covid(?: 19)?\b"
                ),
                False,
            ),
        )

        for (
            pattern,
            negated,
        ) in patterns:
            match = re.search(
                pattern,
                text,
            )

            if not match:
                continue

            return {
                "cause": (
                    match.group(
                        "cause"
                    )
                    .strip()
                ),
                "negated": (
                    negated
                ),
            }

        return None

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