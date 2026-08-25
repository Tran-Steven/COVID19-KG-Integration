import json

from app.database import Neo4jClient
from app.interpretation.history_intent_resolver import (
    HistoryIntentResolver,
)


class HistoryRetriever:
    QUALIFICATIONS = {
        "initial_outbreak_date": (
            "This is the date WHO's China "
            "Country Office picked up the Wuhan "
            "Municipal Health Commission report "
            "about viral pneumonia cases. It is "
            "not represented as the date "
            "SARS-CoV-2 itself was first "
            "biologically identified."
        ),
        "initial_outbreak_location": (
            "This is the location of the viral "
            "pneumonia cases described in WHO's "
            "31 December 2019 timeline event. "
            "The graph does not represent this "
            "as a universal 'first found in' "
            "relationship."
        ),
        "pandemic_characterization_date": (
            "This is the date WHO assessed that "
            "COVID-19 could be characterized as "
            "a pandemic."
        ),
    }

    def __init__(
        self,
        database: Neo4jClient,
        intent_resolver: (
            HistoryIntentResolver
        ),
    ):
        self.database = database
        self.intent_resolver = (
            intent_resolver
        )

    def retrieve(
        self,
        text: str,
    ):
        interpretation = (
            self.intent_resolver.resolve(
                text
            )
        )

        if interpretation is None:
            return {
                "text": text,
                "status": (
                    "NOT_VERIFIABLE_WITH_CURRENT_KG"
                ),
                "interpretation": None,
                "answer": None,
                "evidence": [],
            }

        event_type = interpretation[
            "eventType"
        ]

        semantic_role = interpretation[
            "semanticRole"
        ]

        requested_field = (
            interpretation[
                "requestedField"
            ]
        )

        if (
            requested_field
            == "location"
        ):
            rows = (
                self.database
                .find_history_event_relations(
                    event_type=event_type,
                    semantic_role=(
                        semantic_role
                    ),
                )
            )
        else:
            rows = (
                self.database
                .find_history_events(
                    event_type=event_type
                )
            )

        if not rows:
            return {
                "text": text,
                "status": (
                    "INSUFFICIENT_EVIDENCE"
                ),
                "interpretation": (
                    interpretation
                ),
                "answer": None,
                "evidence": [],
            }

        answer = self._build_answer(
            interpretation,
            rows,
        )

        evidence = [
            self._normalize_evidence(
                row
            )
            for row in rows
        ]

        return {
            "text": text,
            "status": "SUPPORTED",
            "interpretation": (
                interpretation
            ),
            "answer": answer,
            "evidence": evidence,
        }

    def _build_answer(
        self,
        interpretation: dict,
        rows: list[dict],
    ):
        first = rows[0]

        requested_field = (
            interpretation[
                "requestedField"
            ]
        )

        if (
            requested_field
            == "location"
        ):
            value = first.get(
                "relatedEntityName"
            )
        else:
            value = first.get(
                "dateStart"
            )

        if not value:
            return None

        return {
            "field": requested_field,
            "value": value,
            "qualification": (
                self.QUALIFICATIONS.get(
                    interpretation[
                        "intent"
                    ]
                )
            ),
        }

    def _normalize_evidence(
        self,
        row: dict,
    ):
        return {
            "eventId": row.get(
                "eventId"
            ),
            "eventName": row.get(
                "eventName"
            ),
            "eventType": row.get(
                "eventType"
            ),
            "dateStart": row.get(
                "dateStart"
            ),
            "dateEnd": row.get(
                "dateEnd"
            ),
            "sourceText": row.get(
                "sourceText"
            ),
            "sourceUrl": row.get(
                "sourceUrl"
            ),
            "sourceLinks": (
                self._parse_links(
                    row.get(
                        "sourceLinks"
                    )
                )
            ),
            "semanticRole": row.get(
                "semanticRole"
            ),
            "relatedEntityId": (
                row.get(
                    "relatedEntityId"
                )
            ),
            "relatedEntityName": (
                row.get(
                    "relatedEntityName"
                )
            ),
        }

    def _parse_links(
        self,
        value,
    ):
        if value is None:
            return []

        if isinstance(
            value,
            list,
        ):
            return value

        if not isinstance(
            value,
            str,
        ):
            return [
                str(value)
            ]

        value = value.strip()

        if not value:
            return []

        if (
            value.startswith("[")
            and value.endswith("]")
        ):
            try:
                parsed = json.loads(
                    value
                )

                if isinstance(
                    parsed,
                    list,
                ):
                    return [
                        str(item)
                        for item
                        in parsed
                    ]
            except json.JSONDecodeError:
                pass

        return [
            value
        ]