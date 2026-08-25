# Enhancing COVID-19 Information Verification in Large Language Models via Knowledge Graphs

<p align="center">
  <img src="images/icon-128.png" alt="COVID-19 KG Integration logo" width="80">
</p>

A provenance-aware knowledge-graph system for grounding and verifying factual COVID-19 information in Large Language Model responses.

Developed through the **Neuro-Symbolic Computing Research Lab** at the University of Georgia.

## Quick Start

### Requirements

- Docker Desktop
- Python 3.10+
- Internet connection for the initial knowledge-graph build

Clone the repository and run:

```bash
git clone https://github.com/Tran-Steven/COVID19-KG-Integration.git
cd COVID19-KG-Integration
./run.sh
```

That's it.

The first run builds the knowledge graph, starts Neo4j, imports the graph, builds the API, and starts the verification backend.

Later runs reuse the generated knowledge graph and start much faster.

When setup finishes:

```text
API:        http://localhost:8000
API docs:   http://localhost:8000/docs
Neo4j:      http://localhost:7474
```

Verify the backend:

```bash
curl -s http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

### Stop the System

```bash
./run.sh --stop
```

### Rebuild the Knowledge Graph

To discard locally generated graph data and rebuild from the source datasets:

```bash
./run.sh --refresh-data
```

### Help

```bash
./run.sh --help
```

## Browser Extension

After running `./run.sh`:

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Select **Load unpacked**
4. Select the root `COVID19-KG-Integration` directory

The extension integrates knowledge-graph grounding with ChatGPT.

Chrome requires unpacked extensions to be loaded manually, so this is the only part of setup that is not performed by `./run.sh`.

## What `run.sh` Does

On a fresh installation, the launcher automatically:

1. Checks Docker and Python
2. Creates a local Python virtual environment
3. Installs data-processing dependencies
4. Downloads the Monarch Knowledge Graph
5. Extracts the COVID-19 Monarch subgraph
6. Builds the ChEMBL COVID-19 graph
7. Downloads and transforms the WHO COVID-19 timeline
8. Builds WHO historical evidence
9. Builds the unified WHO COVID-19 evidence graph
10. Merges all graph sources
11. Starts Neo4j
12. Imports the merged graph
13. Builds and starts the FastAPI backend
14. Waits until the API is healthy

Individual scripts remain available for reproducibility and development, but they are not required for normal setup.

## Project Overview

Large Language Models can produce fluent responses while still generating unsupported, outdated, or incorrect factual claims.

This project investigates whether a provenance-aware COVID-19 knowledge graph can provide structured external evidence for grounding and verifying those claims.

The system integrates information from:

- World Health Organization
- ChEMBL
- Monarch Initiative

Language-model responses are decomposed into individual factual claims. Each claim is semantically interpreted, routed to an appropriate evidence source, checked against the graph, and assigned a verification outcome.

## Verification Outcomes

### `SUPPORTED`

The available knowledge-graph evidence supports the interpreted proposition.

### `CONTRADICTED`

The available evidence conflicts with the proposition expressed by the claim.

### `INSUFFICIENT_EVIDENCE`

The claim falls within a modeled evidence domain, but the available evidence is not sufficient to support or contradict the proposition.

### `NOT_VERIFIABLE_WITH_CURRENT_KG`

The proposition cannot currently be evaluated using the concepts and relationships represented by the graph.

The system intentionally distinguishes missing evidence from contradictory evidence.

Absence of supporting evidence is not automatically treated as proof that a claim is false.

## System Architecture

```text
User Question / LLM Response
            |
            v
    Factual Claim Extraction
            |
            v
     Semantic Interpretation
            |
            v
   Entity and Concept Linking
            |
            v
      Evidence Routing
       /      |       \
      /       |        \
 WHO Facts  WHO History  General KG
      \       |        /
       \      |       /
            v
  Provenance-Aware Retrieval
            |
            v
   Proposition Verification
            |
            v
 Evidence-Grounding Confidence
            |
            v
   Response-Level Aggregation
```

Deterministic semantic interpretation is attempted first.

When deterministic rules cannot reliably resolve a claim, the final system uses embedding-based semantic fallbacks and constrained reranking.

Semantic models:

- `BAAI/bge-small-en-v1.5`
- `Xenova/ms-marco-MiniLM-L-6-v2`

## Knowledge Graph

### Monarch Initiative

The Monarch subgraph is centered on:

```text
MONDO:0100096
COVID-19

NCBITaxon:2697049
SARS-CoV-2
```

Final extracted slice:

```text
16 nodes
22 edges
```

### ChEMBL

The ChEMBL COVID-19 graph contains:

```text
552 nodes
590 edges
```

Drug-indication records are represented using separate relations:

```text
Phase 4       -> biolink:treats
Phase 1-3     -> biolink:in_clinical_trials_for
Unknown phase -> biolink:studied_to_treat
```

This preserves the distinction between treatment relations and clinical-trial evidence.

### World Health Organization

The WHO evidence graph covers areas including:

- COVID-19 disease basics
- Transmission
- Vaccination
- Long COVID
- SARS-CoV-2 variants
- Current global public-health risk
- COVID-19 history
- SARS-CoV-2 origin assessments

Final WHO graph:

```text
178 nodes
322 edges
145 source-backed evidence statements
```

### Merged Graph

The final merged graph contains:

```text
742 nodes
934 edges
```

Assertions retain source and provenance information during retrieval.

## SARS-CoV-2 Origin Evidence

Origin evidence is represented as scientific assessments rather than a binary origin label.

The graph preserves separate conclusions including:

- Natural zoonotic spillover is the hypothesis best supported by the available scientific evidence
- A laboratory-related event cannot currently be proven or ruled out
- No additional evidence supports a cold-chain introduction hypothesis
- No scientific evidence supports deliberate laboratory manipulation over natural processes
- The overall origin remains inconclusive pending additional information or scientific data

This allows the verifier to preserve uncertainty rather than converting evolving scientific assessments into unsupported binary claims.

## Response Verification

The backend exposes response-level verification through:

```text
POST /kg/verify-response
```

A response is decomposed into factual claims and each claim is independently verified.

This allows one response to contain a mixture of:

```text
SUPPORTED
CONTRADICTED
INSUFFICIENT_EVIDENCE
NOT_VERIFIABLE_WITH_CURRENT_KG
```

The original user question may also be used as context when a response contains references such as:

```text
it
that condition
this treatment
```

## Grounding Score

The response grounding score is:

```text
SUPPORTED factual claims
------------------------
total factual claims
```

The knowledge-graph coverage ratio is:

```text
SUPPORTED + CONTRADICTED + INSUFFICIENT_EVIDENCE claims
-------------------------------------------------------
                  total factual claims
```

These values are not probabilities that the response is correct.

## Evidence-Grounding Confidence

Each verification result includes a heuristic evidence-grounding confidence score.

The score combines:

| Component | Weight |
| --- | ---: |
| Evidence coverage | 0.20 |
| Provenance completeness | 0.15 |
| Relation certainty | 0.15 |
| Entity-link certainty | 0.15 |
| Evidence agreement | 0.15 |
| Source diversity | 0.15 |
| Recency | 0.05 |

The confidence score is explicitly **uncalibrated**.

It measures characteristics of the evidence-grounding process rather than the probability that a factual claim is true.

## Evaluation

The final system was evaluated using frozen holdout benchmarks separate from the development regression cases.

| Evaluation | Case Accuracy | Status Accuracy | Route Accuracy |
| --- | ---: | ---: | ---: |
| Initial 60-case holdout | 41.7% | 47.0% | 65.2% |
| Fresh 80-case holdout | 70.0% | 74.7% | 82.8% |
| Blind holdout v2 | 71.0% | 75.7% | 94.6% |
| Blind holdout v3 | **79.0%** | **82.4%** | **94.4%** |

The final blind-v3 benchmark contains:

```text
100 total cases
80 direct claim cases
20 response-level cases
```

The benchmark was frozen before its first execution against the final semantic-verification implementation.

The benchmarks were internally authored and are not independent third-party evaluations.

## Semantic Verification Ablation

A retrospective paired comparison evaluated a historical deterministic configuration and the semantic-verification configuration on the same frozen 100-case benchmark.

| Metric | Deterministic | Semantic | Difference |
| --- | ---: | ---: | ---: |
| Case accuracy | 53.0% | 79.0% | +26.0 pp |
| Status accuracy | 60.2% | 82.4% | +22.2 pp |
| Route accuracy | 84.3% | 94.4% | +10.2 pp |
| Claim extraction F1 | 94.7% | 94.7% | 0.0 pp |
| Response summary | 65.0% | 85.0% | +20.0 pp |
| Grounding score | 60.0% | 85.0% | +25.0 pp |
| Coverage ratio | 75.0% | 95.0% | +20.0 pp |

Paired case outcomes:

```text
Correct under both:             52
Correct only with semantic:     27
Correct only with deterministic: 1
Incorrect under both:           20
```

An exact two-sided McNemar test over the 28 discordant cases produced:

```text
p = 2.1606684 x 10^-7
```

The comparison measures the integrated semantic-verification package rather than the embedding model alone.

## Remaining Error Patterns

Blind-v3 contained 21 failed cases.

The largest remaining error groups were:

| Error Type | Cases |
| --- | ---: |
| Negation or polarity | 4 |
| Proposition/entity mismatch | 3 |
| State-change polarity | 3 |
| Scope or domain overreach | 2 |
| Historical routing | 2 |

Remaining limitations are concentrated in fine-grained semantic phenomena such as:

- Negation
- Entity identity
- Quantifiers
- State changes
- Scope constraints
- Contextual references
- Logical entailment

## API

After running:

```bash
./run.sh
```

FastAPI documentation is available at:

```text
http://localhost:8000/docs
```

Major backend functionality includes:

- Factual claim extraction
- Entity extraction and linking
- Relation interpretation
- Semantic interpretation
- WHO evidence retrieval
- Historical evidence retrieval
- General graph retrieval
- Prompt grounding
- Prompt augmentation
- Response-level verification
- Evidence-grounding confidence

## Manual Data Pipeline

Normal users should use:

```bash
./run.sh
```

The individual commands below are provided for research reproducibility.

### Monarch

```bash
python3 scripts/download_kg.py
python3 scripts/extract_covid_subgraph.py
```

### ChEMBL

```bash
python3 scripts/download_chembl_covid.py
```

### WHO Timeline and History

```bash
python3 scripts/download_who_covid_timeline.py
python3 scripts/transform_who_covid_timeline.py
python3 scripts/build_who_covid_history.py
```

### WHO Evidence Graph

```bash
python3 scripts/build_who_covid_kg.py
```

### Merge

```bash
python3 scripts/merge_covid_kg.py
```

### Neo4j Import

```bash
docker compose run --rm api \
  python import_kg.py \
  --nodes /data/covid-kg/nodes.tsv \
  --edges /data/covid-kg/edges.tsv \
  --clear
```

## Reproducing the Final Evaluation

With the API running:

```bash
python3 scripts/evaluate_end_to_end_verification.py \
  --cases evaluation/end_to_end_verification_blind_v3_cases.json \
  --output /tmp/end_to_end_verification_blind_v3_reproduction.json
```

The preserved result in the repository is the original frozen first-run result.

Any later execution should be described as a reproduction rather than a new blind evaluation.

## Reproducibility Checkpoints

Final semantic-verification implementation:

```text
38a254667e92aa8bbffe9f0220b4d42f057240a4
```

Frozen blind-v3 benchmark:

```text
f51534ee57ba21b7a08fbe2c4e176b1c8b13f7e4
```

Blind-v3 benchmark SHA-256:

```text
b2e9b2e93099cf34ad683e451520bcfb531ed84c8a5e4a7f17179aa785a40884
```

Historical deterministic ablation checkpoint:

```text
0a2f07cfe2a5b599c5a3662eb61967a272720c45
```

## Repository Structure

```text
backend/
    FastAPI verification backend

evaluation/
    benchmarks, results, analyses, and paper drafts

resources/
    source and generated knowledge-graph data

scripts/
    data construction, validation, and evaluation scripts

popup/
    browser-extension interface

run.sh
    one-command setup and launcher
```

## Research Notes

Additional research notes are available on the project Notion page:

https://steven-tran.notion.site/Enhancing-COVID-19-Information-Verification-in-Large-Language-Models-via-Knowledge-Graphs-253089fcc6cf46009055aecd91f074bb

## Authors

Steven Tran  
Khoa Le  
Tushar Mishra  
Owen Na  
I. Budak Arpinar

**Neuro-Symbolic Computing Research Lab**  
School of Computing  
University of Georgia  
Athens, Georgia 30602-7404, USA

## Limitations

This project is a research prototype and should not be interpreted as a clinical decision-support system.

The knowledge graph is intentionally incomplete, evaluation benchmarks are internally authored, and evidence-grounding confidence is not calibrated as a probability of factual correctness.