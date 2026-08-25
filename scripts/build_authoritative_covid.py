import argparse
import csv
import json
from pathlib import Path


DEFAULT_OUTPUT = Path(
    "resources/authoritative-covid"
)

WHO_COVID_QA = (
    "https://www.who.int/news-room/"
    "questions-and-answers/item/"
    "coronavirus-disease-covid-19"
)

CDC_ABOUT_COVID = (
    "https://www.cdc.gov/covid/about/index.html"
)

WHO_PANDEMIC_TIMELINE = (
    "https://www.who.int/news/item/"
    "29-06-2020-covidtimeline"
)


NODES = [
    {
        "id": "MONDO:0100096",
        "category": "biolink:Disease",
        "name": "COVID-19",
        "xref": "",
        "synonym": "Coronavirus disease 2019",
        "provided_by": (
            "World Health Organization|"
            "Centers for Disease Control and Prevention"
        ),
    },
    {
        "id": "NCBITaxon:2697049",
        "category": "biolink:OrganismTaxon",
        "name": "SARS-CoV-2",
        "xref": "",
        "synonym": (
            "Severe acute respiratory syndrome "
            "coronavirus 2"
        ),
        "provided_by": (
            "World Health Organization|"
            "Centers for Disease Control and Prevention"
        ),
    },
    {
        "id": "covid:location:wuhan",
        "category": "biolink:GeographicLocation",
        "name": "Wuhan, Hubei, China",
        "xref": "",
        "synonym": "Wuhan|Wuhan City",
        "provided_by": "World Health Organization",
    },
    {
        "id": "covid:date:2019-12-31",
        "category": "biolink:NamedThing",
        "name": "31 December 2019",
        "xref": "",
        "synonym": (
            "December 31, 2019|2019-12-31"
        ),
        "provided_by": "World Health Organization",
    },
    {
        "id": "covid:date:2020-03-11",
        "category": "biolink:NamedThing",
        "name": "11 March 2020",
        "xref": "",
        "synonym": (
            "March 11, 2020|2020-03-11"
        ),
        "provided_by": "World Health Organization",
    },
]


EDGES = [
    {
        "id": (
            "authoritative:cdc:"
            "sars-cov-2-causes-covid-19"
        ),
        "predicate": "biolink:causes",
        "category": "biolink:Association",
        "primary_knowledge_source": (
            "Centers for Disease Control and Prevention"
        ),
        "aggregator_knowledge_source": "",
        "provided_by": (
            "Centers for Disease Control and Prevention"
        ),
        "publications": CDC_ABOUT_COVID,
        "subject": "NCBITaxon:2697049",
        "object": "MONDO:0100096",
        "evidence_note": (
            "CDC states that COVID-19 is a disease "
            "caused by the SARS-CoV-2 virus."
        ),
    },
    {
        "id": (
            "authoritative:who:"
            "sars-cov-2-causes-covid-19"
        ),
        "predicate": "biolink:causes",
        "category": "biolink:Association",
        "primary_knowledge_source": (
            "World Health Organization"
        ),
        "aggregator_knowledge_source": "",
        "provided_by": (
            "World Health Organization"
        ),
        "publications": WHO_COVID_QA,
        "subject": "NCBITaxon:2697049",
        "object": "MONDO:0100096",
        "evidence_note": (
            "WHO states that COVID-19 is the disease "
            "caused by SARS-CoV-2."
        ),
    },
    {
        "id": (
            "authoritative:who:"
            "initial-outbreak-reported-in-wuhan"
        ),
        "predicate": (
            "covid:initial_outbreak_reported_in"
        ),
        "category": "biolink:Association",
        "primary_knowledge_source": (
            "World Health Organization"
        ),
        "aggregator_knowledge_source": "",
        "provided_by": (
            "World Health Organization"
        ),
        "publications": WHO_COVID_QA,
        "subject": "MONDO:0100096",
        "object": "covid:location:wuhan",
        "evidence_note": (
            "WHO reports that it first learned of the "
            "new virus following a report of a cluster "
            "of viral pneumonia cases in Wuhan, China."
        ),
    },
    {
        "id": (
            "authoritative:who:"
            "initial-outbreak-reported-on-2019-12-31"
        ),
        "predicate": (
            "covid:initial_outbreak_reported_on"
        ),
        "category": "biolink:Association",
        "primary_knowledge_source": (
            "World Health Organization"
        ),
        "aggregator_knowledge_source": "",
        "provided_by": (
            "World Health Organization"
        ),
        "publications": WHO_COVID_QA,
        "subject": "MONDO:0100096",
        "object": "covid:date:2019-12-31",
        "evidence_note": (
            "WHO states that it first learned of the "
            "new virus on 31 December 2019 following "
            "the report of the Wuhan pneumonia cluster."
        ),
    },
    {
        "id": (
            "authoritative:who:"
            "pandemic-characterized-on-2020-03-11"
        ),
        "predicate": (
            "covid:characterized_as_pandemic_on"
        ),
        "category": "biolink:Association",
        "primary_knowledge_source": (
            "World Health Organization"
        ),
        "aggregator_knowledge_source": "",
        "provided_by": (
            "World Health Organization"
        ),
        "publications": WHO_PANDEMIC_TIMELINE,
        "subject": "MONDO:0100096",
        "object": "covid:date:2020-03-11",
        "evidence_note": (
            "WHO made the assessment on 11 March 2020 "
            "that COVID-19 could be characterized as "
            "a pandemic."
        ),
    },
]


NODE_HEADERS = [
    "id",
    "category",
    "name",
    "xref",
    "synonym",
    "provided_by",
]


EDGE_HEADERS = [
    "id",
    "predicate",
    "category",
    "primary_knowledge_source",
    "aggregator_knowledge_source",
    "provided_by",
    "publications",
    "subject",
    "object",
    "evidence_note",
]


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


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
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_arguments()

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    nodes_path = (
        args.output
        / "nodes.tsv"
    )

    edges_path = (
        args.output
        / "edges.tsv"
    )

    source_path = (
        args.output
        / "source.json"
    )

    write_tsv(
        nodes_path,
        NODE_HEADERS,
        NODES,
    )

    write_tsv(
        edges_path,
        EDGE_HEADERS,
        EDGES,
    )

    source = {
        "name": (
            "Authoritative COVID-19 Core Facts"
        ),
        "type": "curated-authoritative",
        "reviewedOn": "2026-08-24",
        "sources": [
            {
                "name": (
                    "World Health Organization"
                ),
                "url": WHO_COVID_QA,
            },
            {
                "name": (
                    "Centers for Disease Control "
                    "and Prevention"
                ),
                "url": CDC_ABOUT_COVID,
            },
            {
                "name": (
                    "World Health Organization "
                    "COVID-19 timeline"
                ),
                "url": WHO_PANDEMIC_TIMELINE,
            },
        ],
        "nodeCount": len(NODES),
        "edgeCount": len(EDGES),
    }

    source_path.write_text(
        json.dumps(
            source,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Nodes written: {len(NODES)}"
    )

    print(
        f"Edges written: {len(EDGES)}"
    )

    print(
        f"Nodes: {nodes_path}"
    )

    print(
        f"Edges: {edges_path}"
    )

    print(
        f"Metadata: {source_path}"
    )


if __name__ == "__main__":
    main()