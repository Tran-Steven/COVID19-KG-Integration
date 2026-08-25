# Verification Evaluation Summary

This document summarizes the project's fresh holdout evaluations across major system-development stages. The benchmarks differ between rows, so changes in accuracy should be interpreted as system-evolution evidence rather than paired-test improvements.

All listed benchmarks were internally authored. They are useful for measuring generalization beyond development cases, but they are not independent third-party evaluations.

## Frozen holdout progression

| Evaluation | System stage | Case accuracy | Wilson 95% CI | Status accuracy | Route accuracy | Claim extraction F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Initial frozen holdout | Pre-targeted verification refinements | 25/60 (41.7%) | 30.1%–54.3% | 47.0% | 65.2% | 91.4% |
| Fresh 80-case holdout | After targeted claim, history, response, and treatment verification refinements | 56/80 (70.0%) | 59.2%–78.9% | 74.7% | 82.8% | 86.5% |
| Blind holdout v2 | After generalized deterministic routing, origin qualifiers, and response extraction | 71/100 (71.0%) | 61.5%–79.0% | 75.7% | 94.6% | 100.0% |
| Blind holdout v3 | After embedding-based semantic fallbacks and proposition-level origin matching | 79/100 (79.0%) | 70.0%–85.8% | 82.4% | 94.4% | 94.7% |

## Response-level metrics

| Evaluation | Question context | Response summary | Grounding score | Coverage ratio |
| --- | ---: | ---: | ---: | ---: |
| Initial frozen holdout | 66.7% | 58.3% | 58.3% | 50.0% |
| Fresh 80-case holdout | 73.7% | 66.7% | 58.3% | 66.7% |
| Blind holdout v2 | 96.8% | 85.0% | 85.0% | 100.0% |
| Blind holdout v3 | 89.3% | 85.0% | 85.0% | 95.0% |

## Confidence diagnostics

| Evaluation | Mean confidence when status correct | Mean confidence when status incorrect |
| --- | ---: | ---: |
| Initial frozen holdout | 0.816 | 0.484 |
| Fresh 80-case holdout | 0.797 | 0.529 |
| Blind holdout v2 | 0.857 | 0.697 |
| Blind holdout v3 | 0.877 | 0.835 |

Confidence is a heuristic evidence-grounding score. It is not calibrated and must not be interpreted as the probability that a claim is true or that a verification decision is correct.

## Interpretation

The first 60-case holdout produced **41.7% case accuracy**, exposing substantial generalization weaknesses despite strong development-set performance.

After targeted improvements to history, claim interpretation, response handling, and treatment semantics, a separate 80-case holdout reached **70.0%**.

A subsequent 100-case blind holdout after generalized deterministic routing, origin qualifier handling, and response-extraction improvements reached **71.0%**. The limited change on a fresh benchmark suggested that additional lexical and deterministic rules alone were not resolving the remaining semantic bottleneck.

After introducing embedding-based semantic fallbacks and proposition-level semantic matching, the fresh blind-v3 holdout reached **79.0% case accuracy**. Route accuracy remained high while status accuracy improved, supporting the interpretation that the remaining errors are increasingly associated with proposition polarity, entity matching, scope control, contextual references, and state-change semantics rather than broad domain routing.

The 71% and 79% values come from different internally authored holdouts, so the eight-percentage-point difference should not be presented as a paired or statistically significant improvement without additional evaluation.

## Methodological status

### Initial frozen holdout

- First recorded evaluation on the 60-case unseen holdout.
- Labels were defined before the first recorded run.
- The available development transcript does not independently establish that the benchmark file was committed to Git before execution.
- The benchmark was internally authored rather than independently constructed by an external evaluator.

### Fresh 80-case holdout

- Fresh 80-case holdout evaluated before the subsequent semantic-normalization and proposition-level development work.
- The benchmark was internally authored with knowledge of the target system capabilities.
- After this first run, its failures were observed and used to guide later development, so later executions of the same set would not be blind.

### Blind holdout v2

- Fresh 100-case frozen holdout evaluated after deterministic semantic-routing, origin-qualifier, and response-extraction improvements.
- The implementation was not tuned using the results before the reported first-run score.
- The benchmark was internally authored and is not an independent third-party evaluation.

### Blind holdout v3

- Fresh 100-case frozen holdout containing 80 direct claim cases and 20 response-level cases.
- The benchmark was committed before its first execution against the frozen semantic-fallback implementation.
- The benchmark generator rejected exact atomic-claim overlap with prior evaluation sets before freezing.
- The benchmark was internally authored and therefore does not constitute an independent third-party evaluation.
- Frozen implementation commit: `38a254667e92aa8bbffe9f0220b4d42f057240a4`
- Frozen benchmark commit: `f51534ee57ba21b7a08fbe2c4e176b1c8b13f7e4`
- Benchmark SHA-256: `b2e9b2e93099cf34ad683e451520bcfb531ed84c8a5e4a7f17179aa785a40884`

## Reporting guidance

The development regression benchmark may be reported separately as a development check, but its 100% score should not be used as a generalization estimate.

Any rerun of a holdout after its failures have been inspected or used to modify the system must be labeled post-analysis rather than blind or unseen.

No claim of statistical significance should be made from differences across these separately constructed holdouts without an appropriate statistical design.
