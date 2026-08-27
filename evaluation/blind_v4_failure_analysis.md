# Blind V4 Post-Hoc Failure Analysis

## Evaluation record

This analysis was performed only after the untouched blind-v4 result had been executed, committed, and recorded.

- Frozen implementation: `cf18f246092929768876b92352aedea25332e54c`
- Benchmark commit: `2f5fcb0d77e30611e010f1e75676cd4471f085de`
- Benchmark SHA-256: `8dc86acd8b80b45afade79f8c0eac6a4c96b18de08e0414287ad8c7caf698401`
- First-run result commit: `2dae57cd0f9d5d2b73dcf63d13fab8142da8769a`
- First-run result SHA-256: `8ea700d501aad81dc0c897f49fc85533258af1878d75e74bc3c0c0d7cc7d3f3a`
- Execution-record commit: `e6397913943f669d5b8d3635d756aa0dc410507f`

No blind-v4 benchmark labels or first-run results are changed by this analysis.

## First-run performance

| Metric | Result |
|---|---:|
| Case accuracy | 72/100 (72.0%) |
| Status accuracy | 83/109 (76.1%) |
| Route accuracy | 101/109 (92.7%) |
| Claim extraction precision | 90.3% |
| Claim extraction recall | 96.6% |
| Claim extraction F1 | 93.3% |
| Question-context accuracy | 26/29 (89.7%) |
| Response summary status accuracy | 90.0% |
| Response grounding-score accuracy | 90.0% |
| Response coverage-ratio accuracy | 85.0% |
| Mean confidence when status correct | 0.8421 |
| Mean confidence when status incorrect | 0.5992 |

The 80 direct-claim cases produced 59 passes and 21 failures, for 73.75% case accuracy.

The 20 response-level cases produced 13 passes and 7 failures, for 65.0% case accuracy.

The response-level case score is stricter than response-summary accuracy because a case can fail from extraction, route, or question-context metadata even when its aggregate summary remains correct.

## Category performance

| Category | Accuracy |
|---|---:|
| cause | 3/8 (37.5%) |
| claim extraction | 3/4 (75.0%) |
| current risk | 6/6 (100.0%) |
| history | 5/8 (62.5%) |
| long COVID | 5/6 (83.3%) |
| multi-claim | 4/6 (66.7%) |
| origin | 11/12 (91.7%) |
| origin uncertainty | 0/2 (0.0%) |
| question context | 4/6 (66.7%) |
| scope | 4/4 (100.0%) |
| time sensitive | 2/2 (100.0%) |
| transmission | 8/10 (80.0%) |
| treatment | 6/8 (75.0%) |
| vaccination | 7/10 (70.0%) |
| variants | 4/8 (50.0%) |

The strongest categories were current risk, scope, and time-sensitive verification. Origin verification also remained strong at 91.7%.

The weakest direct category was causal verification. Variant state changes, contextual origin statements, historical routing, and several forms of proposition polarity also remained important failure sources.

## Failure taxonomy

The 28 failed cases were assigned one primary post-hoc failure mode. These categories describe observed behavior and likely shared implementation weaknesses; they are not new benchmark labels.

### 1. Causal proposition parsing and canonical-agent comparison

Count: 7

Cases:

- `blind4_cause_04`
- `blind4_cause_05`
- `blind4_cause_06`
- `blind4_cause_07`
- `blind4_cause_08`
- `blind4_multi_claim_02`
- `blind4_multi_claim_05`

Observed behavior:

Alternative etiologic agents were inconsistently classified as `NOT_VERIFIABLE_WITH_CURRENT_KG`, `SUPPORTED`, or otherwise failed to reach the canonical WHO causal relation. Causal paraphrases such as "pathogen responsible for", "gives rise to", "incapable of producing", and an etiologic question were not handled consistently.

The current proposition guard also distinguishes linked and unlinked alternative causes conservatively, which can prevent the downstream canonical-cause comparison from deciding that an asserted alternative etiologic agent conflicts with the modeled SARS-CoV-2 causal relation.

Development principle:

Causal verification should first identify the proposition roles:

`claimed agent -> causes -> COVID-19`

and then compare the claimed agent with the canonical causal agent represented by the evidence.

This should be semantic and entity-based rather than a list of benchmark-specific virus names.

### 2. Polarity, state-change, and absolute-quantifier interpretation

Count: 10

Cases:

- `blind4_transmission_05`
- `blind4_transmission_07`
- `blind4_long_covid_05`
- `blind4_vaccination_04`
- `blind4_vaccination_08`
- `blind4_variants_04`
- `blind4_variants_05`
- `blind4_variants_08`
- `blind4_treatment_07`
- `blind4_treatment_08`

Observed behavior:

The verifier handles several conventional negation forms such as `not`, `cannot`, and `never`, but v4 exposed propositionally equivalent expressions that are not consistently interpreted:

- `sole route`
- `zero protection`
- `no therapeutic role`
- `no connection`
- `stopped monitoring`
- `no longer monitored`
- `dropped from monitoring`
- universal guarantees such as `every vaccinated person`

These expressions alter the truth conditions of the proposition even when they do not use a simple `not` construction.

Development principle:

Polarity should be modeled separately from relation retrieval.

The system should distinguish at least:

- positive assertion
- explicit negation
- cessation or state reversal
- exclusivity
- universal or absolute strengthening
- uncertainty

The verifier should then compare that proposition-level polarity with the retrieved evidence.

### 3. Routing and semantic-vocabulary coverage

Count: 4

Cases:

- `blind4_vaccination_09`
- `blind4_variants_07`
- `blind4_history_06`
- `blind4_history_07`

Observed behavior:

Some claims described modeled concepts using vocabulary that did not activate the intended resolver.

Examples include:

- a non-COVID vaccine being routed into WHO COVID-vaccine evidence
- `surveillance` instead of explicit monitoring language
- historical descriptions of the earliest WHO-linked Wuhan pneumonia report failing to route to history

Development principle:

Routing should use semantic intent plus entity constraints.

Adding isolated benchmark phrases to routing rules would improve the benchmark without solving the underlying problem. The preferred fix is broader semantic matching combined with checks that the retrieved subject and relation match the actual proposition.

### 4. Scope-versus-insufficient-evidence boundary

Count: 1

Case:

- `blind4_history_08`

Observed behavior:

A question asking for the date SARS-CoV-2 was first isolated in a laboratory was classified as `INSUFFICIENT_EVIDENCE` rather than `NOT_VERIFIABLE_WITH_CURRENT_KG`.

Development principle:

`INSUFFICIENT_EVIDENCE` should be used when the KG models the relevant proposition but its evidence is not strong or complete enough to support or contradict the claim.

`NOT_VERIFIABLE_WITH_CURRENT_KG` should be used when the required relation or event is outside the current KG's modeled verification capability.

This boundary should be determined from modeled relation coverage rather than from retrieval failure alone.

### 5. Conversational reference and question-context resolution

Count: 2

Cases:

- `blind4_question_context_01`
- `blind4_question_context_05`

Observed behavior:

`This disease is caused by SARS-CoV-2.` was factually verified but did not record that question context had been used.

`It remains under WHO monitoring.` failed to resolve the referenced variant from the question and consequently failed route, status, and context-use checks.

Development principle:

Question context should be invoked when a response proposition contains an unresolved entity or event reference that is required to interpret the proposition.

References such as:

- `it`
- `this disease`
- `that condition`
- `that possibility`
- `the date`

should be resolved through the question only when the response itself lacks the necessary referent.

Context use should remain explicit in the output so evaluation can distinguish self-contained verification from contextual verification.

### 6. Claim extraction and clause segmentation

Count: 2

Cases:

- `blind4_claim_extraction_01`
- `blind4_origin_uncertainty_01`

Observed behavior:

A presentational line, `Here is the short version:`, was retained as an additional claim.

The sentence `A laboratory-associated event remains possible but unverified.` produced an extraction mismatch, showing that adversative conjunction handling can incorrectly split a single qualified proposition.

Development principle:

Presentational headers should be filtered structurally rather than by hardcoding every possible introductory phrase.

Clause splitting should occur only when both sides represent independently checkable propositions. A construction in which the second phrase qualifies the first proposition should remain intact.

### 7. Origin certainty and uncertainty entailment

Count: 2

Cases:

- `blind4_origin_10`
- `blind4_origin_uncertainty_02`

Observed behavior:

`The exact origin of SARS-CoV-2 is now known beyond scientific uncertainty.` was classified as `INSUFFICIENT_EVIDENCE` rather than contradicting the represented evidence that the precise origin remains unresolved.

In a contextual response, `The precise pathway remains uncertain.` was classified as `INSUFFICIENT_EVIDENCE` rather than supported by the modeled unresolved-origin status.

Development principle:

Origin verification needs proposition-level comparison between:

- unresolved or inconclusive
- possible but unverified
- supported hypothesis
- ruled out
- conclusively established

Uncertainty language should not automatically map to `INSUFFICIENT_EVIDENCE`. A statement that uncertainty exists can itself be directly `SUPPORTED` when the evidence explicitly represents that uncertainty.

## Cross-cutting findings

### Retrieval success is not proposition support

Several failures occurred because relevant evidence was retrieved but the verifier did not fully compare the proposition expressed by the claim with the proposition expressed by the evidence.

The next implementation phase should therefore prioritize proposition interpretation over additional retrieval breadth.

### Negation is broader than the word "not"

The v4 failures show that binary lexical negation detection is insufficient. Cessation, exclusivity, absence, universal quantification, and certainty all alter entailment.

A reusable proposition-polarity representation is preferable to adding independent phrase checks inside each domain resolver.

### Entity constraints matter

Evidence about COVID vaccination should not automatically verify a claim about an arbitrary different vaccine. Similarly, canonical causal evidence should be compared against the claimed etiologic agent rather than treating the presence of causal evidence as sufficient support.

### Response failures are often downstream of direct-verification failures

`blind4_multi_claim_02` and `blind4_multi_claim_05` repeat causal-verification weaknesses also observed in direct cases.

The 28 failed cases therefore do not represent 28 independent implementation defects.

### Confidence has useful separation but remains uncalibrated

Mean confidence was higher when verification status was correct (`0.8421`) than when it was incorrect (`0.5992`).

This is useful evidence that the score tracks grounding quality to some extent, but the score remains heuristic and uncalibrated and must not be described as a probability that a claim is true.

## Label audit

The frozen v4 labels are not changed during post-hoc analysis.

Before development fixes are evaluated, apparently ambiguous cases should be reviewed against the project's status definitions. If a benchmark label is later judged debatable, that observation should be documented separately rather than silently rewriting the frozen benchmark.

In particular, future analysis should preserve the distinction between:

- factual contradiction
- evidence insufficiency
- KG scope limitations
- uncertainty statements that are themselves evidence-backed facts

## Development priorities

The recommended implementation order is:

1. Introduce a reusable proposition-polarity and state-change interpretation layer.
2. Refactor causal verification around semantic agent-relation-object comparison.
3. Apply entity-subject constraints before accepting retrieved relation evidence.
4. Improve context-reference resolution without making all responses depend on question text.
5. Improve semantic history and variant routing.
6. Tighten structural claim extraction and avoid splitting proposition qualifiers.
7. Re-run existing development regressions and blind-v3/v4 only as post-hoc regression sets.

Blind v4 must never be described as fresh or blind again after these development changes.

A future generalization estimate requires a newly frozen implementation and a new unseen benchmark.