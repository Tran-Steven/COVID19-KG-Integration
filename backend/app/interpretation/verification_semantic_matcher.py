import math

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import (
    TextCrossEncoder,
)


class VerificationSemanticMatcher:
    MODEL_NAME = (
        "BAAI/bge-small-en-v1.5"
    )

    RERANK_MODEL_NAME = (
        "Xenova/ms-marco-MiniLM-L-6-v2"
    )

    PROTOTYPES = {
        "cause": [
            (
                "Which biological pathogen "
                "causes COVID-19?"
            ),
            (
                "COVID-19 results from "
                "infection by a virus."
            ),
            (
                "This virus is the causative "
                "agent of COVID-19."
            ),
            (
                "What infectious agent "
                "produces coronavirus "
                "disease 2019?"
            ),
            (
                "This pathogen is responsible "
                "for causing COVID-19."
            ),
        ],
        "treatment": [
            (
                "This medicine is used "
                "therapeutically for COVID-19."
            ),
            (
                "Can this antiviral be given "
                "as treatment for COVID-19?"
            ),
            (
                "The drug is administered "
                "to treat coronavirus "
                "disease 2019."
            ),
            (
                "This medication is a "
                "COVID-19 treatment."
            ),
            (
                "Does this medicine have "
                "a role in treating COVID-19?"
            ),
        ],
        "history": [
            (
                "On what date did WHO "
                "characterize COVID-19 "
                "as a pandemic?"
            ),
            (
                "Where was the earliest "
                "WHO-linked COVID-19 "
                "outbreak report?"
            ),
            (
                "The initial WHO-linked "
                "outbreak report was "
                "recorded in Wuhan."
            ),
            (
                "When did the WHO China "
                "Country Office receive the "
                "Wuhan pneumonia report?"
            ),
            (
                "What was the date of the "
                "first WHO-linked COVID-19 "
                "outbreak report?"
            ),
        ],
        "origin": [
            (
                "The source of SARS-CoV-2 "
                "remains unresolved."
            ),
            (
                "Could a laboratory event "
                "explain the origin of "
                "SARS-CoV-2?"
            ),
            (
                "Natural spillover is the "
                "strongest-supported origin "
                "hypothesis."
            ),
            (
                "Scientists do not know the "
                "exact origin of SARS-CoV-2."
            ),
            (
                "The available evidence "
                "does not establish a "
                "definitive origin."
            ),
            (
                "A laboratory-associated "
                "origin remains possible "
                "but unproven."
            ),
        ],
        "variants": [
            (
                "WHO continues monitoring "
                "this SARS-CoV-2 lineage."
            ),
            (
                "Is this lineage still "
                "tracked by WHO?"
            ),
            (
                "Which coronavirus variants "
                "are on WHO's monitoring list?"
            ),
            (
                "WHO stopped monitoring "
                "this SARS-CoV-2 variant."
            ),
            (
                "This SARS-CoV-2 lineage "
                "remains under surveillance."
            ),
        ],
        "out_of_scope": [
            (
                "Can electromagnetic signals "
                "cure COVID-19?"
            ),
            (
                "Do zodiac signs predict "
                "COVID-19 infection?"
            ),
            (
                "Can a wireless network "
                "cause coronavirus disease?"
            ),
            (
                "Do healing crystals prevent "
                "COVID-19?"
            ),
            (
                "Can radio waves cure "
                "COVID-19?"
            ),
            (
                "Can Bluetooth prevent "
                "COVID-19?"
            ),
        ],
    }

    DESCRIPTIONS = {
        "cause": (
            "COVID-19 biological cause intent: "
            "the statement or question concerns "
            "which virus, pathogen, infectious "
            "agent, or biological infection "
            "causes COVID-19."
        ),
        "treatment": (
            "COVID-19 treatment intent: the "
            "statement or question concerns "
            "whether a medicine, antiviral, "
            "drug, therapy, or clinical "
            "intervention is used to treat "
            "COVID-19."
        ),
        "history": (
            "COVID-19 WHO history intent: the "
            "statement or question concerns "
            "historical dates, locations, the "
            "initial Wuhan outbreak report, or "
            "WHO's pandemic characterization."
        ),
        "origin": (
            "SARS-CoV-2 origin intent: the "
            "statement or question concerns the "
            "origin of SARS-CoV-2, zoonotic "
            "spillover, laboratory-related "
            "events, cold-chain hypotheses, or "
            "uncertainty about the exact origin."
        ),
        "variants": (
            "SARS-CoV-2 variant monitoring "
            "intent: the statement or question "
            "concerns a viral lineage, variant, "
            "WHO monitoring, tracking, or "
            "surveillance."
        ),
        "out_of_scope": (
            "Unsupported COVID-19 claim outside "
            "the modeled medical evidence "
            "relations, such as wireless "
            "signals, astrology, crystals, "
            "Bluetooth, radio waves, or other "
            "nonmedical mechanisms."
        ),
    }

    def __init__(
        self,
        model=None,
        reranker=None,
        threshold: float = 0.70,
        margin: float = 0.02,
        fallback_floor: float = 0.62,
        fallback_margin: float = 0.08,
        rerank_floor: float = 0.62,
        rerank_top_k: int = 3,
    ):
        self.threshold = threshold
        self.margin = margin

        self.fallback_floor = (
            fallback_floor
        )

        self.fallback_margin = (
            fallback_margin
        )

        self.rerank_floor = (
            rerank_floor
        )

        self.rerank_top_k = (
            rerank_top_k
        )

        self.model = (
            model
            if model is not None
            else TextEmbedding(
                model_name=(
                    self.MODEL_NAME
                )
            )
        )

        self.reranker = (
            reranker
            if reranker is not None
            else TextCrossEncoder(
                model_name=(
                    self.RERANK_MODEL_NAME
                )
            )
        )

        self.prototype_embeddings = (
            self._build_embeddings()
        )

    def resolve(
        self,
        text: str,
        allowed_labels: set[str]
        | None = None,
    ):
        rankings = self.rank(
            text=text,
            allowed_labels=(
                allowed_labels
            ),
        )

        match = self._select(
            rankings
        )

        if match:
            return {
                "label": match[
                    "label"
                ],
                "method": (
                    "semantic_embedding"
                ),
                "score": match[
                    "score"
                ],
                "embeddingScore": (
                    match["score"]
                ),
            }

        fallback = (
            self._select_fallback(
                rankings
            )
        )

        if fallback:
            return {
                "label": fallback[
                    "label"
                ],
                "method": (
                    "semantic_embedding_fallback"
                ),
                "score": fallback[
                    "score"
                ],
                "embeddingScore": (
                    fallback[
                        "score"
                    ]
                ),
            }

        reranked = self._rerank(
            text=text,
            rankings=rankings,
        )

        if not reranked:
            return None

        return {
            "label": reranked[
                "label"
            ],
            "method": (
                "semantic_rerank"
            ),
            "score": reranked[
                "score"
            ],
            "embeddingScore": (
                reranked[
                    "embeddingScore"
                ]
            ),
        }

    def rank(
        self,
        text: str,
        allowed_labels: set[str]
        | None = None,
    ):
        vectors = list(
            self.model.embed(
                [text]
            )
        )

        if not vectors:
            return []

        query_vector = vectors[0]

        rankings = []

        for (
            label,
            prototype_vectors,
        ) in (
            self.prototype_embeddings
            .items()
        ):
            if (
                allowed_labels is not None
                and label
                not in allowed_labels
            ):
                continue

            similarities = [
                self._cosine_similarity(
                    query_vector,
                    prototype_vector,
                )
                for prototype_vector
                in prototype_vectors
            ]

            if not similarities:
                continue

            rankings.append(
                {
                    "label": label,
                    "score": round(
                        max(
                            similarities
                        ),
                        4,
                    ),
                }
            )

        rankings.sort(
            key=(
                lambda item:
                item["score"]
            ),
            reverse=True,
        )

        return rankings

    def _build_embeddings(
        self,
    ):
        embeddings = {}

        for (
            label,
            prototypes,
        ) in self.PROTOTYPES.items():
            embeddings[
                label
            ] = list(
                self.model.embed(
                    prototypes
                )
            )

        return embeddings

    def _select(
        self,
        rankings: list[dict],
    ):
        if not rankings:
            return None

        best = rankings[0]

        if (
            best["score"]
            < self.threshold
        ):
            return None

        if len(
            rankings
        ) > 1:
            second = rankings[1]

            if (
                best["score"]
                - second["score"]
                < self.margin
            ):
                return None

        return best

    def _select_fallback(
        self,
        rankings: list[dict],
    ):
        if not rankings:
            return None

        best = rankings[0]

        if (
            best["score"]
            < self.fallback_floor
        ):
            return None

        if len(
            rankings
        ) == 1:
            return best

        second = rankings[1]

        if (
            best["score"]
            - second["score"]
            < self.fallback_margin
        ):
            return None

        return best

    def _rerank(
        self,
        text: str,
        rankings: list[dict],
    ):
        if not rankings:
            return None

        embedding_winner = (
            rankings[0]
        )

        if (
            embedding_winner[
                "score"
            ]
            < self.rerank_floor
        ):
            return None

        candidates = rankings[
            :self.rerank_top_k
        ]

        documents = [
            self.DESCRIPTIONS[
                candidate["label"]
            ]
            for candidate
            in candidates
        ]

        scores = list(
            self.reranker.rerank(
                text,
                documents,
            )
        )

        if not scores:
            return None

        reranked = []

        for (
            candidate,
            score,
        ) in zip(
            candidates,
            scores,
        ):
            reranked.append(
                {
                    "label": (
                        candidate[
                            "label"
                        ]
                    ),
                    "score": round(
                        float(
                            score
                        ),
                        4,
                    ),
                    "embeddingScore": (
                        candidate[
                            "score"
                        ]
                    ),
                }
            )

        reranked.sort(
            key=(
                lambda item:
                item["score"]
            ),
            reverse=True,
        )

        rerank_winner = (
            reranked[0]
        )

        if (
            rerank_winner[
                "label"
            ]
            != embedding_winner[
                "label"
            ]
        ):
            return None

        return rerank_winner

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