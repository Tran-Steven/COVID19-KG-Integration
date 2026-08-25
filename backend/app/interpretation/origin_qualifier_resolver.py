class OriginQualifierResolver:
    def is_inconclusive(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "remains inconclusive",
                "remain inconclusive",
                "is inconclusive",
                "still inconclusive",
                "origin is unknown",
                "origin remains unknown",
                "remains unresolved",
                "remain unresolved",
                "is unresolved",
                "still unresolved",
                "origin is unresolved",
                "origin remains unresolved",
                "remains undetermined",
                "remain undetermined",
                "is undetermined",
                "still undetermined",
                "origin is undetermined",
                "origin remains undetermined",
                "origin has not been settled",
                "origin is not settled",
            )
        )

    def is_uncertain_lab_claim(
        self,
        text: str,
    ):
        uncertainty = any(
            value in text
            for value in (
                "cannot",
                "can not",
                "could not",
                "couldn't",
            )
        )

        exclusion = any(
            value in text
            for value in (
                "rule out",
                "ruled out",
                "exclude",
                "excluded",
            )
        )

        establishment = any(
            value in text
            for value in (
                "prove",
                "proven",
                "proved",
                "confirm",
                "confirmed",
                "establish",
                "established",
                "demonstrate",
                "demonstrated",
            )
        )

        return (
            uncertainty
            and exclusion
            and establishment
        )

    def is_ruled_out(
        self,
        text: str,
    ):
        uncertainty = any(
            value in text
            for value in (
                "cannot",
                "can not",
                "could not",
                "couldn't",
                "not ruled out",
                "not excluded",
            )
        )

        if uncertainty:
            return False

        return any(
            value in text
            for value in (
                "ruled out",
                "completely ruled out",
                "definitively ruled out",
                "excluded as an origin",
                "excluded as the origin",
                "excluded as a possible origin",
                "impossible",
                "impossible as an origin",
            )
        )

    def is_negative_support_claim(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "no evidence supports",
                "no evidence supporting",
                "no scientific evidence supports",
                "no scientific evidence supporting",
                "no additional evidence supports",
                "no additional evidence supporting",
                "does not support",
                "doesn't support",
                "not supported by evidence",
                "lacks supporting evidence",
                "lack supporting evidence",
            )
        )

    def is_positive_support_claim(
        self,
        text: str,
    ):
        if self.is_negative_support_claim(
            text
        ):
            return False

        return any(
            value in text
            for value in (
                "better supported",
                "best supported",
                "more strongly supported",
                "most strongly supported",
                "strongly supported",
                "well supported",
                "evidence supports",
                "evidence strongly supports",
                "supported than natural",
                "new evidence supports",
                "more likely than",
                "strong evidence",
                "strong new evidence",
                "evidence favors",
                "evidence favours",
                "strongly favors",
                "strongly favours",
                "strongest evidence",
                "strongest support",
                "strongest evidentiary support",
            )
        )

    def is_certainty_overclaim(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "conclusively proven",
                "conclusively proved",
                "definitively proven",
                "definitively proved",
                "definitely proven",
                "definitely proved",
                "proven beyond doubt",
                "proved beyond doubt",
                "established beyond doubt",
                "beyond any doubt",
                "beyond doubt",
                "definite origin",
                "certain origin",
                "proven origin",
                "proved origin",
            )
        )

    def is_broad_certainty_claim(
        self,
        text: str,
    ):
        if self.is_certainty_overclaim(
            text
        ):
            return True

        return any(
            value in text
            for value in (
                "know exactly how",
                "knows exactly how",
                "know the exact origin",
                "knows the exact origin",
                "exact origin is known",
                "origin is known exactly",
                "origin is definitely known",
                "origin is definitively known",
                "origin is conclusively known",
                "origin has been conclusively proven",
                "origin has been definitively proven",
                "origin has been proven",
                "exact origin has been established",
                "definitively established the exact origin",
                "conclusively established the exact origin",
            )
        )