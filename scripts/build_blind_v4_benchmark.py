import json
from pathlib import Path


SUPPORTED = "SUPPORTED"
CONTRADICTED = "CONTRADICTED"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
NOT_VERIFIABLE = (
    "NOT_VERIFIABLE_WITH_CURRENT_KG"
)

IMPLEMENTATION_COMMIT = (
    "cf18f246092929768876b92352aedea25332e54c"
)

AUTHORING_BASE_COMMIT = (
    "ab739a4c609f72dd55224146a05abb019346e57c"
)

OUTPUT = Path(
    "evaluation/"
    "end_to_end_verification_blind_v4_cases.json"
)

FREEZE = Path(
    "evaluation/blind_v4_freeze.json"
)

V3 = Path(
    "evaluation/"
    "end_to_end_verification_blind_v3_cases.json"
)


def claim_case(
    case_id,
    category,
    label_basis,
    text,
    route,
    status,
):
    return {
        "id": case_id,
        "mode": "claim",
        "category": category,
        "labelBasis": label_basis,
        "input": {
            "text": text,
        },
        "expected": {
            "route": route,
            "status": status,
        },
    }


def summary_for(
    claims,
):
    total = len(
        claims
    )

    if total == 0:
        return {
            "status": "NO_FACTUAL_CLAIMS",
            "supportedCount": 0,
            "contradictedCount": 0,
            "insufficientEvidenceCount": 0,
            "notVerifiableCount": 0,
            "verifiableClaimCount": 0,
            "needsAttentionCount": 0,
            "supportedRatio": None,
            "coverageRatio": None,
            "groundingScore": None,
        }

    statuses = [
        claim["status"]
        for claim
        in claims
    ]

    supported = statuses.count(
        SUPPORTED
    )

    contradicted = statuses.count(
        CONTRADICTED
    )

    insufficient = statuses.count(
        INSUFFICIENT
    )

    not_verifiable = statuses.count(
        NOT_VERIFIABLE
    )

    verifiable = (
        supported
        + contradicted
        + insufficient
    )

    needs_attention = (
        contradicted
        + insufficient
        + not_verifiable
    )

    if len(
        set(
            statuses
        )
    ) == 1:
        aggregate_status = (
            statuses[0]
        )
    else:
        aggregate_status = "MIXED"

    return {
        "status": aggregate_status,
        "supportedCount": supported,
        "contradictedCount": contradicted,
        "insufficientEvidenceCount": insufficient,
        "notVerifiableCount": not_verifiable,
        "verifiableClaimCount": verifiable,
        "needsAttentionCount": needs_attention,
        "supportedRatio": round(
            supported / total,
            3,
        ),
        "coverageRatio": round(
            verifiable / total,
            3,
        ),
        "groundingScore": round(
            supported / total,
            3,
        ),
    }


def response_case(
    case_id,
    category,
    question,
    response,
    claims,
):
    expected_claims = [
        {
            "text": text,
            "route": route,
            "status": status,
            "usedQuestionContext": used_context,
        }
        for (
            text,
            route,
            status,
            used_context,
        )
        in claims
    ]

    return {
        "id": case_id,
        "mode": "response",
        "category": category,
        "labelBasis": "system",
        "input": {
            "question": question,
            "response": response,
        },
        "expected": {
            "claims": expected_claims,
            "summary": summary_for(
                expected_claims
            ),
        },
    }


direct_groups = {
    "cause": [
        (
            "who",
            "SARS-CoV-2 infection is the etiologic basis of COVID-19.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "COVID-19 develops as a consequence of infection with SARS-CoV-2.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "The virus responsible for COVID-19 is SARS-CoV-2.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Respiratory syncytial virus is the pathogen responsible for COVID-19.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "COVID-19 is caused by seasonal influenza virus.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "Adenovirus infection gives rise to COVID-19.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "SARS-CoV-2 is incapable of producing COVID-19.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "Which virus is etiologically responsible for COVID-19?",
            "who",
            SUPPORTED,
        ),
    ],
    "transmission": [
        (
            "who",
            "SARS-CoV-2 can pass between people in infectious respiratory particles.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Close face-to-face interaction can facilitate COVID-19 transmission.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Respiratory aerosols cannot carry SARS-CoV-2 between people.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "COVID-19 transmission can occur after contact with a contaminated surface followed by touching the face.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Contaminated surfaces are the sole route by which COVID-19 spreads.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "Eating contaminated food is a primary route of COVID-19 transmission.",
            "who",
            INSUFFICIENT,
        ),
        (
            "who",
            "Close interpersonal contact cannot transmit COVID-19.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "Crowded indoor settings can increase the chance of COVID-19 transmission.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Food ingestion is a minor route of COVID-19 transmission.",
            "who",
            INSUFFICIENT,
        ),
        (
            "who",
            "Can SARS-CoV-2 move from person to person via respiratory particles?",
            "who",
            SUPPORTED,
        ),
    ],
    "long_covid": [
        (
            "who",
            "Post-COVID-19 condition may occur after acute COVID-19.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Long COVID can emerge following an earlier COVID-19 illness.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "A COVID-19 infection can never be followed by long COVID.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "The initial COVID-19 episode may precede post-COVID-19 condition.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Recovering from COVID-19 makes later post-COVID-19 condition impossible.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "Is long COVID a possible condition after COVID-19?",
            "who",
            SUPPORTED,
        ),
    ],
    "vaccination": [
        (
            "who",
            "COVID-19 vaccination can reduce the risk of severe disease.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "COVID vaccines can lower the chance of hospitalization.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "Vaccination against COVID-19 can reduce mortality risk.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "COVID-19 vaccination provides zero protection against hospitalization.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "COVID vaccines do not reduce the risk of severe disease.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "A COVID vaccine prevents every breakthrough infection.",
            "who",
            INSUFFICIENT,
        ),
        (
            "who",
            "COVID vaccination completely blocks all transmission.",
            "who",
            INSUFFICIENT,
        ),
        (
            "who",
            "Every vaccinated person is guaranteed to survive COVID-19.",
            "who",
            INSUFFICIENT,
        ),
        (
            "scope_policy",
            "A measles vaccine protects people against severe COVID-19.",
            "relationship",
            NOT_VERIFIABLE,
        ),
        (
            "who",
            "Can a COVID-19 vaccine lower the risk of dying from the disease?",
            "who",
            SUPPORTED,
        ),
    ],
    "variants": [
        (
            "who",
            "WHO currently keeps XFG under monitoring.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "BA.3.2 remains among WHO-monitored SARS-CoV-2 lineages.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "NB.1.8.1 is still tracked by WHO.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "WHO has stopped monitoring XFG.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "BA.3.2 is no longer monitored by WHO.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "Does WHO currently monitor NB.1.8.1?",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "WHO continues surveillance of XFG.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "NB.1.8.1 was dropped from WHO monitoring.",
            "who",
            CONTRADICTED,
        ),
    ],
    "current_risk": [
        (
            "who",
            "WHO currently assesses the worldwide public-health risk from COVID-19 as moderate.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "The present WHO global COVID-19 risk level is high.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "The current global public-health risk associated with COVID-19 is moderate.",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "WHO currently rates the global COVID-19 public-health risk as low.",
            "who",
            CONTRADICTED,
        ),
        (
            "who",
            "How does WHO classify the current worldwide public-health risk from COVID-19?",
            "who",
            SUPPORTED,
        ),
        (
            "who",
            "WHO's current global COVID-19 risk assessment is not moderate.",
            "who",
            CONTRADICTED,
        ),
    ],
    "history": [
        (
            "who_history",
            "On what date did WHO characterize COVID-19 as a pandemic?",
            "history",
            SUPPORTED,
        ),
        (
            "who_history",
            "WHO characterized COVID-19 as a pandemic on 11 March 2020.",
            "history",
            SUPPORTED,
        ),
        (
            "who_history",
            "WHO had already characterized COVID-19 as a pandemic in February 2020.",
            "history",
            CONTRADICTED,
        ),
        (
            "who_history",
            "WHO's China Country Office learned of the Wuhan pneumonia report on 31 December 2019.",
            "history",
            SUPPORTED,
        ),
        (
            "who_history",
            "WHO's China Country Office first learned of the Wuhan pneumonia report on 1 January 2020.",
            "history",
            CONTRADICTED,
        ),
        (
            "who_history",
            "Where was the pneumonia outbreak described in the earliest WHO-linked report?",
            "history",
            SUPPORTED,
        ),
        (
            "who_history",
            "The earliest WHO-linked pneumonia report concerned cases in Wuhan.",
            "history",
            SUPPORTED,
        ),
        (
            "scope_policy",
            "What date was SARS-CoV-2 first isolated in a laboratory?",
            "relationship",
            NOT_VERIFIABLE,
        ),
    ],
    "treatment": [
        (
            "chembl",
            "Remdesivir is used as a treatment for some patients with COVID-19.",
            "relationship",
            SUPPORTED,
        ),
        (
            "chembl",
            "Remdesivir has a therapeutic role in COVID-19.",
            "relationship",
            SUPPORTED,
        ),
        (
            "chembl",
            "Remdesivir is never used to treat COVID-19.",
            "relationship",
            CONTRADICTED,
        ),
        (
            "chembl",
            "COVID-19 treatment does not include remdesivir.",
            "relationship",
            CONTRADICTED,
        ),
        (
            "scope_policy",
            "Remdesivir cures every person who receives it for COVID-19.",
            "relationship",
            NOT_VERIFIABLE,
        ),
        (
            "chembl",
            "Is remdesivir used therapeutically against COVID-19?",
            "relationship",
            SUPPORTED,
        ),
        (
            "chembl",
            "Remdesivir was only studied for COVID-19 and has no therapeutic role.",
            "relationship",
            CONTRADICTED,
        ),
        (
            "chembl",
            "There is no connection between remdesivir and treatment of COVID-19.",
            "relationship",
            CONTRADICTED,
        ),
    ],
    "origin": [
        (
            "who_sago",
            "Natural zoonotic spillover currently has the strongest scientific support among assessed SARS-CoV-2 origin hypotheses.",
            "who",
            SUPPORTED,
        ),
        (
            "who_sago",
            "Natural zoonotic spillover has been proven with complete certainty as the origin of SARS-CoV-2.",
            "who",
            INSUFFICIENT,
        ),
        (
            "who_sago",
            "A laboratory-related pathway remains possible but unconfirmed for the origin of SARS-CoV-2.",
            "who",
            SUPPORTED,
        ),
        (
            "who_sago",
            "A laboratory-associated origin of SARS-CoV-2 has been definitively ruled out.",
            "who",
            CONTRADICTED,
        ),
        (
            "who_sago",
            "Current scientific evidence does not support deliberate laboratory manipulation over natural processes as the origin of SARS-CoV-2.",
            "who",
            SUPPORTED,
        ),
        (
            "who_sago",
            "Scientific evidence currently favors deliberate laboratory manipulation as the origin of SARS-CoV-2.",
            "who",
            CONTRADICTED,
        ),
        (
            "who_sago",
            "The available evidence provides no additional support for a cold-chain origin of SARS-CoV-2.",
            "who",
            SUPPORTED,
        ),
        (
            "who_sago",
            "Current evidence now supports a cold-chain pathway as the origin of SARS-CoV-2.",
            "who",
            CONTRADICTED,
        ),
        (
            "who_sago",
            "The precise origin of SARS-CoV-2 remains unresolved.",
            "who",
            SUPPORTED,
        ),
        (
            "who_sago",
            "The exact origin of SARS-CoV-2 is now known beyond scientific uncertainty.",
            "who",
            CONTRADICTED,
        ),
        (
            "who_sago",
            "Can the exact origin of SARS-CoV-2 currently be stated with certainty?",
            "who",
            INSUFFICIENT,
        ),
        (
            "who_sago",
            "Has natural spillover been conclusively proven as the origin of SARS-CoV-2?",
            "who",
            INSUFFICIENT,
        ),
    ],
    "scope": [
        (
            "scope_policy",
            "Can crystal energy destroy SARS-CoV-2?",
            "relationship",
            NOT_VERIFIABLE,
        ),
        (
            "scope_policy",
            "Do astrological signs determine who becomes infected with COVID-19?",
            "relationship",
            NOT_VERIFIABLE,
        ),
        (
            "scope_policy",
            "Can a Wi-Fi router neutralize COVID-19?",
            "relationship",
            NOT_VERIFIABLE,
        ),
        (
            "scope_policy",
            "Does wearing a magnetic bracelet prevent SARS-CoV-2 infection?",
            "relationship",
            NOT_VERIFIABLE,
        ),
    ],
}


cases = []

for category, entries in (
    direct_groups.items()
):
    for index, (
        label_basis,
        text,
        route,
        status,
    ) in enumerate(
        entries,
        start=1,
    ):
        cases.append(
            claim_case(
                (
                    f"blind4_{category}_"
                    f"{index:02d}"
                ),
                category,
                label_basis,
                text,
                route,
                status,
            )
        )


cases.extend(
    [
        response_case(
            "blind4_claim_extraction_01",
            "claim_extraction",
            "What virus causes COVID-19?",
            (
                "Here is the short version:\n"
                "- SARS-CoV-2 is the virus "
                "responsible for COVID-19."
            ),
            [
                (
                    (
                        "SARS-CoV-2 is the virus "
                        "responsible for COVID-19."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_claim_extraction_02",
            "claim_extraction",
            (
                "Is remdesivir used for "
                "COVID-19 treatment?"
            ),
            (
                "In brief:\n"
                "Remdesivir has a therapeutic "
                "role in COVID-19."
            ),
            [
                (
                    (
                        "Remdesivir has a therapeutic "
                        "role in COVID-19."
                    ),
                    "relationship",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_claim_extraction_03",
            "claim_extraction",
            (
                "What health outcomes can "
                "COVID vaccination reduce?"
            ),
            (
                "COVID vaccination lowers "
                "hospitalization risk. "
                "COVID vaccination reduces "
                "severe-disease risk."
            ),
            [
                (
                    (
                        "COVID vaccination lowers "
                        "hospitalization risk."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
                (
                    (
                        "COVID vaccination reduces "
                        "severe-disease risk."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_claim_extraction_04",
            "claim_extraction",
            (
                "What can you conclude about "
                "the exact SARS-CoV-2 origin?"
            ),
            (
                "I don't have enough "
                "information to answer that."
            ),
            [],
        ),
        response_case(
            "blind4_question_context_01",
            "question_context",
            "What causes COVID-19?",
            (
                "This disease is caused by "
                "SARS-CoV-2."
            ),
            [
                (
                    (
                        "This disease is caused by "
                        "SARS-CoV-2."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_question_context_02",
            "question_context",
            (
                "Can someone develop long COVID "
                "after COVID-19?"
            ),
            (
                "That condition can develop "
                "after the initial illness."
            ),
            [
                (
                    (
                        "That condition can develop "
                        "after the initial illness."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_question_context_03",
            "question_context",
            (
                "Can COVID vaccines reduce "
                "severe disease?"
            ),
            (
                "They can reduce "
                "severe-disease risk."
            ),
            [
                (
                    (
                        "They can reduce "
                        "severe-disease risk."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_question_context_04",
            "question_context",
            (
                "Could a laboratory-related event "
                "explain the origin of SARS-CoV-2?"
            ),
            (
                "That possibility remains "
                "unconfirmed."
            ),
            [
                (
                    (
                        "That possibility remains "
                        "unconfirmed."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_question_context_05",
            "question_context",
            "Is WHO still monitoring XFG?",
            (
                "It remains under WHO "
                "monitoring."
            ),
            [
                (
                    (
                        "It remains under WHO "
                        "monitoring."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_question_context_06",
            "question_context",
            (
                "When did WHO characterize "
                "COVID-19 as a pandemic?"
            ),
            "The date is 11 March 2020.",
            [
                (
                    "The date is 11 March 2020.",
                    "history",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_multi_claim_01",
            "multi_claim",
            (
                "Give me two factual "
                "COVID-19 statements."
            ),
            (
                "COVID-19 is caused by SARS-CoV-2. "
                "Respiratory particles can transmit "
                "COVID-19."
            ),
            [
                (
                    (
                        "COVID-19 is caused by "
                        "SARS-CoV-2."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
                (
                    (
                        "Respiratory particles can "
                        "transmit COVID-19."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_multi_claim_02",
            "multi_claim",
            (
                "Evaluate these two "
                "COVID-19 claims."
            ),
            (
                "COVID vaccination reduces "
                "hospitalization risk. "
                "SARS-CoV-2 cannot produce "
                "COVID-19."
            ),
            [
                (
                    (
                        "COVID vaccination reduces "
                        "hospitalization risk."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
                (
                    (
                        "SARS-CoV-2 cannot produce "
                        "COVID-19."
                    ),
                    "who",
                    CONTRADICTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_multi_claim_03",
            "multi_claim",
            (
                "Evaluate these vaccine "
                "and origin statements."
            ),
            (
                "COVID vaccines can lower "
                "severe-disease risk. "
                "Natural spillover has been proven "
                "with complete certainty as the "
                "origin of SARS-CoV-2."
            ),
            [
                (
                    (
                        "COVID vaccines can lower "
                        "severe-disease risk."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
                (
                    (
                        "Natural spillover has been "
                        "proven with complete certainty "
                        "as the origin of SARS-CoV-2."
                    ),
                    "who",
                    INSUFFICIENT,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_multi_claim_04",
            "multi_claim",
            (
                "Evaluate these treatment "
                "statements."
            ),
            (
                "Remdesivir has a therapeutic role "
                "in COVID-19. "
                "Crystal energy cures COVID-19."
            ),
            [
                (
                    (
                        "Remdesivir has a therapeutic "
                        "role in COVID-19."
                    ),
                    "relationship",
                    SUPPORTED,
                    False,
                ),
                (
                    (
                        "Crystal energy cures "
                        "COVID-19."
                    ),
                    "relationship",
                    NOT_VERIFIABLE,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_multi_claim_05",
            "multi_claim",
            "Evaluate these three claims.",
            (
                "COVID vaccination can reduce "
                "mortality risk. "
                "COVID-19 is caused by influenza "
                "virus. "
                "WHO currently rates the global "
                "COVID-19 public-health risk as high."
            ),
            [
                (
                    (
                        "COVID vaccination can reduce "
                        "mortality risk."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
                (
                    (
                        "COVID-19 is caused by "
                        "influenza virus."
                    ),
                    "who",
                    CONTRADICTED,
                    False,
                ),
                (
                    (
                        "WHO currently rates the "
                        "global COVID-19 public-health "
                        "risk as high."
                    ),
                    "who",
                    CONTRADICTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_multi_claim_06",
            "multi_claim",
            (
                "Evaluate these COVID-related "
                "statements."
            ),
            (
                "Deliberately spitting in a "
                "customer's food is a safety "
                "violation. "
                "Crowded indoor settings can "
                "increase COVID-19 transmission risk."
            ),
            [
                (
                    (
                        "Deliberately spitting in a "
                        "customer's food is a safety "
                        "violation."
                    ),
                    "relationship",
                    NOT_VERIFIABLE,
                    False,
                ),
                (
                    (
                        "Crowded indoor settings can "
                        "increase COVID-19 transmission "
                        "risk."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_time_sensitive_01",
            "time_sensitive",
            (
                "What is WHO's current global "
                "COVID-19 risk rating?"
            ),
            (
                "The current global public-health "
                "risk from COVID-19 is moderate."
            ),
            [
                (
                    (
                        "The current global "
                        "public-health risk from "
                        "COVID-19 is moderate."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_time_sensitive_02",
            "time_sensitive",
            "Is XFG still monitored by WHO?",
            (
                "WHO currently keeps XFG "
                "under monitoring."
            ),
            [
                (
                    (
                        "WHO currently keeps XFG "
                        "under monitoring."
                    ),
                    "who",
                    SUPPORTED,
                    False,
                ),
            ],
        ),
        response_case(
            "blind4_origin_uncertainty_01",
            "origin_uncertainty",
            (
                "How certain is the origin "
                "of SARS-CoV-2?"
            ),
            (
                "The exact origin remains unresolved. "
                "A laboratory-associated event "
                "remains possible but unverified."
            ),
            [
                (
                    (
                        "The exact origin remains "
                        "unresolved."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
                (
                    (
                        "A laboratory-associated event "
                        "remains possible but "
                        "unverified."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
        response_case(
            "blind4_origin_uncertainty_02",
            "origin_uncertainty",
            (
                "What origin hypothesis currently "
                "has the strongest support for "
                "SARS-CoV-2?"
            ),
            (
                "Natural zoonotic spillover has the "
                "strongest scientific support. "
                "The precise pathway remains "
                "uncertain."
            ),
            [
                (
                    (
                        "Natural zoonotic spillover "
                        "has the strongest scientific "
                        "support."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
                (
                    (
                        "The precise pathway remains "
                        "uncertain."
                    ),
                    "who",
                    SUPPORTED,
                    True,
                ),
            ],
        ),
    ]
)


with FREEZE.open(
    "r",
    encoding="utf-8",
) as file:
    freeze = json.load(
        file
    )

if (
    freeze.get(
        "implementationCommit"
    )
    != IMPLEMENTATION_COMMIT
):
    raise RuntimeError(
        "blind_v4_freeze.json does not "
        "match the frozen implementation commit"
    )


ids = [
    case["id"]
    for case
    in cases
]

if len(
    ids
) != len(
    set(
        ids
    )
):
    raise RuntimeError(
        "Duplicate benchmark case IDs"
    )


direct_count = sum(
    1
    for case
    in cases
    if case["mode"] == "claim"
)

response_count = sum(
    1
    for case
    in cases
    if case["mode"] == "response"
)

if direct_count != 80:
    raise RuntimeError(
        f"Expected 80 direct cases, got {direct_count}"
    )

if response_count != 20:
    raise RuntimeError(
        f"Expected 20 response cases, got {response_count}"
    )

if len(
    cases
) != 100:
    raise RuntimeError(
        f"Expected 100 total cases, got {len(cases)}"
    )


if V3.exists():
    with V3.open(
        "r",
        encoding="utf-8",
    ) as file:
        v3 = json.load(
            file
        )

    old_inputs = set()

    for case in v3[
        "cases"
    ]:
        if (
            case["mode"]
            == "claim"
        ):
            old_inputs.add(
                " ".join(
                    case[
                        "input"
                    ][
                        "text"
                    ]
                    .lower()
                    .split()
                )
            )
        else:
            old_inputs.add(
                " ".join(
                    case[
                        "input"
                    ][
                        "question"
                    ]
                    .lower()
                    .split()
                )
            )

            old_inputs.add(
                " ".join(
                    case[
                        "input"
                    ][
                        "response"
                    ]
                    .lower()
                    .split()
                )
            )

    new_inputs = set()

    for case in cases:
        if (
            case["mode"]
            == "claim"
        ):
            new_inputs.add(
                " ".join(
                    case[
                        "input"
                    ][
                        "text"
                    ]
                    .lower()
                    .split()
                )
            )
        else:
            new_inputs.add(
                " ".join(
                    case[
                        "input"
                    ][
                        "question"
                    ]
                    .lower()
                    .split()
                )
            )

            new_inputs.add(
                " ".join(
                    case[
                        "input"
                    ][
                        "response"
                    ]
                    .lower()
                    .split()
                )
            )

    duplicates = sorted(
        old_inputs
        & new_inputs
    )

    if duplicates:
        raise RuntimeError(
            "Exact v3 input reuse detected: "
            + repr(
                duplicates
            )
        )


benchmark = {
    "benchmark": (
        "end_to_end_verification_blind_v4"
    ),
    "frozen": True,
    "implementationCommit": (
        IMPLEMENTATION_COMMIT
    ),
    "benchmarkAuthoringBaseCommit": (
        AUTHORING_BASE_COMMIT
    ),
    "purpose": (
        "Fresh precommitted holdout for "
        "evaluating proposition-aware "
        "COVID-19 knowledge-graph verification "
        "after claim-extraction, semantic-fallback, "
        "scope, and proposition-guard improvements."
    ),
    "notes": [
        (
            "The implementation was frozen "
            "before this benchmark was authored."
        ),
        (
            "Expected labels were defined "
            "before executing this benchmark "
            "against the frozen implementation."
        ),
        (
            "The benchmark must be committed "
            "before its first execution."
        ),
        (
            "No blind-v4 execution result was "
            "consulted while constructing or "
            "labeling these cases."
        ),
        (
            "The implementation must not be "
            "tuned using these cases before "
            "the first-run result is recorded."
        ),
        (
            "The benchmark contains 80 direct "
            "claim cases and 20 response-level "
            "cases."
        ),
        (
            "Case construction is informed by "
            "the modeled KG capabilities and "
            "previously observed broad error "
            "categories, but the benchmark "
            "uses newly authored inputs."
        ),
        (
            "This is an internally authored "
            "holdout rather than an externally "
            "independent benchmark."
        ),
        (
            "Time-sensitive labels reflect the "
            "authoritative evidence snapshot "
            "represented in the frozen KG."
        ),
        (
            "Confidence remains a heuristic "
            "evidence-grounding score and is "
            "not a probability that a claim "
            "is true."
        ),
    ],
    "cases": cases,
}


OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with OUTPUT.open(
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        benchmark,
        file,
        indent=2,
        ensure_ascii=False,
    )

    file.write(
        "\n"
    )


print(
    "Wrote:",
    OUTPUT,
)

print(
    "cases:",
    len(
        cases
    ),
)

print(
    "direct:",
    direct_count,
)

print(
    "response:",
    response_count,
)

print(
    "implementation:",
    IMPLEMENTATION_COMMIT,
)

print(
    "No benchmark execution was performed."
)