import json
import re
from datetime import datetime

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

    MONTHS = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "sept": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
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

        status = self._resolve_status(
            text=text,
            interpretation=(
                interpretation
            ),
            rows=rows,
        )

        return {
            "text": text,
            "status": status,
            "interpretation": (
                interpretation
            ),
            "answer": answer,
            "evidence": evidence,
        }

    def _resolve_status(
        self,
        text: str,
        interpretation: dict,
        rows: list[dict],
    ):
        if self._is_question(
            text
        ):
            return "SUPPORTED"

        requested_field = (
            interpretation[
                "requestedField"
            ]
        )

        if requested_field == "date":
            claimed_date = (
                self._extract_date_claim(
                    text
                )
            )

            if claimed_date is None:
                return (
                    "INSUFFICIENT_EVIDENCE"
                )

            evidence_dates = [
                row.get(
                    "dateStart"
                )
                for row in rows
                if row.get(
                    "dateStart"
                )
            ]

            if not evidence_dates:
                return (
                    "INSUFFICIENT_EVIDENCE"
                )

            if any(
                self._date_matches(
                    claimed_date,
                    evidence_date,
                )
                for evidence_date
                in evidence_dates
            ):
                return "SUPPORTED"

            return "CONTRADICTED"

        if requested_field == "location":
            evidence_locations = [
                row.get(
                    "relatedEntityName"
                )
                for row in rows
                if row.get(
                    "relatedEntityName"
                )
            ]

            if not evidence_locations:
                return (
                    "INSUFFICIENT_EVIDENCE"
                )

            claimed_location = (
                self._extract_location_claim(
                    text
                )
            )

            if claimed_location:
                if any(
                    self._location_matches(
                        claimed_location,
                        evidence_location,
                    )
                    for evidence_location
                    in evidence_locations
                ):
                    return "SUPPORTED"

                return "CONTRADICTED"

            normalized_text = (
                self._normalize(
                    text
                )
            )

            if any(
                self._location_mentioned(
                    normalized_text,
                    evidence_location,
                )
                for evidence_location
                in evidence_locations
            ):
                return "SUPPORTED"

            return (
                "INSUFFICIENT_EVIDENCE"
            )

        return (
            "INSUFFICIENT_EVIDENCE"
        )

    def _extract_date_claim(
        self,
        text: str,
    ):
        normalized = (
            self._normalize(
                text
            )
        )

        month_names = (
            "|".join(
                sorted(
                    self.MONTHS,
                    key=len,
                    reverse=True,
                )
            )
        )

        full_date_patterns = (
            (
                r"\b("
                + month_names
                + r")\s+"
                r"(\d{1,2})\s+"
                r"((?:19|20)\d{2})\b"
            ),
            (
                r"\b(\d{1,2})\s+("
                + month_names
                + r")\s+"
                r"((?:19|20)\d{2})\b"
            ),
        )

        match = re.search(
            full_date_patterns[0],
            normalized,
        )

        if match:
            return {
                "precision": "day",
                "year": int(
                    match.group(3)
                ),
                "month": (
                    self.MONTHS[
                        match.group(1)
                    ]
                ),
                "day": int(
                    match.group(2)
                ),
            }

        match = re.search(
            full_date_patterns[1],
            normalized,
        )

        if match:
            return {
                "precision": "day",
                "year": int(
                    match.group(3)
                ),
                "month": (
                    self.MONTHS[
                        match.group(2)
                    ]
                ),
                "day": int(
                    match.group(1)
                ),
            }

        month_year = re.search(
            (
                r"\b("
                + month_names
                + r")\s+"
                r"((?:19|20)\d{2})\b"
            ),
            normalized,
        )

        if month_year:
            return {
                "precision": "month",
                "year": int(
                    month_year.group(2)
                ),
                "month": (
                    self.MONTHS[
                        month_year.group(1)
                    ]
                ),
                "day": None,
            }

        year = re.search(
            r"\b((?:19|20)\d{2})\b",
            normalized,
        )

        if year:
            return {
                "precision": "year",
                "year": int(
                    year.group(1)
                ),
                "month": None,
                "day": None,
            }

        return None

    def _date_matches(
        self,
        claimed: dict,
        evidence_date: str,
    ):
        try:
            parsed = datetime.strptime(
                evidence_date[:10],
                "%Y-%m-%d",
            )
        except (
            ValueError,
            TypeError,
        ):
            return False

        if (
            claimed[
                "year"
            ]
            != parsed.year
        ):
            return False

        if (
            claimed[
                "precision"
            ]
            == "year"
        ):
            return True

        if (
            claimed[
                "month"
            ]
            != parsed.month
        ):
            return False

        if (
            claimed[
                "precision"
            ]
            == "month"
        ):
            return True

        return (
            claimed[
                "day"
            ]
            == parsed.day
        )

    def _extract_location_claim(
        self,
        text: str,
    ):
        normalized = (
            self._normalize(
                text
            )
        )

        patterns = (
            r"\bfirst reported in ([a-z][a-z\s-]*)$",
            r"\bfirst found in ([a-z][a-z\s-]*)$",
            r"\bfirst detected in ([a-z][a-z\s-]*)$",
            r"\bfirst identified in ([a-z][a-z\s-]*)$",
            r"\breported in ([a-z][a-z\s-]*)$",
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                normalized,
            )

            if match:
                return (
                    match.group(1)
                    .strip()
                )

        return None

    def _location_matches(
        self,
        claimed_location: str,
        evidence_location: str,
    ):
        claimed = self._normalize(
            claimed_location
        )

        evidence = self._normalize(
            evidence_location
        )

        if not claimed or not evidence:
            return False

        if claimed == evidence:
            return True

        primary_location = (
            evidence_location
            .split(
                ",",
                1,
            )[0]
        )

        primary = self._normalize(
            primary_location
        )

        if (
            primary
            and claimed == primary
        ):
            return True

        if evidence.startswith(
            claimed + " "
        ):
            return True

        return False

    def _location_mentioned(
        self,
        normalized_text: str,
        evidence_location: str,
    ):
        evidence = self._normalize(
            evidence_location
        )

        if (
            evidence
            and evidence
            in normalized_text
        ):
            return True

        primary_location = (
            evidence_location
            .split(
                ",",
                1,
            )[0]
        )

        primary = self._normalize(
            primary_location
        )

        if not primary:
            return False

        return (
            re.search(
                (
                    r"\b"
                    + re.escape(
                        primary
                    )
                    + r"\b"
                ),
                normalized_text,
            )
            is not None
        )

    def _is_question(
        self,
        text: str,
    ):
        stripped = (
            text.strip()
        )

        if stripped.endswith(
            "?"
        ):
            return True

        normalized = (
            self._normalize(
                stripped
            )
        )

        return any(
            normalized.startswith(
                value
            )
            for value in (
                "when ",
                "where ",
                "what date ",
                "which date ",
                "what city ",
                "which city ",
                "what location ",
                "which location ",
            )
        )

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

    def _normalize(
        self,
        text: str,
    ):
        lowered = (
            text.lower()
        )

        lowered = re.sub(
            r"[_/]+",
            " ",
            lowered,
        )

        lowered = re.sub(
            r"[^a-z0-9\s-]",
            " ",
            lowered,
        )

        return re.sub(
            r"\s+",
            " ",
            lowered,
        ).strip()