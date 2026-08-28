import ast
from typing import Any


class EvidenceNormalizer:
    def normalize_fact(self, fact: dict):
        properties = dict(
            fact.get(
                "relationshipProperties",
                {},
            )
        )

        return {
            "subject": {
                "id": fact["subjectId"],
                "name": fact["subject"],
                "categories": fact["subjectCategories"],
            },
            "predicate": fact["predicate"],
            "object": {
                "id": fact["objectId"],
                "name": fact["object"],
                "categories": fact["objectCategories"],
            },
            "evidence": {
                "edgeId": properties.get("id"),
                "primaryKnowledgeSource": (properties.get("primary_knowledge_source")),
                "providedBy": self._to_list(properties.get("providedBy")),
                "sourceDataset": properties.get("source_dataset"),
                "references": self._references(properties.get("publications")),
                "maxPhaseForIndication": (
                    self._to_float(properties.get("max_phase_for_ind"))
                ),
                "attributes": (self._additional_attributes(properties)),
            },
        }

    def _references(
        self,
        value: Any,
    ):
        values = self._to_list(value)

        references = []

        for value in values:
            if value.startswith("ClinicalTrials:") and "," in value:
                prefix, identifiers = value.split(
                    ":",
                    1,
                )

                references.extend(
                    f"{prefix}:{identifier.strip()}"
                    for identifier in identifiers.split(",")
                    if identifier.strip()
                )

                continue

            references.append(value)

        return self._unique(references)

    def _to_list(
        self,
        value: Any,
    ):
        if value is None:
            return []

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return self._unique(
                [str(item).strip() for item in value if str(item).strip()]
            )

        text = str(value).strip()

        if not text:
            return []

        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)

                if isinstance(
                    parsed,
                    (list, tuple, set),
                ):
                    return self._unique(
                        [str(item).strip() for item in parsed if str(item).strip()]
                    )
            except (
                ValueError,
                SyntaxError,
            ):
                pass

        if "|" in text:
            return self._unique(
                [item.strip() for item in text.split("|") if item.strip()]
            )

        return [text]

    def _to_float(
        self,
        value: Any,
    ):
        if value is None:
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    def _additional_attributes(
        self,
        properties: dict,
    ):
        excluded = {
            "id",
            "edgeKey",
            "predicate",
            "relation",
            "providedBy",
            "source_dataset",
            "primary_knowledge_source",
            "publications",
            "max_phase_for_ind",
        }

        return {key: value for key, value in properties.items() if key not in excluded}

    def _unique(
        self,
        values: list[str],
    ):
        result = []
        seen = set()

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            result.append(value)

        return result
