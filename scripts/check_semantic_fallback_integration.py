import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES = [
    (
        "Which organism is the etiological agent behind COVID-19?",
        "who",
        "SUPPORTED",
    ),
    (
        "What virus gives rise to coronavirus disease 2019?",
        "who",
        "SUPPORTED",
    ),
    (
        "Can radio-frequency fields give rise to COVID-19?",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
    (
        "Remdesivir may be administered as therapy for COVID-19.",
        "relationship",
        "SUPPORTED",
    ),
    (
        "Remdesivir is never administered therapeutically for COVID-19.",
        "relationship",
        "CONTRADICTED",
    ),
    (
        "Remdesivir cures every COVID-19 patient.",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
    (
        "Zoonotic spillover has been established with complete certainty as the origin of SARS-CoV-2.",
        "who",
        "INSUFFICIENT_EVIDENCE",
    ),
    (
        "A laboratory-related event remains plausible but has not been demonstrated as the origin of SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "A laboratory-related origin has been dismissed as impossible for SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "Available data favor deliberate laboratory manipulation over natural processes for SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "Available data fail to support deliberate laboratory manipulation over natural processes for SARS-CoV-2.",
        "who",
        "SUPPORTED",
    ),
    (
        "The data now point toward a cold-chain origin of SARS-CoV-2.",
        "who",
        "CONTRADICTED",
    ),
    (
        "The precise origin of SARS-CoV-2 remains unsettled.",
        "who",
        "SUPPORTED",
    ),
    (
        "Researchers now know precisely how SARS-CoV-2 originated.",
        "who",
        "CONTRADICTED",
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
        timeout=60,
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
        "SEMANTIC FALLBACK INTEGRATION"
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