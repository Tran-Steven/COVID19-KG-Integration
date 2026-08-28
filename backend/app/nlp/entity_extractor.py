from spacy.language import Language

from app.nlp.kg_entity_matcher import KGEntityMatcher


class EntityExtractor:
    IGNORED_SPACY_TYPES = {
        "CARDINAL",
        "ORDINAL",
        "DATE",
        "TIME",
        "MONEY",
        "PERCENT",
        "QUANTITY",
    }

    def __init__(
        self,
        nlp: Language,
        kg_entity_matcher: KGEntityMatcher,
    ):
        self.nlp = nlp
        self.kg_entity_matcher = kg_entity_matcher

    def extract(self, text: str):
        doc = self.nlp(text)

        kg_entities = self.kg_entity_matcher.extract(doc)

        entities = list(kg_entities)

        for entity in doc.ents:
            if entity.label_ in self.IGNORED_SPACY_TYPES:
                continue

            if self._overlaps_kg_entity(
                entity.start_char,
                entity.end_char,
                kg_entities,
            ):
                continue

            entities.append(
                {
                    "text": entity.text,
                    "type": entity.label_,
                    "start": entity.start_char,
                    "end": entity.end_char,
                }
            )

        entities.sort(
            key=lambda entity: (
                entity["start"],
                entity["end"],
            )
        )

        return entities

    def _overlaps_kg_entity(
        self,
        start: int,
        end: int,
        kg_entities: list[dict],
    ):
        return any(
            start < entity["end"] and end > entity["start"] for entity in kg_entities
        )
