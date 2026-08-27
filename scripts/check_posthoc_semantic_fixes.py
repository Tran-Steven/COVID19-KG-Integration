import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES = [
    {
        "name": "discourse_not_claim",
        "question": (
            "Does remdesivir treat COVID-19?"
        ),
        "response": (
            "That statement is correct. "
            "Remdesivir treats COVID-19."
        ),
        "statuses": [
            "SUPPORTED",
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "alternative_cause_negative",
        "question": (
            "Does influenza cause COVID-19?"
        ),
        "response": (
            "Influenza viruses do not cause "
            "COVID-19. SARS-CoV-2 causes COVID-19."
        ),
        "statuses": [
            "SUPPORTED",
            "SUPPORTED",
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "alternative_cause_positive",
        "question": (
            "What causes COVID-19?"
        ),
        "response": (
            "Influenza viruses cause COVID-19."
        ),
        "statuses": [
            "CONTRADICTED",
        ],
        "summary": "CONTRADICTED",
    },
    {
        "name": "cause_incapable",
        "question": (
            "Does SARS-CoV-2 cause COVID-19?"
        ),
        "response": (
            "SARS-CoV-2 is incapable of "
            "producing COVID-19."
        ),
        "statuses": [
            "CONTRADICTED",
        ],
        "summary": "CONTRADICTED",
    },
    {
        "name": "origin_not_ruled_out",
        "question": (
            "What is known about COVID-19 origin?"
        ),
        "response": (
            "A laboratory-associated origin has "
            "not been completely ruled out."
        ),
        "statuses": [
            "SUPPORTED",
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "origin_unresolved",
        "question": (
            "Is the origin of SARS-CoV-2 settled?"
        ),
        "response": (
            "The exact origin of SARS-CoV-2 has "
            "not been definitively resolved."
        ),
        "statuses": [
            "SUPPORTED",
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "variant_no_additional_risk",
        "question": (
            "What is WHO's assessment of XFG?"
        ),
        "response": (
            "WHO says XFG does not appear to pose "
            "additional public-health risk compared "
            "with other circulating variants."
        ),
        "statuses": [
            "INSUFFICIENT_EVIDENCE",
        ],
        "summary": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "vaccine_not_absolute",
        "question": (
            "How protective are COVID vaccines?"
        ),
        "response": (
            "COVID vaccine protection is not absolute."
        ),
        "statuses": [
            "INSUFFICIENT_EVIDENCE",
        ],
        "summary": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "historical_risk_not_current",
        "question": (
            "How has WHO's risk assessment changed?"
        ),
        "response": (
            "WHO rated the global COVID-19 risk "
            "high in 2024."
        ),
        "statuses": [
            "INSUFFICIENT_EVIDENCE",
        ],
        "summary": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "non_covid_vaccine_entity",
        "question": (
            "Does an MMR vaccine protect against "
            "severe COVID-19?"
        ),
        "response": (
            "An MMR vaccine is not an established "
            "COVID-19 vaccine for preventing severe "
            "COVID-19."
        ),
        "statuses": [
            "INSUFFICIENT_EVIDENCE",
        ],
        "summary": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "list_scope",
        "question": (
            "What do COVID vaccines do and not do?"
        ),
        "response": (
            "COVID vaccines do:\n"
            "Reduce the risk of severe disease.\n"
            "Reduce hospitalization and death.\n"
            "COVID vaccines do not:\n"
            "Guarantee prevention of infection.\n"
            "Completely stop transmission."
        ),
        "claim_contains": [
            (
                "covid vaccines reduce "
                "the risk of severe disease"
            ),
            (
                "covid vaccines reduce "
                "hospitalization and death"
            ),
            (
                "covid vaccines do not "
                "guarantee prevention of infection"
            ),
            (
                "covid vaccines do not "
                "completely stop transmission"
            ),
        ],
    },
    {
        "name": "supported_with_uncovered_detail",
        "question": (
            "Does remdesivir treat COVID-19?"
        ),
        "response": (
            "Remdesivir treats COVID-19. "
            "It is administered intravenously."
        ),
        "statuses": [
            "SUPPORTED",
            "NOT_VERIFIABLE_WITH_CURRENT_KG",
        ],
        "summary": "SUPPORTED",
    },
    {
        "name": "compound_vaccine",
        "question": (
            "What do COVID vaccines protect against?"
        ),
        "response": (
            "COVID vaccination lowers the risk of "
            "severe illness, hospitalization, and "
            "death, although vaccinated people can "
            "still become infected."
        ),
        "statuses": [
            "SUPPORTED",
            "INSUFFICIENT_EVIDENCE",
        ],
        "summary": "MIXED",
    },
    {
        "name": "natural_transmission_context",
        "question": (
            "How do people catch COVID-19?"
        ),
        "response": (
            "People catch COVID-19 by breathing in "
            "respiratory particles, especially during "
            "close or prolonged contact indoors."
        ),
        "statuses": [
            "SUPPORTED",
        ],
        "summary": "SUPPORTED",
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
        timeout=60,
    ) as response:
        return json.load(
            response
        )


def normalize(
    text: str,
):
    return (
        " ".join(
            text.lower()
            .replace(
                "-",
                " ",
            )
            .split()
        )
    )


def main():
    passed = 0

    try:
        for case in CASES:
            data = verify_response(
                case["question"],
                case["response"],
            )

            actual_statuses = [
                claim[
                    "retrieval"
                ][
                    "verification"
                ][
                    "status"
                ]
                for claim
                in data["claims"]
            ]

            ok = True

            if "statuses" in case:
                ok = (
                    actual_statuses
                    == case[
                        "statuses"
                    ]
                )

            if (
                ok
                and "summary" in case
            ):
                ok = (
                    data[
                        "summary"
                    ][
                        "status"
                    ]
                    == case[
                        "summary"
                    ]
                )

            if (
                ok
                and "claim_contains"
                in case
            ):
                actual_claims = [
                    normalize(
                        claim[
                            "text"
                        ]
                    )
                    for claim
                    in data[
                        "claims"
                    ]
                ]

                for expected in case[
                    "claim_contains"
                ]:
                    expected_normalized = (
                        normalize(
                            expected
                        )
                    )

                    if not any(
                        expected_normalized
                        in actual
                        for actual
                        in actual_claims
                    ):
                        ok = False
                        break

            print(
                "PASS" if ok else "FAIL",
                case["name"],
            )

            if not ok:
                print(
                    "  statuses:",
                    actual_statuses,
                )
                print(
                    "  summary:",
                    data[
                        "summary"
                    ][
                        "status"
                    ],
                )

                for claim in data[
                    "claims"
                ]:
                    print(
                        "  claim:",
                        repr(
                            claim[
                                "text"
                            ]
                        ),
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

            if ok:
                passed += 1

    except URLError as error:
        print(
            f"ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    print()
    print(
        "POST-HOC SEMANTIC FIXES"
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