import re

from spacy.language import Language


class ResponseClaimExtractor:
    NON_FACTUAL_PREFIXES = (
        "i think",
        "i believe",
        "i hope",
        "i'm sorry",
        "i am sorry",
        "let me know",
        "hope this helps",
        "thanks",
        "thank you",
    )

    CLAUSE_SEPARATOR = re.compile(
        r",\s+(?:and|but)\s+|;\s*",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        nlp: Language,
    ):
        self.nlp = nlp

    def extract(
        self,
        text: str,
    ):
        doc = self.nlp(
            text
        )

        claims = []
        seen = set()

        for sentence in doc.sents:
            segments = (
                self._sentence_segments(
                    sentence
                )
            )

            for segment in segments:
                claim_text = segment[
                    "text"
                ]

                claim_doc = self.nlp(
                    claim_text
                )

                if not self._is_factual(
                    claim_doc,
                    claim_text,
                ):
                    continue

                key = self._normalize(
                    claim_text
                )

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
                        "start": segment[
                            "start"
                        ],
                        "end": segment[
                            "end"
                        ],
                        "method": segment[
                            "method"
                        ],
                    }
                )

        return claims

    def _sentence_segments(
        self,
        sentence,
    ):
        raw_text = sentence.text

        unsplit = (
            self._trim_segment(
                raw_text,
                sentence.start_char,
                strip_punctuation=False,
                method="sentence_rule",
            )
        )

        separators = list(
            self.CLAUSE_SEPARATOR
            .finditer(
                raw_text
            )
        )

        if not separators:
            return [
                unsplit
            ]

        raw_segments = []
        cursor = 0

        for separator in separators:
            raw_segments.append(
                (
                    raw_text[
                        cursor:
                        separator.start()
                    ],
                    (
                        sentence.start_char
                        + cursor
                    ),
                )
            )

            cursor = (
                separator.end()
            )

        raw_segments.append(
            (
                raw_text[
                    cursor:
                ],
                (
                    sentence.start_char
                    + cursor
                ),
            )
        )

        segments = [
            self._trim_segment(
                segment_text,
                segment_start,
                strip_punctuation=True,
                method="clause_rule",
            )
            for (
                segment_text,
                segment_start,
            )
            in raw_segments
        ]

        if any(
            not segment[
                "text"
            ]
            for segment
            in segments
        ):
            return [
                unsplit
            ]

        if not all(
            self._is_factual(
                self.nlp(
                    segment[
                        "text"
                    ]
                ),
                segment[
                    "text"
                ],
            )
            for segment
            in segments
        ):
            return [
                unsplit
            ]

        return segments

    def _trim_segment(
        self,
        raw_text: str,
        absolute_start: int,
        strip_punctuation: bool,
        method: str,
    ):
        if strip_punctuation:
            leading = re.match(
                r"^[\s,;:.!?]+",
                raw_text,
            )

            trailing = re.search(
                r"[\s,;:.!?]+$",
                raw_text,
            )
        else:
            leading = re.match(
                r"^\s+",
                raw_text,
            )

            trailing = re.search(
                r"\s+$",
                raw_text,
            )

        left_trim = (
            leading.end()
            if leading
            else 0
        )

        right_trim = (
            len(raw_text)
            - trailing.start()
            if trailing
            else 0
        )

        end_index = (
            len(raw_text)
            - right_trim
        )

        claim_text = raw_text[
            left_trim:
            end_index
        ]

        return {
            "text": claim_text,
            "start": (
                absolute_start
                + left_trim
            ),
            "end": (
                absolute_start
                + end_index
            ),
            "method": method,
        }

    def _is_factual(
        self,
        sentence,
        text: str,
    ):
        normalized = (
            self._normalize(
                text
            )
        )

        if not normalized:
            return False

        if text.rstrip().endswith(
            "?"
        ):
            return False

        if any(
            normalized.startswith(
                prefix
            )
            for prefix
            in self.NON_FACTUAL_PREFIXES
        ):
            return False

        alpha_tokens = [
            token
            for token in sentence
            if token.is_alpha
        ]

        if len(
            alpha_tokens
        ) < 2:
            return False

        has_predicate = any(
            token.pos_
            in {
                "VERB",
                "AUX",
            }
            for token
            in sentence
        )

        if not has_predicate:
            return False

        return True

    def _normalize(
        self,
        text: str,
    ):
        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s\-]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()