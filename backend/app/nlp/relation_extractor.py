import re

from spacy.language import Language
from spacy.tokens import Token

from app.interpretation.verification_semantic_matcher import (
    get_verification_semantic_matcher,
)


class RelationExtractor:
    TREATMENT_PATTERNS = (
        r"\bused\s+to\s+treat\b",
        r"\buse\s+to\s+treat\b",
        r"\buses\s+to\s+treat\b",
        r"\busing\s+to\s+treat\b",
        r"\btreatment\s+of\b",
        (
            r"\bused\s+for\s+"
            r"(?:the\s+)?treatment\s+of\b"
        ),
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
        normalized_text = self._normalize_text(text)

        semantic_result = self._semantic_result(
            text,
            normalized_text,
        )

        if self._semantic_out_of_scope(semantic_result):
            return self._empty_result()

        if self._has_treatment_relation(normalized_text):
            return self._treatment_result()

        if self._semantic_treatment_relation(
            semantic_result,
            normalized_text,
        ):
            return self._treatment_result()

        doc = self.nlp(text)

        root = next(
            (token for token in doc if token.dep_ == "ROOT"),
            None,
        )

        if root is None:
            return self._empty_result()

        predicate = self._resolve_predicate(root)

        relation_parts = [predicate.lemma_.lower()]

        modifiers = sorted(
            [
                child
                for child in predicate.children
                if child.dep_
                in {
                    "prt",
                    "prep",
                }
            ],
            key=lambda token: token.i,
        )

        relation_parts.extend(modifier.lemma_.lower() for modifier in modifiers)

        relation_text = " ".join(relation_parts)

        normalized = re.sub(
            r"[^a-z0-9]+",
            "_",
            relation_text,
        ).strip("_")

        return {
            "text": relation_text,
            "normalized": normalized,
            "root": (predicate.lemma_.lower()),
        }

    def _semantic_result(
        self,
        raw_text: str,
        normalized_text: str,
    ):
        if not self._covid_context(normalized_text):
            return None

        return get_verification_semantic_matcher().resolve(raw_text)

    def _semantic_out_of_scope(
        self,
        result,
    ):
        if not result:
            return False

        return result["label"] == "out_of_scope" and result["embeddingScore"] >= 0.82

    def _semantic_treatment_relation(
        self,
        result,
        normalized_text: str,
    ):
        if not result:
            return False

        if self._absolute_cure_claim(normalized_text):
            return False

        return result["label"] == "treatment" and result["embeddingScore"] >= 0.70

    def _treatment_result(
        self,
    ):
        return {
            "text": "treat",
            "normalized": "treat",
            "root": "treat",
        }

    def _empty_result(
        self,
    ):
        return {
            "text": None,
            "normalized": None,
            "root": None,
        }

    def _absolute_cure_claim(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "cure covid",
                "cures covid",
                "cured covid",
                "cure every",
                "cures every",
                "eradicate covid",
                "eradicates covid",
                "eradicated covid",
                "every patient",
                "every case",
                "all patients",
                "100 percent",
            )
        )

    def _covid_context(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "covid",
                "coronavirus disease 2019",
                "sars cov 2",
            )
        )

    def _has_treatment_relation(
        self,
        text: str,
    ):
        return any(
            re.search(
                pattern,
                text,
            )
            is not None
            for pattern in self.TREATMENT_PATTERNS
        )

    def _normalize_text(
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

    def _resolve_predicate(
        self,
        root: Token,
    ):
        if root.pos_ != "AUX":
            return root

        candidates = sorted(
            [
                child
                for child in root.children
                if (
                    child.pos_
                    in {
                        "VERB",
                        "ADJ",
                        "NOUN",
                    }
                    and child.dep_
                    in {
                        "xcomp",
                        "ccomp",
                        "acomp",
                        "attr",
                        "oprd",
                    }
                )
            ],
            key=lambda token: token.i,
        )

        if candidates:
            return candidates[0]

        return root
