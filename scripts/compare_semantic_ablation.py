import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DETERMINISTIC_RESULTS = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_blind_v3_deterministic_ablation_results.json"
)

SEMANTIC_RESULTS = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_blind_v3_results.json"
)

OUTPUT_JSON = (
    ROOT
    / "evaluation"
    / "semantic_fallback_ablation.json"
)

OUTPUT_MARKDOWN = (
    ROOT
    / "evaluation"
    / "semantic_fallback_ablation.md"
)

DETERMINISTIC_COMMIT = (
    "0a2f07cfe2a5b599c5a3662eb61967a272720c45"
)

SEMANTIC_COMMIT = (
    "38a254667e92aa8bbffe9f0220b4d42f057240a4"
)

BENCHMARK_COMMIT = (
    "f51534ee57ba21b7a08fbe2c4e176b1c8b13f7e4"
)


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def pct(value):
    if value is None:
        return None

    return value * 100


def pp_delta(
    semantic_value,
    deterministic_value,
):
    if (
        semantic_value is None
        or deterministic_value is None
    ):
        return None

    return (
        semantic_value
        - deterministic_value
    ) * 100


def metric_accuracy(
    results,
    key,
):
    metric = results.get(key)

    if not metric:
        return None

    return metric.get(
        "accuracy"
    )


def extraction_f1(
    results,
):
    extraction = results.get(
        "claimExtraction"
    )

    if not extraction:
        return None

    return extraction.get(
        "f1"
    )


def result_map(
    results,
):
    return {
        item["id"]: item
        for item in results.get(
            "results",
            []
        )
    }


def exact_binomial_probability(
    n,
    k,
):
    return (
        math.comb(
            n,
            k,
        )
        / (
            2 ** n
        )
    )


def exact_mcnemar(
    semantic_only,
    deterministic_only,
):
    discordant = (
        semantic_only
        + deterministic_only
    )

    if discordant == 0:
        return {
            "semanticOnly": semantic_only,
            "deterministicOnly": deterministic_only,
            "discordant": 0,
            "twoSidedPValue": 1.0,
        }

    smaller = min(
        semantic_only,
        deterministic_only,
    )

    tail = sum(
        exact_binomial_probability(
            discordant,
            value,
        )
        for value
        in range(
            smaller + 1
        )
    )

    p_value = min(
        1.0,
        2.0 * tail,
    )

    return {
        "semanticOnly": semantic_only,
        "deterministicOnly": deterministic_only,
        "discordant": discordant,
        "twoSidedPValue": p_value,
    }


def paired_cases(
    deterministic,
    semantic,
):
    deterministic_map = (
        result_map(
            deterministic
        )
    )

    semantic_map = (
        result_map(
            semantic
        )
    )

    deterministic_ids = set(
        deterministic_map
    )

    semantic_ids = set(
        semantic_map
    )

    if (
        deterministic_ids
        != semantic_ids
    ):
        missing_from_deterministic = sorted(
            semantic_ids
            - deterministic_ids
        )

        missing_from_semantic = sorted(
            deterministic_ids
            - semantic_ids
        )

        raise RuntimeError(
            (
                "Result case IDs differ. "
                f"Missing deterministic: "
                f"{missing_from_deterministic}. "
                f"Missing semantic: "
                f"{missing_from_semantic}."
            )
        )

    pairs = []

    for case_id in sorted(
        semantic_ids
    ):
        deterministic_result = (
            deterministic_map[
                case_id
            ]
        )

        semantic_result = (
            semantic_map[
                case_id
            ]
        )

        pairs.append(
            {
                "id": case_id,
                "category": (
                    semantic_result.get(
                        "category"
                    )
                ),
                "deterministicPassed": (
                    bool(
                        deterministic_result.get(
                            "passed"
                        )
                    )
                ),
                "semanticPassed": (
                    bool(
                        semantic_result.get(
                            "passed"
                        )
                    )
                ),
            }
        )

    return pairs


def paired_summary(
    pairs,
):
    both_correct = 0
    semantic_only = 0
    deterministic_only = 0
    both_wrong = 0

    semantic_wins = []
    deterministic_wins = []

    for pair in pairs:
        deterministic_passed = (
            pair[
                "deterministicPassed"
            ]
        )

        semantic_passed = (
            pair[
                "semanticPassed"
            ]
        )

        if (
            deterministic_passed
            and semantic_passed
        ):
            both_correct += 1

        elif (
            not deterministic_passed
            and semantic_passed
        ):
            semantic_only += 1
            semantic_wins.append(
                pair["id"]
            )

        elif (
            deterministic_passed
            and not semantic_passed
        ):
            deterministic_only += 1
            deterministic_wins.append(
                pair["id"]
            )

        else:
            both_wrong += 1

    return {
        "bothCorrect": both_correct,
        "semanticOnlyCorrect": (
            semantic_only
        ),
        "deterministicOnlyCorrect": (
            deterministic_only
        ),
        "bothWrong": both_wrong,
        "semanticWinCases": (
            semantic_wins
        ),
        "deterministicWinCases": (
            deterministic_wins
        ),
        "mcnemarExact": (
            exact_mcnemar(
                semantic_only,
                deterministic_only,
            )
        ),
    }


def category_summary(
    deterministic,
    semantic,
):
    deterministic_categories = (
        deterministic.get(
            "categoryAccuracy",
            {}
        )
    )

    semantic_categories = (
        semantic.get(
            "categoryAccuracy",
            {}
        )
    )

    categories = sorted(
        set(
            deterministic_categories
        )
        | set(
            semantic_categories
        )
    )

    summary = {}

    for category in categories:
        deterministic_metric = (
            deterministic_categories.get(
                category
            )
        )

        semantic_metric = (
            semantic_categories.get(
                category
            )
        )

        deterministic_accuracy = (
            deterministic_metric.get(
                "accuracy"
            )
            if deterministic_metric
            else None
        )

        semantic_accuracy = (
            semantic_metric.get(
                "accuracy"
            )
            if semantic_metric
            else None
        )

        summary[
            category
        ] = {
            "deterministic": (
                deterministic_metric
            ),
            "semantic": (
                semantic_metric
            ),
            "deltaPercentagePoints": (
                pp_delta(
                    semantic_accuracy,
                    deterministic_accuracy,
                )
            ),
        }

    return summary


def metrics_summary(
    deterministic,
    semantic,
):
    definitions = [
        (
            "caseAccuracy",
            "Case accuracy",
            metric_accuracy,
        ),
        (
            "statusAccuracy",
            "Status accuracy",
            metric_accuracy,
        ),
        (
            "routeAccuracy",
            "Route accuracy",
            metric_accuracy,
        ),
        (
            "claimExtractionF1",
            "Claim extraction F1",
            extraction_f1,
        ),
        (
            "responseSummaryStatusAccuracy",
            "Response summary",
            metric_accuracy,
        ),
        (
            "responseGroundingScoreAccuracy",
            "Grounding score",
            metric_accuracy,
        ),
        (
            "responseCoverageRatioAccuracy",
            "Coverage ratio",
            metric_accuracy,
        ),
    ]

    summary = {}

    for (
        key,
        label,
        resolver,
    ) in definitions:
        if resolver is metric_accuracy:
            deterministic_value = (
                resolver(
                    deterministic,
                    key,
                )
            )

            semantic_value = (
                resolver(
                    semantic,
                    key,
                )
            )

        else:
            deterministic_value = (
                resolver(
                    deterministic
                )
            )

            semantic_value = (
                resolver(
                    semantic
                )
            )

        summary[
            key
        ] = {
            "label": label,
            "deterministic": (
                deterministic_value
            ),
            "semantic": (
                semantic_value
            ),
            "deltaPercentagePoints": (
                pp_delta(
                    semantic_value,
                    deterministic_value,
                )
            ),
        }

    return summary


def format_percent(
    value,
):
    if value is None:
        return "—"

    return (
        f"{value * 100:.1f}%"
    )


def format_delta(
    value,
):
    if value is None:
        return "—"

    sign = (
        "+"
        if value > 0
        else ""
    )

    return (
        f"{sign}{value:.1f} pp"
    )


def build_markdown(
    metrics,
    paired,
    categories,
):
    lines = []

    lines.append(
        "# Semantic Fallback Ablation"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "This comparison evaluates a historical "
            "deterministic-only verification checkpoint "
            "and the final semantic-fallback system on "
            "the same frozen blind-v3 benchmark."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The comparison is retrospective. "
            "The blind-v3 benchmark had already been "
            "executed and inspected before the historical "
            "deterministic configuration was evaluated. "
            "Therefore, the deterministic run is not "
            "reported as a new blind evaluation."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The configuration difference should be "
            "interpreted as an ablation of the integrated "
            "semantic-fallback package, not as an isolated "
            "test of the embedding model alone. The final "
            "configuration includes embedding-based intent "
            "fallbacks together with proposition-level "
            "semantic handling introduced during semantic "
            "integration."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Overall Results"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "| Metric | Deterministic-only | "
            "Semantic fallback | Difference |"
        )
    )

    lines.append(
        "| --- | ---: | ---: | ---: |"
    )

    for metric in metrics.values():
        lines.append(
            (
                f"| {metric['label']} "
                f"| {format_percent(metric['deterministic'])} "
                f"| {format_percent(metric['semantic'])} "
                f"| {format_delta(metric['deltaPercentagePoints'])} |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "## Paired Case Comparison"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            f"- Correct under both configurations: "
            f"{paired['bothCorrect']}"
        )
    )

    lines.append(
        (
            f"- Correct only with semantic fallbacks: "
            f"{paired['semanticOnlyCorrect']}"
        )
    )

    lines.append(
        (
            f"- Correct only with deterministic-only "
            f"configuration: "
            f"{paired['deterministicOnlyCorrect']}"
        )
    )

    lines.append(
        (
            f"- Incorrect under both configurations: "
            f"{paired['bothWrong']}"
        )
    )

    lines.append(
        ""
    )

    mcnemar = paired[
        "mcnemarExact"
    ]

    lines.append(
        (
            "An exact two-sided McNemar test was applied "
            "to the discordant per-case outcomes. "
            f"The test used {mcnemar['discordant']} "
            "discordant cases and produced "
            f"`p = {mcnemar['twoSidedPValue']:.8g}`."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "This paired test quantifies the difference "
            "between the two configurations on this "
            "specific benchmark. It does not remove the "
            "limitations associated with the benchmark "
            "being internally authored."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Category Results"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "| Category | Deterministic-only | "
            "Semantic fallback | Difference |"
        )
    )

    lines.append(
        "| --- | ---: | ---: | ---: |"
    )

    for (
        category,
        values,
    ) in sorted(
        categories.items(),
        key=lambda item: (
            item[1][
                "deltaPercentagePoints"
            ]
            if item[1][
                "deltaPercentagePoints"
            ]
            is not None
            else -999
        ),
        reverse=True,
    ):
        deterministic_metric = (
            values[
                "deterministic"
            ]
        )

        semantic_metric = (
            values[
                "semantic"
            ]
        )

        deterministic_accuracy = (
            deterministic_metric.get(
                "accuracy"
            )
            if deterministic_metric
            else None
        )

        semantic_accuracy = (
            semantic_metric.get(
                "accuracy"
            )
            if semantic_metric
            else None
        )

        lines.append(
            (
                f"| {category} "
                f"| {format_percent(deterministic_accuracy)} "
                f"| {format_percent(semantic_accuracy)} "
                f"| {format_delta(values['deltaPercentagePoints'])} |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "## Interpretation"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The semantic-fallback configuration improves "
            "overall case accuracy while leaving factual "
            "claim extraction F1 unchanged. This indicates "
            "that the principal gain occurs after claim "
            "extraction, particularly in semantic routing "
            "and verification-status assignment."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The largest category-level gains identify "
            "domains in which deterministic lexical "
            "normalization was insufficient. These include "
            "origin propositions, treatment semantics, "
            "biological-cause formulations, long-COVID "
            "relations, and multi-claim response verification."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The comparison also records any cases that "
            "were correct under the deterministic checkpoint "
            "but incorrect under the semantic system. Such "
            "cases are retained as evidence that semantic "
            "generalization can introduce scope or "
            "overgeneralization errors even when aggregate "
            "accuracy improves."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Reproducibility"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            f"- Deterministic checkpoint: "
            f"`{DETERMINISTIC_COMMIT}`"
        )
    )

    lines.append(
        (
            f"- Semantic integration checkpoint: "
            f"`{SEMANTIC_COMMIT}`"
        )
    )

    lines.append(
        (
            f"- Frozen blind-v3 benchmark commit: "
            f"`{BENCHMARK_COMMIT}`"
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Both configurations were evaluated against "
            "the same benchmark labels and the same Neo4j "
            "knowledge-graph contents."
        )
    )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


def main():
    deterministic = load_json(
        DETERMINISTIC_RESULTS
    )

    semantic = load_json(
        SEMANTIC_RESULTS
    )

    if (
        deterministic.get(
            "benchmark"
        )
        != semantic.get(
            "benchmark"
        )
    ):
        raise RuntimeError(
            "Benchmark identifiers differ"
        )

    pairs = paired_cases(
        deterministic,
        semantic,
    )

    paired = paired_summary(
        pairs
    )

    metrics = metrics_summary(
        deterministic,
        semantic,
    )

    categories = category_summary(
        deterministic,
        semantic,
    )

    output = {
        "benchmark": semantic.get(
            "benchmark"
        ),
        "comparisonType": (
            "retrospective_paired_semantic_fallback_ablation"
        ),
        "deterministicCommit": (
            DETERMINISTIC_COMMIT
        ),
        "semanticCommit": (
            SEMANTIC_COMMIT
        ),
        "benchmarkCommit": (
            BENCHMARK_COMMIT
        ),
        "isolatesEmbeddingModelOnly": False,
        "blindEvaluation": False,
        "metrics": metrics,
        "pairedCaseComparison": paired,
        "categories": categories,
        "methodology": {
            "sameBenchmark": True,
            "pairedCases": True,
            "benchmarkInternallyAuthored": True,
            "interpretation": (
                "Ablation of the integrated semantic "
                "fallback package rather than an isolated "
                "embedding-model-only ablation."
            ),
        },
    }

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

        file.write(
            "\n"
        )

    markdown = build_markdown(
        metrics,
        paired,
        categories,
    )

    with OUTPUT_MARKDOWN.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            markdown
        )

    print(
        "SEMANTIC FALLBACK ABLATION"
    )

    print()

    for metric in metrics.values():
        print(
            (
                f"{metric['label']}: "
                f"{format_percent(metric['deterministic'])} "
                f"-> "
                f"{format_percent(metric['semantic'])} "
                f"({format_delta(metric['deltaPercentagePoints'])})"
            )
        )

    print()

    print(
        "PAIRED CASES"
    )

    print(
        (
            f"both correct: "
            f"{paired['bothCorrect']}"
        )
    )

    print(
        (
            f"semantic only correct: "
            f"{paired['semanticOnlyCorrect']}"
        )
    )

    print(
        (
            f"deterministic only correct: "
            f"{paired['deterministicOnlyCorrect']}"
        )
    )

    print(
        (
            f"both wrong: "
            f"{paired['bothWrong']}"
        )
    )

    print()

    print(
        (
            "McNemar exact two-sided p: "
            f"{paired['mcnemarExact']['twoSidedPValue']:.8g}"
        )
    )

    print()

    print(
        "SEMANTIC-ONLY WINS"
    )

    for case_id in paired[
        "semanticWinCases"
    ]:
        print(
            case_id
        )

    print()

    print(
        "DETERMINISTIC-ONLY WINS"
    )

    for case_id in paired[
        "deterministicWinCases"
    ]:
        print(
            case_id
        )

    print()

    print(
        f"JSON: {OUTPUT_JSON}"
    )

    print(
        f"MARKDOWN: {OUTPUT_MARKDOWN}"
    )


if __name__ == "__main__":
    main()