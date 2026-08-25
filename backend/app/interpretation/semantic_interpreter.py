import math

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import (
    TextCrossEncoder,
)


class SemanticInterpreter:
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    RERANK_MODEL_NAME = (
        "Xenova/ms-marco-MiniLM-L-6-v2"
    )

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
        "broad_effect": [
            "Does this factor matter for the disease?",
            "Could this factor affect what happens with the disease?",
            "Does this factor change the overall disease outcome?",
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

    DIRECTION_PROTOTYPES = {
        "increase": [
            "This makes the outcome more likely.",
            "This increases the risk of the outcome.",
            "This makes the disease worse.",
            "This makes it easier for the outcome to happen.",
        ],
        "decrease": [
            "This makes the outcome less likely.",
            "This decreases the risk of the outcome.",
            "This makes the disease less severe.",
            "This makes it harder for the outcome to happen.",
        ],
    }

    INTENT_DESCRIPTIONS = {
        "treatment": (
            "Treatment intent: asking whether a drug, "
            "therapy, or intervention can be used to "
            "treat or help with a disease."
        ),
        "risk_modifier": (
            "Risk modifier intent: asking whether a "
            "factor increases or decreases the chance "
            "or severity of a health outcome."
        ),
        "causation": (
            "Causation intent: asking whether one "
            "factor directly causes or leads to a "
            "disease or health condition."
        ),
        "association": (
            "Association intent: asking whether two "
            "health concepts are related, linked, "
            "correlated, or associated."
        ),
        "clinical_study": (
            "Clinical study intent: asking whether a "
            "drug or intervention has been studied, "
            "tested, or investigated in clinical trials."
        ),
        "phenotype": (
            "Phenotype intent: asking whether a symptom, "
            "sign, or manifestation occurs as part of "
            "a disease."
        ),
        "broad_effect": (
            "Broad effect intent: asking generally "
            "whether a factor matters for, affects, "
            "influences, or changes a disease without "
            "specifying a particular health outcome."
        ),
    }

    OUTCOME_DESCRIPTIONS = {
        "infection": (
            "Infection outcome: becoming infected, "
            "catching the disease, or contracting "
            "the infection."
        ),
        "severity": (
            "Severity outcome: the disease becoming "
            "more serious, more severe, or worse."
        ),
        "hospitalization": (
            "Hospitalization outcome: requiring hospital "
            "care, being admitted to a hospital, or "
            "ending up in the hospital."
        ),
        "mortality": (
            "Mortality outcome: death, dying, fatality, "
            "or the risk of dying from the disease."
        ),
    }

    DIRECTION_DESCRIPTIONS = {
        "increase": (
            "Increase direction: the factor makes the "
            "specified outcome more likely, more common, "
            "more severe, easier to occur, or higher risk."
        ),
        "decrease": (
            "Decrease direction: the factor makes the "
            "specified outcome less likely, less common, "
            "less severe, harder to occur, or lower risk."
        ),
    }

    def __init__(
        self,
        intent_threshold: float = 0.70,
        intent_margin: float = 0.035,
        outcome_threshold: float = 0.70,
        outcome_margin: float = 0.035,
        direction_threshold: float = 0.70,
        direction_margin: float = 0.035,
        intent_rerank_floor: float = 0.65,
        outcome_rerank_floor: float = 0.65,
        direction_rerank_floor: float = 0.65,
        rerank_top_k: int = 3,
    ):
        self.intent_threshold = intent_threshold
        self.intent_margin = intent_margin
        self.outcome_threshold = outcome_threshold
        self.outcome_margin = outcome_margin
        self.direction_threshold = (
            direction_threshold
        )
        self.direction_margin = (
            direction_margin
        )

        self.intent_rerank_floor = (
            intent_rerank_floor
        )

        self.outcome_rerank_floor = (
            outcome_rerank_floor
        )

        self.direction_rerank_floor = (
            direction_rerank_floor
        )

        self.rerank_top_k = rerank_top_k

        self.model = TextEmbedding(
            model_name=self.MODEL_NAME
        )

        self.reranker = TextCrossEncoder(
            model_name=self.RERANK_MODEL_NAME
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

        self.direction_embeddings = (
            self._build_prototype_embeddings(
                self.DIRECTION_PROTOTYPES
            )
        )

    def resolve_intent(
        self,
        text: str,
    ):
        rankings = self.rank_intents(
            text
        )

        match = self._select(
            rankings=rankings,
            threshold=self.intent_threshold,
            margin=self.intent_margin,
        )

        if match:
            return {
                "intent": match["label"],
                "direction": None,
                "matchedText": None,
                "specific": (
                    match["label"]
                    != "broad_effect"
                ),
                "method": "semantic",
                "score": match["score"],
            }

        reranked = self._rerank(
            text=text,
            rankings=rankings,
            descriptions=(
                self.INTENT_DESCRIPTIONS
            ),
            floor=self.intent_rerank_floor,
        )

        if not reranked:
            return None

        return {
            "intent": reranked["label"],
            "direction": None,
            "matchedText": None,
            "specific": (
                reranked["label"]
                != "broad_effect"
            ),
            "method": "semantic_rerank",
            "score": reranked["score"],
        }

    def resolve_outcome(
        self,
        text: str,
    ):
        rankings = self.rank_outcomes(
            text
        )

        match = self._select(
            rankings=rankings,
            threshold=self.outcome_threshold,
            margin=self.outcome_margin,
        )

        if match:
            return {
                "outcome": match["label"],
                "matchedText": None,
                "method": "semantic",
                "score": match["score"],
            }

        reranked = self._rerank(
            text=text,
            rankings=rankings,
            descriptions=(
                self.OUTCOME_DESCRIPTIONS
            ),
            floor=self.outcome_rerank_floor,
        )

        if not reranked:
            return None

        return {
            "outcome": reranked["label"],
            "matchedText": None,
            "method": "semantic_rerank",
            "score": reranked["score"],
        }

    def resolve_direction(
        self,
        text: str,
    ):
        rankings = self.rank_directions(
            text
        )

        match = self._select(
            rankings=rankings,
            threshold=self.direction_threshold,
            margin=self.direction_margin,
        )

        if match:
            return {
                "direction": match["label"],
                "method": "semantic",
                "score": match["score"],
            }

        reranked = self._rerank(
            text=text,
            rankings=rankings,
            descriptions=(
                self.DIRECTION_DESCRIPTIONS
            ),
            floor=self.direction_rerank_floor,
        )

        if not reranked:
            return None

        return {
            "direction": reranked["label"],
            "method": "semantic_rerank",
            "score": reranked["score"],
        }

    def rank_intents(
        self,
        text: str,
    ):
        return self._rank(
            text=text,
            prototype_embeddings=(
                self.intent_embeddings
            ),
        )

    def rank_outcomes(
        self,
        text: str,
    ):
        return self._rank(
            text=text,
            prototype_embeddings=(
                self.outcome_embeddings
            ),
        )

    def rank_directions(
        self,
        text: str,
    ):
        return self._rank(
            text=text,
            prototype_embeddings=(
                self.direction_embeddings
            ),
        )

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

    def _rank(
        self,
        text: str,
        prototype_embeddings: dict,
    ):
        query_vectors = list(
            self.model.embed(
                [text]
            )
        )

        if not query_vectors:
            return []

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
                    "score": round(
                        max(similarities),
                        4,
                    ),
                }
            )

        scores.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scores

    def _select(
        self,
        rankings: list[dict],
        threshold: float,
        margin: float,
    ):
        if not rankings:
            return None

        best = rankings[0]

        if best["score"] < threshold:
            return None

        if len(rankings) > 1:
            second = rankings[1]

            if (
                best["score"]
                - second["score"]
                < margin
            ):
                return None

        return best

    def _rerank(
        self,
        text: str,
        rankings: list[dict],
        descriptions: dict[str, str],
        floor: float,
    ):
        if not rankings:
            return None

        if rankings[0]["score"] < floor:
            return None

        candidates = rankings[
            :self.rerank_top_k
        ]

        documents = [
            descriptions[
                candidate["label"]
            ]
            for candidate in candidates
        ]

        rerank_scores = list(
            self.reranker.rerank(
                text,
                documents,
            )
        )

        if not rerank_scores:
            return None

        reranked = []

        for candidate, score in zip(
            candidates,
            rerank_scores,
        ):
            reranked.append(
                {
                    "label": candidate[
                        "label"
                    ],
                    "score": round(
                        float(score),
                        4,
                    ),
                }
            )

        reranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return reranked[0]

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