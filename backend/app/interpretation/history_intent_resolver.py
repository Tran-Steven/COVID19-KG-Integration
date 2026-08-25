import re


class HistoryIntentResolver:
    COVID_PATTERNS = [
        r"\bcovid(?:-19)?\b",
        r"\bcoronavirus disease 2019\b",
        r"\bchinese virus\b",
    ]

    INITIAL_EVENT_PHRASES = [
        "first found",
        "first identified",
        "first detected",
        "first discovered",
        "first reported",
        "initially found",
        "initially identified",
        "initially detected",
        "initially reported",
    ]

    LOCATION_QUESTION_PHRASES = [
        "where",
        "what city",
        "which city",
        "what location",
        "which location",
        "what country",
        "which country",
    ]

    DATE_QUESTION_PHRASES = [
        "when",
        "what date",
        "which date",
    ]

    def resolve(
        self,
        text: str,
    ):
        normalized = self._normalize(
            text
        )

        if not self._has_covid_reference(
            normalized
        ):
            return None

        if (
            "pandemic" in normalized
            and self._is_date_question(
                normalized
            )
        ):
            return {
                "intent": (
                    "pandemic_characterization_date"
                ),
                "canonicalSubject": "COVID-19",
                "eventType": (
                    "pandemic_characterization"
                ),
                "semanticRole": None,
                "requestedField": "date",
                "matchedText": "pandemic",
                "method": "rule",
            }

        initial_phrase = (
            self._find_phrase(
                normalized,
                self.INITIAL_EVENT_PHRASES,
            )
        )

        if initial_phrase is None:
            return None

        if self._is_location_question(
            normalized
        ):
            return {
                "intent": (
                    "initial_outbreak_location"
                ),
                "canonicalSubject": "COVID-19",
                "eventType": (
                    "initial_outbreak_report"
                ),
                "semanticRole": (
                    "reported_case_location"
                ),
                "requestedField": (
                    "location"
                ),
                "matchedText": (
                    initial_phrase
                ),
                "method": "rule",
            }

        if self._is_date_question(
            normalized
        ):
            return {
                "intent": (
                    "initial_outbreak_date"
                ),
                "canonicalSubject": "COVID-19",
                "eventType": (
                    "initial_outbreak_report"
                ),
                "semanticRole": None,
                "requestedField": "date",
                "matchedText": (
                    initial_phrase
                ),
                "method": "rule",
            }

        return None

    def _normalize(
        self,
        text: str,
    ):
        lowered = text.lower()

        lowered = re.sub(
            r"[^\w\s-]",
            " ",
            lowered,
        )

        lowered = re.sub(
            r"\s+",
            " ",
            lowered,
        )

        return lowered.strip()

    def _has_covid_reference(
        self,
        text: str,
    ):
        return any(
            re.search(
                pattern,
                text,
            )
            is not None
            for pattern
            in self.COVID_PATTERNS
        )

    def _is_location_question(
        self,
        text: str,
    ):
        return any(
            phrase in text
            for phrase
            in self.LOCATION_QUESTION_PHRASES
        )

    def _is_date_question(
        self,
        text: str,
    ):
        return any(
            phrase in text
            for phrase
            in self.DATE_QUESTION_PHRASES
        )

    def _find_phrase(
        self,
        text: str,
        phrases: list[str],
    ):
        for phrase in phrases:
            if phrase in text:
                return phrase

        return None