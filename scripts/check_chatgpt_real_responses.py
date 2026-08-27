import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"

CASES_PATH = Path(
    "evaluation/chatgpt_real_response_cases.json"
)

OUTPUT_PATH = Path(
    "evaluation/chatgpt_real_response_results.json"
)


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


def confidence_text(
    claim: dict,
):
    retrieval = claim.get(
        "retrieval",
        {},
    )

    verification = retrieval.get(
        "verification",
        {},
    )

    confidence = verification.get(
        "confidence",
        {},
    )

    score = confidence.get(
        "score"
    )

    level = confidence.get(
        "level"
    )

    if score is None:
        return "n/a"

    if level:
        return (
            f"{score:.3f} "
            f"({level})"
        )

    return f"{score:.3f}"


def evidence_count(
    claim: dict,
):
    retrieval = claim.get(
        "retrieval",
        {},
    )

    verification = retrieval.get(
        "verification",
        {},
    )

    count = verification.get(
        "evidenceCount"
    )

    if count is not None:
        return count

    facts = retrieval.get(
        "facts",
        [],
    )

    return len(
        facts
    )


def main():
    if not CASES_PATH.exists():
        print(
            f"ERROR: missing {CASES_PATH}"
        )
        return 1

    with CASES_PATH.open(
        encoding="utf-8"
    ) as file:
        payload = json.load(
            file
        )

    cases = payload.get(
        "cases",
        [],
    )

    if not cases:
        print(
            "ERROR: no cases found"
        )
        return 1

    results = []

    try:
        for index, case in enumerate(
            cases,
            start=1,
        ):
            print()
            print(
                "=" * 88
            )
            print(
                f"{index:02d}/{len(cases):02d} "
                f"{case['id']}"
            )
            print(
                "=" * 88
            )

            print(
                "QUESTION"
            )
            print(
                case["question"]
            )

            print()
            print(
                "CHATGPT RESPONSE"
            )
            print(
                case["response"]
            )

            data = verify_response(
                case["question"],
                case["response"],
            )

            claims = data.get(
                "claims",
                [],
            )

            print()
            print(
                f"EXTRACTED CLAIMS: "
                f"{len(claims)}"
            )

            if not claims:
                print(
                    "  none"
                )

            for (
                claim_index,
                claim,
            ) in enumerate(
                claims,
                start=1,
            ):
                retrieval = claim.get(
                    "retrieval",
                    {},
                )

                verification = retrieval.get(
                    "verification",
                    {},
                )

                print()
                print(
                    f"  CLAIM {claim_index}"
                )
                print(
                    "    text: "
                    f"{claim.get('text')}"
                )
                print(
                    "    route: "
                    f"{retrieval.get('verificationType')}"
                )
                print(
                    "    status: "
                    f"{verification.get('status')}"
                )
                print(
                    "    context: "
                    f"{claim.get('usedQuestionContext')}"
                )
                print(
                    "    confidence: "
                    f"{confidence_text(claim)}"
                )
                print(
                    "    evidenceCount: "
                    f"{evidence_count(claim)}"
                )

                reason = verification.get(
                    "reason"
                )

                if reason:
                    print(
                        "    reason: "
                        f"{reason}"
                    )

            summary = data.get(
                "summary",
                {},
            )

            print()
            print(
                "SUMMARY"
            )
            print(
                "  status: "
                f"{summary.get('status')}"
            )
            print(
                "  supported: "
                f"{summary.get('supportedCount')}"
            )
            print(
                "  contradicted: "
                f"{summary.get('contradictedCount')}"
            )
            print(
                "  insufficient: "
                f"{summary.get('insufficientEvidenceCount')}"
            )
            print(
                "  notVerifiable: "
                f"{summary.get('notVerifiableCount')}"
            )
            print(
                "  verifiable: "
                f"{summary.get('verifiableClaimCount')}"
            )
            print(
                "  needsAttention: "
                f"{summary.get('needsAttentionCount')}"
            )
            print(
                "  supportedRatio: "
                f"{summary.get('supportedRatio')}"
            )
            print(
                "  groundingScore: "
                f"{summary.get('groundingScore')}"
            )
            print(
                "  coverageRatio: "
                f"{summary.get('coverageRatio')}"
            )

            results.append(
                {
                    "id": case["id"],
                    "question": (
                        case["question"]
                    ),
                    "response": (
                        case["response"]
                    ),
                    "actual": data,
                }
            )

    except HTTPError as error:
        print()
        print(
            f"HTTP ERROR: "
            f"{error.code} "
            f"{error.reason}"
        )

        try:
            print(
                error.read().decode()
            )
        except Exception:
            pass

        return 1

    except URLError as error:
        print()
        print(
            "ERROR: could not reach "
            f"{BASE_URL}: {error}"
        )
        return 1

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "suite": (
                    payload.get(
                        "suite"
                    )
                ),
                "caseCount": len(
                    results
                ),
                "results": results,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

        file.write(
            "\n"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "REAL CHATGPT RESPONSE REGRESSION"
    )
    print(
        f"cases: {len(results)}"
    )
    print(
        f"results: {OUTPUT_PATH}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )