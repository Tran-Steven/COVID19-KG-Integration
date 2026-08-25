import sys
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(
        ROOT / "backend"
    ),
)

from app.interpretation.verification_semantic_matcher import (
    VerificationSemanticMatcher,
)


CASES = [
    (
        "What infectious agent gives rise to COVID-19?",
        "cause",
    ),
    (
        "The etiologic virus behind COVID-19 is SARS-CoV-2.",
        "cause",
    ),
    (
        "Coronavirus disease 2019 follows infection by SARS-CoV-2.",
        "cause",
    ),
    (
        "RSV is responsible for COVID-19.",
        "cause",
    ),
    (
        "Remdesivir may be administered for treatment of COVID-19.",
        "treatment",
    ),
    (
        "Is remdesivir a therapeutic option for coronavirus disease 2019?",
        "treatment",
    ),
    (
        "Doctors can use remdesivir therapeutically in COVID-19.",
        "treatment",
    ),
    (
        "Remdesivir has no role in treating COVID-19.",
        "treatment",
    ),
    (
        "On what date did WHO first characterize COVID-19 as a pandemic?",
        "history",
    ),
    (
        "Which city was associated with the earliest WHO-linked outbreak report?",
        "history",
    ),
    (
        "The WHO China office received the Wuhan pneumonia report at the end of 2019.",
        "history",
    ),
    (
        "When was the initial Wuhan pneumonia report picked up by WHO?",
        "history",
    ),
    (
        "The precise source of SARS-CoV-2 has not been settled.",
        "origin",
    ),
    (
        "A lab-associated incident remains one possible origin hypothesis.",
        "origin",
    ),
    (
        "Available evidence favors animal-to-human spillover as the leading origin explanation.",
        "origin",
    ),
    (
        "The exact origin of SARS-CoV-2 is still uncertain.",
        "origin",
    ),
    (
        "WHO still tracks the lineage BA.3.2.",
        "variants",
    ),
    (
        "Has WHO stopped following XFG?",
        "variants",
    ),
    (
        "Which SARS-CoV-2 lineages remain on the WHO monitoring list?",
        "variants",
    ),
    (
        "NB.1.8.1 is still being watched by WHO.",
        "variants",
    ),
    (
        "Can radio-frequency radiation eliminate COVID-19?",
        "out_of_scope",
    ),
    (
        "Do horoscopes determine who contracts COVID-19?",
        "out_of_scope",
    ),
    (
        "Can a Wi-Fi router prevent severe COVID-19?",
        "out_of_scope",
    ),
    (
        "Do crystals stop coronavirus infection?",
        "out_of_scope",
    ),
]


def main():
    matcher = (
        VerificationSemanticMatcher()
    )

    passed = 0

    for (
        text,
        expected,
    ) in CASES:
        result = matcher.resolve(
            text
        )

        actual = (
            result["label"]
            if result
            else None
        )

        ok = (
            actual == expected
        )

        if ok:
            passed += 1

        print(
            "PASS" if ok else "FAIL",
            text,
        )

        print(
            "  expected:",
            expected,
        )

        print(
            "  actual:",
            actual,
        )

        if result:
            print(
                "  method:",
                result[
                    "method"
                ],
            )

            print(
                "  score:",
                result[
                    "score"
                ],
            )

            print(
                "  embedding:",
                result[
                    "embeddingScore"
                ],
            )

        if not ok:
            print(
                "  rankings:"
            )

            for ranking in (
                matcher.rank(
                    text
                )[:3]
            ):
                print(
                    "   ",
                    ranking[
                        "label"
                    ],
                    ranking[
                        "score"
                    ],
                )

    print()

    print(
        "VERIFICATION SEMANTIC MATCHER"
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