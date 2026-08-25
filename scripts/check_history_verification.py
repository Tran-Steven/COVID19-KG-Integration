import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES = [
    (
        "WHO characterized COVID-19 as a pandemic on March 11, 2020.",
        "history",
        "SUPPORTED",
    ),
    (
        "WHO characterized COVID-19 as a pandemic in February 2020.",
        "history",
        "CONTRADICTED",
    ),
    (
        "The Wuhan pneumonia report reached the WHO China Country Office on December 31, 2019.",
        "history",
        "SUPPORTED",
    ),
    (
        "The first WHO-linked Wuhan outbreak report was in January 2020.",
        "history",
        "CONTRADICTED",
    ),
    (
        "COVID-19 was first reported in Wuhan.",
        "history",
        "SUPPORTED",
    ),
    (
        "COVID-19 was first reported in London.",
        "history",
        "CONTRADICTED",
    ),
    (
        "When did COVID become a pandemic?",
        "history",
        "SUPPORTED",
    ),
    (
        "Where was COVID-19 first found?",
        "history",
        "SUPPORTED",
    ),
    (
        "When was SARS-CoV-2 first found?",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
]


def retrieve(text):
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
        return json.load(response)


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
            f"ERROR: could not reach {BASE_URL}: {error}"
        )
        return 1

    print()
    print(
        "HISTORY VERIFICATION"
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