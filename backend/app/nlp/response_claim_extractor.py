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
            raw_text = sentence.text

            left_trim = (
                len(raw_text)
                - len(
                    raw_text.lstrip()
                )
            )

            right_trim = (
                len(raw_text)
                - len(
                    raw_text.rstrip()
                )
            )

            claim_text = (
                raw_text.strip()
            )

            if not claim_text:
                continue

            start = (
                sentence.start_char
                + left_trim
            )

            end = (
                sentence.end_char
                - right_trim
            )

            if not self._is_factual(
                sentence,
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
                    "start": start,
                    "end": end,
                    "method": (
                        "sentence_rule"
                    ),
                }
            )

        return claims

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