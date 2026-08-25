import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES = [
    (
        "Which pathogen is responsible for COVID-19?",
        "who",
        "SUPPORTED",
    ),
    (
        "SARS-CoV-2 is the causative agent of COVID-19.",
        "who",
        "SUPPORTED",
    ),
    (
        "COVID-19 develops after infection with SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "Adenovirus causes COVID-19.",
        "who",
        "CONTRADICTED",
    ),
    (
        "COVID-19 is not caused by SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "What causes COVID-19?",
        "who",
        "SUPPORTED",
    ),
    (
        "Does 5G cause COVID-19?",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
    (
        "Does Wi-Fi cause COVID-19?",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
    (
        "The lineage BA.3.2 remains under WHO monitoring.",
        "who",
        "SUPPORTED",
    ),
    (
        "Is NB.1.8.1 currently monitored by WHO?",
        "who",
        "SUPPORTED",
    ),
    (
        "WHO is not monitoring BA.3.2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "XFG remains on WHO's monitoring list.",
        "who",
        "SUPPORTED",
    ),
    (
        "COVID vaccines guarantee that infection cannot occur.",
        "who",
        "INSUFFICIENT_EVIDENCE",
    ),
    (
        "COVID vaccines completely stop transmission.",
        "who",
        "INSUFFICIENT_EVIDENCE",
    ),
    (
        "COVID vaccination lowers hospitalization risk.",
        "who",
        "SUPPORTED",
    ),
    (
        "Influenza vaccines prevent severe COVID-19.",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
]


def retrieve(
    text: str,
):
    request = Request(
        f"{BASE_URL}/kg/retrieve",
        data=json.dumps(
            {
                "text": text,
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
        for (
            text,
            expected_route,
            expected_status,
        ) in CASES:
            data = retrieve(
                text
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
                and status
                == expected_status
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

    except URLError as error:
        print(
            f"ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    print()
    print(
        "SEMANTIC NORMALIZATION"
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