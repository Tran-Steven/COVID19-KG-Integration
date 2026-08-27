import re


class PropositionSemantics:
    DISCOURSE_ONLY = re.compile(
        (
            r"^\s*(?:"
            r"yes"
            r"|no"
            r"|true"
            r"|false"
            r"|correct"
            r"|incorrect"
            r"|that is correct"
            r"|that is incorrect"
            r"|that is true"
            r"|that is false"
            r"|that statement is correct"
            r"|that statement is incorrect"
            r"|that statement is true"
            r"|that statement is false"
            r")\s*[.!]?\s*$"
        ),
        flags=re.IGNORECASE,
    )

    NEGATION = re.compile(
        (
            r"\b(?:"
            r"not"
            r"|never"
            r"|cannot"
            r"|can not"
            r"|can't"
            r"|does not"
            r"|doesn't"
            r"|do not"
            r"|don't"
            r"|did not"
            r"|didn't"
            r"|no longer"
            r"|zero"
            r"|nothing"
            r"|incapable"
            r")\b"
        ),
        flags=re.IGNORECASE,
    )

    ABSOLUTE_LIMITATION = (
        "not absolute",
        "isn't absolute",
        "is not absolute",
        "are not absolute",
        "does not guarantee",
        "doesn't guarantee",
        "do not guarantee",
        "don't guarantee",
        "cannot guarantee",
        "can't guarantee",
        "does not completely prevent",
        "doesn't completely prevent",
        "do not completely prevent",
        "don't completely prevent",
        "does not completely stop",
        "doesn't completely stop",
        "do not completely stop",
        "don't completely stop",
        "does not make severe illness impossible",
        "doesn't make severe illness impossible",
        "do not make severe illness impossible",
        "don't make severe illness impossible",
        "does not make infection impossible",
        "doesn't make infection impossible",
        "do not make infection impossible",
        "don't make infection impossible",
    )

    NON_RELATION_NEGATION = (
        "not absolute",
        "not completely ruled out",
        "not been completely ruled out",
        "cannot be ruled out",
        "can not be ruled out",
        "could not be ruled out",
        "not proven",
        "not been proven",
        "not conclusively proven",
        "not confirmed",
        "not been confirmed",
        "not resolved",
        "not been resolved",
        "not definitively resolved",
        "not conclusively resolved",
        "not known",
        "not known with certainty",
        "does not necessarily mean",
        "doesn't necessarily mean",
        "does not appear to pose additional",
        "doesn't appear to pose additional",
        "does not pose additional",
        "doesn't pose additional",
    )

    def normalize(
        self,
        text: str,
    ):
        normalized = text.lower()

        normalized = (
            normalized
            .replace(
                "’",
                "'",
            )
            .replace(
                "–",
                "-",
            )
            .replace(
                "—",
                "-",
            )
        )

        normalized = re.sub(
            r"[_/\-]+",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"[^a-z0-9'\s]+",
            " ",
            normalized,
        )

        return re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

    def is_discourse_only(
        self,
        text: str,
    ):
        return (
            self.DISCOURSE_ONLY.match(
                text
            )
            is not None
        )

    def is_absolute_limitation(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        return any(
            value in normalized
            for value
            in self.ABSOLUTE_LIMITATION
        )

    def is_relation_negated(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        if self.is_no_additional_risk_claim(
            text
        ):
            return False

        if any(
            value in normalized
            for value
            in self.NON_RELATION_NEGATION
        ):
            return False

        if any(
            value in normalized
            for value in (
                "zero protection",
                "nothing to do with",
                "no connection between",
                "no connection to",
                "no relationship between",
                "no relationship to",
                "no relation between",
                "no relation to",
                "incapable of",
            )
        ):
            return True

        return (
            self.NEGATION.search(
                normalized
            )
            is not None
        )

    def is_origin_inconclusive(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        return any(
            value in normalized
            for value in (
                "origin remains inconclusive",
                "origin is inconclusive",
                "origin remains unresolved",
                "origin is unresolved",
                "origin remains unknown",
                "origin is unknown",
                "exact origin is still not known",
                "exact origin is not known",
                "exact origin remains unknown",
                "not known with certainty",
                "do not know the exact origin",
                "don't know the exact origin",
                "not definitively resolved",
                "not conclusively resolved",
                "has not been definitively resolved",
                "has not been conclusively resolved",
                "precise origin remains unresolved",
                "precise pathway remains uncertain",
                "origin remains uncertain",
            )
        )

    def is_lab_uncertainty(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        laboratory = any(
            value in normalized
            for value in (
                "laboratory",
                "lab associated",
                "lab related",
                "lab origin",
                "lab event",
                "lab leak",
            )
        )

        uncertainty = any(
            value in normalized
            for value in (
                "cannot be ruled out",
                "can not be ruled out",
                "not completely ruled out",
                "not been completely ruled out",
                "could not be ruled out",
                "cannot be excluded",
                "can not be excluded",
                "cannot be confirmed or excluded",
                "cannot currently be confirmed or excluded",
                "not proven",
                "not been proven",
                "not conclusively proven",
                "remains possible",
                "remain possible",
                "remains a possibility",
                "no conclusive evidence",
                "no definitive evidence",
                "cannot be established",
            )
        )

        return (
            laboratory
            and uncertainty
        )

    def is_no_additional_risk_claim(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        if (
            "no additional public health risk"
            in normalized
        ):
            return True

        return (
            re.search(
                (
                    r"\b(?:does not|doesn't|doesnt|doesn t)\s+"
                    r"(?:currently\s+)?"
                    r"(?:(?:appear|seem) to\s+)?"
                    r"(?:currently\s+)?"
                    r"pose\s+"
                    r"(?:an\s+)?"
                    r"additional\s+"
                    r"public health risk\b"
                ),
                normalized,
            )
            is not None
        )

    def explicit_years(
        self,
        text: str,
    ):
        return [
            int(value)
            for value
            in re.findall(
                r"\b(?:19|20)\d{2}\b",
                text,
            )
        ]

    def has_current_language(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        return any(
            value in normalized
            for value in (
                "current",
                "currently",
                "latest",
                "present",
                "presently",
                "as of today",
                "now rated",
            )
        )

    def is_non_covid_vaccine(
        self,
        text: str,
    ):
        normalized = self.normalize(
            text
        )

        return any(
            value in normalized
            for value in (
                "measles vaccine",
                "measles containing vaccine",
                "mmr vaccine",
                "mmr vaccination",
                "influenza vaccine",
                "influenza vaccination",
                "flu vaccine",
                "flu vaccination",
                "polio vaccine",
                "polio vaccination",
                "hepatitis vaccine",
                "hepatitis vaccination",
            )
        )