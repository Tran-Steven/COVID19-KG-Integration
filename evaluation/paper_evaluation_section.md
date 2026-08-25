# Evaluation

## Evaluation Objectives

The evaluation examined whether the proposed knowledge-graph verification system could generalize beyond development examples when assessing factual COVID-19 claims. The system was evaluated on both individual claims and multi-claim responses, with particular attention to four components of the verification pipeline: factual claim extraction, semantic routing to the appropriate evidence source, verification-status assignment, and response-level aggregation.

The primary verification labels were `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, and `NOT_VERIFIABLE_WITH_CURRENT_KG`. These labels were designed to distinguish evidence-supported or evidence-conflicting claims from claims for which the available knowledge graph was either insufficient or outside the modeled scope. This distinction is important because failure to retrieve supporting evidence was not treated as equivalent to contradiction.

The evaluation also measured the system's evidence-grounding confidence score. This score summarizes properties of the verification process, including evidence coverage, provenance completeness, relation certainty, entity-link certainty, evidence agreement, source diversity, and recency. It is a heuristic measure of evidence grounding and is not interpreted as the probability that a claim is factually true.

## Evaluation Design

Evaluation was performed incrementally as the system architecture developed. Development and regression cases were used to verify expected behavior during implementation, while separate holdout sets were created to assess generalization.

The development benchmark ultimately contained 33 cases and reached 100% accuracy after iterative development. Because these cases were repeatedly used during implementation, this score is treated only as a regression result and not as an estimate of generalization.

Four separate holdout evaluations were used to examine system performance across major architectural stages. The benchmarks differed between stages and therefore do not constitute a paired comparison. Each should instead be interpreted as a measurement of system behavior at a particular stage of development.

The first holdout contained 60 cases and was evaluated before the targeted verification refinements developed from its observed failures. The system achieved 25 correct cases, or 41.7% case accuracy.

A subsequent 80-case holdout was evaluated after improvements to claim interpretation, historical COVID-19 verification, response handling, and treatment semantics. The system achieved 56 correct cases, corresponding to 70.0% case accuracy.

A third holdout, referred to as blind holdout v2, contained 100 cases and was evaluated after generalized deterministic semantic routing, origin qualifier handling, and response-extraction improvements. The system achieved 71 correct cases, corresponding to 71.0% case accuracy.

The final evaluation, blind holdout v3, was created after embedding-based semantic fallbacks and proposition-level origin matching were integrated into the system. It contained 100 cases, including 80 direct claim cases and 20 response-level cases. The implementation was frozen at commit `38a254667e92aa8bbffe9f0220b4d42f057240a4` before execution. The benchmark was separately committed before its first run, and an automated overlap check rejected exact atomic-claim matches with previous evaluation sets.

All holdout benchmarks were internally authored based on the intended capabilities of the system. They therefore provide evidence of generalization beyond development examples but should not be interpreted as independent third-party evaluations.

## Evaluation Metrics

Case accuracy was the primary metric. A direct-claim case was counted as correct only when both the expected verification route and expected verification status were correct. Response-level cases additionally required correct factual claim extraction, claim verification, question-context behavior, and response aggregation.

Additional metrics were calculated to identify which parts of the pipeline contributed to errors.

Status accuracy measured the proportion of individual factual claims assigned the expected verification status.

Route accuracy measured whether a claim was directed to the expected verification pathway, such as WHO semantic evidence, WHO historical evidence, or the general knowledge-graph relationship path.

Claim extraction was measured using precision, recall, and F1 score over factual claims extracted from response text.

For response-level evaluation, the system also measured question-context behavior, overall response status, grounding score, and knowledge-graph coverage ratio.

The grounding score was defined as the fraction of extracted factual claims receiving `SUPPORTED` status. It was not used as a probability of response correctness.

Wilson score intervals were calculated for overall case accuracy to show uncertainty associated with the finite benchmark sizes. Because the reported stages use different internally authored holdouts, differences between stages are not treated as paired statistical comparisons.

## System Evolution Results

| Evaluation stage | Cases | Case accuracy | Wilson 95% CI | Status accuracy | Route accuracy | Claim extraction F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial frozen holdout | 60 | 41.7% | 30.1%–54.3% | 47.0% | 65.2% | 91.4% |
| Fresh 80-case holdout | 80 | 70.0% | 59.2%–78.9% | 74.7% | 82.8% | 86.5% |
| Blind holdout v2 | 100 | 71.0% | 61.5%–79.0% | 75.7% | 94.6% | 100.0% |
| Blind holdout v3 | 100 | 79.0% | 70.0%–85.8% | 82.4% | 94.4% | 94.7% |

The initial holdout exposed a large discrepancy between development behavior and unseen performance. Although claim extraction was already relatively strong, with an F1 score of 91.4%, overall case accuracy was only 41.7%. Route accuracy was 65.2% and verification-status accuracy was 47.0%, indicating that claim interpretation and evidence selection were larger limitations than factual claim extraction.

After targeted verification improvements, the fresh 80-case holdout reached 70.0% case accuracy. Route accuracy increased to 82.8%, while status accuracy increased to 74.7%. This stage demonstrated that explicit treatment of historical evidence, query semantics, contextual claims, and treatment relations substantially improved the verification pipeline.

Blind holdout v2 produced 71.0% case accuracy. Route accuracy increased further to 94.6%, but status accuracy remained 75.7%. This result was important because it showed that the system was usually selecting the correct evidence pathway while still making incorrect verification decisions after retrieval. The remaining bottleneck therefore appeared to be semantic interpretation of the proposition being verified rather than broad evidence routing.

This observation motivated the addition of embedding-based semantic fallbacks and proposition-level semantic matching. On the independently frozen blind holdout v3, the resulting system achieved 79.0% case accuracy and 82.4% status accuracy while maintaining 94.4% route accuracy.

The increase from 71.0% on blind holdout v2 to 79.0% on blind holdout v3 is consistent with the hypothesis that semantic matching improved generalization beyond deterministic phrase normalization. However, because the two values were obtained on different internally authored holdout sets, the eight-percentage-point difference is reported as system-evolution evidence rather than as a paired or statistically significant improvement.

## Response-Level Results

| Evaluation stage | Question context | Response summary | Grounding score | Coverage ratio |
| --- | ---: | ---: | ---: | ---: |
| Initial frozen holdout | 66.7% | 58.3% | 58.3% | 50.0% |
| Fresh 80-case holdout | 73.7% | 66.7% | 58.3% | 66.7% |
| Blind holdout v2 | 96.8% | 85.0% | 85.0% | 100.0% |
| Blind holdout v3 | 89.3% | 85.0% | 85.0% | 95.0% |

Response-level behavior improved substantially over the course of development. In the initial holdout, only 58.3% of response-summary statuses were correct, and the expected grounding score was reproduced in 58.3% of response cases. By blind holdout v2, both measures reached 85.0%.

Blind holdout v3 maintained 85.0% accuracy for response-summary status and grounding score. Coverage-ratio accuracy was 95.0%. Question-context accuracy was 89.3%, indicating that contextual information from the user's original question was usually preserved correctly but remained an identifiable source of error.

These results support the use of claim-level verification rather than assigning a single verification result directly to an entire language-model response. A response may contain a mixture of supported, contradicted, insufficiently evidenced, and currently unverifiable claims, and the aggregation layer preserves those distinctions.

## Blind Holdout v3 Error Analysis

The final blind evaluation contained 21 failed cases. A deterministic post-hoc error analysis was performed after the first-run score had been preserved. This analysis did not alter benchmark labels or the reported 79.0% result.

| Primary failure class | Failed cases |
| --- | ---: |
| Negation or polarity | 4 |
| Proposition/entity mismatch | 3 |
| State-change polarity | 3 |
| Scope or domain overreach | 2 |
| Historical routing | 2 |
| Exclusivity or quantifier semantics | 1 |
| Treatment overclaim scope | 1 |
| Uncertainty entailment | 1 |
| Context-usage mismatch | 1 |
| Claim extraction | 1 |
| Contextual reference resolution | 1 |
| Certainty-overclaim semantics | 1 |

The most frequent remaining error type involved proposition polarity. For example, semantically negative claims such as a treatment having "no therapeutic use" or a vaccine offering "no protection" were sometimes interpreted as positive instances of the underlying relation because the evidence relation itself was correctly retrieved but the polarity of the proposition was not preserved.

A related problem appeared in variant-monitoring claims. Statements such as a lineage having been removed from monitoring or no longer being monitored were routed to the correct variant evidence but sometimes interpreted as positive monitoring claims. These failures suggest that state-transition semantics require more explicit representation than simple similarity to a monitoring relation.

Cause verification also exposed an entity-specific limitation. Claims assigning COVID-19 to an incorrect pathogen were sometimes treated as supported because the system correctly recognized the proposition as a COVID-19 causation claim but did not always preserve the claimed causal entity strongly enough during verification.

Scope errors occurred when semantically similar but unsupported concepts were mapped into an otherwise valid COVID-19 evidence domain. Examples included an influenza vaccine being interpreted through the COVID-19 vaccination pathway and a Bluetooth-related transmission claim being mapped into the transmission domain. These cases demonstrate the need to distinguish semantic similarity to a known relation from actual entity and domain compatibility.

Question-context failures included missed contextual references and pronoun-like statements whose interpretation depended on the user's preceding question. This remains particularly important for verifying natural language model responses, which frequently omit repeated entities after they have been established in prior context.

The final error distribution therefore suggests that broad evidence routing is no longer the dominant limitation. Remaining errors are more concentrated in fine-grained semantic phenomena including polarity, entity identity, state changes, quantifiers, scope constraints, and contextual reference resolution.

## Confidence Analysis

| Evaluation stage | Mean confidence when status correct | Mean confidence when status incorrect |
| --- | ---: | ---: |
| Initial frozen holdout | 0.816 | 0.484 |
| Fresh 80-case holdout | 0.797 | 0.529 |
| Blind holdout v2 | 0.857 | 0.697 |
| Blind holdout v3 | 0.877 | 0.835 |

The confidence score generally increased when the verification system had strong evidence coverage, provenance, entity linking, and relation matching. In earlier evaluations, correct verification decisions received substantially higher confidence than incorrect decisions.

On blind holdout v3, however, the difference narrowed considerably: the mean confidence was 0.877 for correct verification statuses and 0.835 for incorrect statuses. This indicates that the current confidence heuristic does not reliably detect many semantic verification failures. In particular, the system may retrieve authoritative and internally consistent evidence with high confidence while still misinterpreting the polarity or entity structure of the claim being compared against that evidence.

For this reason, the confidence score is presented only as an evidence-grounding measure. It is not empirically calibrated and is not interpreted as a probability of factual correctness or verification accuracy.

## Limitations of the Evaluation

The evaluation has several limitations.

First, the benchmarks were internally authored with knowledge of the target system capabilities. Although holdout cases were separated from development cases and later benchmarks were frozen before execution, they are not independent external evaluations.

Second, the benchmarks are relatively small. The final holdout contains 100 cases, which is sufficient to reveal broad failure patterns but not to establish production-level reliability across the full range of possible COVID-19 questions.

Third, benchmark stages differ in composition. The progression from 41.7% to 70.0%, 71.0%, and 79.0% documents system evolution across separately constructed holdouts rather than performance on one fixed test set. These values should therefore not be interpreted as a controlled paired ablation.

Fourth, the knowledge graph intentionally represents a constrained set of authoritative evidence. `INSUFFICIENT_EVIDENCE` and `NOT_VERIFIABLE_WITH_CURRENT_KG` are therefore expected outcomes for some claims rather than system failures.

Fifth, the current evaluation primarily measures whether system-generated verification decisions match manually assigned benchmark labels. It does not include an external user study or an independent expert evaluation of user trust, usability, or satisfaction.

Finally, the confidence score has not been calibrated against empirical verification accuracy. Its interpretation is limited to the strength and completeness of the evidence-grounding process.

## Evaluation Summary

The evaluation demonstrates that a knowledge-graph verification pipeline can provide structured evidence checks for factual COVID-19 statements generated or presented in natural language. Early results showed that high development accuracy did not translate directly to unseen performance. Progressive improvements to semantic routing, claim interpretation, provenance-aware retrieval, response decomposition, and proposition matching increased fresh-holdout case accuracy from 41.7% in the initial evaluation to 79.0% in the final blind evaluation.

The final system routes claims to the intended evidence pathway with approximately 94% accuracy, while verification-status accuracy reaches approximately 82%. The remaining errors are concentrated primarily in fine-grained semantic interpretation rather than evidence retrieval itself. These findings motivate future work on stronger entailment and contradiction modeling, entity-aware proposition comparison, contextual reference resolution, and calibrated confidence estimation.