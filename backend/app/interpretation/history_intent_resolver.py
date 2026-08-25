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

    INITIAL_REPORT_CONTEXT = [
        "wuhan pneumonia report",
        "wuhan outbreak report",
        "wuhan viral pneumonia",
        "viral pneumonia cases",
        "who china country office",
        "who linked wuhan",
        "who-linked wuhan",
    ]

    PANDEMIC_ASSERTION_PHRASES = [
        "characterized",
        "characterised",
        "declared",
        "became a pandemic",
        "became pandemic",
        "was a pandemic",
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

    MONTHS = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    def resolve(
        self,
        text: str,
    ):
        normalized = self._normalize(
            text
        )

        has_covid = (
            self._has_covid_reference(
                normalized
            )
        )

        has_initial_context = (
            self._has_initial_report_context(
                normalized
            )
        )

        if (
            "pandemic" in normalized
            and has_covid
        ):
            if (
                self._is_date_question(
                    normalized
                )
                or self._has_date_expression(
                    normalized
                )
                or self._has_pandemic_assertion(
                    normalized
                )
            ):
                return {
                    "intent": (
                        "pandemic_characterization_date"
                    ),
                    "canonicalSubject": (
                        "COVID-19"
                    ),
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

        if (
            initial_phrase is None
            and not has_initial_context
        ):
            return None

        if (
            not has_covid
            and not has_initial_context
        ):
            return None

        matched_text = (
            initial_phrase
            or self._find_phrase(
                normalized,
                self.INITIAL_REPORT_CONTEXT,
            )
        )

        if self._is_location_question(
            normalized
        ):
            return (
                self._initial_location(
                    matched_text
                )
            )

        if self._is_date_question(
            normalized
        ):
            return (
                self._initial_date(
                    matched_text
                )
            )

        if self._has_date_expression(
            normalized
        ):
            return (
                self._initial_date(
                    matched_text
                )
            )

        if self._has_wuhan_location_claim(
            normalized
        ):
            return (
                self._initial_location(
                    matched_text
                )
            )

        return None

    def _initial_location(
        self,
        matched_text: str | None,
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
            "requestedField": "location",
            "matchedText": matched_text,
            "method": "rule",
        }

    def _initial_date(
        self,
        matched_text: str | None,
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
            "matchedText": matched_text,
            "method": "rule",
        }

    def _normalize(
        self,
        text: str,
    ):
        lowered = text.lower()

        lowered = re.sub(
            r"[_/]+",
            " ",
            lowered,
        )

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

    def _has_initial_report_context(
        self,
        text: str,
    ):
        return any(
            phrase in text
            for phrase
            in self.INITIAL_REPORT_CONTEXT
        )

    def _has_pandemic_assertion(
        self,
        text: str,
    ):
        return any(
            phrase in text
            for phrase
            in self.PANDEMIC_ASSERTION_PHRASES
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

    def _has_date_expression(
        self,
        text: str,
    ):
        month_pattern = (
            "|".join(
                self.MONTHS
            )
        )

        if re.search(
            (
                r"\b(?:"
                + month_pattern
                + r")\b"
            ),
            text,
        ):
            return True

        return (
            re.search(
                r"\b(?:19|20)\d{2}\b",
                text,
            )
            is not None
        )

    def _has_wuhan_location_claim(
        self,
        text: str,
    ):
        if "wuhan" not in text:
            return False

        return any(
            phrase in text
            for phrase in (
                "reported in wuhan",
                "found in wuhan",
                "identified in wuhan",
                "detected in wuhan",
                "discovered in wuhan",
                "cases in wuhan",
            )
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