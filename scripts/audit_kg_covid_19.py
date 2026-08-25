import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_NODES = Path(
    "resources/kg-covid-19/extracted/merged-kg_nodes.tsv"
)

DEFAULT_EDGES = Path(
    "resources/kg-covid-19/extracted/merged-kg_edges.tsv"
)

DEFAULT_OUTPUT = Path(
    "evaluation/kg_covid_19_coverage_audit.json"
)

DEFAULT_TERMS = [
    "covid-19",
    "sars-cov-2",
    "wuhan",
    "pandemic",
    "origin",
    "zoonotic",
    "laboratory",
    "engineered",
    "transmission",
    "vaccine",
    "variant",
    "hospitalization",
    "mortality",
    "long covid",
    "mask",
    "remdesivir",
    "paxlovid",
    "nirmatrelvir",
]

NODE_SEARCH_FIELDS = [
    "id",
    "name",
    "description",
    "synonym",
    "xref",
    "xrefs",
]

NODE_SAMPLE_LIMIT = 20
EDGE_SAMPLE_LIMIT = 20
TOP_PREDICATE_LIMIT = 50
TOP_SOURCE_LIMIT = 30


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--nodes",
        type=Path,
        default=DEFAULT_NODES,
    )

    parser.add_argument(
        "--edges",
        type=Path,
        default=DEFAULT_EDGES,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--terms",
        nargs="*",
        default=DEFAULT_TERMS,
    )

    return parser.parse_args()


def normalize(value):
    if value is None:
        return ""

    return str(value).lower()


def split_values(value):
    if not value:
        return []

    for separator in ["|", ";"]:
        if separator in value:
            return [
                item.strip()
                for item in value.split(
                    separator
                )
                if item.strip()
            ]

    return [
        value.strip()
    ]


def compact_node(row):
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "category": row.get(
            "category"
        ),
        "providedBy": row.get(
            "provided_by"
        ),
        "synonym": row.get(
            "synonym"
        ),
        "description": row.get(
            "description"
        ),
    }


def compact_edge(row):
    return {
        "id": row.get("id"),
        "subject": row.get(
            "subject"
        ),
        "predicate": row.get(
            "predicate"
        ),
        "object": row.get(
            "object"
        ),
        "relation": row.get(
            "relation"
        ),
        "providedBy": row.get(
            "provided_by"
        ),
        "knowledgeSource": row.get(
            "knowledge_source"
        ),
        "publication": (
            row.get("publication")
            or row.get(
                "publications"
            )
        ),
        "evidence": row.get(
            "evidence"
        ),
        "comment": row.get(
            "comment"
        ),
    }


def scan_nodes(
    path,
    terms,
):
    term_ids = {
        term: set()
        for term in terms
    }

    term_counts = Counter()

    term_samples = {
        term: []
        for term in terms
    }

    category_counts = Counter()
    source_counts = Counter()

    node_names = {}

    total = 0

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter="\t",
        )

        for row in reader:
            total += 1

            node_id = row.get(
                "id"
            )

            if node_id:
                node_names[
                    node_id
                ] = (
                    row.get("name")
                    or node_id
                )

            for category in split_values(
                row.get(
                    "category",
                    "",
                )
            ):
                category_counts[
                    category
                ] += 1

            for source in split_values(
                row.get(
                    "provided_by",
                    "",
                )
            ):
                source_counts[
                    source
                ] += 1

            searchable = " ".join(
                normalize(
                    row.get(field)
                )
                for field
                in NODE_SEARCH_FIELDS
            )

            for term in terms:
                if normalize(
                    term
                ) not in searchable:
                    continue

                term_counts[
                    term
                ] += 1

                if node_id:
                    term_ids[
                        term
                    ].add(
                        node_id
                    )

                if (
                    len(
                        term_samples[
                            term
                        ]
                    )
                    < NODE_SAMPLE_LIMIT
                ):
                    term_samples[
                        term
                    ].append(
                        compact_node(
                            row
                        )
                    )

    return {
        "total": total,
        "termIds": term_ids,
        "termCounts": term_counts,
        "termSamples": term_samples,
        "categoryCounts": category_counts,
        "sourceCounts": source_counts,
        "nodeNames": node_names,
    }


def build_reverse_index(
    term_ids,
):
    reverse = defaultdict(
        set
    )

    for term, identifiers in (
        term_ids.items()
    ):
        for identifier in identifiers:
            reverse[
                identifier
            ].add(
                term
            )

    return reverse


def scan_edges(
    path,
    terms,
    reverse_index,
    node_names,
):
    total = 0

    predicate_counts = Counter()
    source_counts = Counter()

    neighborhood_counts = Counter()

    neighborhood_predicates = {
        term: Counter()
        for term in terms
    }

    neighborhood_sources = {
        term: Counter()
        for term in terms
    }

    neighborhood_samples = {
        term: []
        for term in terms
    }

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter="\t",
        )

        for row in reader:
            total += 1

            if (
                total
                % 1_000_000
                == 0
            ):
                print(
                    "Scanned "
                    f"{total:,} edges",
                    flush=True,
                )

            predicate = (
                row.get(
                    "predicate"
                )
                or row.get(
                    "relation"
                )
                or ""
            )

            if predicate:
                predicate_counts[
                    predicate
                ] += 1

            edge_sources = (
                split_values(
                    row.get(
                        "provided_by",
                        "",
                    )
                )
            )

            for source in edge_sources:
                source_counts[
                    source
                ] += 1

            subject = row.get(
                "subject"
            )

            object_id = row.get(
                "object"
            )

            matched_terms = set()

            if subject:
                matched_terms.update(
                    reverse_index.get(
                        subject,
                        set(),
                    )
                )

            if object_id:
                matched_terms.update(
                    reverse_index.get(
                        object_id,
                        set(),
                    )
                )

            if not matched_terms:
                continue

            for term in matched_terms:
                neighborhood_counts[
                    term
                ] += 1

                if predicate:
                    neighborhood_predicates[
                        term
                    ][
                        predicate
                    ] += 1

                for source in edge_sources:
                    neighborhood_sources[
                        term
                    ][
                        source
                    ] += 1

                samples = (
                    neighborhood_samples[
                        term
                    ]
                )

                if (
                    len(samples)
                    >= EDGE_SAMPLE_LIMIT
                ):
                    continue

                edge = compact_edge(
                    row
                )

                edge[
                    "subjectName"
                ] = node_names.get(
                    subject,
                    subject,
                )

                edge[
                    "objectName"
                ] = node_names.get(
                    object_id,
                    object_id,
                )

                samples.append(
                    edge
                )

    return {
        "total": total,
        "predicateCounts": predicate_counts,
        "sourceCounts": source_counts,
        "neighborhoodCounts": neighborhood_counts,
        "neighborhoodPredicates": neighborhood_predicates,
        "neighborhoodSources": neighborhood_sources,
        "neighborhoodSamples": neighborhood_samples,
    }


def counter_dict(
    counter,
    limit=None,
):
    values = (
        counter.most_common(
            limit
        )
        if limit
        else counter.most_common()
    )

    return {
        key: value
        for key, value in values
    }


def main():
    csv.field_size_limit(
        sys.maxsize
    )

    args = parse_arguments()

    terms = [
        term.lower()
        for term in args.terms
    ]

    print(
        "Scanning nodes..."
    )

    nodes = scan_nodes(
        args.nodes,
        terms,
    )

    print(
        "Matched node counts:"
    )

    for term in terms:
        print(
            f"  {term}: "
            f"{nodes['termCounts'][term]:,}"
        )

    reverse_index = (
        build_reverse_index(
            nodes[
                "termIds"
            ]
        )
    )

    print(
        "Scanning edges..."
    )

    edges = scan_edges(
        args.edges,
        terms,
        reverse_index,
        nodes[
            "nodeNames"
        ],
    )

    term_results = {}

    for term in terms:
        term_results[
            term
        ] = {
            "matchingNodeCount": (
                nodes[
                    "termCounts"
                ][term]
            ),
            "matchingNodeSamples": (
                nodes[
                    "termSamples"
                ][term]
            ),
            "touchingEdgeCount": (
                edges[
                    "neighborhoodCounts"
                ][term]
            ),
            "predicateCounts": (
                counter_dict(
                    edges[
                        "neighborhoodPredicates"
                    ][term],
                    TOP_PREDICATE_LIMIT,
                )
            ),
            "sourceCounts": (
                counter_dict(
                    edges[
                        "neighborhoodSources"
                    ][term],
                    TOP_SOURCE_LIMIT,
                )
            ),
            "edgeSamples": (
                edges[
                    "neighborhoodSamples"
                ][term]
            ),
        }

    result = {
        "nodes": {
            "count": nodes[
                "total"
            ],
            "topCategories": (
                counter_dict(
                    nodes[
                        "categoryCounts"
                    ],
                    TOP_PREDICATE_LIMIT,
                )
            ),
            "topSources": (
                counter_dict(
                    nodes[
                        "sourceCounts"
                    ],
                    TOP_SOURCE_LIMIT,
                )
            ),
        },
        "edges": {
            "count": edges[
                "total"
            ],
            "topPredicates": (
                counter_dict(
                    edges[
                        "predicateCounts"
                    ],
                    TOP_PREDICATE_LIMIT,
                )
            ),
            "topSources": (
                counter_dict(
                    edges[
                        "sourceCounts"
                    ],
                    TOP_SOURCE_LIMIT,
                )
            ),
        },
        "terms": term_results,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            result,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Coverage summary:"
    )

    for term in terms:
        data = term_results[
            term
        ]

        top_predicates = list(
            data[
                "predicateCounts"
            ].items()
        )[:5]

        formatted = ", ".join(
            f"{predicate}={count:,}"
            for predicate, count
            in top_predicates
        )

        print(
            f"{term}: "
            f"{data['matchingNodeCount']:,} nodes, "
            f"{data['touchingEdgeCount']:,} edges"
        )

        if formatted:
            print(
                f"  {formatted}"
            )

    print()
    print(
        f"Audit written to {args.output}"
    )


if __name__ == "__main__":
    main()