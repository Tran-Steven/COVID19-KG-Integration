import argparse
import csv
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_EVENTS = Path(
    "resources/who-covid-timeline/events.tsv"
)

DEFAULT_TRANSFORM = Path(
    "resources/who-covid-timeline/transform.json"
)

DEFAULT_OUTPUT = Path(
    "resources/who-covid-history"
)

COVID_ID = "MONDO:0100096"
WUHAN_ID = "covidkg:place:wuhan"

SOURCE_NAME = (
    "World Health Organization"
)

EVENT_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://www.who.int/news/item/"
    "29-06-2020-covidtimeline",
)

EVENT_SPECS = [
    {
        "key": "initial_wuhan_report",
        "date": "2019-12-31",
        "contains": [
            "Wuhan Municipal Health Commission",
            "viral pneumonia",
        ],
        "name": (
            "WHO pickup of Wuhan viral pneumonia report"
        ),
        "event_type": (
            "initial_outbreak_report"
        ),
    },
    {
        "key": "novel_coronavirus_cause_report",
        "date": "2020-01-09",
        "contains": [
            "outbreak is caused by a novel coronavirus",
        ],
        "name": (
            "WHO report that outbreak was caused "
            "by a novel coronavirus"
        ),
        "event_type": (
            "etiology_report"
        ),
    },
    {
        "key": "pandemic_characterization",
        "date": "2020-03-11",
        "contains": [
            "could be characterized as a pandemic",
        ],
        "name": (
            "WHO characterization of COVID-19 "
            "as a pandemic"
        ),
        "event_type": (
            "pandemic_characterization"
        ),
    },
]


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--events",
        type=Path,
        default=DEFAULT_EVENTS,
    )

    parser.add_argument(
        "--transform",
        type=Path,
        default=DEFAULT_TRANSFORM,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def sha256(
    path: Path,
):
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def read_events(
    path: Path,
):
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(
                file,
                delimiter="\t",
            )
        )


def select_event(
    events: list[dict],
    spec: dict,
):
    matches = []

    for event in events:
        if (
            event.get(
                "date_start"
            )
            != spec["date"]
        ):
            continue

        text = (
            event.get(
                "text",
                ""
            )
        )

        if all(
            marker.lower()
            in text.lower()
            for marker
            in spec[
                "contains"
            ]
        ):
            matches.append(
                event
            )

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one WHO "
            "event for "
            f"{spec['key']}, found "
            f"{len(matches)}"
        )

    return matches[0]


def edge_id(
    subject: str,
    role: str,
    object_id: str,
):
    value = "|".join(
        [
            subject,
            role,
            object_id,
        ]
    )

    identifier = uuid.uuid5(
        EVENT_NAMESPACE,
        value,
    )

    return (
        f"urn:uuid:{identifier}"
    )


def build_event_node(
    event: dict,
    spec: dict,
    source_url: str,
):
    return {
        "id": event["id"],
        "category": "biolink:Event",
        "name": spec["name"],
        "description": event[
            "text"
        ],
        "xref": "",
        "synonym": "",
        "provided_by": SOURCE_NAME,
        "event_type": spec[
            "event_type"
        ],
        "event_date_start": event[
            "date_start"
        ],
        "event_date_end": event[
            "date_end"
        ],
        "source_event_id": event[
            "id"
        ],
        "source_text": event[
            "text"
        ],
        "source_links": event[
            "links"
        ],
        "source_url": source_url,
    }


def build_edge(
    event: dict,
    object_id: str,
    semantic_role: str,
    source_url: str,
):
    return {
        "id": edge_id(
            event["id"],
            semantic_role,
            object_id,
        ),
        "predicate": (
            "biolink:related_to"
        ),
        "relation": (
            "biolink:related_to"
        ),
        "category": (
            "biolink:Association"
        ),
        "primary_knowledge_source": (
            SOURCE_NAME
        ),
        "provided_by": (
            SOURCE_NAME
        ),
        "publications": source_url,
        "semantic_role": (
            semantic_role
        ),
        "source_event_id": (
            event["id"]
        ),
        "source_text": (
            event["text"]
        ),
        "source_links": (
            event["links"]
        ),
        "subject": event[
            "id"
        ],
        "object": object_id,
    }


def write_tsv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict],
):
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                row
            )


def main():
    args = parse_arguments()

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    transform = json.loads(
        args.transform.read_text(
            encoding="utf-8"
        )
    )

    source_url = transform[
        "sourceUrl"
    ]

    expected_input_hash = (
        transform.get(
            "outputSha256"
        )
    )

    actual_input_hash = sha256(
        args.events
    )

    if (
        expected_input_hash
        and actual_input_hash
        != expected_input_hash
    ):
        raise RuntimeError(
            "WHO events.tsv hash does "
            "not match transform.json."
        )

    events = read_events(
        args.events
    )

    selected = {}

    for spec in EVENT_SPECS:
        selected[
            spec["key"]
        ] = select_event(
            events,
            spec,
        )

    nodes = [
        {
            "id": COVID_ID,
            "category": (
                "biolink:Disease"
            ),
            "name": "COVID-19",
            "description": "",
            "xref": "",
            "synonym": "",
            "provided_by": "",
            "event_type": "",
            "event_date_start": "",
            "event_date_end": "",
            "source_event_id": "",
            "source_text": "",
            "source_links": "",
            "source_url": "",
        },
        {
            "id": WUHAN_ID,
            "category": (
                "biolink:GeographicLocation"
            ),
            "name": (
                "Wuhan, People's Republic "
                "of China"
            ),
            "description": "",
            "xref": "",
            "synonym": "Wuhan",
            "provided_by": SOURCE_NAME,
            "event_type": "",
            "event_date_start": "",
            "event_date_end": "",
            "source_event_id": "",
            "source_text": "",
            "source_links": "",
            "source_url": source_url,
        },
    ]

    for spec in EVENT_SPECS:
        event = selected[
            spec["key"]
        ]

        nodes.append(
            build_event_node(
                event,
                spec,
                source_url,
            )
        )

    initial_event = selected[
        "initial_wuhan_report"
    ]

    cause_event = selected[
        "novel_coronavirus_cause_report"
    ]

    pandemic_event = selected[
        "pandemic_characterization"
    ]

    edges = [
        build_edge(
            initial_event,
            COVID_ID,
            "historical_event_about_covid_19",
            source_url,
        ),
        build_edge(
            initial_event,
            WUHAN_ID,
            "reported_case_location",
            source_url,
        ),
        build_edge(
            cause_event,
            COVID_ID,
            "historical_event_about_covid_19",
            source_url,
        ),
        build_edge(
            pandemic_event,
            COVID_ID,
            "historical_event_about_covid_19",
            source_url,
        ),
    ]

    node_fields = [
        "id",
        "category",
        "name",
        "description",
        "xref",
        "synonym",
        "provided_by",
        "event_type",
        "event_date_start",
        "event_date_end",
        "source_event_id",
        "source_text",
        "source_links",
        "source_url",
    ]

    edge_fields = [
        "id",
        "predicate",
        "relation",
        "category",
        "primary_knowledge_source",
        "provided_by",
        "publications",
        "semantic_role",
        "source_event_id",
        "source_text",
        "source_links",
        "subject",
        "object",
    ]

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
        node_fields,
        nodes,
    )

    write_tsv(
        edges_path,
        edge_fields,
        edges,
    )

    metadata = {
        "source": SOURCE_NAME,
        "sourceUrl": source_url,
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "inputEvents": str(
            args.events
        ),
        "inputEventsSha256": (
            actual_input_hash
        ),
        "nodeCount": len(
            nodes
        ),
        "edgeCount": len(
            edges
        ),
        "selectedEvents": {
            spec["key"]: (
                selected[
                    spec["key"]
                ]["id"]
            )
            for spec in EVENT_SPECS
        },
        "semanticInterpretation": True,
        "interpretationMethod": (
            "deterministic source-backed "
            "event normalization"
        ),
        "outputHashes": {
            "nodes": sha256(
                nodes_path
            ),
            "edges": sha256(
                edges_path
            ),
        },
    }

    metadata_path = (
        args.output
        / "source.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "Selected events:"
    )

    for spec in EVENT_SPECS:
        event = selected[
            spec["key"]
        ]

        print(
            f"  {spec['key']}: "
            f"{event['id']}"
        )

    print()
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