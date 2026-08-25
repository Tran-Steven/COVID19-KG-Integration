# Enhancing COVID-19 Information Verification in Large Language Models via Knowledge Graphs

<p align="center">
  <img src="images/icon-128.png" alt="COVID-19 KG Integration logo" width="80">
</p>

A provenance-aware knowledge-graph system for grounding and verifying factual COVID-19 information in Large Language Model responses.

Developed through the **Neuro-Symbolic Computing Research Lab** at the University of Georgia.

## Quick Start

Requirements:

- Docker Desktop
- Python 3.10+
- Internet connection on the first run

```bash
git clone https://github.com/Tran-Steven/COVID19-KG-Integration.git
cd COVID19-KG-Integration
./run.sh
```

The first run builds the knowledge graph, imports it into Neo4j, and starts the verification API.

Later runs reuse the generated graph.

When ready:

```text
API:      http://localhost:8000
API Docs: http://localhost:8000/docs
Neo4j:    http://localhost:7474
```

Stop the system with:

```bash
./run.sh --stop
```

Force a fresh data rebuild with:

```bash
./run.sh --refresh-data
```

## Overview

The system integrates evidence from:

- World Health Organization
- ChEMBL
- Monarch Initiative

LLM responses are decomposed into factual claims and checked against the knowledge graph.

Each claim receives one of four verification outcomes:

- `SUPPORTED`
- `CONTRADICTED`
- `INSUFFICIENT_EVIDENCE`
- `NOT_VERIFIABLE_WITH_CURRENT_KG`

The system uses deterministic semantic interpretation first, followed by embedding-based semantic fallbacks when necessary.

## Architecture

```text
LLM Response
     |
     v
Claim Extraction
     |
     v
Semantic Interpretation
     |
     v
Entity / Concept Linking
     |
     v
Evidence Retrieval
     |
     v
Claim Verification
     |
     v
Confidence + Response Summary
```

The merged COVID-19 graph contains **742 nodes and 934 edges**, with source provenance preserved during retrieval.

## Evaluation

The final frozen 100-case holdout produced:

| Metric | Result |
| --- | ---: |
| Case accuracy | **79.0%** |
| Verification-status accuracy | **82.4%** |
| Evidence-route accuracy | **94.4%** |
| Claim extraction F1 | **94.7%** |

A retrospective paired ablation on the same benchmark compared the historical deterministic system with the final semantic-verification system:

```text
53.0% -> 79.0% case accuracy
```

The evaluation benchmarks were internally authored and are not independent third-party evaluations.

## Browser Extension

After running `./run.sh`:

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Select **Load unpacked**
4. Select this repository

The extension integrates knowledge-graph grounding with ChatGPT.

## Documentation

More detailed project documentation:

- [System Architecture](docs/architecture.md)
- [Knowledge Graph Construction](docs/knowledge-graph.md)
- [Verification Pipeline](docs/verification.md)
- [Evaluation and Results](docs/evaluation.md)
- [Reproducibility](docs/reproducibility.md)

Additional research notes are available on the project Notion page.

## Authors

Steven Tran  

**Neuro-Symbolic Computing Research Lab**  
School of Computing  
University of Georgia  
Athens, Georgia 30602-7404, USA

## Disclaimer

This project is a research prototype and is not intended for clinical decision-making.