import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RESULTS = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_blind_v3_results.json"
)

DEFAULT_JSON_OUTPUT = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_blind_v3_error_analysis.json"
)

DEFAULT_MARKDOWN_OUTPUT = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_blind_v3_error_analysis.md"
)

SUPPORTED = "SUPPORTED"
CONTRADICTED = "CONTRADICTED"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
NOT_VERIFIABLE = (
    "NOT_VERIFIABLE_WITH_CURRENT_KG"
)

CAUSE_PRIORITY = [
    "claim_extraction",
    "contextual_reference_resolution",
    "history_routing",
    "scope_or_domain_overreach",
    "proposition_entity_mismatch",
    "state_change_polarity",
    "exclusivity_or_quantifier",
    "negation_or_polarity",
    "treatment_overclaim_scope",
    "certainty_overclaim_semantics",
    "uncertainty_entailment",
    "semantic_routing",
    "context_usage_mismatch",
    "response_aggregation",
    "other",
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


def normalize(
    text: str,
):
    return " ".join(
        text.lower().split()
    )


def contains_any(
    text: str,
    values,
):
    normalized = normalize(
        text
    )

    return any(
        value in normalized
        for value in values
    )


def classify_atomic_failure(
    text: str,
    category: str,
    expected: dict,
    actual: dict | None,
):
    if actual is None:
        return (
            "claim_extraction"
        )

    expected_route = (
        expected.get(
            "route"
        )
    )

    actual_route = (
        actual.get(
            "route"
        )
    )

    expected_status = (
        expected.get(
            "status"
        )
    )

    actual_status = (
        actual.get(
            "status"
        )
    )

    expected_context = (
        expected.get(
            "usedQuestionContext"
        )
    )

    actual_context = (
        actual.get(
            "usedQuestionContext"
        )
    )

    route_mismatch = (
        expected_route
        != actual_route
    )

    status_mismatch = (
        expected_status
        != actual_status
    )

    context_mismatch = (
        expected_context is not None
        and expected_context
        != actual_context
    )

    if route_mismatch:
        if category == "history":
            return (
                "history_routing"
            )

        if (
            expected_status
            == NOT_VERIFIABLE
            or category == "scope"
            or (
                expected_route
                == "relationship"
                and actual_route
                == "who"
            )
        ):
            return (
                "scope_or_domain_overreach"
            )

        if expected_context is True:
            return (
                "contextual_reference_resolution"
            )

        return (
            "semantic_routing"
        )

    if context_mismatch:
        if not status_mismatch:
            return (
                "context_usage_mismatch"
            )

        return (
            "contextual_reference_resolution"
        )

    if not status_mismatch:
        return "other"

    if (
        expected_status
        == CONTRADICTED
        and actual_status
        == SUPPORTED
    ):
        if category == "cause":
            return (
                "proposition_entity_mismatch"
            )

        if category == "variants":
            return (
                "state_change_polarity"
            )

        if contains_any(
            text,
            (
                "exclusive",
                "only way",
                "sole way",
                "sole route",
                "only route",
                "solely",
                "exclusively",
            ),
        ):
            return (
                "exclusivity_or_quantifier"
            )

        if contains_any(
            text,
            (
                " not ",
                " no ",
                "never",
                "unable",
                "cannot",
                "can't",
                "doesn't",
                "does not",
                "do not",
                "nothing to do",
                "no longer",
                "removed",
                "left ",
                "unable to",
            ),
        ):
            return (
                "negation_or_polarity"
            )

        return (
            "negation_or_polarity"
        )

    if (
        expected_status
        == NOT_VERIFIABLE
        and actual_status
        == SUPPORTED
    ):
        if category == "treatment":
            return (
                "treatment_overclaim_scope"
            )

        return (
            "scope_or_domain_overreach"
        )

    if (
        expected_status
        == INSUFFICIENT
        and actual_status
        == SUPPORTED
    ):
        return (
            "certainty_overclaim_semantics"
        )

    if (
        expected_status
        == SUPPORTED
        and actual_status
        == INSUFFICIENT
    ):
        return (
            "uncertainty_entailment"
        )

    return "other"


def atomic_failure_detail(
    text: str,
    expected: dict,
    actual: dict | None,
):
    if actual is None:
        return {
            "text": text,
            "expectedRoute": (
                expected.get(
                    "route"
                )
            ),
            "actualRoute": None,
            "expectedStatus": (
                expected.get(
                    "status"
                )
            ),
            "actualStatus": None,
            "expectedQuestionContext": (
                expected.get(
                    "usedQuestionContext"
                )
            ),
            "actualQuestionContext": None,
        }

    return {
        "text": text,
        "expectedRoute": (
            expected.get(
                "route"
            )
        ),
        "actualRoute": (
            actual.get(
                "route"
            )
        ),
        "expectedStatus": (
            expected.get(
                "status"
            )
        ),
        "actualStatus": (
            actual.get(
                "status"
            )
        ),
        "expectedQuestionContext": (
            expected.get(
                "usedQuestionContext"
            )
        ),
        "actualQuestionContext": (
            actual.get(
                "usedQuestionContext"
            )
        ),
    }


def analyze_claim_result(
    result: dict,
):
    text = (
        result.get(
            "input",
            {},
        ).get(
            "text",
            "",
        )
    )

    expected = (
        result.get(
            "expected",
            {}
        )
    )

    actual = (
        result.get(
            "actual"
        )
    )

    cause = (
        classify_atomic_failure(
            text=text,
            category=result.get(
                "category",
                "unknown",
            ),
            expected=expected,
            actual=actual,
        )
    )

    return {
        "causes": [
            cause
        ],
        "details": [
            atomic_failure_detail(
                text=text,
                expected=expected,
                actual=actual,
            )
        ],
    }


def analyze_response_result(
    result: dict,
):
    causes = []
    details = []

    checks = (
        result.get(
            "checks",
            {}
        )
    )

    if (
        checks.get(
            "claimCount"
        )
        is False
        or checks.get(
            "claimTexts"
        )
        is False
    ):
        causes.append(
            "claim_extraction"
        )

    claim_checks = (
        result.get(
            "claimChecks",
            []
        )
    )

    for claim_check in claim_checks:
        if claim_check.get(
            "passed"
        ):
            continue

        expected = (
            claim_check.get(
                "expected",
                {}
            )
        )

        actual = (
            claim_check.get(
                "actual"
            )
        )

        text = (
            claim_check.get(
                "text",
                ""
            )
        )

        cause = (
            classify_atomic_failure(
                text=text,
                category=result.get(
                    "category",
                    "unknown",
                ),
                expected=expected,
                actual=actual,
            )
        )

        causes.append(
            cause
        )

        details.append(
            atomic_failure_detail(
                text=text,
                expected=expected,
                actual=actual,
            )
        )

    if (
        not checks.get(
            "summary",
            True,
        )
        and not causes
    ):
        causes.append(
            "response_aggregation"
        )

    if not causes:
        causes.append(
            "other"
        )

    return {
        "causes": list(
            dict.fromkeys(
                causes
            )
        ),
        "details": details,
    }


def cause_rank(
    cause: str,
):
    try:
        return (
            CAUSE_PRIORITY.index(
                cause
            )
        )

    except ValueError:
        return len(
            CAUSE_PRIORITY
        )


def primary_cause(
    causes,
):
    return min(
        causes,
        key=cause_rank,
    )


def analyze_result(
    result: dict,
):
    if result.get(
        "mode"
    ) == "response":
        analysis = (
            analyze_response_result(
                result
            )
        )

    else:
        analysis = (
            analyze_claim_result(
                result
            )
        )

    causes = analysis[
        "causes"
    ]

    return {
        "id": result.get(
            "id"
        ),
        "mode": result.get(
            "mode"
        ),
        "category": result.get(
            "category"
        ),
        "labelBasis": result.get(
            "labelBasis"
        ),
        "primaryCause": (
            primary_cause(
                causes
            )
        ),
        "causes": causes,
        "input": result.get(
            "input"
        ),
        "details": analysis[
            "details"
        ],
    }


def format_expected_actual(
    detail: dict,
):
    expected_route = (
        detail.get(
            "expectedRoute"
        )
    )

    actual_route = (
        detail.get(
            "actualRoute"
        )
    )

    expected_status = (
        detail.get(
            "expectedStatus"
        )
    )

    actual_status = (
        detail.get(
            "actualStatus"
        )
    )

    expected_context = (
        detail.get(
            "expectedQuestionContext"
        )
    )

    actual_context = (
        detail.get(
            "actualQuestionContext"
        )
    )

    parts = []

    if (
        expected_route
        != actual_route
    ):
        parts.append(
            (
                f"route "
                f"{expected_route}"
                f" → "
                f"{actual_route}"
            )
        )

    if (
        expected_status
        != actual_status
    ):
        parts.append(
            (
                f"status "
                f"{expected_status}"
                f" → "
                f"{actual_status}"
            )
        )

    if (
        expected_context
        is not None
        and expected_context
        != actual_context
    ):
        parts.append(
            (
                f"context "
                f"{expected_context}"
                f" → "
                f"{actual_context}"
            )
        )

    if not parts:
        return "case-level mismatch"

    return "; ".join(
        parts
    )


def markdown_escape(
    value,
):
    return (
        str(
            value
        )
        .replace(
            "|",
            "\\|",
        )
        .replace(
            "\n",
            " ",
        )
    )


def case_text(
    failure: dict,
):
    input_data = failure.get(
        "input",
        {}
    )

    if failure.get(
        "mode"
    ) == "response":
        return input_data.get(
            "response",
            "",
        )

    return input_data.get(
        "text",
        "",
    )


def failure_difference(
    failure: dict,
):
    details = failure.get(
        "details",
        []
    )

    if not details:
        return (
            "response-level mismatch"
        )

    values = [
        format_expected_actual(
            detail
        )
        for detail in details
    ]

    return " / ".join(
        values
    )


def build_markdown(
    source: dict,
    failures: list[dict],
    primary_counts: Counter,
    category_counts: Counter,
):
    lines = []

    lines.append(
        "# Blind v3 Error Analysis"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            f"Benchmark: "
            f"`{source.get('benchmark')}`"
        )
    )

    lines.append(
        ""
    )

    case_accuracy = (
        source.get(
            "caseAccuracy",
            {}
        )
    )

    passed = case_accuracy.get(
        "passed"
    )

    total = case_accuracy.get(
        "total"
    )

    accuracy = case_accuracy.get(
        "accuracy"
    )

    if accuracy is not None:
        lines.append(
            (
                f"Untouched first-run case accuracy: "
                f"**{passed}/{total} "
                f"({accuracy:.1%})**"
            )
        )

        lines.append(
            ""
        )

    lines.append(
        (
            "The taxonomy below is a deterministic "
            "post-hoc diagnostic grouping of failed "
            "cases. It is not a new benchmark score "
            "and does not change the frozen first-run "
            "results."
        )
    )

    lines.append(
        ""
    )

    lines.append(
        "## Primary failure causes"
    )

    lines.append(
        ""
    )

    lines.append(
        "| Cause | Failed cases |"
    )

    lines.append(
        "| --- | ---: |"
    )

    for (
        cause,
        count,
    ) in primary_counts.most_common():
        lines.append(
            (
                f"| {markdown_escape(cause)} "
                f"| {count} |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "## Failures by benchmark category"
    )

    lines.append(
        ""
    )

    lines.append(
        "| Category | Failed cases |"
    )

    lines.append(
        "| --- | ---: |"
    )

    for (
        category,
        count,
    ) in category_counts.most_common():
        lines.append(
            (
                f"| {markdown_escape(category)} "
                f"| {count} |"
            )
        )

    lines.append(
        ""
    )

    lines.append(
        "## Failed cases"
    )

    lines.append(
        ""
    )

    lines.append(
        (
            "| ID | Category | Mode | "
            "Primary cause | Difference | Input |"
        )
    )

    lines.append(
        (
            "| --- | --- | --- | --- | --- | --- |"
        )
    )

    for failure in failures:
        lines.append(
            (
                f"| {markdown_escape(failure['id'])} "
                f"| {markdown_escape(failure['category'])} "
                f"| {markdown_escape(failure['mode'])} "
                f"| {markdown_escape(failure['primaryCause'])} "
                f"| {markdown_escape(failure_difference(failure))} "
                f"| {markdown_escape(case_text(failure))} |"
            )
        )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


def main():
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS,
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
    )

    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT,
    )

    args = (
        parser.parse_args()
    )

    source = load_json(
        args.results
    )

    failed_results = [
        result
        for result in source.get(
            "results",
            []
        )
        if not result.get(
            "passed",
            False,
        )
    ]

    failures = [
        analyze_result(
            result
        )
        for result in failed_results
    ]

    primary_counts = Counter(
        failure[
            "primaryCause"
        ]
        for failure in failures
    )

    cause_counts = Counter()

    for failure in failures:
        cause_counts.update(
            failure[
                "causes"
            ]
        )

    category_counts = Counter(
        failure[
            "category"
        ]
        for failure in failures
    )

    output = {
        "benchmark": source.get(
            "benchmark"
        ),
        "sourceResults": str(
            args.results
        ),
        "caseAccuracy": source.get(
            "caseAccuracy"
        ),
        "statusAccuracy": source.get(
            "statusAccuracy"
        ),
        "routeAccuracy": source.get(
            "routeAccuracy"
        ),
        "claimExtraction": source.get(
            "claimExtraction"
        ),
        "responseSummaryStatusAccuracy": (
            source.get(
                "responseSummaryStatusAccuracy"
            )
        ),
        "responseGroundingScoreAccuracy": (
            source.get(
                "responseGroundingScoreAccuracy"
            )
        ),
        "responseCoverageRatioAccuracy": (
            source.get(
                "responseCoverageRatioAccuracy"
            )
        ),
        "confidenceDiagnostics": source.get(
            "confidenceDiagnostics"
        ),
        "failedCaseCount": len(
            failures
        ),
        "primaryCauseCounts": dict(
            primary_counts
        ),
        "allCauseCounts": dict(
            cause_counts
        ),
        "failedCategoryCounts": dict(
            category_counts
        ),
        "failures": failures,
        "methodology": {
            "type": (
                "deterministic_post_hoc_error_taxonomy"
            ),
            "changesFrozenBenchmarkScore": False,
            "usedForBlindScore": False,
        },
    }

    args.json_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with args.json_output.open(
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

    markdown = (
        build_markdown(
            source=source,
            failures=failures,
            primary_counts=primary_counts,
            category_counts=category_counts,
        )
    )

    with args.markdown_output.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            markdown
        )

    print(
        "BLIND V3 ERROR ANALYSIS"
    )

    print(
        f"failed cases: "
        f"{len(failures)}"
    )

    print()

    print(
        "PRIMARY FAILURE CAUSES"
    )

    for (
        cause,
        count,
    ) in primary_counts.most_common():
        print(
            f"{cause}: {count}"
        )

    print()

    print(
        "FAILED CASES BY CATEGORY"
    )

    for (
        category,
        count,
    ) in category_counts.most_common():
        print(
            f"{category}: {count}"
        )

    print()

    print(
        "JSON:"
    )

    print(
        args.json_output
    )

    print()

    print(
        "MARKDOWN:"
    )

    print(
        args.markdown_output
    )


if __name__ == "__main__":
    main()