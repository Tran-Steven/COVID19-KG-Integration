import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES = [
    (
        "Remdesivir can be used to treat COVID-19.",
        "relationship",
        "SUPPORTED",
    ),
    (
        "Remdesivir has never been used to treat COVID-19.",
        "relationship",
        "CONTRADICTED",
    ),
    (
        "Remdesivir is unrelated to treatment of COVID-19.",
        "relationship",
        "CONTRADICTED",
    ),
    (
        "Remdesivir cures every case of COVID-19.",
        "relationship",
        "NOT_VERIFIABLE_WITH_CURRENT_KG",
    ),
    (
        "Remdesivir was only studied for COVID-19 and never used to treat it.",
        "relationship",
        "CONTRADICTED",
    ),
    (
        "Can remdesivir treat coronavirus disease 2019?",
        "relationship",
        "SUPPORTED",
    ),
    (
        "Remdesivir treats COVID-19.",
        "relationship",
        "SUPPORTED",
    ),
    (
        "Remdesivir does not treat COVID-19.",
        "relationship",
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

            if not ok:
                print(
                    "  relation:",
                    data.get(
                        "relation"
                    ),
                )

                print(
                    "  relationships:",
                    data.get(
                        "relationships"
                    ),
                )

                print(
                    "  facts:",
                    len(
                        data.get(
                            "facts",
                            [],
                        )
                    ),
                )

    except URLError as error:
        print(
            f"ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    print()
    print(
        "TREATMENT VERIFICATION"
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