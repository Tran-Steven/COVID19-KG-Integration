# Semantic Fallback Ablation

This comparison evaluates a historical deterministic-only verification checkpoint and the final semantic-fallback system on the same frozen blind-v3 benchmark.

The comparison is retrospective. The blind-v3 benchmark had already been executed and inspected before the historical deterministic configuration was evaluated. Therefore, the deterministic run is not reported as a new blind evaluation.

The configuration difference should be interpreted as an ablation of the integrated semantic-fallback package, not as an isolated test of the embedding model alone. The final configuration includes embedding-based intent fallbacks together with proposition-level semantic handling introduced during semantic integration.

## Overall Results

| Metric | Deterministic-only | Semantic fallback | Difference |
| --- | ---: | ---: | ---: |
| Case accuracy | 53.0% | 79.0% | +26.0 pp |
| Status accuracy | 60.2% | 82.4% | +22.2 pp |
| Route accuracy | 84.3% | 94.4% | +10.2 pp |
| Claim extraction F1 | 94.7% | 94.7% | 0.0 pp |
| Response summary | 65.0% | 85.0% | +20.0 pp |
| Grounding score | 60.0% | 85.0% | +25.0 pp |
| Coverage ratio | 75.0% | 95.0% | +20.0 pp |

## Paired Case Comparison

- Correct under both configurations: 52
- Correct only with semantic fallbacks: 27
- Correct only with deterministic-only configuration: 1
- Incorrect under both configurations: 20

An exact two-sided McNemar test was applied to the discordant per-case outcomes. The test used 28 discordant cases and produced `p = 2.1606684e-07`.

This paired test quantifies the difference between the two configurations on this specific benchmark. It does not remove the limitations associated with the benchmark being internally authored.

## Category Results

| Category | Deterministic-only | Semantic fallback | Difference |
| --- | ---: | ---: | ---: |
| multi_claim | 16.7% | 83.3% | +66.7 pp |
| origin | 25.0% | 91.7% | +66.7 pp |
| treatment | 0.0% | 62.5% | +62.5 pp |
| cause | 12.5% | 62.5% | +50.0 pp |
| claim_extraction | 50.0% | 100.0% | +50.0 pp |
| long_covid | 50.0% | 100.0% | +50.0 pp |
| current_risk | 83.3% | 100.0% | +16.7 pp |
| history | 75.0% | 75.0% | 0.0 pp |
| origin_uncertainty | 100.0% | 100.0% | 0.0 pp |
| question_context | 50.0% | 50.0% | 0.0 pp |
| scope | 75.0% | 75.0% | 0.0 pp |
| time_sensitive | 100.0% | 100.0% | 0.0 pp |
| transmission | 80.0% | 80.0% | 0.0 pp |
| variants | 62.5% | 62.5% | 0.0 pp |
| vaccination | 90.0% | 80.0% | -10.0 pp |

## Interpretation

The semantic-fallback configuration improves overall case accuracy while leaving factual claim extraction F1 unchanged. This indicates that the principal gain occurs after claim extraction, particularly in semantic routing and verification-status assignment.

The largest category-level gains identify domains in which deterministic lexical normalization was insufficient. These include origin propositions, treatment semantics, biological-cause formulations, long-COVID relations, and multi-claim response verification.

The comparison also records any cases that were correct under the deterministic checkpoint but incorrect under the semantic system. Such cases are retained as evidence that semantic generalization can introduce scope or overgeneralization errors even when aggregate accuracy improves.

## Reproducibility

- Deterministic checkpoint: `0a2f07cfe2a5b599c5a3662eb61967a272720c45`
- Semantic integration checkpoint: `38a254667e92aa8bbffe9f0220b4d42f057240a4`
- Frozen blind-v3 benchmark commit: `f51534ee57ba21b7a08fbe2c4e176b1c8b13f7e4`

Both configurations were evaluated against the same benchmark labels and the same Neo4j knowledge-graph contents.
