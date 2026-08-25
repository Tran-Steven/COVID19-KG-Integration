# Enhancing COVID-19 Information Verification in Large Language Models via Knowledge Graphs

<p align="center">
  <img src="images/icon-128.png" alt="COVID-19 KG Integration logo" width="80">
</p>

A provenance-aware knowledge-graph system for grounding and verifying factual COVID-19 information in Large Language Model responses.

This project was developed through the Neuro-Symbolic Computing Research Lab at the University of Georgia.

## Authors

- Steven Tran
- Khoa Le
- Tushar Mishra
- Owen Na
- I. Budak Arpinar

**Neuro-Symbolic Computing Research Lab**  
School of Computing  
University of Georgia  
Athens, Georgia 30602-7404, USA

## Project Overview

Large Language Models can generate fluent answers while still producing unsupported, outdated, or incorrect factual claims. This project investigates whether a provenance-aware COVID-19 knowledge graph can provide structured external evidence for verifying those claims.

The system integrates biomedical and public-health evidence from:

- World Health Organization
- ChEMBL
- Monarch Initiative

LLM responses can be decomposed into individual factual claims. Each claim is interpreted, routed to an appropriate evidence pathway, checked against the knowledge graph, and assigned one of four verification outcomes:

- `SUPPORTED`
- `CONTRADICTED`
- `INSUFFICIENT_EVIDENCE`
- `NOT_VERIFIABLE_WITH_CURRENT_KG`

The system intentionally distinguishes missing evidence from contradictory evidence. A claim is not considered false merely because the current graph does not contain evidence supporting it.

## System Architecture

The verification pipeline is:

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

Deterministic semantic rules are attempted first. When deterministic interpretation is insufficient, the final system uses embedding-based semantic fallbacks and constrained reranking.

The semantic matcher uses:

- `BAAI/bge-small-en-v1.5`
- `Xenova/ms-marco-MiniLM-L-6-v2`

The semantic layer is especially important for distinguishing propositions involving uncertainty, evidentiary support, treatment semantics, biological causation, and SARS-CoV-2 origin hypotheses.

## Knowledge Graph

### Monarch Initiative

The Monarch Initiative provides biomedical entities and general disease relationships.

The project downloads the Monarch Knowledge Graph and extracts a COVID-19-centered subgraph around:

- `MONDO:0100096` — COVID-19
- `NCBITaxon:2697049` — SARS-CoV-2

The final one-hop Monarch slice contains:

- 16 nodes
- 22 edges

### ChEMBL

ChEMBL provides structured COVID-19 drug-indication information.

The generated COVID-19 slice contains:

- 552 nodes
- 590 edges

Indication records are mapped into distinct predicates:

- Phase 4 → `biolink:treats`
- Phase 1–3 → `biolink:in_clinical_trials_for`
- Unknown phase → `biolink:studied_to_treat`

This mapping preserves the distinction between treatment relations and clinical-trial evidence.

### World Health Organization

WHO evidence expands coverage beyond biomedical graph relations into areas including:

- COVID-19 disease basics
- Transmission
- Vaccination
- Long COVID
- SARS-CoV-2 variants
- Current global public-health risk
- COVID-19 history
- SARS-CoV-2 origin assessments

The final WHO graph contains:

- 178 nodes
- 322 edges
- 145 source-backed evidence statements

WHO source files and metadata retain provenance information such as source URL, source date, retrieval metadata, and SHA-256 digests.

### Merged Graph

The final merged COVID-19 knowledge graph contains:

- 742 nodes
- 934 edges

Shared canonical entities are merged while separate source assertions and provenance are preserved.

## SARS-CoV-2 Origin Representation

Origin evidence is not represented as a simple binary claim.

The WHO SAGO assessment is modeled using separate hypotheses and evidence states, including:

- Natural zoonotic spillover as the hypothesis best supported by the available scientific evidence
- A laboratory-related event as neither proven nor ruled out with the available information
- No additional supporting evidence for a cold-chain introduction hypothesis
- No scientific evidence supporting deliberate laboratory manipulation over natural processes
- Overall SARS-CoV-2 origin remaining inconclusive pending additional information or scientific data

This representation preserves scientific uncertainty rather than flattening it into a binary conclusion.

## Claim Verification

For each interpreted factual claim, the verifier produces one of four statuses.

### `SUPPORTED`

The available knowledge-graph evidence supports the interpreted proposition.

### `CONTRADICTED`

The available evidence conflicts with the proposition expressed by the claim.

### `INSUFFICIENT_EVIDENCE`

The claim falls within a modeled evidence domain, but the current evidence is not sufficient to support or contradict the requested proposition.

### `NOT_VERIFIABLE_WITH_CURRENT_KG`

The requested proposition cannot be evaluated using the concepts and relationships represented by the current graph.

## Response Verification

The `/kg/verify-response` endpoint verifies LLM responses at the individual-claim level.

The response verifier:

1. Extracts factual claims from the response
2. Verifies each claim independently
3. Uses the original question as context when necessary
4. Preserves each claim's verification result
5. Produces an aggregate response summary

A response can therefore contain a mixture of supported, contradicted, insufficiently evidenced, and currently unverifiable claims.

The response grounding score is defined as:

```text
SUPPORTED factual claims / total extracted factual claims
```

The knowledge-graph coverage ratio is:

```text
claims receiving SUPPORTED, CONTRADICTED, or INSUFFICIENT_EVIDENCE
-----------------------------------------------------------------
                  total extracted factual claims
```

Neither value is interpreted as the probability that the entire response is correct.

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

The confidence score is explicitly uncalibrated.

It represents the strength of the evidence-grounding process, not the probability that a claim is true or that the verification decision is correct.

## Evaluation

The final development regression benchmark reached 100%, but development cases were repeatedly used during implementation and are not treated as a generalization estimate.

Fresh holdout evaluations were used throughout development:

| Evaluation | Case Accuracy | Status Accuracy | Route Accuracy |
| --- | ---: | ---: | ---: |
| Initial 60-case holdout | 41.7% | 47.0% | 65.2% |
| Fresh 80-case holdout | 70.0% | 74.7% | 82.8% |
| Blind holdout v2 | 71.0% | 75.7% | 94.6% |
| Blind holdout v3 | **79.0%** | **82.4%** | **94.4%** |

Blind holdout v3 contains 100 cases:

- 80 direct factual-claim cases
- 20 response-level cases

The benchmark was frozen before its first execution against the final semantic-verification implementation.

All evaluation benchmarks were internally authored and should not be interpreted as independent third-party evaluations.

## Semantic Verification Ablation

A retrospective paired ablation compared a historical deterministic-only checkpoint with the final semantic-verification system on the same frozen blind-v3 benchmark.

| Metric | Deterministic | Semantic | Difference |
| --- | ---: | ---: | ---: |
| Case accuracy | 53.0% | 79.0% | +26.0 pp |
| Status accuracy | 60.2% | 82.4% | +22.2 pp |
| Route accuracy | 84.3% | 94.4% | +10.2 pp |
| Claim extraction F1 | 94.7% | 94.7% | 0.0 pp |
| Response summary | 65.0% | 85.0% | +20.0 pp |
| Grounding score | 60.0% | 85.0% | +25.0 pp |
| Coverage ratio | 75.0% | 95.0% | +20.0 pp |

Paired outcomes:

- Correct under both configurations: 52
- Correct only with semantic verification: 27
- Correct only with deterministic verification: 1
- Incorrect under both configurations: 20

An exact two-sided McNemar test over the 28 discordant cases produced:

```text
p = 2.1606684 × 10^-7
```

Because the benchmark is internally authored, this statistical result should be interpreted as a within-benchmark comparison rather than evidence of population-wide performance.

The comparison is an ablation of the integrated semantic-verification package, not the embedding model alone.

## Remaining Error Patterns

The final blind-v3 evaluation contained 21 failed cases.

The primary failure categories were:

| Failure Type | Cases |
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

The final system therefore performs substantially better at identifying the correct evidence domain than at resolving every fine-grained natural-language proposition.

Current limitations are concentrated in areas such as:

- Negation
- Entity identity
- Quantifiers
- State changes
- Scope constraints
- Contextual references
- Logical entailment

## Repository Structure

```text
backend/
    app/
        augmentation/
        ingestion/
        interpretation/
        nlp/
        retrieval/
    import_kg.py

evaluation/
    benchmark definitions
    frozen result files
    error analyses
    system-evolution summaries
    ablation results
    paper drafts

resources/
    source-specific graph data
    merged COVID-19 graph

scripts/
    graph acquisition and construction
    source auditing
    regression checks
    end-to-end evaluation
    evaluation analysis

background.js
contentScript.js
manifest.json
popup/
docker-compose.yml
```

## Requirements

### Runtime

- Docker
- Docker Compose
- Neo4j 5
- Python 3

The backend container installs:

- FastAPI
- Uvicorn
- Neo4j Python driver
- Pydantic
- spaCy
- FastEmbed
- NumPy

### Data Construction

Install the additional data-processing dependencies:

```bash
python3 -m pip install -r requirements-data.txt
```

## Building the Knowledge Graph

### 1. Download Monarch

The full Monarch graph is large and is not stored directly in this repository.

```bash
python3 scripts/download_kg.py
```

This downloads and extracts the current Monarch KG into:

```text
resources/monarch-kg/
```

### 2. Extract the COVID-19 Monarch Subgraph

```bash
python3 scripts/extract_covid_subgraph.py
```

Output:

```text
resources/monarch-covid/
```

### 3. Build the ChEMBL COVID-19 Graph

```bash
python3 scripts/download_chembl_covid.py
```

Output:

```text
resources/chembl-covid/
```

### 4. Build WHO Historical Evidence

```bash
python3 scripts/build_who_covid_history.py
```

### 5. Build the WHO COVID-19 Graph

```bash
python3 scripts/build_who_covid_kg.py
```

Output:

```text
resources/who-covid-kg/
```

### 6. Merge the Graphs

```bash
python3 scripts/merge_covid_kg.py
```

Output:

```text
resources/covid-kg/
```

The merged directory contains the node and edge TSV files used by Neo4j.

## Running the System

Build and start Neo4j and the API:

```bash
docker compose up -d --build
```

Verify that the containers are running:

```bash
docker compose ps
```

Import the generated graph into Neo4j:

```bash
docker compose exec api \
  python import_kg.py \
  --nodes /data/covid-kg/nodes.tsv \
  --edges /data/covid-kg/edges.tsv \
  --clear
```

Verify API health:

```bash
curl -s http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## API

The backend is available by default at:

```text
http://localhost:8000
```

Interactive FastAPI documentation is available at:

```text
http://localhost:8000/docs
```

Major functionality includes:

- NLP and entity extraction
- Entity linking
- Semantic interpretation
- Graph retrieval
- WHO evidence retrieval
- Historical evidence retrieval
- Prompt grounding
- Prompt augmentation
- Response-level claim verification

## Browser Extension

The repository also contains a Chrome extension for integrating the knowledge graph with ChatGPT.

To load the extension:

1. Start the backend and Neo4j services.
2. Open `chrome://extensions`.
3. Enable **Developer mode**.
4. Select **Load unpacked**.
5. Select the root directory of this repository.

The extension can retrieve grounding context for ChatGPT queries and augment the current prompt with knowledge-graph evidence.

The response-level verification system is implemented in the backend and evaluated through the API. The current extension should not be interpreted as a complete user-facing implementation of every verification feature.

## Reproducing the Final Evaluation

Start the API and ensure the merged graph has been imported.

Then run:

```bash
python3 scripts/evaluate_end_to_end_verification.py \
  --cases evaluation/end_to_end_verification_blind_v3_cases.json \
  --output /tmp/end_to_end_verification_blind_v3_reproduction.json
```

The preserved first-run blind-v3 result is stored separately in the repository.

A new execution is a reproduction of the benchmark and should not be described as a new blind evaluation.

Evaluation analysis can be regenerated with:

```bash
python3 scripts/analyze_verification_failures.py

python3 scripts/build_evaluation_summary.py
```

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

Historical deterministic checkpoint used for the retrospective ablation:

```text
0a2f07cfe2a5b599c5a3662eb61967a272720c45
```

## Research Notes

Additional project documentation and research notes are available on the project Notion page:

https://steven-tran.notion.site/Enhancing-COVID-19-Information-Verification-in-Large-Language-Models-via-Knowledge-Graphs-253089fcc6cf46009055aecd91f074bb

## Limitations

This project should not be interpreted as a clinical decision-support system.

The knowledge graph is intentionally incomplete, the verification benchmarks are internally authored, and the confidence score is not calibrated as a probability of factual correctness.

The system is a research prototype for investigating knowledge-graph grounding and factual verification of COVID-19 information in LLM responses.

## Acknowledgments

This research was conducted through the Neuro-Symbolic Computing Research Lab in the School of Computing at the University of Georgia.