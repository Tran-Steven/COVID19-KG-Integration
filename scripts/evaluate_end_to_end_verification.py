import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CASES = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_cases.json"
)

DEFAULT_OUTPUT = (
    ROOT
    / "evaluation"
    / "end_to_end_verification_results.json"
)

DEFAULT_BASE_URL = (
    "http://localhost:8000"
)


def load_benchmark(
    path: Path,
):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def request_json(
    base_url: str,
    endpoint: str,
    payload: dict,
):
    body = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        (
            base_url.rstrip("/")
            + endpoint
        ),
        data=body,
        headers={
            "Content-Type": (
                "application/json"
            )
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:
        return json.loads(
            response.read().decode(
                "utf-8"
            )
        )


def normalize_text(
    text: str,
):
    return " ".join(
        text.lower()
        .split()
    )


def ratio(
    numerator: int,
    denominator: int,
):
    if denominator == 0:
        return None

    return (
        numerator
        / denominator
    )


def close_enough(
    expected,
    actual,
):
    if (
        expected is None
        or actual is None
    ):
        return (
            expected is None
            and actual is None
        )

    return (
        abs(
            float(expected)
            - float(actual)
        )
        <= 0.001
    )


def new_metrics():
    return {
        "cases": {
            "passed": 0,
            "total": 0,
        },
        "status": {
            "passed": 0,
            "total": 0,
        },
        "route": {
            "passed": 0,
            "total": 0,
        },
        "responseSummaryStatus": {
            "passed": 0,
            "total": 0,
        },
        "responseGroundingScore": {
            "passed": 0,
            "total": 0,
        },
        "responseCoverageRatio": {
            "passed": 0,
            "total": 0,
        },
        "questionContext": {
            "passed": 0,
            "total": 0,
        },
        "claimExtraction": {
            "matched": 0,
            "expected": 0,
            "actual": 0,
        },
        "confidenceRecords": [],
    }


def increment_metric(
    metric: dict,
    passed: bool,
):
    metric[
        "total"
    ] += 1

    if passed:
        metric[
            "passed"
        ] += 1


def record_confidence(
    metrics: dict,
    confidence: dict | None,
    status_correct: bool,
):
    if not confidence:
        return

    score = confidence.get(
        "score"
    )

    level = confidence.get(
        "level"
    )

    if score is None:
        return

    metrics[
        "confidenceRecords"
    ].append(
        {
            "score": float(
                score
            ),
            "level": level,
            "statusCorrect": (
                status_correct
            ),
        }
    )


def evaluate_claim_case(
    case: dict,
    base_url: str,
    metrics: dict,
):
    response = request_json(
        base_url,
        "/kg/retrieve",
        {
            "text": case[
                "input"
            ][
                "text"
            ]
        },
    )

    expected = case[
        "expected"
    ]

    verification = response[
        "verification"
    ]

    actual = {
        "route": response[
            "verificationType"
        ],
        "status": verification[
            "status"
        ],
        "confidence": verification.get(
            "confidence"
        ),
    }

    checks = {
        "route": (
            expected[
                "route"
            ]
            == actual[
                "route"
            ]
        ),
        "status": (
            expected[
                "status"
            ]
            == actual[
                "status"
            ]
        ),
    }

    increment_metric(
        metrics[
            "route"
        ],
        checks[
            "route"
        ],
    )

    increment_metric(
        metrics[
            "status"
        ],
        checks[
            "status"
        ],
    )

    record_confidence(
        metrics,
        actual[
            "confidence"
        ],
        checks[
            "status"
        ],
    )

    return {
        "actual": actual,
        "checks": checks,
        "passed": all(
            checks.values()
        ),
    }


def extraction_counts(
    expected_claims: list[dict],
    actual_claims: list[dict],
):
    expected_counter = Counter(
        normalize_text(
            claim[
                "text"
            ]
        )
        for claim
        in expected_claims
    )

    actual_counter = Counter(
        normalize_text(
            claim[
                "text"
            ]
        )
        for claim
        in actual_claims
    )

    matched = sum(
        (
            expected_counter
            & actual_counter
        ).values()
    )

    return {
        "matched": matched,
        "expected": sum(
            expected_counter.values()
        ),
        "actual": sum(
            actual_counter.values()
        ),
    }


def build_actual_claim_map(
    claims: list[dict],
):
    return {
        normalize_text(
            claim[
                "text"
            ]
        ): claim
        for claim
        in claims
    }


def compare_summary(
    expected: dict,
    actual: dict,
):
    checks = {}

    exact_fields = (
        "status",
        "supportedCount",
        "contradictedCount",
        "insufficientEvidenceCount",
        "notVerifiableCount",
        "verifiableClaimCount",
        "needsAttentionCount",
    )

    float_fields = (
        "supportedRatio",
        "coverageRatio",
        "groundingScore",
    )

    for field in exact_fields:
        checks[
            field
        ] = (
            expected[
                field
            ]
            == actual[
                field
            ]
        )

    for field in float_fields:
        checks[
            field
        ] = close_enough(
            expected[
                field
            ],
            actual[
                field
            ],
        )

    return checks


def evaluate_response_case(
    case: dict,
    base_url: str,
    metrics: dict,
):
    response = request_json(
        base_url,
        "/kg/verify-response",
        {
            "question": case[
                "input"
            ][
                "question"
            ],
            "response": case[
                "input"
            ][
                "response"
            ],
        },
    )

    expected = case[
        "expected"
    ]

    expected_claims = expected[
        "claims"
    ]

    actual_claims = response[
        "claims"
    ]

    counts = extraction_counts(
        expected_claims,
        actual_claims,
    )

    metrics[
        "claimExtraction"
    ][
        "matched"
    ] += counts[
        "matched"
    ]

    metrics[
        "claimExtraction"
    ][
        "expected"
    ] += counts[
        "expected"
    ]

    metrics[
        "claimExtraction"
    ][
        "actual"
    ] += counts[
        "actual"
    ]

    expected_texts = [
        normalize_text(
            claim[
                "text"
            ]
        )
        for claim
        in expected_claims
    ]

    actual_texts = [
        normalize_text(
            claim[
                "text"
            ]
        )
        for claim
        in actual_claims
    ]

    claim_map = (
        build_actual_claim_map(
            actual_claims
        )
    )

    claim_checks = []

    for expected_claim in expected_claims:
        key = normalize_text(
            expected_claim[
                "text"
            ]
        )

        actual_claim = (
            claim_map.get(
                key
            )
        )

        if actual_claim is None:
            status_passed = False
            route_passed = False
            context_passed = False

            actual_claim_result = None

        else:
            retrieval = actual_claim[
                "retrieval"
            ]

            verification = retrieval[
                "verification"
            ]

            status_passed = (
                expected_claim[
                    "status"
                ]
                == verification[
                    "status"
                ]
            )

            route_passed = (
                expected_claim[
                    "route"
                ]
                == retrieval[
                    "verificationType"
                ]
            )

            context_passed = (
                expected_claim[
                    "usedQuestionContext"
                ]
                == actual_claim[
                    "usedQuestionContext"
                ]
            )

            actual_claim_result = {
                "route": retrieval[
                    "verificationType"
                ],
                "status": verification[
                    "status"
                ],
                "usedQuestionContext": (
                    actual_claim[
                        "usedQuestionContext"
                    ]
                ),
                "confidence": (
                    verification.get(
                        "confidence"
                    )
                ),
            }

            record_confidence(
                metrics,
                verification.get(
                    "confidence"
                ),
                status_passed,
            )

        increment_metric(
            metrics[
                "status"
            ],
            status_passed,
        )

        increment_metric(
            metrics[
                "route"
            ],
            route_passed,
        )

        increment_metric(
            metrics[
                "questionContext"
            ],
            context_passed,
        )

        claim_checks.append(
            {
                "text": expected_claim[
                    "text"
                ],
                "expected": (
                    expected_claim
                ),
                "actual": (
                    actual_claim_result
                ),
                "checks": {
                    "status": (
                        status_passed
                    ),
                    "route": (
                        route_passed
                    ),
                    "usedQuestionContext": (
                        context_passed
                    ),
                },
                "passed": (
                    status_passed
                    and route_passed
                    and context_passed
                ),
            }
        )

    summary_checks = compare_summary(
        expected[
            "summary"
        ],
        response[
            "summary"
        ],
    )

    increment_metric(
        metrics[
            "responseSummaryStatus"
        ],
        summary_checks[
            "status"
        ],
    )

    increment_metric(
        metrics[
            "responseGroundingScore"
        ],
        summary_checks[
            "groundingScore"
        ],
    )

    increment_metric(
        metrics[
            "responseCoverageRatio"
        ],
        summary_checks[
            "coverageRatio"
        ],
    )

    checks = {
        "claimCount": (
            len(
                expected_claims
            )
            == response[
                "claimCount"
            ]
        ),
        "claimTexts": (
            expected_texts
            == actual_texts
        ),
        "claimVerification": all(
            item[
                "passed"
            ]
            for item
            in claim_checks
        ),
        "summary": all(
            summary_checks.values()
        ),
    }

    return {
        "actual": {
            "claimCount": response[
                "claimCount"
            ],
            "claimTexts": [
                claim[
                    "text"
                ]
                for claim
                in actual_claims
            ],
            "summary": response[
                "summary"
            ],
        },
        "claimChecks": (
            claim_checks
        ),
        "summaryChecks": (
            summary_checks
        ),
        "checks": checks,
        "passed": all(
            checks.values()
        ),
    }


def confidence_diagnostics(
    records: list[dict],
):
    levels = {
        "low": [],
        "medium": [],
        "high": [],
    }

    correct_scores = []
    incorrect_scores = []

    for record in records:
        level = record.get(
            "level"
        )

        if level not in levels:
            levels[
                level
            ] = []

        levels[
            level
        ].append(
            record
        )

        if record[
            "statusCorrect"
        ]:
            correct_scores.append(
                record[
                    "score"
                ]
            )
        else:
            incorrect_scores.append(
                record[
                    "score"
                ]
            )

    by_level = {}

    for level, values in (
        levels.items()
    ):
        if not values:
            by_level[
                level
            ] = {
                "count": 0,
                "correct": 0,
                "accuracy": None,
                "meanScore": None,
            }

            continue

        correct = sum(
            1
            for value
            in values
            if value[
                "statusCorrect"
            ]
        )

        by_level[
            level
        ] = {
            "count": len(
                values
            ),
            "correct": correct,
            "accuracy": (
                correct
                / len(
                    values
                )
            ),
            "meanScore": (
                sum(
                    value[
                        "score"
                    ]
                    for value
                    in values
                )
                / len(
                    values
                )
            ),
        }

    return {
        "target": (
            "verification_status_correctness"
        ),
        "calibrated": False,
        "meanConfidenceWhenCorrect": (
            (
                sum(
                    correct_scores
                )
                / len(
                    correct_scores
                )
            )
            if correct_scores
            else None
        ),
        "meanConfidenceWhenIncorrect": (
            (
                sum(
                    incorrect_scores
                )
                / len(
                    incorrect_scores
                )
            )
            if incorrect_scores
            else None
        ),
        "byLevel": by_level,
    }


def metric_report(
    metric: dict,
):
    return {
        "passed": metric[
            "passed"
        ],
        "total": metric[
            "total"
        ],
        "accuracy": ratio(
            metric[
                "passed"
            ],
            metric[
                "total"
            ],
        ),
    }


def extraction_report(
    extraction: dict,
):
    precision = ratio(
        extraction[
            "matched"
        ],
        extraction[
            "actual"
        ],
    )

    recall = ratio(
        extraction[
            "matched"
        ],
        extraction[
            "expected"
        ],
    )

    if (
        precision is None
        or recall is None
        or (
            precision
            + recall
        )
        == 0
    ):
        f1 = None

    else:
        f1 = (
            2
            * precision
            * recall
            / (
                precision
                + recall
            )
        )

    return {
        "matched": extraction[
            "matched"
        ],
        "expected": extraction[
            "expected"
        ],
        "actual": extraction[
            "actual"
        ],
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def print_case_failure(
    case: dict,
    result: dict,
):
    print(
        f"FAIL  {case['id']}"
    )

    if case[
        "mode"
    ] == "claim":
        print(
            "      "
            f"{case['input']['text']}"
        )

        for field, passed in (
            result[
                "checks"
            ].items()
        ):
            if passed:
                continue

            print(
                "      "
                f"{field}: "
                f"expected="
                f"{case['expected'][field]!r} "
                f"actual="
                f"{result['actual'][field]!r}"
            )

        return

    for field, passed in (
        result[
            "checks"
        ].items()
    ):
        if not passed:
            print(
                "      "
                f"{field}=FAIL"
            )

    for claim in result[
        "claimChecks"
    ]:
        if claim[
            "passed"
        ]:
            continue

        print(
            "      claim: "
            f"{claim['text']}"
        )

        for field, passed in (
            claim[
                "checks"
            ].items()
        ):
            if passed:
                continue

            expected_value = (
                claim[
                    "expected"
                ].get(
                    field
                )
            )

            actual_value = (
                None
                if claim[
                    "actual"
                ] is None
                else claim[
                    "actual"
                ].get(
                    field
                )
            )

            print(
                "        "
                f"{field}: "
                f"expected="
                f"{expected_value!r} "
                f"actual="
                f"{actual_value!r}"
            )

    for field, passed in (
        result[
            "summaryChecks"
        ].items()
    ):
        if passed:
            continue

        print(
            "      summary."
            f"{field}: "
            f"expected="
            f"{case['expected']['summary'][field]!r} "
            f"actual="
            f"{result['actual']['summary'][field]!r}"
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--fail-on-error",
        action="store_true",
    )

    args = parser.parse_args()

    benchmark = load_benchmark(
        args.cases
    )

    cases = benchmark[
        "cases"
    ]

    metrics = new_metrics()

    results = []

    category_totals = {}

    for case in cases:
        metrics[
            "cases"
        ][
            "total"
        ] += 1

        category = case[
            "category"
        ]

        if category not in (
            category_totals
        ):
            category_totals[
                category
            ] = {
                "passed": 0,
                "total": 0,
            }

        category_totals[
            category
        ][
            "total"
        ] += 1

        try:
            if (
                case[
                    "mode"
                ]
                == "claim"
            ):
                evaluation = (
                    evaluate_claim_case(
                        case,
                        args.base_url,
                        metrics,
                    )
                )

            elif (
                case[
                    "mode"
                ]
                == "response"
            ):
                evaluation = (
                    evaluate_response_case(
                        case,
                        args.base_url,
                        metrics,
                    )
                )

            else:
                raise ValueError(
                    "Unsupported case mode: "
                    f"{case['mode']}"
                )

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            KeyError,
            ValueError,
        ) as error:
            print(
                f"ERROR {case['id']}"
            )

            print(
                f"      {error}"
            )

            sys.exit(
                1
            )

        if evaluation[
            "passed"
        ]:
            metrics[
                "cases"
            ][
                "passed"
            ] += 1

            category_totals[
                category
            ][
                "passed"
            ] += 1

            print(
                f"PASS  {case['id']}"
            )

        else:
            print_case_failure(
                case,
                evaluation,
            )

        results.append(
            {
                "id": case[
                    "id"
                ],
                "mode": case[
                    "mode"
                ],
                "category": (
                    category
                ),
                "labelBasis": case[
                    "labelBasis"
                ],
                "input": case[
                    "input"
                ],
                "expected": case[
                    "expected"
                ],
                **evaluation,
            }
        )

    category_report = {
        category: {
            "passed": values[
                "passed"
            ],
            "total": values[
                "total"
            ],
            "accuracy": ratio(
                values[
                    "passed"
                ],
                values[
                    "total"
                ],
            ),
        }
        for category, values
        in sorted(
            category_totals.items()
        )
    }

    report = {
        "benchmark": benchmark[
            "benchmark"
        ],
        "frozen": benchmark[
            "frozen"
        ],
        "caseAccuracy": (
            metric_report(
                metrics[
                    "cases"
                ]
            )
        ),
        "statusAccuracy": (
            metric_report(
                metrics[
                    "status"
                ]
            )
        ),
        "routeAccuracy": (
            metric_report(
                metrics[
                    "route"
                ]
            )
        ),
        "claimExtraction": (
            extraction_report(
                metrics[
                    "claimExtraction"
                ]
            )
        ),
        "questionContextAccuracy": (
            metric_report(
                metrics[
                    "questionContext"
                ]
            )
        ),
        "responseSummaryStatusAccuracy": (
            metric_report(
                metrics[
                    "responseSummaryStatus"
                ]
            )
        ),
        "responseGroundingScoreAccuracy": (
            metric_report(
                metrics[
                    "responseGroundingScore"
                ]
            )
        ),
        "responseCoverageRatioAccuracy": (
            metric_report(
                metrics[
                    "responseCoverageRatio"
                ]
            )
        ),
        "confidenceDiagnostics": (
            confidence_diagnostics(
                metrics[
                    "confidenceRecords"
                ]
            )
        ),
        "categoryAccuracy": (
            category_report
        ),
        "results": results,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with args.output.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
        )

        file.write(
            "\n"
        )

    total = metrics[
        "cases"
    ][
        "total"
    ]

    passed = metrics[
        "cases"
    ][
        "passed"
    ]

    extraction = report[
        "claimExtraction"
    ]

    print()
    print(
        "END-TO-END VERIFICATION"
    )

    print(
        f"cases: "
        f"{passed}/{total} "
        f"({passed / total:.1%})"
    )

    print(
        "status accuracy: "
        f"{report['statusAccuracy']['accuracy']:.1%}"
    )

    print(
        "route accuracy: "
        f"{report['routeAccuracy']['accuracy']:.1%}"
    )

    if (
        extraction[
            "precision"
        ] is not None
    ):
        print(
            "claim extraction precision: "
            f"{extraction['precision']:.1%}"
        )

    if (
        extraction[
            "recall"
        ] is not None
    ):
        print(
            "claim extraction recall: "
            f"{extraction['recall']:.1%}"
        )

    if (
        extraction[
            "f1"
        ] is not None
    ):
        print(
            "claim extraction F1: "
            f"{extraction['f1']:.1%}"
        )

    print(
        "response summary status: "
        f"{report['responseSummaryStatusAccuracy']['accuracy']:.1%}"
    )

    print(
        "response grounding score: "
        f"{report['responseGroundingScoreAccuracy']['accuracy']:.1%}"
    )

    print(
        "response coverage ratio: "
        f"{report['responseCoverageRatioAccuracy']['accuracy']:.1%}"
    )

    print()
    print(
        "CATEGORY ACCURACY"
    )

    for category, values in (
        category_report.items()
    ):
        print(
            f"{category}: "
            f"{values['passed']}/"
            f"{values['total']} "
            f"({values['accuracy']:.1%})"
        )

    print()
    print(
        "CONFIDENCE DIAGNOSTICS"
    )

    confidence = report[
        "confidenceDiagnostics"
    ]

    print(
        "mean confidence when "
        "status correct:",
        confidence[
            "meanConfidenceWhenCorrect"
        ],
    )

    print(
        "mean confidence when "
        "status incorrect:",
        confidence[
            "meanConfidenceWhenIncorrect"
        ],
    )

    print()
    print(
        "Results written to:"
    )

    print(
        args.output
    )

    if (
        args.fail_on_error
        and passed != total
    ):
        sys.exit(
            1
        )


if __name__ == "__main__":
    main()