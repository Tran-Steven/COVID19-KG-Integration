import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

SUMMARY_RESPONSE = """Here’s the COVID-19 discussion summarized:

- Cause: COVID-19 is caused by infection with the SARS-CoV-2 virus.
- Transmission: It mainly spreads through respiratory particles from infected people, especially through close indoor contact.
- Sex: Sex itself does not cause COVID-19, but close face-to-face contact during sex can transmit SARS-CoV-2.
- Spitting in food: Spitting in someone’s food could potentially expose them to infectious saliva, though eating contaminated food is not considered a major route of COVID transmission. Doing this deliberately is also a serious health/safety violation.
- Smoking: Smoking does not cause COVID-19, although smoking can damage the respiratory system and may increase the risk of severe illness.
- Fentanyl: Fentanyl does not cause COVID-19.
- Gaming: Video games do not cause COVID-19.
- Remdesivir: Remdesivir does not cause COVID-19; it is an antiviral medication used in certain patients to treat COVID-19.
- Treatments: Proven approaches include appropriate antiviral treatment such as Paxlovid or remdesivir for eligible patients, along with supportive care. Antibiotics do not treat the virus itself.
- Origin: SARS-CoV-2 was first identified during the outbreak in Wuhan, China, in late 2019. That does not establish that China deliberately created or released it.
- Manufactured virus claim: There is no established evidence that SARS-CoV-2 was deliberately engineered as a biological weapon. The exact pathway by which the virus first entered humans remains debated.
- U.S. blaming China: U.S. politicians and officials did publicly criticize China over its handling of the outbreak and transparency. Some of that was geopolitical/political messaging, but that is separate from proving that China manufactured or deliberately released the virus.
"""


def verify(
    question: str,
    response: str,
):
    request = Request(
        f"{BASE_URL}/kg/verify-response",
        data=json.dumps(
            {
                "question": question,
                "response": response,
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
    ) as result:
        return json.load(result)


def status_of(
    claims: list[dict],
    text: str,
):
    for claim in claims:
        if claim["text"] == text:
            return claim["retrieval"]["verification"]["status"]

    return None


def contains_claim(
    claims: list[dict],
    fragment: str,
):
    fragment = fragment.lower()

    return any(fragment in claim["text"].lower() for claim in claims)


def check(
    condition: bool,
    label: str,
):
    print(
        "PASS" if condition else "FAIL",
        label,
    )

    return condition


def main():
    try:
        data = verify(
            "covid 19 summary",
            SUMMARY_RESPONSE,
        )
    except URLError as error:
        print(f"ERROR: could not reach {BASE_URL}: {error}")
        return 1

    claims = data["claims"]

    passed = 0
    total = 0

    checks = [
        (
            not contains_claim(
                claims,
                ("here’s the covid-19 discussion summarized"),
            ),
            "meta_summary_not_extracted",
        ),
        (
            all("\n" not in claim["text"] for claim in claims),
            "no_cross_line_claims",
        ),
        (
            contains_claim(
                claims,
                ("close face-to-face contact during sex can transmit sars-cov-2"),
            ),
            "sex_transmission_preserved",
        ),
        (
            contains_claim(
                claims,
                (
                    "spitting in someone’s food "
                    "could potentially expose them "
                    "to infectious saliva"
                ),
            ),
            "spitting_claim_separate",
        ),
        (
            contains_claim(
                claims,
                (
                    "eating contaminated food "
                    "is not considered a major "
                    "route of covid transmission"
                ),
            ),
            "food_route_claim_separate",
        ),
        (
            contains_claim(
                claims,
                ("smoking may increase the risk of severe illness"),
            ),
            "smoking_subject_inherited",
        ),
        (
            contains_claim(
                claims,
                (
                    "remdesivir is an antiviral "
                    "medication used in certain "
                    "patients to treat covid-19"
                ),
            ),
            "remdesivir_pronoun_resolved",
        ),
        (
            status_of(
                claims,
                ("Sex itself does not cause COVID-19"),
            )
            != "CONTRADICTED",
            "sex_negative_cause_not_reversed",
        ),
        (
            status_of(
                claims,
                ("Video games do not cause COVID-19."),
            )
            != "CONTRADICTED",
            "gaming_negative_cause_not_reversed",
        ),
        (
            status_of(
                claims,
                (
                    "eating contaminated food "
                    "is not considered a major "
                    "route of COVID transmission"
                ),
            )
            == "INSUFFICIENT_EVIDENCE",
            "food_route_qualification_conservative",
        ),
        (
            status_of(
                claims,
                ("Doing this deliberately is also a serious health/safety violation."),
            )
            == ("NOT_VERIFIABLE_WITH_CURRENT_KG"),
            "irrelevant_context_not_supported",
        ),
        (
            status_of(
                claims,
                (
                    "Remdesivir is an antiviral "
                    "medication used in certain "
                    "patients to treat COVID-19"
                ),
            )
            == "SUPPORTED",
            "remdesivir_treatment_grounded",
        ),
    ]

    for condition, label in checks:
        total += 1

        if check(
            condition,
            label,
        ):
            passed += 1

    targeted = [
        (
            ("SARS-CoV-2 is the established cause of COVID-19."),
            "SUPPORTED",
            "established_cause_paraphrase",
        ),
        (
            ("SARS-CoV-2 is the virus that causes the disease COVID-19."),
            "SUPPORTED",
            "cause_disease_paraphrase",
        ),
        (
            ("It is incorrect to say that SARS-CoV-2 does not cause COVID-19."),
            "SUPPORTED",
            "meta_negative_cause_reversal",
        ),
        (
            ("It is incorrect to say that SARS-CoV-2 causes COVID-19."),
            "CONTRADICTED",
            "meta_positive_cause_reversal",
        ),
        (
            ("COVID-19 is caused by SARS-CoV-2, not by radio waves."),
            "SUPPORTED",
            "alternative_cause_negation_scope",
        ),
        (
            ("COVID-19 is caused by SARS-CoV-2, not 5G or influenza viruses."),
            "SUPPORTED",
            "alternative_cause_compound_scope",
        ),
        (
            ("COVID-19 is the disease, while SARS-CoV-2 is the virus that causes it."),
            "SUPPORTED",
            "cause_pronoun_within_sentence",
        ),
        (
            ("COVID-19 is an infectious disease caused by the coronavirus SARS-CoV-2."),
            "SUPPORTED",
            "descriptive_passive_cause",
        ),
        (
            ("COVID-19 is an infectious disease not caused by SARS-CoV-2."),
            "CONTRADICTED",
            "descriptive_passive_negative_cause",
        ),
        (
            "SARS-CoV-2 does not cause COVID-19.",
            "CONTRADICTED",
            "canonical_negative_cause",
        ),
        (
            "Video games do not cause COVID-19.",
            ("NOT_VERIFIABLE_WITH_CURRENT_KG"),
            "unlinked_alternative_cause",
        ),
        (
            ("COVID-19 does not spread through respiratory particles."),
            "CONTRADICTED",
            "matched_negative_transmission",
        ),
        (
            (
                "Eating contaminated food is not "
                "considered a major route of "
                "COVID transmission."
            ),
            "INSUFFICIENT_EVIDENCE",
            "ranked_transmission_claim",
        ),
    ]

    for response, expected, label in targeted:
        result = verify(
            "Check this COVID-19 claim.",
            response,
        )

        actual = result["claims"][0]["retrieval"]["verification"]["status"]

        total += 1

        if check(
            actual == expected,
            label,
        ):
            passed += 1

    print()
    print("PROPOSITION REGRESSIONS")

    print(f"checks: {passed}/{total} ({passed / total:.1%})")

    print(
        "claimCount:",
        data["claimCount"],
    )

    if passed != total:
        print()

        for claim in claims:
            print(claim["text"])

            print(
                "  ",
                claim["retrieval"]["verificationType"],
                claim["retrieval"]["verification"]["status"],
            )

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
