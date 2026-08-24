from spacy.language import Language


class EntityExtractor:
    def __init__(self, nlp: Language):
        self.nlp = nlp

    def extract(self, text: str):
        doc = self.nlp(text)

        return [
            {
                "text": entity.text,
                "type": entity.label_,
                "start": entity.start_char,
                "end": entity.end_char,
            }
            for entity in doc.ents
        ]