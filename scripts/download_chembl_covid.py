import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


COVID_ID = "MONDO:0100096"

API_URL = "https://www.ebi.ac.uk/chembl/api/data/drug_indication.json"

OUTPUT_DIRECTORY = Path("resources/chembl-covid")


def fetch_json(url: str):
    request = Request(
        url,
        headers={
            "User-Agent": "COVID19-KG-Integration/1.0",
        },
    )

    with urlopen(request) as response:
        return json.load(response)


def fetch_indications():
    params = {
        "efo_id": COVID_ID,
        "limit": 1000,
    }

    url = f"{API_URL}?{urlencode(params)}"

    records = []

    while url:
        print(f"Fetching {url}")

        data = fetch_json(url)

        records.extend(
            data.get(
                "drug_indications",
                [],
            )
        )

        page_meta = data.get(
            "page_meta",
            {},
        )

        url = page_meta.get(
            "next",
        )

    return records


def fetch_molecule(chembl_id: str):
    url = (
        "https://www.ebi.ac.uk/chembl/api/data/"
        f"molecule/{chembl_id}.json"
    )

    return fetch_json(url)


def normalize_phase(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def predicate_for_indication(record: dict):
    phase = normalize_phase(
        record.get("max_phase_for_ind")
    )

    if phase == 4.0:
        return "biolink:treats"

    if phase is not None and phase >= 1.0:
        return "biolink:in_clinical_trials_for"

    return "biolink:studied_to_treat"


def build_nodes(indications: list[dict]):
    nodes = {
        COVID_ID: {
            "id": COVID_ID,
            "category": "biolink:Disease",
            "name": "COVID-19",
            "xref": "",
            "synonym": "",
            "provided_by": "infores:chembl",
        }
    }

    molecule_ids = sorted(
        {
            record["molecule_chembl_id"]
            for record in indications
            if record.get("molecule_chembl_id")
        }
    )

    for index, chembl_id in enumerate(
        molecule_ids,
        start=1,
    ):
        print(
            f"Fetching molecule {index}/"
            f"{len(molecule_ids)}: {chembl_id}"
        )

        molecule = fetch_molecule(
            chembl_id
        )

        name = (
            molecule.get("pref_name")
            or chembl_id
        )

        synonyms = []

        for synonym in molecule.get(
            "molecule_synonyms",
            [],
        ):
            value = synonym.get(
                "molecule_synonym"
            )

            if value:
                synonyms.append(value)

        nodes[chembl_id] = {
            "id": chembl_id,
            "category": "biolink:ChemicalEntity",
            "name": name,
            "xref": chembl_id,
            "synonym": "|".join(
                sorted(set(synonyms))
            ),
            "provided_by": "infores:chembl",
        }

    return nodes


def build_edges(indications: list[dict]):
    edges = []

    for index, record in enumerate(
        indications,
        start=1,
    ):
        molecule_id = record.get(
            "molecule_chembl_id"
        )

        if not molecule_id:
            continue

        efo_id = record.get(
            "efo_id"
        )

        if efo_id != COVID_ID:
            continue

        edge_id = (
            f"chembl:covid-indication:"
            f"{molecule_id}:{index}"
        )

        references = record.get(
            "indication_refs"
        ) or []

        reference_values = []

        for reference in references:
            ref_type = reference.get(
                "ref_type"
            )

            ref_id = reference.get(
                "ref_id"
            )

            if ref_type and ref_id:
                reference_values.append(
                    f"{ref_type}:{ref_id}"
                )

        predicate = predicate_for_indication(
            record
        )

        edges.append(
            {
                "id": edge_id,
                "predicate": predicate,
                "category": "biolink:ChemicalToDiseaseOrPhenotypicFeatureAssociation",
                "primary_knowledge_source": "infores:chembl",
                "provided_by": "infores:chembl",
                "publications": "|".join(
                    reference_values
                ),
                "max_phase_for_ind": record.get(
                    "max_phase_for_ind"
                ),
                "mesh_id": record.get(
                    "mesh_id"
                ),
                "mesh_heading": record.get(
                    "mesh_heading"
                ),
                "efo_id": record.get(
                    "efo_id"
                ),
                "efo_term": record.get(
                    "efo_term"
                ),
                "subject": molecule_id,
                "object": COVID_ID,
            }
        )

    return edges


def write_nodes(
    nodes: dict[str, dict],
    path: Path,
):
    fieldnames = [
        "id",
        "category",
        "name",
        "xref",
        "synonym",
        "provided_by",
    ]

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

        for node in nodes.values():
            writer.writerow(node)


def write_edges(
    edges: list[dict],
    path: Path,
):
    fieldnames = [
        "id",
        "predicate",
        "category",
        "primary_knowledge_source",
        "provided_by",
        "publications",
        "max_phase_for_ind",
        "mesh_id",
        "mesh_heading",
        "efo_id",
        "efo_term",
        "subject",
        "object",
    ]

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

        for edge in edges:
            writer.writerow(edge)


def main():
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    indications = fetch_indications()

    print(
        f"Found {len(indications)} "
        f"COVID-19 drug indications"
    )

    nodes = build_nodes(
        indications
    )

    edges = build_edges(
        indications
    )

    nodes_path = (
        OUTPUT_DIRECTORY
        / "nodes.tsv"
    )

    edges_path = (
        OUTPUT_DIRECTORY
        / "edges.tsv"
    )

    write_nodes(
        nodes,
        nodes_path,
    )

    write_edges(
        edges,
        edges_path,
    )

    predicate_counts = {}

    for edge in edges:
        predicate = edge["predicate"]

        predicate_counts[predicate] = (
            predicate_counts.get(
                predicate,
                0,
            )
            + 1
        )

    metadata = {
        "source": "ChEMBL",
        "sourceUrl": API_URL,
        "diseaseId": COVID_ID,
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "predicateCounts": predicate_counts,
    }

    metadata_path = (
        OUTPUT_DIRECTORY
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