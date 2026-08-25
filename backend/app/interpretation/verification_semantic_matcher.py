import math

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder


class VerificationSemanticMatcher:
    MODEL_NAME = "BAAI/bge-small-en-v1.5"
    RERANK_MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"

    PROTOTYPES = {
        "cause": [
            "Which biological pathogen causes COVID-19?",
            "COVID-19 results from infection by a virus.",
            "This virus is the causative agent of COVID-19.",
            "What infectious agent produces coronavirus disease 2019?",
            "This pathogen is responsible for causing COVID-19.",
        ],
        "treatment": [
            "This medicine is used therapeutically for COVID-19.",
            "Can this antiviral be given as treatment for COVID-19?",
            "The drug is administered to treat coronavirus disease 2019.",
            "This medication is a COVID-19 treatment.",
            "Does this medicine have a role in treating COVID-19?",
        ],
        "history": [
            "On what date did WHO characterize COVID-19 as a pandemic?",
            "Where was the earliest WHO-linked COVID-19 outbreak report?",
            "The initial WHO-linked outbreak report was recorded in Wuhan.",
            "When did the WHO China Country Office receive the Wuhan pneumonia report?",
            "What was the date of the first WHO-linked COVID-19 outbreak report?",
        ],
        "origin": [
            "The source of SARS-CoV-2 remains unresolved.",
            "Could a laboratory event explain the origin of SARS-CoV-2?",
            "Natural spillover is the strongest-supported origin hypothesis.",
            "Scientists do not know the exact origin of SARS-CoV-2.",
            "The available evidence does not establish a definitive origin.",
            "A laboratory-associated origin remains possible but unproven.",
        ],
        "variants": [
            "WHO continues monitoring this SARS-CoV-2 lineage.",
            "Is this lineage still tracked by WHO?",
            "Which coronavirus variants are on WHO's monitoring list?",
            "WHO stopped monitoring this SARS-CoV-2 variant.",
            "This SARS-CoV-2 lineage remains under surveillance.",
        ],
        "out_of_scope": [
            "Can electromagnetic signals cure COVID-19?",
            "Do zodiac signs predict COVID-19 infection?",
            "Can a wireless network cause coronavirus disease?",
            "Do healing crystals prevent COVID-19?",
            "Can radio waves cure COVID-19?",
            "Can Bluetooth prevent COVID-19?",
        ],
    }

    DESCRIPTIONS = {
        "cause": (
            "COVID-19 biological cause intent involving which virus, "
            "pathogen, infectious agent, or biological infection causes "
            "COVID-19."
        ),
        "treatment": (
            "COVID-19 treatment intent involving whether a medicine, "
            "antiviral, drug, therapy, or clinical intervention is used "
            "to treat COVID-19."
        ),
        "history": (
            "COVID-19 WHO history intent involving historical dates, "
            "locations, the initial Wuhan outbreak report, or WHO's "
            "pandemic characterization."
        ),
        "origin": (
            "SARS-CoV-2 origin intent involving zoonotic spillover, "
            "laboratory-related events, cold-chain hypotheses, or "
            "uncertainty about the exact origin."
        ),
        "variants": (
            "SARS-CoV-2 variant monitoring intent involving a lineage, "
            "variant, WHO monitoring, tracking, or surveillance."
        ),
        "out_of_scope": (
            "Unsupported COVID-19 claim outside modeled medical evidence "
            "relations such as wireless signals, astrology, crystals, "
            "Bluetooth, radio waves, or other nonmedical mechanisms."
        ),
    }

    ORIGIN_PROTOTYPES = {
        "origin_inconclusive": [
            "The exact origin remains unsettled.",
            "Researchers have not determined the precise origin.",
            "The source remains unresolved.",
            "Scientists are still uncertain about the exact origin.",
            "The available evidence does not settle the origin.",
        ],
        "origin_lab_uncertain": [
            "A laboratory-related origin remains possible but unproven.",
            "A lab-associated event cannot be confirmed or excluded.",
            "The laboratory hypothesis has neither been established nor dismissed.",
            "A lab event remains plausible without being demonstrated.",
            "Available evidence cannot establish or reject a laboratory origin.",
        ],
        "origin_lab_ruled_out": [
            "A laboratory-related origin has been ruled out.",
            "Researchers have excluded a laboratory event as the origin.",
            "A lab-associated explanation has been dismissed as impossible.",
            "Scientists have eliminated a laboratory origin as a possibility.",
        ],
        "origin_negative_support": [
            "There is no evidence supporting this origin hypothesis.",
            "Scientific evidence does not support this hypothesis over natural processes.",
            "No additional evidence supports the proposed origin mechanism.",
            "Available data fail to support this origin explanation.",
            "The evidence provides no support for this hypothesis.",
        ],
        "origin_positive_support": [
            "New evidence supports this origin hypothesis.",
            "Scientific evidence favors this origin explanation over alternatives.",
            "This hypothesis has stronger evidentiary support.",
            "Additional evidence supports the proposed origin mechanism.",
            "Available data point toward this origin explanation.",
        ],
        "origin_certainty": [
            "This origin hypothesis has been conclusively established.",
            "This explanation has been proven beyond doubt.",
            "Scientists have definitively proven this origin mechanism.",
            "This hypothesis is established with complete certainty.",
            "Researchers have conclusively demonstrated this specific origin.",
        ],
        "origin_broad_certainty": [
            "Scientists have settled the exact origin.",
            "The exact origin is definitively known.",
            "Researchers know precisely how the virus originated.",
            "Scientists now know the precise source with certainty.",
            "The origin question has been completely resolved.",
        ],
    }

    ORIGIN_DESCRIPTIONS = {
        "origin_inconclusive": (
            "The overall SARS-CoV-2 origin remains unresolved, uncertain, "
            "undetermined, or not settled."
        ),
        "origin_lab_uncertain": (
            "A laboratory-related origin cannot currently be proven or "
            "ruled out and remains possible but unconfirmed."
        ),
        "origin_lab_ruled_out": (
            "The claim says a laboratory-related origin has been ruled "
            "out, excluded, dismissed, or shown impossible."
        ),
        "origin_negative_support": (
            "The claim says scientific or additional evidence does not "
            "support an origin hypothesis."
        ),
        "origin_positive_support": (
            "The claim says evidence supports, favors, points toward, or "
            "strengthens an origin hypothesis."
        ),
        "origin_certainty": (
            "The claim presents a specific origin hypothesis as proven, "
            "conclusive, definitive, or established beyond uncertainty."
        ),
        "origin_broad_certainty": (
            "The claim presents the overall exact origin as settled, "
            "definitively known, precisely established, or completely resolved."
        ),
    }

    def __init__(
        self,
        model=None,
        reranker=None,
        threshold=0.70,
        margin=0.02,
        fallback_floor=0.62,
        fallback_margin=0.08,
        rerank_floor=0.62,
        rerank_top_k=3,
    ):
        self.threshold = threshold
        self.margin = margin
        self.fallback_floor = fallback_floor
        self.fallback_margin = fallback_margin
        self.rerank_floor = rerank_floor
        self.rerank_top_k = rerank_top_k

        self.model = (
            model
            if model is not None
            else TextEmbedding(
                model_name=self.MODEL_NAME
            )
        )

        self.reranker = (
            reranker
            if reranker is not None
            else TextCrossEncoder(
                model_name=self.RERANK_MODEL_NAME
            )
        )

        self.prototype_embeddings = (
            self._build_embeddings(
                self.PROTOTYPES
            )
        )

        self.origin_embeddings = (
            self._build_embeddings(
                self.ORIGIN_PROTOTYPES
            )
        )

    def resolve(
        self,
        text,
        allowed_labels=None,
    ):
        rankings = self.rank(
            text=text,
            allowed_labels=allowed_labels,
        )

        return self._resolve_rankings(
            text=text,
            rankings=rankings,
            descriptions=self.DESCRIPTIONS,
            threshold=self.threshold,
            margin=self.margin,
            fallback_floor=self.fallback_floor,
            fallback_margin=self.fallback_margin,
            rerank_floor=self.rerank_floor,
        )

    def resolve_origin_proposition(
        self,
        text,
    ):
        rankings = (
            self.rank_origin_propositions(
                text
            )
        )

        return self._resolve_rankings(
            text=text,
            rankings=rankings,
            descriptions=self.ORIGIN_DESCRIPTIONS,
            threshold=0.70,
            margin=0.02,
            fallback_floor=0.62,
            fallback_margin=0.07,
            rerank_floor=0.62,
        )

    def rank(
        self,
        text,
        allowed_labels=None,
    ):
        return self._rank(
            text=text,
            prototype_embeddings=(
                self.prototype_embeddings
            ),
            allowed_labels=allowed_labels,
        )

    def rank_origin_propositions(
        self,
        text,
    ):
        return self._rank(
            text=text,
            prototype_embeddings=(
                self.origin_embeddings
            ),
            allowed_labels=None,
        )

    def _build_embeddings(
        self,
        prototypes,
    ):
        result = {}

        for (
            label,
            phrases,
        ) in prototypes.items():
            result[label] = list(
                self.model.embed(
                    phrases
                )
            )

        return result

    def _rank(
        self,
        text,
        prototype_embeddings,
        allowed_labels,
    ):
        query_vectors = list(
            self.model.embed(
                [text]
            )
        )

        if not query_vectors:
            return []

        query_vector = (
            query_vectors[0]
        )

        rankings = []

        for (
            label,
            vectors,
        ) in (
            prototype_embeddings
            .items()
        ):
            if (
                allowed_labels
                is not None
                and label
                not in allowed_labels
            ):
                continue

            similarities = [
                self._cosine_similarity(
                    query_vector,
                    vector,
                )
                for vector
                in vectors
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
            key=lambda item: (
                item["score"]
            ),
            reverse=True,
        )

        return rankings

    def _resolve_rankings(
        self,
        text,
        rankings,
        descriptions,
        threshold,
        margin,
        fallback_floor,
        fallback_margin,
        rerank_floor,
    ):
        match = self._select(
            rankings,
            threshold,
            margin,
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
                    match[
                        "score"
                    ]
                ),
            }

        fallback = (
            self._select_fallback(
                rankings,
                fallback_floor,
                fallback_margin,
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
            descriptions=descriptions,
            floor=rerank_floor,
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

    def _select(
        self,
        rankings,
        threshold,
        margin,
    ):
        if not rankings:
            return None

        best = rankings[0]

        if (
            best["score"]
            < threshold
        ):
            return None

        if len(
            rankings
        ) > 1:
            second = rankings[1]

            if (
                best["score"]
                - second["score"]
                < margin
            ):
                return None

        return best

    def _select_fallback(
        self,
        rankings,
        floor,
        margin,
    ):
        if not rankings:
            return None

        best = rankings[0]

        if best["score"] < floor:
            return None

        if len(rankings) == 1:
            return best

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
        text,
        rankings,
        descriptions,
        floor,
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
            < floor
        ):
            return None

        candidates = rankings[
            :self.rerank_top_k
        ]

        documents = [
            descriptions[
                candidate[
                    "label"
                ]
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
            key=lambda item: (
                item["score"]
            ),
            reverse=True,
        )

        winner = (
            reranked[0]
        )

        if (
            winner["label"]
            != embedding_winner[
                "label"
            ]
        ):
            return None

        return winner

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


_matcher = None


def get_verification_semantic_matcher():
    global _matcher

    if _matcher is None:
        _matcher = (
            VerificationSemanticMatcher()
        )

    return _matcher