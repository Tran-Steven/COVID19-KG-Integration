import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_NODES = "resources/monarch-kg/nodes.tsv"
DEFAULT_EDGES = "resources/monarch-kg/edges.tsv"
DEFAULT_OUTPUT = "resources/monarch-covid"

SEED_IDS = {
    "MONDO:0100096",
    "NCBITaxon:2697049",
}


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--nodes",
        default=DEFAULT_NODES,
    )

    parser.add_argument(
        "--edges",
        default=DEFAULT_EDGES,
    )

    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--hops",
        type=int,
        default=1,
    )

    return parser.parse_args()


def discover_seeds(nodes_path: Path):
    seeds = {}

    with nodes_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter="\t",
        )

        for row in reader:
            node_id = row.get("id")

            if node_id not in SEED_IDS:
                continue

            seeds[node_id] = {
                "id": node_id,
                "name": row.get("name"),
                "category": row.get("category"),
            }

    missing = SEED_IDS - set(seeds)

    if missing:
        raise RuntimeError(
            f"Missing required seed nodes: {sorted(missing)}"
        )

    return seeds


def expand_neighbors(
    edges_path: Path,
    seed_ids: set[str],
    hops: int,
):
    selected = set(seed_ids)
    frontier = set(seed_ids)

    for hop in range(hops):
        if not frontier:
            break

        next_frontier = set()

        print(
            f"Scanning edges for hop {hop + 1} "
            f"with {len(frontier)} frontier nodes"
        )

        with edges_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(
                file,
                delimiter="\t",
            )

            for row in reader:
                subject = row.get("subject")
                object_id = row.get("object")

                if not subject or not object_id:
                    continue

                if subject in frontier and object_id not in selected:
                    next_frontier.add(object_id)

                if object_id in frontier and subject not in selected:
                    next_frontier.add(subject)

        selected.update(next_frontier)
        frontier = next_frontier

        print(
            f"Hop {hop + 1}: discovered "
            f"{len(next_frontier)} new nodes"
        )

    return selected


def write_nodes(
    source_path: Path,
    destination_path: Path,
    selected_ids: set[str],
):
    count = 0

    with source_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as source:
        reader = csv.DictReader(
            source,
            delimiter="\t",
        )

        if reader.fieldnames is None:
            raise RuntimeError(
                "Node TSV does not contain a header"
            )

        with destination_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as destination:
            writer = csv.DictWriter(
                destination,
                fieldnames=reader.fieldnames,
                delimiter="\t",
                extrasaction="ignore",
                lineterminator="\n",
            )

            writer.writeheader()

            for row in reader:
                if row.get("id") not in selected_ids:
                    continue

                writer.writerow(row)
                count += 1

    return count


def write_edges(
    source_path: Path,
    destination_path: Path,
    selected_ids: set[str],
):
    count = 0

    with source_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as source:
        reader = csv.DictReader(
            source,
            delimiter="\t",
        )

        if reader.fieldnames is None:
            raise RuntimeError(
                "Edge TSV does not contain a header"
            )

        with destination_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as destination:
            writer = csv.DictWriter(
                destination,
                fieldnames=reader.fieldnames,
                delimiter="\t",
                extrasaction="ignore",
                lineterminator="\n",
            )

            writer.writeheader()

            for row in reader:
                subject = row.get("subject")
                object_id = row.get("object")

                if (
                    subject not in selected_ids
                    or object_id not in selected_ids
                ):
                    continue

                writer.writerow(row)
                count += 1

    return count


def main():
    args = parse_arguments()

    nodes_path = Path(args.nodes)
    edges_path = Path(args.edges)
    output_path = Path(args.output)

    if not nodes_path.exists():
        raise FileNotFoundError(nodes_path)

    if not edges_path.exists():
        raise FileNotFoundError(edges_path)

    if args.hops < 0:
        raise ValueError(
            "hops must be greater than or equal to 0"
        )

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Loading canonical COVID-19 seed nodes")

    seeds = discover_seeds(nodes_path)

    for seed in seeds.values():
        print(
            f"{seed['id']} | "
            f"{seed['category']} | "
            f"{seed['name']}"
        )

    selected_ids = expand_neighbors(
        edges_path,
        set(seeds),
        args.hops,
    )

    print(
        f"Selected {len(selected_ids)} total nodes"
    )

    output_nodes = output_path / "nodes.tsv"
    output_edges = output_path / "edges.tsv"

    print("Writing filtered nodes")

    node_count = write_nodes(
        nodes_path,
        output_nodes,
        selected_ids,
    )

    print("Writing filtered edges")

    edge_count = write_edges(
        edges_path,
        output_edges,
        selected_ids,
    )

    metadata = {
        "source": "Monarch Initiative Knowledge Graph",
        "derivedDataset": "COVID-19 focused Monarch subgraph",
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "hops": args.hops,
        "seedIds": sorted(SEED_IDS),
        "seeds": list(seeds.values()),
        "nodeCount": node_count,
        "edgeCount": edge_count,
    }

    metadata_path = output_path / "source.json"

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Nodes written: {node_count}"
    )

    print(
        f"Edges written: {edge_count}"
    )

    print(
        f"Nodes: {output_nodes}"
    )

    print(
        f"Edges: {output_edges}"
    )

    print(
        f"Metadata: {metadata_path}"
    )


if __name__ == "__main__":
    main()