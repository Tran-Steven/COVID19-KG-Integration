import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CASES = (
    ROOT
    / "evaluation"
    / "interpretation_cases.json"
)

DEFAULT_URL = (
    "http://localhost:8000/nlp/interpret"
)


def load_cases(path: Path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def request_interpretation(
    url: str,
    text: str,
):
    body = json.dumps(
        {
            "text": text
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return json.loads(
            response.read().decode(
                "utf-8"
            )
        )


def get_actual(result: dict):
    interpretation = result[
        "interpretation"
    ]

    relation_intent = interpretation[
        "relationIntent"
    ]

    outcomes = sorted(
        item["outcome"]
        for item in interpretation[
            "outcomes"
        ]
    )

    return {
        "intent": relation_intent[
            "intent"
        ],
        "direction": relation_intent[
            "direction"
        ],
        "outcomes": outcomes,
        "ambiguous": interpretation[
            "ambiguous"
        ],
    }


def compare_case(
    expected: dict,
    actual: dict,
):
    checks = {
        "intent": (
            expected["intent"]
            == actual["intent"]
        ),
        "direction": (
            expected["direction"]
            == actual["direction"]
        ),
        "outcomes": (
            sorted(
                expected["outcomes"]
            )
            == actual["outcomes"]
        ),
        "ambiguous": (
            expected["ambiguous"]
            == actual["ambiguous"]
        ),
    }

    return checks


def print_failure(
    case: dict,
    expected: dict,
    actual: dict,
    checks: dict,
):
    print(
        f"FAIL  {case['id']}"
    )

    print(
        f"      {case['text']}"
    )

    for field, passed in checks.items():
        if passed:
            continue

        print(
            "      "
            f"{field}: "
            f"expected={expected[field]!r} "
            f"actual={actual[field]!r}"
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    args = parser.parse_args()

    cases = load_cases(
        args.cases
    )

    field_totals = {
        "intent": 0,
        "direction": 0,
        "outcomes": 0,
        "ambiguous": 0,
    }

    case_passes = 0
    results = []

    for case in cases:
        try:
            response = (
                request_interpretation(
                    args.url,
                    case["text"],
                )
            )
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
        ) as error:
            print(
                f"ERROR {case['id']}"
            )
            print(
                f"      {error}"
            )
            sys.exit(1)

        expected = case[
            "expected"
        ]

        actual = get_actual(
            response
        )

        checks = compare_case(
            expected,
            actual,
        )

        for field, passed in checks.items():
            if passed:
                field_totals[field] += 1

        passed = all(
            checks.values()
        )

        if passed:
            case_passes += 1

            print(
                f"PASS  {case['id']}"
            )
        else:
            print_failure(
                case,
                expected,
                actual,
                checks,
            )

        results.append(
            {
                "id": case["id"],
                "text": case["text"],
                "expected": expected,
                "actual": actual,
                "checks": checks,
                "passed": passed,
            }
        )

    total = len(cases)

    print()
    print(
        f"Cases: {case_passes}/{total} "
        f"({case_passes / total:.1%})"
    )

    for field, passed in (
        field_totals.items()
    ):
        print(
            f"{field}: "
            f"{passed}/{total} "
            f"({passed / total:.1%})"
        )

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "total": total,
            "passed": case_passes,
            "accuracy": (
                case_passes / total
            ),
            "fieldAccuracy": {
                field: passed / total
                for field, passed
                in field_totals.items()
            },
            "results": results,
        }

        with args.output.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=2,
            )

            file.write("\n")


if __name__ == "__main__":
    main()