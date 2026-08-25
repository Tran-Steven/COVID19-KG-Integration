import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CLAIM_CASES = [
    (
        "Zoonotic spillover has been established beyond doubt as the origin of SARS-CoV-2.",
        "who",
        "INSUFFICIENT_EVIDENCE",
    ),
    (
        "A laboratory-associated event cannot be confirmed or excluded as an origin of SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "A laboratory origin for SARS-CoV-2 has been completely ruled out.",
        "who",
        "CONTRADICTED",
    ),
    (
        "Deliberate laboratory manipulation is more likely than natural spillover for SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "Scientific evidence does not support deliberate laboratory manipulation over natural processes for SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "Strong evidence now favors a cold-chain origin for SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "There is no additional evidence supporting a cold-chain origin of SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "The origin of SARS-CoV-2 remains unresolved.",
        "who",
        "SUPPORTED",
    ),
    (
        "The origin of SARS-CoV-2 is still undetermined.",
        "who",
        "SUPPORTED",
    ),
    (
        "Scientists have definitively established the exact origin of SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "Natural spillover remains the best-supported origin hypothesis for SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "What is the origin of SARS-CoV-2?",
        "who",
        "INSUFFICIENT_EVIDENCE",
    ),
]

RESPONSE_CASES = [
    {
        "name": "contextual_origin_uncertainty",
        "question": (
            "What does current evidence say about "
            "the origin of SARS-CoV-2?"
        ),
        "response": (
            "A laboratory-associated event cannot "
            "currently be confirmed or excluded. "
            "The overall origin remains unresolved."
        ),
        "claims": [
            (
                "A laboratory-associated event cannot "
                "currently be confirmed or excluded.",
                "who",
                "SUPPORTED",
                True,
            ),
            (
                "The overall origin remains unresolved.",
                "who",
                "SUPPORTED",
                True,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "contextual_origin_certainty",
        "question": (
            "What is known about the origin "
            "of COVID-19?"
        ),
        "response": (
            "The exact origin is definitely known."
        ),
        "claims": [
            (
                "The exact origin is definitely known.",
                "who",
                "CONTRADICTED",
                True,
            ),
        ],
        "summary": "CONTRADICTED",
    },
]


def post(
    endpoint: str,
    payload: dict,
):
    request = Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(
            payload
        ).encode(),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(
        request,
        timeout=30,
    ) as response:
        return json.load(
            response
        )


def check_claim_cases():
    passed = 0

    for (
        text,
        expected_route,
        expected_status,
    ) in CLAIM_CASES:
        data = post(
            "/kg/retrieve",
            {
                "text": text,
            },
        )

        route = data[
            "verificationType"
        ]

        status = data[
            "verification"
        ][
            "status"
        ]

        ok = (
            route == expected_route
            and status == expected_status
        )

        if ok:
            passed += 1

        print(
            "PASS" if ok else "FAIL",
            text,
        )

        print(
            "  route:",
            route,
            "expected:",
            expected_route,
        )

        print(
            "  status:",
            status,
            "expected:",
            expected_status,
        )

    return passed


def check_response_cases():
    passed = 0

    for case in RESPONSE_CASES:
        data = post(
            "/kg/verify-response",
            {
                "question": case[
                    "question"
                ],
                "response": case[
                    "response"
                ],
            },
        )

        actual_claims = data[
            "claims"
        ]

        expected_claims = case[
            "claims"
        ]

        claims_ok = (
            len(actual_claims)
            == len(expected_claims)
        )

        if claims_ok:
            for (
                actual,
                expected,
            ) in zip(
                actual_claims,
                expected_claims,
            ):
                (
                    expected_text,
                    expected_route,
                    expected_status,
                    expected_context,
                ) = expected

                if (
                    actual[
                        "text"
                    ]
                    != expected_text
                    or actual[
                        "retrieval"
                    ][
                        "verificationType"
                    ]
                    != expected_route
                    or actual[
                        "retrieval"
                    ][
                        "verification"
                    ][
                        "status"
                    ]
                    != expected_status
                    or actual[
                        "usedQuestionContext"
                    ]
                    != expected_context
                ):
                    claims_ok = False

        summary_ok = (
            data[
                "summary"
            ][
                "status"
            ]
            == case[
                "summary"
            ]
        )

        ok = (
            claims_ok
            and summary_ok
        )

        if ok:
            passed += 1

        print(
            "PASS" if ok else "FAIL",
            case["name"],
        )

        if not ok:
            for claim in actual_claims:
                print(
                    "  claim:",
                    claim[
                        "text"
                    ],
                )
                print(
                    "    route:",
                    claim[
                        "retrieval"
                    ][
                        "verificationType"
                    ],
                )
                print(
                    "    status:",
                    claim[
                        "retrieval"
                    ][
                        "verification"
                    ][
                        "status"
                    ],
                )
                print(
                    "    context:",
                    claim[
                        "usedQuestionContext"
                    ],
                )

            print(
                "  summary:",
                data[
                    "summary"
                ][
                    "status"
                ],
                "expected:",
                case[
                    "summary"
                ],
            )

    return passed


def main():
    try:
        claim_passed = (
            check_claim_cases()
        )

        response_passed = (
            check_response_cases()
        )

    except URLError as error:
        print(
            f"ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    passed = (
        claim_passed
        + response_passed
    )

    total = (
        len(CLAIM_CASES)
        + len(RESPONSE_CASES)
    )

    print()
    print(
        "ORIGIN SEMANTICS"
    )
    print(
        f"cases: {passed}/{total} "
        f"({passed / total:.1%})"
    )

    return (
        0
        if passed == total
        else 1
    )


if __name__ == "__main__":
    sys.exit(
        main()
    )