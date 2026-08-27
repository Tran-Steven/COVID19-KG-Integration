import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"


CASES = [
    {
        "name": "nonfactual_uncertainty",
        "question": (
            "How does COVID-19 spread?"
        ),
        "response": (
            "I'm not sure. "
            "Thanks for asking. "
            "Would you like anything else?"
        ),
        "claims": [],
        "summary": (
            "NO_FACTUAL_CLAIMS"
        ),
    },
    {
        "name": "unknown_claim_preserved",
        "question": (
            "What causes COVID-19 and "
            "can remdesivir treat it?"
        ),
        "response": (
            "SARS-CoV-2 causes COVID-19. "
            "Remdesivir treats COVID-19. "
            "5G cures COVID-19."
        ),
        "claims": [
            (
                "SARS-CoV-2 causes COVID-19.",
                "who",
                "SUPPORTED",
                False,
            ),
            (
                "Remdesivir treats COVID-19.",
                "relationship",
                "SUPPORTED",
                False,
            ),
            (
                "5G cures COVID-19.",
                "relationship",
                (
                    "NOT_VERIFIABLE_"
                    "WITH_CURRENT_KG"
                ),
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "but_clause_split",
        "question": (
            "How does COVID spread and "
            "can COVID vaccination reduce "
            "hospitalization?"
        ),
        "response": (
            "COVID spreads only via "
            "contaminated surfaces, but "
            "vaccines lower hospitalization risk."
        ),
        "claims": [
            (
                "COVID spreads only via "
                "contaminated surfaces",
                "who",
                "CONTRADICTED",
                False,
            ),
            (
                "vaccines lower "
                "hospitalization risk",
                "who",
                "SUPPORTED",
                True,
            ),
        ],
        "summary": "MIXED",
    },
    {
        "name": "and_clause_split",
        "question": (
            "How does COVID spread and "
            "what do vaccines reduce?"
        ),
        "response": (
            "COVID spreads through the air "
            "and vaccines lower "
            "hospitalization risk."
        ),
        "claims": [
            (
                "COVID spreads through the air",
                "who",
                "SUPPORTED",
                False,
            ),
            (
                "vaccines lower "
                "hospitalization risk",
                "who",
                "SUPPORTED",
                True,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "multi_outcome_not_split",
        "question": (
            "What do COVID vaccines "
            "protect against?"
        ),
        "response": (
            "COVID vaccines reduce severe "
            "disease, hospitalization, and death."
        ),
        "claims": [
            (
                "COVID vaccines reduce severe "
                "disease, hospitalization, and death.",
                "who",
                "SUPPORTED",
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "uncertainty_then_fact",
        "question": (
            "How does COVID-19 spread?"
        ),
        "response": (
            "I don't know. "
            "COVID can spread through the air."
        ),
        "claims": [
            (
                "COVID can spread through the air.",
                "who",
                "SUPPORTED",
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "vaccine_context",
        "question": (
            "How effective are COVID vaccines?"
        ),
        "response": (
            "They guarantee that infection "
            "cannot occur."
        ),
        "claims": [
            (
                "They guarantee that infection "
                "cannot occur.",
                "who",
                "INSUFFICIENT_EVIDENCE",
                True,
            ),
        ],
        "summary": (
            "INSUFFICIENT_EVIDENCE"
        ),
    },
    {
        "name": "semicolon_split",
        "question": (
            "How does COVID spread and "
            "what do vaccines reduce?"
        ),
        "response": (
            "COVID can spread through the air; "
            "COVID vaccines reduce hospitalization."
        ),
        "claims": [
            (
                "COVID can spread through the air",
                "who",
                "SUPPORTED",
                False,
            ),
            (
                "COVID vaccines reduce hospitalization",
                "who",
                "SUPPORTED",
                False,
            ),
        ],
        "summary": "SUPPORTED",
    },
]


def verify(
    question: str,
    response: str,
):
    request = Request(
        (
            f"{BASE_URL}"
            "/kg/verify-response"
        ),
        data=json.dumps(
            {
                "question": question,
                "response": response,
            }
        ).encode(),
        headers={
            "Content-Type": (
                "application/json"
            ),
        },
        method="POST",
    )

    with urlopen(
        request,
        timeout=30,
    ) as result:
        return json.load(
            result
        )


def check_case(
    case: dict,
):
    data = verify(
        case[
            "question"
        ],
        case[
            "response"
        ],
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

            retrieval = actual[
                "retrieval"
            ]

            verification = retrieval[
                "verification"
            ]

            if (
                actual[
                    "text"
                ]
                != expected_text
                or retrieval[
                    "verificationType"
                ]
                != expected_route
                or verification[
                    "status"
                ]
                != expected_status
                or actual[
                    "usedQuestionContext"
                ]
                != expected_context
            ):
                claims_ok = False

    summary_status = data[
        "summary"
    ][
        "status"
    ]

    summary_ok = (
        summary_status
        == case[
            "summary"
        ]
    )

    passed = (
        claims_ok
        and summary_ok
    )

    print(
        "PASS" if passed else "FAIL",
        case[
            "name"
        ],
    )

    if not passed:
        print(
            "  claimCount:",
            len(actual_claims),
            "expected:",
            len(expected_claims),
        )

        for claim in actual_claims:
            retrieval = claim[
                "retrieval"
            ]

            print(
                "  claim:",
                claim[
                    "text"
                ],
            )

            print(
                "    route:",
                retrieval[
                    "verificationType"
                ],
            )

            print(
                "    status:",
                retrieval[
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
            summary_status,
            "expected:",
            case[
                "summary"
            ],
        )

    return passed


def main():
    passed = 0

    try:
        for case in CASES:
            if check_case(
                case
            ):
                passed += 1

    except URLError as error:
        print(
            f"ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    print()
    print(
        "RESPONSE ROBUSTNESS"
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