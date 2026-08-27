import json
import sys
from urllib.request import Request, urlopen

API = "http://localhost:8000/kg/verify-response"

cases = [
    {
        "name": "origin_unknown_contraction",
        "question": "What is the exact origin of SARS-CoV-2?",
        "response": "We don't know the exact origin.",
        "expected": "SUPPORTED",
    },
    {
        "name": "origin_specific_source_not_identified",
        "question": "What is the exact origin of SARS-CoV-2?",
        "response": (
            "Researchers have not identified the specific infected "
            "animal or complete transmission chain."
        ),
        "expected": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "origin_known_overclaim",
        "question": "What is the exact origin of SARS-CoV-2?",
        "response": "The exact origin is known.",
        "expected": "CONTRADICTED",
    },
    {
        "name": "origin_identified_overclaim",
        "question": "What is the exact origin of SARS-CoV-2?",
        "response": "The exact origin has been identified.",
        "expected": "CONTRADICTED",
    },
    {
        "name": "origin_engineered_distinction",
        "question": "Was SARS-CoV-2 definitely created in a laboratory?",
        "response": (
            "Those are different claims from saying the virus was "
            "deliberately created or engineered in a lab."
        ),
        "expected": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "mmr_compound_vaccine_qualification",
        "question": "Is a measles vaccine effective against severe COVID-19?",
        "response": (
            "The evidence has not shown it to be a reliable substitute "
            "for COVID-19 vaccination, which is specifically designed "
            "to reduce the risk of severe COVID-19, hospitalization, "
            "and death."
        ),
        "expected": "SUPPORTED",
    },
    {
        "name": "xfg_vum_not_dangerous",
        "question": "Why are they still tracking XFG?",
        "response": (
            "WHO still tracks XFG because Variant Under Monitoring "
            "is essentially a watchlist category, not a declaration "
            "that the variant is especially dangerous."
        ),
        "expected": "SUPPORTED",
    },
    {
        "name": "xfg_no_additional_risk_indirect",
        "question": "Why are they still tracking XFG?",
        "response": (
            "WHO currently says the evidence does not indicate that "
            "XFG poses additional public-health risk compared with "
            "other circulating SARS-CoV-2 variants."
        ),
        "expected": "INSUFFICIENT_EVIDENCE",
    },
    {
        "name": "xfg_tracking_not_severity_rationale",
        "question": "Why are they still tracking XFG?",
        "response": (
            "They are tracking XFG to catch a meaningful change early, "
            "not because they presently think XFG is unusually severe."
        ),
        "expected": "INSUFFICIENT_EVIDENCE",
    },
]

passed = 0

for case in cases:
    req = Request(
        API,
        data=json.dumps({
            "question": case["question"],
            "response": case["response"],
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(req, timeout=60) as response:
        result = json.load(response)

    claims = result.get("claims", [])

    if len(claims) != 1:
        print(f"FAIL {case['name']}")
        print(f"  claimCount: {len(claims)}")
        continue

    verification = claims[0]["retrieval"]["verification"]
    actual = verification["status"]

    if actual == case["expected"]:
        print(f"PASS {case['name']}")
        passed += 1
    else:
        print(f"FAIL {case['name']}")
        print(f"  expected: {case['expected']}")
        print(f"  actual:   {actual}")
        print(f"  reason:   {verification['reason']}")

print()
print("TARGETED SEMANTIC REGRESSIONS")
print(f"cases: {passed}/{len(cases)}")

if passed != len(cases):
    sys.exit(1)
