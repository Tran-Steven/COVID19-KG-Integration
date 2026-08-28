from spacy.language import Language


class DirectionResolver:
    INCREASE_TERMS = {
        "increase",
        "raise",
        "worsen",
        "heighten",
        "elevate",
        "aggravate",
        "greater",
        "higher",
        "worse",
    }

    DECREASE_TERMS = {
        "decrease",
        "reduce",
        "lower",
        "lessen",
        "protect",
        "prevent",
        "reduced",
    }

    COMPARATIVE_CONTEXT = {
        "risk",
        "chance",
        "likely",
        "severity",
        "severe",
        "serious",
        "dangerous",
        "mortality",
        "death",
        "hospitalization",
        "hospital",
        "infection",
        "infected",
    }

    def __init__(
        self,
        nlp: Language,
    ):
        self.nlp = nlp

    def resolve(
        self,
        text: str,
    ):
        doc = self.nlp(text)

        terms = set()

        for token in doc:
            terms.add(token.text.lower())

            terms.add(token.lemma_.lower())

        has_increase = bool(terms & self.INCREASE_TERMS)

        has_decrease = bool(terms & self.DECREASE_TERMS)

        if has_increase and not has_decrease:
            return "increase"

        if has_decrease and not has_increase:
            return "decrease"

        has_context = bool(terms & self.COMPARATIVE_CONTEXT)

        if has_context:
            if "more" in terms and "less" not in terms:
                return "increase"

            if "less" in terms and "more" not in terms:
                return "decrease"

        return None
