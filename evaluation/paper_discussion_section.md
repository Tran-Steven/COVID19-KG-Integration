# Discussion

## Overview

The results demonstrate both the potential and the limitations of using a provenance-aware knowledge graph to verify factual COVID-19 statements associated with large language model responses.

The project began with the assumption that factual reliability could be improved by grounding language-model output against trusted structured evidence. The completed system supports this objective, but the evaluation also shows that evidence retrieval alone is not sufficient. A verifier must correctly interpret the proposition expressed by a claim before authoritative evidence can be used meaningfully.

This distinction became increasingly clear across the evaluation stages.

The initial frozen holdout achieved only 41.7% case accuracy despite substantially stronger development-set performance. Later architectural improvements raised performance to 70.0% on a separate 80-case holdout and 71.0% on blind holdout v2. By that stage, route accuracy had reached 94.6%, while verification-status accuracy remained 75.7%.

The difference between these metrics suggested that the system was usually reaching the appropriate evidence domain but was still incorrectly interpreting the relationship between the natural-language proposition and the retrieved evidence.

The final architecture addressed this problem by supplementing deterministic interpretation with embedding-based semantic fallbacks and proposition-level semantic matching. On the separately frozen blind-v3 benchmark, the system achieved 79.0% case accuracy, 82.4% status accuracy, and 94.4% route accuracy.

These results indicate that the principal remaining challenge is no longer identifying the broad evidence domain. Instead, failures are increasingly concentrated in fine-grained semantic interpretation.

## Contribution of Semantic Verification

A retrospective paired ablation was performed to examine the contribution of the semantic-fallback architecture more directly.

The historical deterministic checkpoint and the final semantic-fallback configuration were evaluated against the same 100-case blind-v3 benchmark.

The deterministic configuration achieved 53.0% case accuracy, while the semantic configuration achieved 79.0%, corresponding to an absolute increase of 26.0 percentage points.

Status accuracy increased from 60.2% to 82.4%, while route accuracy increased from 84.3% to 94.4%.

Claim-extraction F1 remained exactly 94.7% in both configurations. This result is particularly important because it indicates that the observed improvement was not caused by a change in which claims were extracted from responses. The primary gains instead occurred during semantic interpretation, evidence routing, and verification-status assignment.

At the case level, 52 cases were correct under both configurations. Twenty-seven cases were incorrect under the deterministic system but correct under the semantic system. Only one case showed the opposite pattern, while 20 cases remained incorrect under both configurations.

An exact two-sided McNemar test over the 28 discordant cases produced a p-value of approximately `2.16 × 10^-7`.

Within this benchmark, the paired result provides strong evidence that the integrated semantic-fallback configuration performs differently from and substantially better than the deterministic checkpoint.

This statistical result should nevertheless be interpreted narrowly. The benchmark was internally authored and does not represent an independently sampled population of COVID-19 claims. The McNemar test therefore quantifies the configuration difference on this specific paired benchmark rather than establishing a population-wide estimate of superiority.

The comparison should also be understood as an ablation of the integrated semantic-verification package rather than an isolated evaluation of one embedding model. The final system includes embedding-based intent matching, constrained reranking, and proposition-level semantic handling, particularly for SARS-CoV-2 origin claims.

## Domain-Specific Effects

The paired ablation reveals that the semantic architecture was most beneficial in areas requiring substantial linguistic variation or proposition interpretation.

Origin accuracy increased from 25.0% to 91.7%. This was the largest scientifically important improvement because origin claims frequently contain qualifiers such as uncertainty, evidentiary support, exclusion, certainty, and comparison between hypotheses.

A simple keyword match for terms such as "lab," "zoonotic," or "origin" is insufficient to distinguish statements such as:

- a laboratory-associated origin remains possible but unproven;
- a laboratory-associated origin has been ruled out;
- evidence supports a laboratory-associated origin;
- no evidence supports a laboratory-associated origin;
- the exact origin remains unresolved; and
- the exact origin has been conclusively established.

Representing these as distinct propositions allowed the final system to preserve the uncertainty expressed in the underlying WHO SAGO evidence.

Treatment accuracy increased from 0.0% in the deterministic checkpoint to 62.5% in the semantic configuration.

This improvement reflects the difficulty of recognizing varied natural-language treatment formulations while maintaining the distinction between treatment evidence, clinical-trial evidence, and claims of universal efficacy.

Cause accuracy increased from 12.5% to 62.5%, while long-COVID accuracy increased from 50.0% to 100.0%.

Multi-claim response accuracy increased from 16.7% to 83.3%. This improvement is important for the intended LLM-verification use case because generated responses commonly contain several factual assertions rather than one isolated proposition.

The semantic architecture did not improve every domain. History, transmission, variants, question context, scope, and time-sensitive categories remained unchanged in case-level accuracy in the paired comparison.

Vaccination accuracy decreased from 90.0% to 80.0%. The single deterministic-only win involved the statement that a flu vaccine protects against severe COVID-19. The semantic system incorrectly generalized the claim into the modeled COVID-19 vaccination relation.

This failure demonstrates a key tradeoff introduced by semantic similarity. Greater tolerance for linguistic variation improves recall but can also cause conceptually related yet distinct entities to be mapped to the same evidence relation.

## Remaining Error Patterns

The blind-v3 error analysis identified 21 failed cases.

The most common remaining failure type was negation or proposition polarity. Four cases involved claims whose primary semantic relation was recognized correctly but whose negative meaning was not preserved.

For example, a statement that a treatment has "no therapeutic use" can be lexically and semantically similar to a statement that the treatment is "used therapeutically." If verification operates primarily on relation similarity, both claims may retrieve the same evidence even though they express opposite propositions.

Three failures involved proposition/entity mismatches in COVID-19 causation. In these cases, the system recognized that the claim concerned the etiologic agent of COVID-19 but did not sufficiently preserve the identity of the claimed pathogen.

This distinction is essential. Recognizing that a sentence expresses a `causes` relation is not enough; the verifier must compare the claimed subject and object against the subject and object represented by the evidence.

Three additional failures involved state-change polarity for SARS-CoV-2 variants. Statements that a variant "has been removed," is "no longer monitored," or "has left" a monitoring list were sometimes interpreted as positive instances of the `variant_under_monitoring` relation.

These errors indicate that state transitions require representation beyond static semantic similarity.

Other failures involved scope or domain overreach, historical routing, exclusivity and quantifier semantics, treatment overclaims, origin uncertainty entailment, claim extraction, contextual reference resolution, and certainty overclaims.

The distribution suggests that future improvements should focus less on expanding the number of broad intent rules and more on structured proposition comparison.

## Knowledge Graph Coverage

The system intentionally distinguishes between evidence that contradicts a claim and absence of sufficient evidence.

This design is one of the central differences between the proposed verifier and a simple knowledge-graph lookup system.

`SUPPORTED` indicates that retrieved evidence supports the interpreted proposition.

`CONTRADICTED` indicates that the evidence conflicts with the interpreted proposition.

`INSUFFICIENT_EVIDENCE` indicates that the proposition falls within a modeled evidence domain, but the graph does not contain sufficient information to resolve it.

`NOT_VERIFIABLE_WITH_CURRENT_KG` indicates that the requested proposition lies outside the relations or concepts currently represented by the graph.

The last two statuses are important because the graph is deliberately incomplete.

For example, WHO evidence in the final graph explicitly models protection from severe disease, hospitalization, and death for COVID-19 vaccination. It does not represent a universal claim that vaccination completely prevents infection.

The system therefore should not infer that such a universal infection-prevention statement is false solely because a corresponding graph edge is absent.

This approach reduces the risk of transforming knowledge-graph incompleteness into artificial contradiction.

## Provenance and Scientific Uncertainty

The project also demonstrates the importance of preserving provenance and epistemic qualifiers during knowledge-graph construction.

The SARS-CoV-2 origin domain provides the clearest example.

A binary statement such as `SARS-CoV-2 man_made false` would discard much of the meaning contained in current scientific assessments.

Instead, the graph represents separate hypotheses and evidence assessments.

Natural zoonotic spillover is represented as the hypothesis best supported by currently available scientific evidence.

A laboratory-related event is represented as not proven but also not ruled out.

The deliberate-manipulation hypothesis is represented as lacking scientific evidence supporting it over natural processes.

The overall origin remains represented as inconclusive.

This structure allows the verifier to distinguish between evidence preference, absence of support, uncertainty, exclusion, and certainty.

The same provenance-oriented design is applied to historical events, current WHO risk assessments, variant-monitoring information, and ChEMBL treatment evidence.

## Confidence Score Interpretation

The confidence mechanism was designed to summarize the strength of the evidence-grounding process rather than estimate factual truth probability.

This distinction is strongly supported by the evaluation results.

On the initial frozen holdout, the mean confidence score was approximately 0.816 when the verification status was correct and 0.484 when it was incorrect.

On blind holdout v3, these values were approximately 0.877 and 0.835.

The much smaller separation in the final benchmark shows that strong evidence grounding does not necessarily imply a correct semantic comparison.

A system can retrieve authoritative, recent, well-provenanced, internally consistent evidence and still misunderstand what the input claim asserts.

For example, a negated claim may retrieve exactly the same authoritative relationship as its positive equivalent. Evidence coverage and provenance may therefore be high even though the final verification status is wrong.

The confidence score should consequently be interpreted as answering a question closer to:

"How strongly is this verification result grounded in the available evidence pipeline?"

rather than:

"What is the probability that this claim is true?"

The current confidence score is explicitly uncalibrated, and no probability interpretation is claimed.

## Implications for LLM Verification

The results support a claim-level rather than response-level approach to LLM factual verification.

Language-model responses frequently contain a mixture of factual statements, explanations, qualifications, and conversational text.

Assigning one binary label to an entire response would hide important distinctions between individual claims.

The implemented response verifier instead extracts individual factual statements, verifies each claim independently, and aggregates the results afterward.

This allows one response to contain simultaneously supported, contradicted, insufficiently evidenced, and currently unverifiable claims.

The response grounding score therefore reflects the proportion of extracted factual claims supported by the graph rather than claiming to represent the probability that the entire response is correct.

This structure also permits evidence and provenance to be presented at the individual-claim level, which is more compatible with transparent verification than a single opaque response-level score.

## Limitations

### Internally Authored Benchmarks

The largest evaluation limitation is that all benchmarks were internally authored.

The holdout sets were separated from development cases, and the later blind-v3 benchmark was frozen and committed before its first execution against the final implementation. Exact atomic-text overlap with previous benchmark cases was also checked before freezing.

These procedures reduce direct test contamination but do not provide independence from the system designers.

The benchmark authors understood the intended domain coverage, status taxonomy, and architecture.

Performance may therefore differ on claims written by independent annotators or sampled from real-world LLM responses.

Future evaluation should use independently constructed datasets and, ideally, multiple domain experts for label assignment.

### Benchmark Size

The final holdout contained 100 cases.

This size is sufficient to reveal major architectural differences and recurring error patterns but is small relative to the range of possible COVID-19 statements.

Several category-level percentages are based on only a small number of cases and should therefore be interpreted descriptively rather than as precise population estimates.

### Changing Holdouts Across Development

The project used multiple fresh holdouts over the course of development.

The progression from 41.7% to 70.0%, 71.0%, and 79.0% documents system evolution but does not represent repeated measurement on one unchanged test distribution.

For this reason, the cross-stage percentages are not treated as paired statistical comparisons.

The semantic-fallback ablation is different because both configurations were evaluated on the same blind-v3 cases. That paired comparison is suitable for a within-benchmark McNemar test, although the benchmark itself remains internally authored.

### Retrospective Ablation

The deterministic checkpoint was evaluated against blind-v3 only after blind-v3 had already been executed and inspected using the final semantic system.

The deterministic result is therefore retrospective and is not described as a blind holdout result.

It remains useful for measuring the behavior of two fixed historical configurations on the same cases, but it should not be confused with a prospective model-selection experiment.

### Semantic Package Rather Than Isolated Component

The historical-to-final comparison does not isolate the effect of the BGE embedding model alone.

The final semantic integration includes embedding-based intent fallbacks, constrained MiniLM reranking, and proposition-level semantic logic.

The 26-percentage-point difference should therefore be attributed to the integrated semantic-verification package rather than to one specific model component.

A stricter future ablation could evaluate rules only, rules plus embeddings, rules plus embeddings and reranking, and full proposition-level semantics as separate controlled configurations.

### Knowledge Graph Completeness

The graph represents selected authoritative COVID-19 evidence and is not intended to encode all biomedical knowledge.

Claims outside the represented relations may correctly receive `INSUFFICIENT_EVIDENCE` or `NOT_VERIFIABLE_WITH_CURRENT_KG`.

These outcomes reflect graph scope rather than necessarily indicating that the claim itself is unknowable or false.

### Source Interpretation

The graph construction process converts heterogeneous sources into normalized semantic relations.

Although this process is deterministic and provenance is retained, some mappings necessarily encode project-specific interpretation.

The ChEMBL phase mapping is one example. Phase 4 indications are represented using `biolink:treats` within this project's graph model, while lower phases are distinguished as clinical-trial or studied-to-treat evidence.

This mapping supports the project's verification logic but should not be interpreted as an independent clinical judgment that trial phase alone establishes treatment efficacy.

### Temporal Information

Some COVID-19 information changes over time.

Variant-monitoring status and global public-health risk assessments are explicitly treated as temporal evidence, but the current graph is not a fully versioned temporal knowledge graph.

A production system would require continuous source refresh, historical version tracking, and explicit validity intervals for changing assertions.

### Contextual Reference Resolution

Question-context accuracy remained imperfect.

Natural LLM responses frequently use pronouns, ellipsis, and expressions such as "it," "that condition," or "this treatment."

The current system performs contextual retry using the user's question but does not implement a general coreference-resolution model.

This limits verification of conversational responses whose propositions depend heavily on preceding discourse.

### Negation and Logical Composition

Negation, quantifiers, exclusivity, and state changes remain significant weaknesses.

A statement such as "X can transmit COVID-19" and "X cannot transmit COVID-19" may be semantically close in embedding space despite expressing opposite propositions.

Similarly, statements containing terms such as "only," "always," "never," "completely," or "no longer" may require logical interpretation beyond semantic similarity.

Future systems should represent claim polarity and logical qualifiers explicitly before evidence comparison.

### Confidence Calibration

The current confidence mechanism is heuristic and uncalibrated.

The final benchmark showed that incorrect statuses could still receive high evidence-grounding scores.

Future work should evaluate calibration methods using a larger independent verification set and should separate evidence quality from semantic decision confidence.

### No Independent User Study

The original research direction considered user confidence and satisfaction with verified LLM responses.

The completed evaluation does not include a formal user study.

No claims are therefore made about improved user trust, satisfaction, decision quality, or perceived credibility.

Evaluating these outcomes would require a separately designed human-subject study.

## Future Work

The most direct technical extension is structured proposition representation.

Instead of representing an interpreted claim primarily as a relation and collection of candidate entities, future versions could explicitly construct a proposition containing subject, predicate, object, polarity, modality, quantifiers, temporal qualifiers, and epistemic qualifiers.

Verification could then compare this normalized proposition against evidence assertions rather than relying on semantic similarity alone.

A second direction is natural-language inference.

A dedicated entailment model could evaluate whether retrieved source-backed evidence entails, contradicts, or is neutral toward the extracted claim. Such a model should remain constrained by retrieved provenance rather than replacing the knowledge graph with unconstrained model knowledge.

Entity-aware semantic matching would also address errors in which the correct relation is identified but the claimed entity is wrong.

Contextual verification could be improved through explicit coreference resolution and conversation-level entity tracking.

The knowledge graph itself could be extended with versioned temporal evidence, additional authoritative sources, and automated refresh pipelines.

Finally, confidence scoring should be decomposed into at least two distinct quantities: evidence quality and semantic decision confidence. These could then be calibrated independently on a larger externally authored benchmark.

## Discussion Summary

The completed system demonstrates that authoritative knowledge-graph evidence can support transparent verification of factual COVID-19 claims, but also shows that retrieval is only one part of the problem.

The strongest result is not simply the final 79.0% case accuracy. More informative is the separation between 94.4% route accuracy and 82.4% verification-status accuracy, together with the paired ablation showing a rise from 53.0% to 79.0% when the integrated semantic-verification package is added.

These findings indicate that a verification system can successfully locate relevant evidence while still misinterpreting the proposition being checked.

The project therefore supports a layered architecture in which provenance-aware retrieval is combined with explicit semantic verification, uncertainty-preserving status labels, claim-level response decomposition, and transparent confidence reporting.

At the same time, the remaining errors demonstrate that semantic similarity alone is not equivalent to logical entailment. Robust factual verification will require stronger modeling of entity identity, polarity, quantification, temporal state, and conversational context.