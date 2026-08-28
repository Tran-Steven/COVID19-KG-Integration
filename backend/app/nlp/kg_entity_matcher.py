from spacy.language import Language
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc
from spacy.util import filter_spans

from app.database import Neo4jClient


class KGEntityMatcher:
    def __init__(
        self,
        nlp: Language,
        database: Neo4jClient,
    ):
        self.nlp = nlp
        self.database = database
        self.matcher = PhraseMatcher(
            nlp.vocab,
            attr="LOWER",
        )
        self.loaded = False

    def extract(self, doc: Doc):
        if not self.loaded:
            self._load()

        matches = self.matcher(doc)

        spans = filter_spans([doc[start:end] for _, start, end in matches])

        return [
            {
                "text": span.text,
                "type": "KG_ENTITY",
                "start": span.start_char,
                "end": span.end_char,
            }
            for span in spans
        ]

    def _load(self):
        entities = self.database.get_entity_terms()

        terms = {}

        for entity in entities:
            values = [
                entity.get("id"),
                entity.get("name"),
                *entity.get("aliases", []),
            ]

            for value in values:
                if not value:
                    continue

                term = str(value).strip()

                if not self._is_matchable(term):
                    continue

                terms[term.lower()] = term

        patterns = [self.nlp.make_doc(term) for term in terms.values()]

        if patterns:
            self.matcher.add(
                "KG_ENTITY",
                patterns,
            )

        self.loaded = True

    def _is_matchable(self, term: str):
        if len(term) < 3:
            return False

        doc = self.nlp.make_doc(term)

        if len(doc) == 1 and doc[0].is_stop:
            return False

        return True
