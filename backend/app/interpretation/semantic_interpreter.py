import math

from fastembed import TextEmbedding


class SemanticInterpreter:
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    INTENT_PROTOTYPES = {
        "treatment": [
            "Can a medicine help treat this disease?",
            "Is this drug useful against the disease?",
            "Can this treatment help someone with the illness?",
            "Is this therapy effective for treating the disease?",
        ],
        "risk_modifier": [
            "Does this factor increase the risk of a health outcome?",
            "Does this factor decrease the risk of a health outcome?",
            "Can this condition make the disease worse?",
            "Does this exposure change the chance of a bad outcome?",
        ],
        "causation": [
            "Does this factor cause the disease?",
            "Can this exposure lead to the illness?",
            "Does one condition result in another disease?",
        ],
        "association": [
            "Is this factor associated with the disease?",
            "Is this exposure linked to the illness?",
            "Are these two health conditions related?",
        ],
        "clinical_study": [
            "Has this treatment been studied in clinical trials?",
            "Has this drug been investigated in clinical research?",
            "Have researchers tested this treatment in trials?",
        ],
        "phenotype": [
            "Is this a symptom of the disease?",
            "Is this clinical sign a manifestation of the illness?",
            "Does this disease have this symptom?",
        ],
    }

    OUTCOME_PROTOTYPES = {
        "infection": [
            "What is the risk of getting infected?",
            "Could someone catch the disease?",
            "What is the chance of contracting the infection?",
        ],
        "severity": [
            "Could the disease become more severe?",
            "Could this lead to a more serious case of the illness?",
            "Could the disease become worse?",
        ],
        "hospitalization": [
            "Could someone be hospitalized because of the disease?",
            "Could someone end up in the hospital from the illness?",
            "Could the disease require hospital admission?",
        ],
        "mortality": [
            "Could someone die from the disease?",
            "Does this affect the risk of death from the illness?",
            "Does this affect mortality from the disease?",
        ],
    }

    def __init__(
        self,
        intent_threshold: float = 0.70,
        intent_margin: float = 0.035,
        outcome_threshold: float = 0.70,
        outcome_margin: float = 0.035,
    ):
        self.intent_threshold = intent_threshold
        self.intent_margin = intent_margin
        self.outcome_threshold = outcome_threshold
        self.outcome_margin = outcome_margin

        self.model = TextEmbedding(
            model_name=self.MODEL_NAME
        )

        self.intent_embeddings = (
            self._build_prototype_embeddings(
                self.INTENT_PROTOTYPES
            )
        )

        self.outcome_embeddings = (
            self._build_prototype_embeddings(
                self.OUTCOME_PROTOTYPES
            )
        )

    def resolve_intent(
        self,
        text: str,
    ):
        match = self._resolve(
            text=text,
            prototype_embeddings=(
                self.intent_embeddings
            ),
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
            prototype_embeddings=(
                self.outcome_embeddings
            ),
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

    def _build_prototype_embeddings(
        self,
        prototypes: dict[str, list[str]],
    ):
        result = {}

        for label, phrases in prototypes.items():
            vectors = list(
                self.model.embed(
                    phrases
                )
            )

            result[label] = vectors

        return result

    def _resolve(
        self,
        text: str,
        prototype_embeddings: dict,
        threshold: float,
        margin: float,
    ):
        query_vectors = list(
            self.model.embed(
                [text]
            )
        )

        if not query_vectors:
            return None

        query_vector = query_vectors[0]

        scores = []

        for label, vectors in (
            prototype_embeddings.items()
        ):
            similarities = [
                self._cosine_similarity(
                    query_vector,
                    vector,
                )
                for vector in vectors
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
            key=lambda item: item["score"],
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

    def _cosine_similarity(
        self,
        first,
        second,
    ):
        dot_product = float(
            first @ second
        )

        first_norm = math.sqrt(
            float(
                first @ first
            )
        )

        second_norm = math.sqrt(
            float(
                second @ second
            )
        )

        if (
            first_norm == 0
            or second_norm == 0
        ):
            return 0.0

        return (
            dot_product
            / (
                first_norm
                * second_norm
            )
        )