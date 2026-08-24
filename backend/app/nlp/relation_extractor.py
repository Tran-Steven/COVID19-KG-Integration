import re

from spacy.language import Language
from spacy.tokens import Token


class RelationExtractor:
    def __init__(self, nlp: Language):
        self.nlp = nlp

    def extract(self, text: str):
        doc = self.nlp(text)
        root = next((token for token in doc if token.dep_ == "ROOT"), None)

        if root is None:
            return {
                "text": None,
                "normalized": None,
                "root": None,
            }

        predicate = self._resolve_predicate(root)

        relation_parts = [predicate.lemma_.lower()]

        modifiers = sorted(
            [
                child
                for child in predicate.children
                if child.dep_ in {"prt", "prep"}
            ],
            key=lambda token: token.i,
        )

        relation_parts.extend(
            modifier.lemma_.lower()
            for modifier in modifiers
        )

        relation_text = " ".join(relation_parts)
        normalized = re.sub(r"[^a-z0-9]+", "_", relation_text).strip("_")

        return {
            "text": relation_text,
            "normalized": normalized,
            "root": predicate.lemma_.lower(),
        }

    def _resolve_predicate(self, root: Token):
        if root.pos_ != "AUX":
            return root

        candidates = sorted(
            [
                child
                for child in root.children
                if child.pos_ in {"VERB", "ADJ", "NOUN"}
                and child.dep_ in {"xcomp", "ccomp", "acomp", "attr", "oprd"}
            ],
            key=lambda token: token.i,
        )

        if candidates:
            return candidates[0]

        return root