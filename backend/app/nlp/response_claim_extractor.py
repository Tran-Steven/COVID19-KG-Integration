import re

from app.interpretation.proposition_semantics import (
    PropositionSemantics,
)
from app.nlp.response_claim_extractor_base import (
    ResponseClaimExtractor as BaseResponseClaimExtractor,
)


class ResponseClaimExtractor(
    BaseResponseClaimExtractor
):
    LIST_SCOPE_HEADER = re.compile(
        (
            r"^\s*"
            r"(?P<subject>.+?)\s+"
            r"(?P<aux>do|does)\s*"
            r"(?P<neg>not)?"
            r"\s*:\s*$"
        ),
        flags=re.IGNORECASE,
    )

    TRANSITION_START = re.compile(
        (
            r"^\s*(?:"
            r"so\b"
            r"|overall\b"
            r"|in short\b"
            r"|in summary\b"
            r"|however\b"
            r"|importantly\b"
            r"|the main\b"
            r")"
        ),
        flags=re.IGNORECASE,
    )

    CONTRAST_SEPARATOR = re.compile(
        (
            r",?\s+"
            r"(?:although|though|but)"
            r"\s+"
        ),
        flags=re.IGNORECASE,
    )

    TOPIC_LABEL = re.compile(
        (
            r"^"
            r"(?P<label>[^:\n]{1,60})"
            r":\s+"
            r"(?P<content>.+)$"
        )
    )

    PRONOUN_START = re.compile(
        (
            r"^(?P<pronoun>"
            r"it|they|this|that|these|those"
            r")\b"
        ),
        flags=re.IGNORECASE,
    )

    BLOCKED_INHERITANCE_STARTS = {
        "because",
        "for",
        "if",
        "unless",
        "when",
        "where",
        "while",
        "which",
        "who",
        "whose",
    }

    def __init__(
        self,
        nlp,
    ):
        super().__init__(
            nlp
        )

        self.semantics = (
            PropositionSemantics()
        )

    def extract(
        self,
        text: str,
    ):
        base_claims = (
            super().extract(
                text
            )
        )

        (
            section_ranges,
            section_claims,
        ) = self._section_claims(
            text
        )

        candidates = []

        for claim in base_claims:
            if self._inside_ranges(
                claim["start"],
                section_ranges,
            ):
                continue

            cleaned = (
                self._clean_topic_label(
                    claim
                )
            )

            if self.semantics.is_discourse_only(
                cleaned["text"]
            ):
                continue

            candidates.extend(
                self._split_contrast_claim(
                    cleaned
                )
            )

        candidates.extend(
            section_claims
        )

        candidates.sort(
            key=lambda value: (
                value["start"],
                value["end"],
            )
        )

        claims = []
        seen = set()

        for claim in candidates:
            claim_text = (
                claim["text"]
                .strip()
            )

            if not claim_text:
                continue

            if self.semantics.is_discourse_only(
                claim_text
            ):
                continue

            key = self._normalize(
                claim_text
            )

            if not key:
                continue

            if key in seen:
                continue

            seen.add(
                key
            )

            claims.append(
                {
                    "index": (
                        len(claims)
                        + 1
                    ),
                    "text": claim_text,
                    "start": claim[
                        "start"
                    ],
                    "end": claim[
                        "end"
                    ],
                    "method": claim[
                        "method"
                    ],
                }
            )

        return claims

    def _section_claims(
        self,
        text: str,
    ):
        ranges = []
        claims = []

        subject = None
        negated = False

        for match in re.finditer(
            r"[^\r\n]+",
            text,
        ):
            raw = match.group(
                0
            )

            stripped = raw.strip()

            if not stripped:
                continue

            heading = (
                self.LIST_SCOPE_HEADER
                .match(
                    stripped
                )
            )

            if heading:
                subject = (
                    heading.group(
                        "subject"
                    )
                    .strip()
                )

                negated = bool(
                    heading.group(
                        "neg"
                    )
                )

                ranges.append(
                    (
                        match.start(),
                        match.end(),
                    )
                )

                continue

            if subject is None:
                continue

            if (
                stripped.endswith(
                    ":"
                )
                or self.TRANSITION_START.match(
                    stripped
                )
            ):
                subject = None
                negated = False
                continue

            list_prefix = (
                self.LIST_PREFIX.match(
                    stripped
                )
            )

            if list_prefix:
                stripped = (
                    stripped[
                        list_prefix.end():
                    ]
                    .strip()
                )

            if not stripped:
                continue

            reconstructed = (
                self._reconstruct_section_claim(
                    subject=subject,
                    text=stripped,
                    negated=negated,
                )
            )

            if not reconstructed:
                continue

            if not self._is_factual_text(
                reconstructed
            ):
                continue

            ranges.append(
                (
                    match.start(),
                    match.end(),
                )
            )

            claims.append(
                {
                    "text": reconstructed,
                    "start": (
                        match.start()
                    ),
                    "end": (
                        match.end()
                    ),
                    "method": (
                        "list_scope_rule"
                    ),
                }
            )

        return (
            ranges,
            claims,
        )

    def _reconstruct_section_claim(
        self,
        subject: str,
        text: str,
        negated: bool,
    ):
        normalized_subject = (
            self._normalize(
                subject
            )
        )

        normalized_text = (
            self._normalize(
                text
            )
        )

        if not normalized_text:
            return None

        if normalized_text.startswith(
            normalized_subject
        ):
            return text

        first = (
            text[:1].lower()
            + text[1:]
            if text
            else text
        )

        if negated:
            return (
                f"{subject} do not "
                f"{first}"
            )

        return (
            f"{subject} {first}"
        )

    def _clean_topic_label(
        self,
        claim: dict,
    ):
        match = self.TOPIC_LABEL.match(
            claim["text"]
        )

        if not match:
            return claim

        label = match.group(
            "label"
        )

        if not self._is_topic_label(
            label
        ):
            return claim

        content = match.group(
            "content"
        ).strip()

        if not content:
            return claim

        offset = match.start(
            "content"
        )

        return {
            **claim,
            "text": content,
            "start": (
                claim["start"]
                + offset
            ),
        }

    def _split_contrast_claim(
        self,
        claim: dict,
    ):
        text = claim[
            "text"
        ]

        separator = (
            self.CONTRAST_SEPARATOR
            .search(
                text
            )
        )

        if not separator:
            return [
                claim
            ]

        left_text = (
            text[
                :separator.start()
            ]
            .strip(
                " ,;"
            )
        )

        right_text = (
            text[
                separator.end():
            ]
            .strip(
                " ,;"
            )
        )

        if (
            not left_text
            or not right_text
        ):
            return [
                claim
            ]

        left_doc = self.nlp(
            left_text
        )

        subject = (
            self._subject_phrase(
                left_doc
            )
        )

        if subject:
            pronoun = (
                self.PRONOUN_START
                .match(
                    right_text
                )
            )

            if pronoun:
                right_text = (
                    subject
                    + right_text[
                        pronoun.end():
                    ]
                )

        if (
            not self._is_factual_text(
                left_text
            )
            or not self._is_factual_text(
                right_text
            )
        ):
            return [
                claim
            ]

        right_offset = (
            separator.end()
        )

        return [
            {
                **claim,
                "text": left_text,
                "end": (
                    claim["start"]
                    + separator.start()
                ),
                "method": (
                    "contrast_clause_rule"
                ),
            },
            {
                **claim,
                "text": right_text,
                "start": (
                    claim["start"]
                    + right_offset
                ),
                "method": (
                    "contrast_clause_rule"
                ),
            },
        ]

    def _is_factual_text(
        self,
        text: str,
    ):
        doc = self.nlp(
            text
        )

        return self._is_factual(
            doc,
            text,
        )

    def _inside_ranges(
        self,
        start: int,
        ranges: list[
            tuple[int, int]
        ],
    ):
        return any(
            range_start
            <= start
            < range_end
            for (
                range_start,
                range_end,
            )
            in ranges
        )

    def _can_inherit_subject(
        self,
        doc,
    ):
        meaningful = [
            token
            for token in doc
            if not token.is_space
            and not token.is_punct
        ]

        if meaningful:
            if (
                meaningful[0].lower_
                in self.BLOCKED_INHERITANCE_STARTS
            ):
                return False

        return super()._can_inherit_subject(
            doc
        )