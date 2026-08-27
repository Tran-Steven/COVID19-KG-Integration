import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES = [
    {
        "name": "multi_clause",
        "question": (
            "How does COVID spread and do "
            "COVID vaccines reduce severe disease?"
        ),
        "response": (
            "COVID spreads through the air, "
            "and vaccines reduce severe disease."
        ),
        "claims": [
            (
                "COVID spreads through the air",
                "who",
                "SUPPORTED",
                False,
            ),
            (
                "vaccines reduce severe disease",
                "who",
                "SUPPORTED",
                True,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "transmission_context",
        "question": (
            "How does COVID-19 spread?"
        ),
        "response": (
            "It can spread through the air."
        ),
        "claims": [
            (
                "It can spread through the air.",
                "who",
                "SUPPORTED",
                True,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "vaccine_context",
        "question": (
            "Do COVID vaccines help prevent "
            "hospitalization?"
        ),
        "response": (
            "They reduce the risk of hospitalization."
        ),
        "claims": [
            (
                "They reduce the risk of hospitalization.",
                "who",
                "SUPPORTED",
                True,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "origin_uncertainty",
        "question": (
            "What does WHO say about the "
            "origin of COVID-19?"
        ),
        "response": (
            "A laboratory-related event cannot "
            "currently be ruled out or proven. "
            "The overall origin remains inconclusive."
        ),
        "claims": [
            (
                "A laboratory-related event cannot "
                "currently be ruled out or proven.",
                "who",
                "SUPPORTED",
                False,
            ),
            (
                "The overall origin remains inconclusive.",
                "who",
                "SUPPORTED",
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "origin_overclaim",
        "question": (
            "What do we know about the "
            "origin of COVID-19?"
        ),
        "response": (
            "Natural spillover is the best-supported "
            "hypothesis. "
            "The origin has been conclusively proven."
        ),
        "claims": [
            (
                "Natural spillover is the "
                "best-supported hypothesis.",
                "who",
                "SUPPORTED",
                True,
            ),
            (
                "The origin has been conclusively proven.",
                "who",
                "CONTRADICTED",
                True,
            ),
        ],
        "summary": "MIXED",
    },
    {
        "name": "vaccine_absolute_context",
        "question": (
            "How effective are COVID vaccines?"
        ),
        "response": (
            "COVID vaccines reduce severe disease. "
            "They completely prevent infection."
        ),
        "claims": [
            (
                "COVID vaccines reduce severe disease.",
                "who",
                "SUPPORTED",
                False,
            ),
            (
                "They completely prevent infection.",
                "who",
                "INSUFFICIENT_EVIDENCE",
                True,
            ),
        ],
        "summary": "MIXED",
    },
    {
        "name": "multi_outcome_not_split",
        "question": (
            "What do COVID vaccines protect against?"
        ),
        "response": (
            "COVID vaccines reduce severe disease, "
            "hospitalization, and death."
        ),
        "claims": [
            (
                "COVID vaccines reduce severe disease, "
                "hospitalization, and death.",
                "who",
                "SUPPORTED",
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "history_direct",
        "question": (
            "When did COVID-19 become a pandemic?"
        ),
        "response": (
            "WHO characterized COVID-19 as a pandemic "
            "on March 11, 2020."
        ),
        "claims": [
            (
                "WHO characterized COVID-19 as a pandemic "
                "on March 11, 2020.",
                "history",
                "SUPPORTED",
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "no_factual_claims",
        "question": (
            "What causes COVID-19?"
        ),
        "response": (
            "Maybe. I hope that helps. "
            "What else would you like to know?"
        ),
        "claims": [],
        "summary": "NO_FACTUAL_CLAIMS",
    },
]


def verify_response(
    question: str,
    response_text: str,
):
    request = Request(
        f"{BASE_URL}/kg/verify-response",
        data=json.dumps(
            {
                "question": question,
                "response": response_text,
            }
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


def main():
    passed = 0

    try:
        for case in CASES:
            data = verify_response(
                case["question"],
                case["response"],
            )

            actual_claims = data[
                "claims"
            ]

            expected_claims = case[
                "claims"
            ]

            claim_count_ok = (
                len(actual_claims)
                == len(expected_claims)
            )

            claims_ok = (
                claim_count_ok
            )

            if claim_count_ok:
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
                        actual["text"]
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
                claim_count_ok
                and claims_ok
                and summary_ok
            )

            if ok:
                passed += 1

            print(
                "PASS" if ok else "FAIL",
                case["name"],
            )

            if not ok:
                print(
                    "  claimCount:",
                    len(actual_claims),
                    "expected:",
                    len(expected_claims),
                )

                for index, actual in enumerate(
                    actual_claims
                ):
                    print(
                        "  claim",
                        index + 1,
                        repr(
                            actual[
                                "text"
                            ]
                        ),
                    )
                    print(
                        "    route:",
                        actual[
                            "retrieval"
                        ][
                            "verificationType"
                        ],
                    )
                    print(
                        "    status:",
                        actual[
                            "retrieval"
                        ][
                            "verification"
                        ][
                            "status"
                        ],
                    )
                    print(
                        "    context:",
                        actual[
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

    except URLError as error:
        print(
            f"ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    print()
    print(
        "RESPONSE VERIFICATION"
    )
    print(
        f"cases: {passed}/{len(CASES)} "
        f"({passed / len(CASES):.1%})"
    )

    return (
        0
        if passed == len(CASES)
        else 1
    )


if __name__ == "__main__":
    sys.exit(
        main()
    )