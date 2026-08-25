# Methods and System Architecture

## System Overview

The proposed system integrates a provenance-aware COVID-19 knowledge graph with a large language model interface to provide external grounding and post-generation factual verification. Rather than treating the knowledge graph as an oracle or assuming that absence of evidence implies falsity, the system retrieves evidence relevant to individual factual propositions and assigns one of four verification outcomes: `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, or `NOT_VERIFIABLE_WITH_CURRENT_KG`.

The architecture separates language interpretation from evidence retrieval and verification. This separation was designed to address a central problem encountered during development: recognizing that a sentence concerns COVID-19 is not sufficient to determine whether the proposition expressed by that sentence agrees with the retrieved evidence.

The final verification pipeline can be summarized as:

User question or language-model response → factual claim extraction → semantic interpretation → entity and concept resolution → evidence-path routing → provenance-aware knowledge-graph retrieval → proposition verification → evidence-grounding confidence → response-level aggregation.

The verification backend does not use a generative language model to decide whether a claim is supported or contradicted. Deterministic interpretation is attempted first, followed by embedding-based semantic fallbacks for cases that cannot be resolved reliably through lexical rules. The external large language model remains responsible for natural-language response generation, while the knowledge-graph system provides grounding evidence and verification metadata.

## Knowledge Graph Construction

### Source Selection

The final verification graph combines information from the Monarch Initiative, ChEMBL, and the World Health Organization (WHO). These sources serve different purposes within the architecture.

The Monarch Initiative provides biomedical entities and general disease relationships using Biolink-style identifiers and predicates. A COVID-19-centered subgraph was extracted around the canonical COVID-19 disease identifier `MONDO:0100096` and the SARS-CoV-2 taxon identifier `NCBITaxon:2697049`. In the project build used for the final system, the resulting Monarch slice contained 16 nodes and 22 edges. The local neighborhood primarily provided disease, phenotype, subclass, model, and related biomedical relationships rather than detailed treatment or public-health evidence.

ChEMBL was used to obtain structured COVID-19 drug-indication data. Records were queried from the ChEMBL API using `MONDO:0100096` as the COVID-19 indication identifier. Molecules were represented as `biolink:ChemicalEntity` nodes and linked to COVID-19 using predicates derived from the indication's maximum clinical phase.

The implemented mapping distinguishes three relation types. Phase 4 indications are mapped to `biolink:treats`; indications with a reported phase from 1 through 3 are mapped to `biolink:in_clinical_trials_for`; and indications without a usable phase value are mapped to `biolink:studied_to_treat`. This distinction prevents clinical-study evidence from automatically being converted into a treatment assertion. The mapping represents how the project interprets the ChEMBL indication record and is not intended to imply that phase status alone proves clinical efficacy.

The generated ChEMBL COVID-19 slice contained 552 nodes and 590 edges. Its treatment-related relations included 570 `biolink:in_clinical_trials_for` edges, 17 `biolink:treats` edges, and 3 `biolink:studied_to_treat` edges.

WHO material was added because biomedical graph sources alone did not provide sufficient coverage for many factual COVID-19 questions involving transmission, vaccination, variants, current public-health risk, long COVID, history, and SARS-CoV-2 origin assessments.

### WHO Evidence Graph

The WHO ingestion pipeline retrieves source documents directly and retains source metadata for reproducibility. The final WHO build incorporates seven principal contemporary sources: the WHO COVID-19 fact sheet, the WHO post-COVID-19 condition fact sheet, the WHO SARS-CoV-2 variant tracker, WHO COVID-19 vaccination policy material, the July 2026 WHO vaccine position paper, the August 2026 WHO global COVID-19 risk assessment, and the 2025 WHO Scientific Advisory Group for the Origins of Novel Pathogens (SAGO) assessment of SARS-CoV-2 origins.

Raw HTML and PDF material is retained during acquisition. Source metadata includes the source URL, source date, retrieval timestamp, downloaded file, SHA-256 digest, and related HTTP metadata where available. Expected-content checks are performed during ingestion so that a changed or incorrect source page does not silently produce an incomplete graph.

The WHO builder uses deterministic extraction logic rather than a language model to invent predicates from arbitrary text. Extracted assertions are assigned explicit semantic roles corresponding to the type of evidence represented by the source.

Examples include `causes`, `transmitted_via`, `transmission_risk_context`, `protects_against`, `variant_under_monitoring`, `global_public_health_risk_level`, `origin_hypothesis_assessment`, and `overall_origin_status`.

The WHO portion used in the final merged build contained 178 nodes, 322 edges, and 145 source-backed evidence statements.

### Origin Evidence Representation

SARS-CoV-2 origin evidence required a more explicit representation than a simple binary relationship such as `man_made = false`.

The SAGO assessment is represented using separate origin-hypothesis nodes and evidence assessments. Natural zoonotic spillover is represented as the hypothesis best supported by the available scientific evidence. An accidental laboratory-related event is represented as a hypothesis that cannot be ruled out or proven with the currently available information. The cold-chain introduction hypothesis is represented as lacking additional supporting evidence. Deliberate laboratory manipulation is represented as lacking scientific evidence supporting it over natural processes. The overall origin is separately represented as remaining inconclusive pending additional information or scientific data.

This structure preserves the epistemic status of the source rather than flattening uncertain scientific conclusions into unsupported binary claims.

### WHO Historical Evidence

Historical questions are represented using a dedicated event-oriented resource derived from the WHO COVID-19 timeline.

The history builder parsed dated timeline statements and retained event dates, source text, source URLs, and semantic relationships. Examples used by the verifier include the WHO China Country Office receiving the Wuhan pneumonia report on 31 December 2019 and WHO's characterization of COVID-19 as a pandemic on 11 March 2020.

Historical evidence is intentionally separated from broader questions about the biological origin or first laboratory identification of SARS-CoV-2. For example, the system can verify when the first WHO-linked Wuhan outbreak report occurred without claiming that this date represents the biological origin or first scientific identification of the virus.

### Source Audit

A large pre-existing KG-COVID-19 snapshot was also evaluated during source selection. The audited snapshot contained substantially more nodes and edges than the final project graph, but the relevant COVID-19 neighborhoods were dominated by broad relations such as `biolink:mentions` and generic molecular interactions. The snapshot also exhibited relation flattening and weaker coverage of newer treatment concepts relevant to the intended verification tasks.

For this reason, graph size alone was not used as the selection criterion. The final system instead prioritizes smaller evidence sets with interpretable semantics and preserved provenance.

## Graph Integration

The source-specific graph slices are merged by `scripts/merge_covid_kg.py`. The merge process normalizes node and edge fields, records the originating source dataset, deduplicates nodes that share canonical identifiers, and preserves distinct edge assertions.

The final merged build contained 742 nodes and 934 edges. The difference between the sum of the source node counts and the final node count results from canonical entities shared across sources, including COVID-19 and SARS-CoV-2.

The merged graph is loaded into Neo4j. Nodes are stored as `KGEntity` objects and graph assertions are stored as `KG_RELATION` relationships. Each relationship may contain the original predicate, semantic role, source dataset, primary knowledge source, references, source-specific attributes, and an edge identifier.

The use of an edge identifier is important because multiple assertions involving the same subject, predicate, and object may originate from different evidence records. These assertions are not collapsed into a single source-free fact.

## Evidence Normalization and Provenance

Retrieved graph assertions are converted into a common evidence representation before verification.

Each normalized fact contains a subject identifier, subject name and categories, a predicate, an object identifier, object name and categories, and an evidence object.

The evidence object preserves the graph edge identifier, primary knowledge source, provider information, source dataset, references, maximum clinical phase when relevant, and additional source-specific attributes.

WHO evidence may additionally contain source text, source date, source URL, source identifier, semantic role, and assessment information. Historical evidence similarly retains event identifiers, source text, source URLs, and dates.

This normalization allows verification and confidence scoring to operate over a consistent structure even though the underlying sources use different schemas.

## Factual Claim Extraction

Language-model responses may contain multiple factual statements mixed with conversational or non-factual text. The response-verification endpoint therefore operates at the claim level rather than assigning one verification result to the entire response.

The `ResponseClaimExtractor` uses spaCy sentence segmentation followed by deterministic filtering. Statements beginning with expressions such as uncertainty, apology, or conversational acknowledgements are excluded when they do not form independent factual claims. Questions are also excluded from response claim extraction because the response verifier evaluates assertions made by the language model rather than the user's question itself.

Multi-clause sentences may be divided at conjunctions such as "and" or "but" and at semicolons. A split is retained only when every resulting segment independently satisfies the factual-predicate test. Otherwise, the original sentence remains intact. This prevents arbitrary grammatical splitting from turning dependent fragments into separate factual propositions.

Each extracted claim retains its text, character offsets, extraction method, and claim index.

## Entity Extraction and Linking

Entity extraction combines knowledge-graph terminology with spaCy named-entity recognition.

At initialization, terms from Neo4j are loaded into a case-insensitive spaCy `PhraseMatcher`. The matcher includes canonical identifiers, entity names, and aliases. Overlapping spans are filtered so that the longest appropriate knowledge-graph entity is retained.

spaCy named entities that do not overlap an existing knowledge-graph term are also retained as candidate entities.

Extracted entities are subsequently linked to Neo4j candidates. Exact case-insensitive name matches and exact identifier matches receive the highest candidate score. Exact alias matches receive a slightly lower score, followed by containment-based matches.

Event and information-content nodes are excluded from the general entity-matching candidate set. These node types are used for specialized evidence retrieval but would otherwise introduce noisy terms into ordinary entity linking.

## Relation and Semantic Interpretation

The system uses a rule-first interpretation strategy.

Deterministic resolvers recognize well-defined semantic patterns for supported COVID-19 domains, including cause, transmission, vaccination, long COVID, current global risk, variants, origin, treatment, and historical questions.

This approach provides predictable behavior for unambiguous expressions and reduces dependence on statistical similarity when a claim can already be mapped reliably.

However, frozen holdout evaluation showed that deterministic lexical rules did not generalize adequately to many semantically equivalent formulations. The final architecture therefore adds embedding-based semantic fallbacks after deterministic interpretation fails.

### Semantic Verification Matcher

The semantic fallback uses `BAAI/bge-small-en-v1.5` through FastEmbed to embed the input claim and a collection of semantic prototype statements.

The principal semantic classes include biological cause, treatment, historical evidence, origin, SARS-CoV-2 variant monitoring, and modeled out-of-scope claims.

Cosine similarity between the input and each prototype is used to rank candidate classes. A high-confidence match requires a similarity score of at least 0.70 and sufficient separation from the second-ranked class. A lower-confidence fallback may be accepted at a score of at least 0.62 when the margin from competing classes is substantially larger.

Cases that remain ambiguous may be passed to the `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder reranker. The cross-encoder is used conservatively: a reranked result is accepted only when its winning class agrees with the class that had the highest embedding similarity. This prevents the reranker from independently changing the semantic class selected by the embedding model.

The resulting architecture is therefore a cascade rather than a single classifier:

deterministic rule → high-confidence embedding match → separated lower-confidence embedding fallback → constrained cross-encoder reranking → abstention.

### Origin Proposition Matching

Origin verification additionally uses semantic prototype classes for proposition-level qualifiers.

These classes represent overall inconclusiveness, laboratory-origin uncertainty, claims that a laboratory origin has been ruled out, negative evidentiary support, positive evidentiary support, certainty about a specific origin hypothesis, and certainty about the overall exact origin.

The origin qualifier resolver combines explicit lexical evidence with these semantic dimensions. This allows the system to distinguish, for example, between "a laboratory event remains possible but unproven" and "a laboratory event has been ruled out," even though both sentences refer to the same origin hypothesis.

The semantic classifier does not replace deterministic interpretation. Explicit lexical and compositional evidence is evaluated first, with semantic scores used as fallbacks when the proposition cannot otherwise be resolved.

## Verification Routing

For each claim, the backend attempts specialized evidence routes before falling back to generic graph retrieval.

Historical interpretation is attempted first. If a recognized historical intent is found, the dedicated history retriever is used.

If the claim is not historical, the WHO intent resolver evaluates whether it corresponds to one of the structured WHO evidence domains. Supported WHO routes include origin, variants, vaccine protection, long COVID, transmission, biological cause, and current global public-health risk.

If neither specialized route applies, the claim is handled by the general relationship retriever. This path performs entity linking, relation resolution, and graph lookup across the merged biomedical graph.

This ordering prevents semantically specialized WHO or historical assertions from being reduced to a generic graph-neighborhood query when stronger structured evidence is available.

## Evidence Retrieval

The WHO retriever converts a resolved semantic interpretation into specific semantic roles and, when possible, constrained subject and object identifiers. For example, vaccine queries may target the COVID-19 vaccination concept and one or more outcomes such as severe disease, hospitalization, or death.

The historical retriever uses event types and semantic event relationships rather than ordinary entity-neighborhood lookup.

The generic graph retriever resolves linked entities and candidate relationship types before querying Neo4j for matching incoming or outgoing assertions.

All retrieved graph assertions are passed through the common evidence normalizer before verification.

## Verification Status Resolution

The verifier produces four primary statuses.

`SUPPORTED` indicates that the current graph contains evidence that directly supports the interpreted proposition.

`CONTRADICTED` indicates that the retrieved evidence conflicts with the proposition expressed by the claim.

`INSUFFICIENT_EVIDENCE` indicates that the claim maps to a modeled verification domain but the available evidence is not sufficient to support or contradict the requested proposition.

`NOT_VERIFIABLE_WITH_CURRENT_KG` indicates that the claim cannot be evaluated using the relations and concepts represented by the current graph.

These distinctions are intentional. In particular, failure to retrieve supporting evidence does not automatically produce `CONTRADICTED`.

Verification logic is proposition-aware for domains where a simple relation lookup would be misleading. Cause verification considers the claimed causal proposition, vaccine verification distinguishes modeled outcomes from unsupported guarantees, transmission verification considers qualifiers and negation, treatment verification distinguishes treatment from clinical-study evidence, and origin verification preserves SAGO's uncertainty and hypothesis-specific assessments.

## Question Context

Language-model responses frequently omit entities that are explicit in the preceding user question. The response-verification endpoint therefore supports contextual retries.

Each extracted claim is first verified independently. If the direct result is `NOT_VERIFIABLE_WITH_CURRENT_KG` or `INSUFFICIENT_EVIDENCE`, the backend may retry interpretation using the original question as additional context.

The contextual text is used only when the claim itself does not already contain explicit COVID-19 context and the original question does. A contextual result is used only when it provides a stronger modeled verification route or resolves a previously unverifiable claim.

The final response includes a `usedQuestionContext` field for each claim so that contextual resolution remains observable during evaluation.

## Evidence-Grounding Confidence

Each verification result is accompanied by a heuristic evidence-grounding confidence score.

The score is a weighted combination of seven components:

- evidence coverage: 0.20
- provenance completeness: 0.15
- relation certainty: 0.15
- entity-link certainty: 0.15
- evidence agreement: 0.15
- source diversity: 0.15
- recency: 0.05

Evidence coverage increases as distinct evidence records are retrieved. Provenance completeness measures whether evidence records contain identifiers, source information, references, and source-specific metadata. Relation certainty reflects the resolved relation score, while entity-link certainty uses the top entity-linking candidate scores.

Evidence agreement is reduced when retrieved records contain conflicting explicit stances. Source diversity increases when independent source identifiers are represented.

Recency is applied only to explicitly temporal relations such as current global public-health risk and currently monitored variants. Historical events do not receive an age penalty merely because they occurred in the past.

The score is bounded between 0 and 0.99. `NOT_VERIFIABLE_WITH_CURRENT_KG` results are capped at 0.45. An `INSUFFICIENT_EVIDENCE` result with no retrieved evidence is capped at 0.60.

Scores of at least 0.85 are labeled high confidence, scores of at least 0.65 are labeled medium confidence, and lower values are labeled low confidence.

The confidence score is explicitly marked `calibrated: false`. It represents the strength of the evidence-grounding process and is not a probability that the claim is factually true or that the verification decision itself is correct.

## Response-Level Aggregation

After every extracted factual claim is verified independently, the `ResponseVerificationAggregator` summarizes the complete response.

The aggregator counts supported, contradicted, insufficient-evidence, and not-verifiable claims. It also reports the number of verifiable claims and the number of claims requiring attention.

The response grounding score is defined as:

grounding score = number of `SUPPORTED` factual claims / total extracted factual claims.

The knowledge-graph coverage ratio is defined as:

coverage ratio = number of claims assigned `SUPPORTED`, `CONTRADICTED`, or `INSUFFICIENT_EVIDENCE` / total extracted factual claims.

A response containing only supported claims receives overall status `SUPPORTED`. Analogous homogeneous responses may receive `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, or `NOT_VERIFIABLE_WITH_CURRENT_KG`. Responses containing multiple status types receive `MIXED`. If no factual claims are extracted, the response receives `NO_FACTUAL_CLAIMS`.

Neither the grounding score nor the aggregate status is interpreted as a probability that the entire language-model response is correct.

## LLM and Browser Integration

The project exposes the verification system through a FastAPI backend and a browser extension intended for use with ChatGPT.

The backend provides separate endpoints for entity extraction, entity linking, relation interpretation, semantic inspection, graph retrieval, grounding-context generation, prompt augmentation, historical retrieval, and response verification.

For prompt grounding, `/kg/augment` constructs a structured prompt containing the original user query, retrieved knowledge-graph context, verification metadata, and explicit response requirements. The generated instructions tell the language model to use relevant graph evidence, preserve uncertainty and provenance, avoid treating missing evidence as proof of falsity, and keep treatment relations distinct from clinical-trial relations.

The Chrome extension identifies the ChatGPT prompt editor and can replace the user's draft with this augmented prompt. It also exposes a panel showing linked entities, the resolved relation, and grounding context, and allows the original prompt to be restored.

The current browser interface primarily implements query and prompt grounding. The response-level verification architecture is exposed by the backend endpoint `/kg/verify-response` and was evaluated directly through the API. The paper therefore distinguishes the implemented verification backend from user-interface features that may be added later.

## Implementation

The backend is implemented in Python using FastAPI. spaCy with `en_core_web_sm` provides sentence segmentation, tokenization, syntactic information, and general named-entity recognition. FastEmbed provides embedding inference for semantic fallbacks, and a MiniLM cross-encoder is used for constrained reranking.

Neo4j stores the merged graph and serves graph queries. Source ingestion and benchmark scripts are implemented as reproducible Python programs.

Docker Compose is used to run the API and Neo4j services. The browser integration is implemented as a Chrome extension using JavaScript.

The semantic embedding and cross-encoder models are initialized within the API service and reused through a module-level semantic matcher instance.

## Design Principles

Several principles were maintained throughout implementation.

First, source provenance is preserved through retrieval rather than discarded after graph construction.

Second, the knowledge graph is not treated as complete. Missing evidence is distinguished from evidence of contradiction.

Third, scientific uncertainty is represented explicitly, particularly for SARS-CoV-2 origin evidence.

Fourth, deterministic interpretation is preferred when a claim can be resolved unambiguously, with embedding-based semantics used as a fallback rather than as an unrestricted replacement.

Fifth, factual language-model responses are decomposed into individual claims so that supported and unsupported statements within the same response remain distinguishable.

Finally, system confidence represents evidence grounding rather than factual truth probability. This distinction is necessary because the evaluation showed that authoritative evidence can be retrieved with high confidence even when the subsequent proposition comparison is incorrect.