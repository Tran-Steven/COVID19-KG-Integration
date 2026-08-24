import csv
import hashlib
import json
from pathlib import Path

from app.database import Neo4jClient


class KGXImporter:
    def __init__(
        self,
        database: Neo4jClient,
        batch_size: int = 1000,
    ):
        self.database = database
        self.batch_size = batch_size

    def import_graph(
        self,
        nodes_path: str,
        edges_path: str,
        clear: bool = False,
    ):
        if clear:
            self.database.clear_graph()

        self.database.ensure_kg_constraints()

        node_count = self._import_nodes(Path(nodes_path))
        edge_count = self._import_edges(Path(edges_path))

        return {
            "nodes": node_count,
            "edges": edge_count,
        }

    def _import_nodes(self, path: Path):
        total = 0
        batch = []

        for row in self._read_tsv(path):
            node = self._normalize_node(row)

            if node is None:
                continue

            batch.append(node)

            if len(batch) >= self.batch_size:
                total += self.database.upsert_kg_nodes(batch)
                batch = []

        if batch:
            total += self.database.upsert_kg_nodes(batch)

        return total

    def _import_edges(self, path: Path):
        total = 0
        batch = []

        for row in self._read_tsv(path):
            edge = self._normalize_edge(row)

            if edge is None:
                continue

            batch.append(edge)

            if len(batch) >= self.batch_size:
                total += self.database.upsert_kg_edges(batch)
                batch = []

        if batch:
            total += self.database.upsert_kg_edges(batch)

        return total

    def _read_tsv(self, path: Path):
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
                yield {
                    key: value.strip()
                    if isinstance(value, str)
                    else value
                    for key, value in row.items()
                }

    def _normalize_node(self, row: dict):
        node_id = row.get("id")

        if not node_id:
            return None

        name = row.get("name") or node_id

        categories = self._parse_list(
            row.get("category")
            or row.get("categories")
        )

        aliases = self._parse_list(
            row.get("aliases")
            or row.get("alias")
            or row.get("synonym")
            or row.get("synonyms")
        )

        provided_by = self._parse_list(
            row.get("provided_by")
            or row.get("providedBy")
        )

        excluded = {
            "id",
            "name",
            "category",
            "categories",
            "aliases",
            "alias",
            "synonym",
            "synonyms",
            "provided_by",
            "providedBy",
        }

        properties = self._additional_properties(
            row,
            excluded,
        )

        return {
            "id": node_id,
            "name": name,
            "categories": categories,
            "aliases": aliases,
            "providedBy": provided_by,
            "properties": properties,
        }

    def _normalize_edge(self, row: dict):
        subject = row.get("subject")
        object_id = row.get("object")

        if not subject or not object_id:
            return None

        predicate = (
            row.get("predicate")
            or row.get("edge_label")
            or row.get("relation")
            or "related_to"
        )

        relation = row.get("relation") or predicate

        provided_by = self._parse_list(
            row.get("provided_by")
            or row.get("providedBy")
        )

        edge_key = self._edge_key(
            subject,
            predicate,
            object_id,
            relation,
            provided_by,
        )

        excluded = {
            "subject",
            "object",
            "predicate",
            "edge_label",
            "relation",
            "provided_by",
            "providedBy",
        }

        properties = self._additional_properties(
            row,
            excluded,
        )

        return {
            "subject": subject,
            "object": object_id,
            "predicate": predicate,
            "relation": relation,
            "providedBy": provided_by,
            "edgeKey": edge_key,
            "properties": properties,
        }

    def _additional_properties(
        self,
        row: dict,
        excluded: set[str],
    ):
        properties = {}

        for key, value in row.items():
            if key in excluded:
                continue

            if value is None or value == "":
                continue

            properties[key] = value

        return properties

    def _parse_list(self, value: str | None):
        if not value:
            return []

        value = value.strip()

        if value.startswith("[") and value.endswith("]"):
            try:
                parsed = json.loads(value)

                if isinstance(parsed, list):
                    return [
                        str(item)
                        for item in parsed
                        if item is not None
                    ]
            except json.JSONDecodeError:
                pass

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

    def _edge_key(
        self,
        subject: str,
        predicate: str,
        object_id: str,
        relation: str,
        provided_by: list[str],
    ):
        value = "|".join(
            [
                subject,
                predicate,
                object_id,
                relation,
                ",".join(sorted(provided_by)),
            ]
        )

        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()