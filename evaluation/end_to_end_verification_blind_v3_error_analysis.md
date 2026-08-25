# Blind v3 Error Analysis

Benchmark: `end_to_end_verification_blind_v3`

Untouched first-run case accuracy: **79/100 (79.0%)**

The taxonomy below is a deterministic post-hoc diagnostic grouping of failed cases. It is not a new benchmark score and does not change the frozen first-run results.

## Primary failure causes

| Cause | Failed cases |
| --- | ---: |
| negation_or_polarity | 4 |
| proposition_entity_mismatch | 3 |
| state_change_polarity | 3 |
| scope_or_domain_overreach | 2 |
| history_routing | 2 |
| exclusivity_or_quantifier | 1 |
| treatment_overclaim_scope | 1 |
| uncertainty_entailment | 1 |
| context_usage_mismatch | 1 |
| claim_extraction | 1 |
| contextual_reference_resolution | 1 |
| certainty_overclaim_semantics | 1 |

## Failures by benchmark category

| Category | Failed cases |
| --- | ---: |
| cause | 3 |
| variants | 3 |
| treatment | 3 |
| question_context | 3 |
| transmission | 2 |
| vaccination | 2 |
| history | 2 |
| origin | 1 |
| scope | 1 |
| multi_claim | 1 |

## Failed cases

| ID | Category | Mode | Primary cause | Difference | Input |
| --- | --- | --- | --- | --- | --- |
| blind3_cause_04 | cause | claim | proposition_entity_mismatch | status CONTRADICTED → SUPPORTED | A rhinovirus is the etiologic agent behind COVID-19. |
| blind3_cause_05 | cause | claim | proposition_entity_mismatch | status CONTRADICTED → SUPPORTED | COVID-19 is attributable to Ebola virus infection. |
| blind3_cause_06 | cause | claim | proposition_entity_mismatch | status CONTRADICTED → SUPPORTED | COVID-19 results from measles virus infection. |
| blind3_transmission_03 | transmission | claim | negation_or_polarity | status CONTRADICTED → SUPPORTED | Respiratory aerosols are unable to transmit COVID-19. |
| blind3_transmission_05 | transmission | claim | exclusivity_or_quantifier | status CONTRADICTED → SUPPORTED | Contaminated surfaces are the exclusive way COVID-19 spreads. |
| blind3_vaccination_05 | vaccination | claim | negation_or_polarity | status CONTRADICTED → SUPPORTED | Vaccines against COVID-19 offer no protection from severe disease. |
| blind3_vaccination_09 | vaccination | claim | scope_or_domain_overreach | route relationship → who; status NOT_VERIFIABLE_WITH_CURRENT_KG → SUPPORTED | A flu vaccine protects people from severe COVID-19. |
| blind3_variants_04 | variants | claim | state_change_polarity | status CONTRADICTED → SUPPORTED | XFG has been removed from WHO monitoring. |
| blind3_variants_05 | variants | claim | state_change_polarity | status CONTRADICTED → SUPPORTED | WHO no longer keeps BA.3.2 on its monitoring list. |
| blind3_variants_08 | variants | claim | state_change_polarity | status CONTRADICTED → SUPPORTED | NB.1.8.1 has left WHO's monitoring list. |
| blind3_history_06 | history | claim | history_routing | route history → relationship | Which city was tied to the earliest WHO-linked COVID-19 outbreak report? |
| blind3_history_07 | history | claim | history_routing | route history → relationship; status SUPPORTED → NOT_VERIFIABLE_WITH_CURRENT_KG | The earliest WHO-linked COVID-19 outbreak report described pneumonia cases in Wuhan. |
| blind3_treatment_03 | treatment | claim | negation_or_polarity | status CONTRADICTED → SUPPORTED | Remdesivir has no therapeutic use for COVID-19. |
| blind3_treatment_05 | treatment | claim | treatment_overclaim_scope | status NOT_VERIFIABLE_WITH_CURRENT_KG → SUPPORTED | Remdesivir eliminates COVID-19 in every treated person. |
| blind3_treatment_08 | treatment | claim | negation_or_polarity | status CONTRADICTED → SUPPORTED | Remdesivir has nothing to do with treating COVID-19. |
| blind3_origin_03 | origin | claim | uncertainty_entailment | status SUPPORTED → INSUFFICIENT_EVIDENCE | A laboratory-associated event remains plausible but unverified as an origin of SARS-CoV-2. |
| blind3_scope_03 | scope | claim | scope_or_domain_overreach | route relationship → who; status NOT_VERIFIABLE_WITH_CURRENT_KG → SUPPORTED | Can Bluetooth radiation stop COVID-19 transmission? |
| blind3_question_context_01 | question_context | response | context_usage_mismatch | context True → False | The disease is caused by SARS-CoV-2. |
| blind3_question_context_04 | question_context | response | claim_extraction | route who → None; status SUPPORTED → None; context True → None | It remains possible but has not been confirmed. |
| blind3_question_context_05 | question_context | response | contextual_reference_resolution | route who → relationship; status SUPPORTED → NOT_VERIFIABLE_WITH_CURRENT_KG; context True → False | WHO continues to track it. |
| blind3_multi_claim_03 | multi_claim | response | certainty_overclaim_semantics | status INSUFFICIENT_EVIDENCE → SUPPORTED | COVID vaccination can reduce severe-disease risk. Zoonotic spillover has been established beyond uncertainty as the origin of SARS-CoV-2. |
