import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_JSON = (
    ROOT
    / "evaluation"
    / "verification_evaluation_summary.json"
)

OUTPUT_MARKDOWN = (
    ROOT
    / "evaluation"
    / "verification_evaluation_summary.md"
)

STAGES = [
    {
        "id": "initial_holdout",
        "label": "Initial frozen holdout",
        "systemStage": (
            "Pre-targeted verification refinements"
        ),
        "path": (
            ROOT
            / "evaluation"
            / "end_to_end_verification_holdout_initial_results.json"
        ),
        "evaluationType": (
            "fresh_holdout_first_run"
        ),
        "generalizationEstimate": True,
        "notes": [
            (
                "First recorded evaluation on the "
                "60-case unseen holdout."
            ),
            (
                "Labels were defined before the first "
                "recorded run."
            ),
            (
                "The available development transcript "
                "does not independently establish that "
                "the benchmark file was committed to Git "
                "before execution."
            ),
            (
                "The benchmark was internally authored "
                "rather than independently constructed "
                "by an external evaluator."
            ),
        ],
    },
    {
        "id": "final_holdout_v1",
        "label": "Fresh 80-case holdout",
        "systemStage": (
            "After targeted claim, history, response, "
            "and treatment verification refinements"
        ),
        "path": (
            ROOT
            / "evaluation"
            / "end_to_end_verification_final_holdout_results.json"
        ),
        "evaluationType": (
            "fresh_holdout_first_run"
        ),
        "generalizationEstimate": True,
        "notes": [
            (
                "Fresh 80-case holdout evaluated before "
                "the subsequent semantic-normalization "
                "and proposition-level development work."
            ),
            (
                "The benchmark was internally authored "
                "with knowledge of the target system "
                "capabilities."
            ),
            (
                "After this first run, its failures were "
                "observed and used to guide later "
                "development, so later executions of the "
                "same set would not be blind."
            ),
        ],
    },
    {
        "id": "blind_v2",
        "label": "Blind holdout v2",
        "systemStage": (
            "After generalized deterministic routing, "
            "origin qualifiers, and response extraction"
        ),
        "path": (
            ROOT
            / "evaluation"
            / "end_to_end_verification_blind_v2_results.json"
        ),
        "evaluationType": (
            "fresh_frozen_holdout_first_run"
        ),
        "generalizationEstimate": True,
        "notes": [
            (
                "Fresh 100-case frozen holdout evaluated "
                "after deterministic semantic-routing, "
                "origin-qualifier, and response-extraction "
                "improvements."
            ),
            (
                "The implementation was not tuned using "
                "the results before the reported first-run "
                "score."
            ),
            (
                "The benchmark was internally authored "
                "and is not an independent third-party "
                "evaluation."
            ),
        ],
    },
    {
        "id": "blind_v3",
        "label": "Blind holdout v3",
        "systemStage": (
            "After embedding-based semantic fallbacks "
            "and proposition-level origin matching"
        ),
        "path": (
            ROOT
            / "evaluation"
            / "end_to_end_verification_blind_v3_results.json"
        ),
        "evaluationType": (
            "fresh_frozen_holdout_first_run"
        ),
        "generalizationEstimate": True,
        "implementationCommit": (
            "38a254667e92aa8bbffe9f0220b4d42f057240a4"
        ),
        "benchmarkCommit": (
            "f51534ee57ba21b7a08fbe2c4e176b1c8b13f7e4"
        ),
        "benchmarkSha256": (
            "b2e9b2e93099cf34ad683e451520bcfb"
            "531ed84c8a5e4a7f17179aa785a40884"
        ),
        "notes": [
            (
                "Fresh 100-case frozen holdout containing "
                "80 direct claim cases and 20 "
                "response-level cases."
            ),
            (
                "The benchmark was committed before its "
                "first execution against the frozen "
                "semantic-fallback implementation."
            ),
            (
                "The benchmark generator rejected exact "
                "atomic-claim overlap with prior "
                "evaluation sets before freezing."
            ),
            (
                "The benchmark was internally authored "
                "and therefore does not constitute an "
                "independent third-party evaluation."
            ),
        ],
    },
]


def load_json(
    path: Path,
):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def accuracy(
    metric,
):
    if not metric:
        return None

    return metric.get(
        "accuracy"
    )


def percent(
    value,
):
    if value is None:
        return None

    return round(
        value * 100,
        1,
    )


def wilson_interval(
    passed,
    total,
    z=1.96,
):
    if not total:
        return {
            "lower": None,
            "upper": None,
        }

    proportion = (
        passed
        / total
    )

    denominator = (
        1
        + (
            z * z
            / total
        )
    )

    center = (
        proportion
        + (
            z * z
            / (
                2
                * total
            )
        )
    )

    adjustment = (
        z
        * math.sqrt(
            (
                proportion
                * (
                    1
                    - proportion
                )
                / total
            )
            + (
                z
                * z
                / (
                    4
                    * total
                    * total
                )
            )
        )
    )

    lower = (
        center
        - adjustment
    ) / denominator

    upper = (
        center
        + adjustment
    ) / denominator

    return {
        "lower": lower,
        "upper": upper,
    }


def metric_summary(
    metric,
):
    if not metric:
        return None

    return {
        "passed": metric.get(
            "passed"
        ),
        "total": metric.get(
            "total"
        ),
        "accuracy": metric.get(
            "accuracy"
        ),
    }


def extraction_summary(
    extraction,
):
    if not extraction:
        return None

    return {
        "matched": extraction.get(
            "matched"
        ),
        "expected": extraction.get(
            "expected"
        ),
        "actual": extraction.get(
            "actual"
        ),
        "precision": extraction.get(
            "precision"
        ),
        "recall": extraction.get(
            "recall"
        ),
        "f1": extraction.get(
            "f1"
        ),
    }


def summarize_stage(
    definition,
):
    results = load_json(
        definition[
            "path"
        ]
    )

    case_metric = results[
        "caseAccuracy"
    ]

    interval = wilson_interval(
        case_metric[
            "passed"
        ],
        case_metric[
            "total"
        ],
    )

    confidence = results.get(
        "confidenceDiagnostics",
        {},
    )

    stage = {
        "id": definition[
            "id"
        ],
        "label": definition[
            "label"
        ],
        "systemStage": definition[
            "systemStage"
        ],
        "benchmark": results.get(
            "benchmark"
        ),
        "evaluationType": definition[
            "evaluationType"
        ],
        "generalizationEstimate": (
            definition[
                "generalizationEstimate"
            ]
        ),
        "sourceResults": str(
            definition[
                "path"
            ].relative_to(
                ROOT
            )
        ),
        "caseAccuracy": (
            metric_summary(
                case_metric
            )
        ),
        "caseAccuracyWilson95": (
            interval
        ),
        "statusAccuracy": (
            metric_summary(
                results.get(
                    "statusAccuracy"
                )
            )
        ),
        "routeAccuracy": (
            metric_summary(
                results.get(
                    "routeAccuracy"
                )
            )
        ),
        "claimExtraction": (
            extraction_summary(
                results.get(
                    "claimExtraction"
                )
            )
        ),
        "questionContextAccuracy": (
            metric_summary(
                results.get(
                    "questionContextAccuracy"
                )
            )
        ),
        "responseSummaryStatusAccuracy": (
            metric_summary(
                results.get(
                    "responseSummaryStatusAccuracy"
                )
            )
        ),
        "responseGroundingScoreAccuracy": (
            metric_summary(
                results.get(
                    "responseGroundingScoreAccuracy"
                )
            )
        ),
        "responseCoverageRatioAccuracy": (
            metric_summary(
                results.get(
                    "responseCoverageRatioAccuracy"
                )
            )
        ),
        "confidenceDiagnostics": {
            "calibrated": confidence.get(
                "calibrated"
            ),
            "meanConfidenceWhenCorrect": (
                confidence.get(
                    "meanConfidenceWhenCorrect"
                )
            ),
            "meanConfidenceWhenIncorrect": (
                confidence.get(
                    "meanConfidenceWhenIncorrect"
                )
            ),
        },
        "notes": definition[
            "notes"
        ],
    }

    if (
        "implementationCommit"
        in definition
    ):
        stage[
            "implementationCommit"
        ] = definition[
            "implementationCommit"
        ]

    if (
        "benchmarkCommit"
        in definition
    ):
        stage[
            "benchmarkCommit"
        ] = definition[
            "benchmarkCommit"
        ]

    if (
        "benchmarkSha256"
        in definition
    ):
        stage[
            "benchmarkSha256"
        ] = definition[
            "benchmarkSha256"
        ]

    return stage


def value_or_dash(
    value,
):
    if value is None:
        return "—"

    return (
        f"{value * 100:.1f}%"
    )


def case_value(
    stage,
):
    metric = stage[
        "caseAccuracy"
    ]

    return (
        f"{metric['passed']}/"
        f"{metric['total']} "
        f"({metric['accuracy'] * 100:.1f}%)"
    )


def ci_value(
    stage,
):
    interval = stage[
        "caseAccuracyWilson95"
    ]

    return (
        f"{interval['lower'] * 100:.1f}%–"
        f"{interval['upper'] * 100:.1f}%"
    )


def extraction_f1(
    stage,
):
    extraction = stage.get(
        "claimExtraction"
    )

    if not extraction:
        return "—"

    value = extraction.get(
        "f1"
    )

    return value_or_dash(
        value
    )


def metric_value(
    stage,
    key,
):
    metric = stage.get(
        key
    )

    if not metric:
        return "—"

    return value_or_dash(
        metric.get(
            "accuracy"
        )
    )


def build_markdown(
    stages,
):
    lines = []

    lines.append(
        "# Verification Evaluation Summary"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "This document summarizes the project's "
            "fresh holdout evaluations across major "
            "system-development stages. The benchmarks "
            "differ between rows, so changes in accuracy "
            "should be interpreted as system-evolution "
            "evidence rather than paired-test improvements."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "All listed benchmarks were internally "
            "authored. They are useful for measuring "
            "generalization beyond development cases, "
            "but they are not independent third-party "
            "evaluations."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Frozen holdout progression"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "| Evaluation | System stage | "
            "Case accuracy | Wilson 95% CI | "
            "Status accuracy | Route accuracy | "
            "Claim extraction F1 |"
        )
    )

    lines.append(
        (
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |"
        )
    )

    for stage in stages:
        lines.append(
            (
                f"| {stage['label']} "
                f"| {stage['systemStage']} "
                f"| {case_value(stage)} "
                f"| {ci_value(stage)} "
                f"| {metric_value(stage, 'statusAccuracy')} "
                f"| {metric_value(stage, 'routeAccuracy')} "
                f"| {extraction_f1(stage)} |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "## Response-level metrics"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "| Evaluation | Question context | "
            "Response summary | Grounding score | Coverage ratio |"
        )
    )

    lines.append(
        "| --- | ---: | ---: | ---: | ---: |"
    )

    for stage in stages:
        lines.append(
            (
                f"| {stage['label']} "
                f"| {metric_value(stage, 'questionContextAccuracy')} "
                f"| {metric_value(stage, 'responseSummaryStatusAccuracy')} "
                f"| {metric_value(stage, 'responseGroundingScoreAccuracy')} "
                f"| {metric_value(stage, 'responseCoverageRatioAccuracy')} |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "## Confidence diagnostics"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "| Evaluation | Mean confidence when "
            "status correct | Mean confidence when "
            "status incorrect |"
        )
    )

    lines.append(
        "| --- | ---: | ---: |"
    )

    for stage in stages:
        confidence = stage[
            "confidenceDiagnostics"
        ]

        correct = confidence.get(
            "meanConfidenceWhenCorrect"
        )

        incorrect = confidence.get(
            "meanConfidenceWhenIncorrect"
        )

        lines.append(
            (
                f"| {stage['label']} "
                f"| {correct:.3f} "
                if correct is not None
                else (
                    f"| {stage['label']} | — "
                )
            )
            + (
                f"| {incorrect:.3f} |"
                if incorrect is not None
                else "| — |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        (
            "Confidence is a heuristic "
            "evidence-grounding score. It is not "
            "calibrated and must not be interpreted "
            "as the probability that a claim is true "
            "or that a verification decision is correct."
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
            "The first 60-case holdout produced "
            "**41.7% case accuracy**, exposing substantial "
            "generalization weaknesses despite strong "
            "development-set performance."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "After targeted improvements to history, "
            "claim interpretation, response handling, "
            "and treatment semantics, a separate "
            "80-case holdout reached **70.0%**."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "A subsequent 100-case blind holdout after "
            "generalized deterministic routing, origin "
            "qualifier handling, and response-extraction "
            "improvements reached **71.0%**. The limited "
            "change on a fresh benchmark suggested that "
            "additional lexical and deterministic rules "
            "alone were not resolving the remaining "
            "semantic bottleneck."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "After introducing embedding-based semantic "
            "fallbacks and proposition-level semantic "
            "matching, the fresh blind-v3 holdout reached "
            "**79.0% case accuracy**. Route accuracy "
            "remained high while status accuracy improved, "
            "supporting the interpretation that the "
            "remaining errors are increasingly associated "
            "with proposition polarity, entity matching, "
            "scope control, contextual references, and "
            "state-change semantics rather than broad "
            "domain routing."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The 71% and 79% values come from different "
            "internally authored holdouts, so the "
            "eight-percentage-point difference should "
            "not be presented as a paired or statistically "
            "significant improvement without additional "
            "evaluation."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Methodological status"
    )

    lines.append(
        ""
    )

    for stage in stages:
        lines.append(
            f"### {stage['label']}"
        )

        lines.append(
            ""
        )

        for note in stage[
            "notes"
        ]:
            lines.append(
                f"- {note}"
            )

        if stage.get(
            "implementationCommit"
        ):
            lines.append(
                (
                    "- Frozen implementation commit: "
                    f"`{stage['implementationCommit']}`"
                )
            )

        if stage.get(
            "benchmarkCommit"
        ):
            lines.append(
                (
                    "- Frozen benchmark commit: "
                    f"`{stage['benchmarkCommit']}`"
                )
            )

        if stage.get(
            "benchmarkSha256"
        ):
            lines.append(
                (
                    "- Benchmark SHA-256: "
                    f"`{stage['benchmarkSha256']}`"
                )
            )

        lines.append(
            ""
        )

    lines.append(
        "## Reporting guidance"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "The development regression benchmark may "
            "be reported separately as a development "
            "check, but its 100% score should not be "
            "used as a generalization estimate."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "Any rerun of a holdout after its failures "
            "have been inspected or used to modify the "
            "system must be labeled post-analysis rather "
            "than blind or unseen."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "No claim of statistical significance should "
            "be made from differences across these "
            "separately constructed holdouts without an "
            "appropriate statistical design."
        )
    )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


def main():
    stages = [
        summarize_stage(
            definition
        )
        for definition in STAGES
    ]

    output = {
        "title": (
            "COVID-19 KG verification evaluation summary"
        ),
        "comparisonType": (
            "system_evolution_across_distinct_holdouts"
        ),
        "pairedComparison": False,
        "independentExternalEvaluation": False,
        "stages": stages,
        "reportingConstraints": [
            (
                "Do not describe development-set "
                "performance as blind generalization."
            ),
            (
                "Do not describe a holdout as blind "
                "after its failures have been inspected "
                "and used for tuning."
            ),
            (
                "Do not claim statistical significance "
                "for differences across distinct "
                "internally authored holdouts without "
                "additional analysis."
            ),
            (
                "Do not interpret confidence scores as "
                "truth probabilities."
            ),
        ],
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
        stages
    )

    with OUTPUT_MARKDOWN.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            markdown
        )

    print(
        "VERIFICATION EVALUATION SUMMARY"
    )

    print()

    for stage in stages:
        case_metric = stage[
            "caseAccuracy"
        ]

        print(
            (
                f"{stage['label']}: "
                f"{case_metric['passed']}/"
                f"{case_metric['total']} "
                f"({case_metric['accuracy'] * 100:.1f}%)"
            )
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