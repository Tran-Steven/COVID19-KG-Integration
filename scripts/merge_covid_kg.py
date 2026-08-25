import argparse
import ast
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_MONARCH = Path("resources/monarch-covid")
DEFAULT_CHEMBL = Path("resources/chembl-covid")
DEFAULT_OUTPUT = Path("resources/covid-kg")

NODE_LIST_FIELDS = {
    "xref",
    "synonym",
    "synonyms",
    "provided_by",
    "source_dataset",
}


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--monarch",
        type=Path,
        default=DEFAULT_MONARCH,
    )

    parser.add_argument(
        "--chembl",
        type=Path,
        default=DEFAULT_CHEMBL,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def sha256(path: Path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path):
    if not path.exists():
        return None

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def parse_list(value: str | None):
    if not value:
        return []

    value = value.strip()

    if not value:
        return []

    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)

            if isinstance(
                parsed,
                (list, tuple, set),
            ):
                return [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip()
                ]
        except (ValueError, SyntaxError):
            inner = value[1:-1].strip()

            if inner:
                return [
                    item.strip().strip("'\"")
                    for item in inner.split(",")
                    if item.strip().strip("'\"")
                ]

            return []

    if "|" in value:
        return [
            item.strip()
            for item in value.split("|")
            if item.strip()
        ]

    if ";" in value:
        return [
            item.strip()
            for item in value.split(";")
            if item.strip()
        ]

    return [value]


def unique(values: list[str]):
    result = []
    seen = set()

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def merge_list_values(
    first: str | None,
    second: str | None,
):
    values = unique(
        parse_list(first)
        + parse_list(second)
    )

    return "|".join(values)


def read_tsv(path: Path):
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter="\t",
        )

        if reader.fieldnames is None:
            raise RuntimeError(
                f"Missing TSV header: {path}"
            )

        rows = [
            dict(row)
            for row in reader
        ]

        return list(reader.fieldnames), rows


def normalize_node(
    row: dict,
    source: str,
):
    normalized = dict(row)

    for field in NODE_LIST_FIELDS:
        if field == "source_dataset":
            continue

        if field in normalized:
            normalized[field] = "|".join(
                unique(
                    parse_list(
                        normalized.get(field)
                    )
                )
            )

    normalized["source_dataset"] = source

    return normalized


def merge_node(
    existing: dict,
    incoming: dict,
):
    result = dict(existing)

    for key in set(existing) | set(incoming):
        existing_value = result.get(
            key,
            "",
        )

        incoming_value = incoming.get(
            key,
            "",
        )

        if key in NODE_LIST_FIELDS:
            result[key] = merge_list_values(
                existing_value,
                incoming_value,
            )
            continue

        if not existing_value and incoming_value:
            result[key] = incoming_value

    return result


def load_nodes(
    directory: Path,
    source: str,
):
    path = directory / "nodes.tsv"

    headers, rows = read_tsv(path)

    normalized_rows = [
        normalize_node(
            row,
            source,
        )
        for row in rows
    ]

    return headers, normalized_rows


def load_edges(
    directory: Path,
    source: str,
):
    path = directory / "edges.tsv"

    headers, rows = read_tsv(path)

    normalized_rows = []

    for index, row in enumerate(
        rows,
        start=1,
    ):
        normalized = dict(row)

        normalized[
            "source_dataset"
        ] = source

        edge_id = normalized.get(
            "id"
        )

        if not edge_id:
            value = "|".join(
                [
                    source,
                    normalized.get(
                        "subject",
                        "",
                    ),
                    normalized.get(
                        "predicate",
                        "",
                    ),
                    normalized.get(
                        "object",
                        "",
                    ),
                    str(index),
                ]
            )

            normalized["id"] = hashlib.sha256(
                value.encode("utf-8")
            ).hexdigest()

        normalized_rows.append(
            normalized
        )

    return headers, normalized_rows


def combine_headers(
    base: list[str],
    *headers: list[str],
):
    result = []
    seen = set()

    for field in base:
        if field not in seen:
            seen.add(field)
            result.append(field)

    for header in headers:
        for field in header:
            if field not in seen:
                seen.add(field)
                result.append(field)

    if "source_dataset" not in seen:
        result.append(
            "source_dataset"
        )

    return result


def write_tsv(
    path: Path,
    headers: list[str],
    rows: list[dict],
):
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=headers,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row.get(
                        field,
                        "",
                    )
                    for field in headers
                }
            )


def main():
    csv.field_size_limit(
        sys.maxsize
    )

    args = parse_arguments()

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    monarch_node_headers, monarch_nodes = load_nodes(
        args.monarch,
        "monarch",
    )

    chembl_node_headers, chembl_nodes = load_nodes(
        args.chembl,
        "chembl",
    )

    nodes = {}

    for node in monarch_nodes + chembl_nodes:
        node_id = node.get("id")

        if not node_id:
            continue

        if node_id in nodes:
            nodes[node_id] = merge_node(
                nodes[node_id],
                node,
            )
        else:
            nodes[node_id] = node

    monarch_edge_headers, monarch_edges = load_edges(
        args.monarch,
        "monarch",
    )

    chembl_edge_headers, chembl_edges = load_edges(
        args.chembl,
        "chembl",
    )

    edges = {}
    node_ids = set(nodes)

    for edge in monarch_edges + chembl_edges:
        edge_id = edge["id"]

        if edge_id in edges:
            raise RuntimeError(
                f"Duplicate edge ID: {edge_id}"
            )

        subject = edge.get(
            "subject"
        )

        object_id = edge.get(
            "object"
        )

        if subject not in node_ids:
            raise RuntimeError(
                f"Missing subject node: {subject}"
            )

        if object_id not in node_ids:
            raise RuntimeError(
                f"Missing object node: {object_id}"
            )

        edges[edge_id] = edge

    node_headers = combine_headers(
        [
            "id",
            "category",
            "name",
            "xref",
            "synonym",
            "provided_by",
            "source_dataset",
        ],
        monarch_node_headers,
        chembl_node_headers,
    )

    edge_headers = combine_headers(
        [
            "id",
            "predicate",
            "category",
            "primary_knowledge_source",
            "aggregator_knowledge_source",
            "provided_by",
            "publications",
            "subject",
            "object",
            "source_dataset",
        ],
        monarch_edge_headers,
        chembl_edge_headers,
    )

    nodes_path = (
        args.output
        / "nodes.tsv"
    )

    edges_path = (
        args.output
        / "edges.tsv"
    )

    write_tsv(
        nodes_path,
        node_headers,
        list(nodes.values()),
    )

    write_tsv(
        edges_path,
        edge_headers,
        list(edges.values()),
    )

    category_counts = Counter(
        node.get(
            "category",
            "",
        )
        for node in nodes.values()
    )

    predicate_counts = Counter(
        edge.get(
            "predicate",
            "",
        )
        for edge in edges.values()
    )

    metadata = {
        "name": "COVID-19 Knowledge Graph",
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "sources": {
            "monarch": load_json(
                args.monarch
                / "source.json"
            ),
            "chembl": load_json(
                args.chembl
                / "source.json"
            ),
        },
        "inputHashes": {
            "monarchNodes": sha256(
                args.monarch
                / "nodes.tsv"
            ),
            "monarchEdges": sha256(
                args.monarch
                / "edges.tsv"
            ),
            "chemblNodes": sha256(
                args.chembl
                / "nodes.tsv"
            ),
            "chemblEdges": sha256(
                args.chembl
                / "edges.tsv"
            ),
        },
        "nodeCategoryCounts": dict(
            sorted(
                category_counts.items()
            )
        ),
        "predicateCounts": dict(
            sorted(
                predicate_counts.items()
            )
        ),
    }

    metadata["outputHashes"] = {
        "nodes": sha256(
            nodes_path
        ),
        "edges": sha256(
            edges_path
        ),
    }

    metadata_path = (
        args.output
        / "source.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Nodes written: {len(nodes)}"
    )

    print(
        f"Edges written: {len(edges)}"
    )

    print(
        f"Nodes: {nodes_path}"
    )

    print(
        f"Edges: {edges_path}"
    )

    print(
        f"Metadata: {metadata_path}"
    )


if __name__ == "__main__":
    main()