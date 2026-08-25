from spacy.language import Language


class SemanticInterpreter:
    INTENT_PROTOTYPES = {
        "treatment": [
            "a medicine is useful as a treatment for a disease",
            "a drug helps treat an illness",
            "a therapy is used against a disease",
        ],
        "risk_modifier": [
            "a factor changes the risk of a health outcome",
            "a factor makes a disease more severe",
            "a factor changes the chance of becoming ill",
        ],
        "causation": [
            "one thing causes a disease",
            "an exposure leads to an illness",
            "one condition results in another condition",
        ],
        "association": [
            "one factor is associated with a disease",
            "two health concepts are related",
            "an exposure is linked to an illness",
        ],
        "clinical_study": [
            "a drug has been studied in clinical trials",
            "a treatment has been investigated in a clinical study",
            "researchers tested a medicine in trials",
        ],
        "phenotype": [
            "a symptom is a manifestation of a disease",
            "a clinical sign occurs with an illness",
            "a disease has a symptom",
        ],
    }

    OUTCOME_PROTOTYPES = {
        "infection": [
            "getting infected with the disease",
            "catching the infection",
            "contracting the disease",
        ],
        "severity": [
            "the illness becomes more severe",
            "developing serious disease",
            "the disease becomes worse",
        ],
        "hospitalization": [
            "being admitted to the hospital",
            "ending up in the hospital because of illness",
            "requiring hospitalization for the disease",
        ],
        "mortality": [
            "dying from the disease",
            "death caused by the illness",
            "risk of mortality from the disease",
        ],
    }

    def __init__(
        self,
        nlp: Language,
        intent_threshold: float = 0.62,
        intent_margin: float = 0.04,
        outcome_threshold: float = 0.60,
        outcome_margin: float = 0.035,
    ):
        self.nlp = nlp

        self.intent_threshold = (
            intent_threshold
        )

        self.intent_margin = (
            intent_margin
        )

        self.outcome_threshold = (
            outcome_threshold
        )

        self.outcome_margin = (
            outcome_margin
        )

        self.intent_docs = (
            self._build_prototype_docs(
                self.INTENT_PROTOTYPES
            )
        )

        self.outcome_docs = (
            self._build_prototype_docs(
                self.OUTCOME_PROTOTYPES
            )
        )

    def resolve_intent(
        self,
        text: str,
    ):
        match = self._resolve(
            text=text,
            prototype_docs=self.intent_docs,
            threshold=self.intent_threshold,
            margin=self.intent_margin,
        )

        if not match:
            return None

        return {
            "intent": match["label"],
            "direction": None,
            "matchedText": None,
            "specific": True,
            "method": "semantic",
            "score": match["score"],
        }

    def resolve_outcome(
        self,
        text: str,
    ):
        match = self._resolve(
            text=text,
            prototype_docs=self.outcome_docs,
            threshold=self.outcome_threshold,
            margin=self.outcome_margin,
        )

        if not match:
            return None

        return {
            "outcome": match["label"],
            "matchedText": None,
            "method": "semantic",
            "score": match["score"],
        }

    def _build_prototype_docs(
        self,
        prototypes: dict[str, list[str]],
    ):
        return {
            label: [
                self.nlp.make_doc(
                    prototype
                )
                for prototype in phrases
            ]
            for label, phrases
            in prototypes.items()
        }

    def _resolve(
        self,
        text: str,
        prototype_docs: dict,
        threshold: float,
        margin: float,
    ):
        query_doc = self.nlp.make_doc(
            text
        )

        if query_doc.vector_norm == 0:
            return None

        scores = []

        for label, docs in (
            prototype_docs.items()
        ):
            similarities = [
                query_doc.similarity(
                    prototype_doc
                )
                for prototype_doc in docs
                if prototype_doc.vector_norm > 0
            ]

            if not similarities:
                continue

            scores.append(
                {
                    "label": label,
                    "score": max(
                        similarities
                    ),
                }
            )

        if not scores:
            return None

        scores.sort(
            key=lambda item: item[
                "score"
            ],
            reverse=True,
        )

        best = scores[0]

        if best["score"] < threshold:
            return None

        if len(scores) > 1:
            second = scores[1]

            if (
                best["score"]
                - second["score"]
                < margin
            ):
                return None

        return {
            "label": best["label"],
            "score": round(
                best["score"],
                4,
            ),
        }