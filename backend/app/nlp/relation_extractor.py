import re

from spacy.language import Language
from spacy.tokens import Token


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
        normalized_text = (
            self._normalize_text(
                text
            )
        )

        if self._has_treatment_relation(
            normalized_text
        ):
            return {
                "text": "treat",
                "normalized": "treat",
                "root": "treat",
            }

        doc = self.nlp(
            text
        )

        root = next(
            (
                token
                for token in doc
                if token.dep_
                == "ROOT"
            ),
            None,
        )

        if root is None:
            return {
                "text": None,
                "normalized": None,
                "root": None,
            }

        predicate = (
            self._resolve_predicate(
                root
            )
        )

        relation_parts = [
            predicate.lemma_.lower()
        ]

        modifiers = sorted(
            [
                child
                for child
                in predicate.children
                if child.dep_
                in {
                    "prt",
                    "prep",
                }
            ],
            key=(
                lambda token:
                token.i
            ),
        )

        relation_parts.extend(
            modifier.lemma_.lower()
            for modifier
            in modifiers
        )

        relation_text = " ".join(
            relation_parts
        )

        normalized = re.sub(
            r"[^a-z0-9]+",
            "_",
            relation_text,
        ).strip(
            "_"
        )

        return {
            "text": relation_text,
            "normalized": normalized,
            "root": (
                predicate.lemma_.lower()
            ),
        }

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
            for pattern
            in self.TREATMENT_PATTERNS
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
                for child
                in root.children
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
            key=(
                lambda token:
                token.i
            ),
        )

        if candidates:
            return candidates[0]

        return root