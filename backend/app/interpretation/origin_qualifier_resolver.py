from app.interpretation.verification_semantic_matcher import (
    get_verification_semantic_matcher,
)


class OriginQualifierResolver:
    def __init__(
        self,
    ):
        self.semantic_cache = {}

    def is_inconclusive(
        self,
        text: str,
    ):
        if self._positive_certainty_assertion(text):
            return False

        lexical = any(
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
                "remains unsettled",
                "remain unsettled",
                "is unsettled",
                "still unsettled",
                "has not been determined",
                "have not determined",
                "not been determined",
            )
        )

        if lexical:
            return True

        return (
            self._semantic_score(
                text,
                "origin_inconclusive",
            )
            >= 0.78
        )

    def is_uncertain_lab_claim(
        self,
        text: str,
    ):
        if self._positive_certainty_assertion(text):
            return False

        if self._lexical_lab_uncertainty(text):
            return True

        if self._lexical_ruled_out(text):
            return False

        return (
            self._semantic_score(
                text,
                "origin_lab_uncertain",
            )
            >= 0.80
        )

    def is_ruled_out(
        self,
        text: str,
    ):
        if self._lexical_uncertainty_guard(text):
            return False

        if self._lexical_ruled_out(text):
            return True

        return (
            self._semantic_score(
                text,
                "origin_lab_ruled_out",
            )
            >= 0.82
        )

    def is_negative_support_claim(
        self,
        text: str,
    ):
        lexical = any(
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
                "do not support",
                "did not support",
                "not supported by evidence",
                "lacks supporting evidence",
                "lack supporting evidence",
                "fails to support",
                "fail to support",
                "failed to support",
                "without supporting evidence",
                "without evidence supporting",
            )
        )

        if lexical:
            return True

        if self._is_question(text):
            return False

        negative = self._semantic_score(
            text,
            "origin_negative_support",
        )

        positive = self._semantic_score(
            text,
            "origin_positive_support",
        )

        return negative >= 0.68 and (negative - positive) >= 0.04

    def is_positive_support_claim(
        self,
        text: str,
    ):
        if self.is_negative_support_claim(text):
            return False

        distinction = any(
            value in text
            for value in (
                "different claim from",
                "different claims from",
                "different from saying",
                "not the same as saying",
                "is not the same as",
                "isn't the same as",
                "does not mean",
                "doesn't mean",
                "not equivalent to",
                "distinct from saying",
            )
        )

        if distinction:
            return False

        lexical = any(
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
                "additional evidence supports",
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
                "data favor",
                "data favors",
                "data favour",
                "data favours",
                "data point toward",
                "data points toward",
                "evidence points toward",
            )
        )

        if lexical:
            return True

        if self._is_question(text):
            return False

        positive = self._semantic_score(
            text,
            "origin_positive_support",
        )

        negative = self._semantic_score(
            text,
            "origin_negative_support",
        )

        return positive >= 0.63 and (positive - negative) >= 0.04

    def is_certainty_overclaim(
        self,
        text: str,
    ):
        if self._negative_establishment(text):
            return False

        if self._positive_certainty_assertion(text):
            return True

        certainty_score = self._semantic_score(
            text,
            "origin_certainty",
        )

        inconclusive_score = self._semantic_score(
            text,
            "origin_inconclusive",
        )

        return (
            certainty_score >= 0.70 and (certainty_score - inconclusive_score) >= 0.03
        )

    def is_broad_certainty_claim(
        self,
        text: str,
    ):
        if self._negative_establishment(text):
            return False

        if self._positive_certainty_assertion(text):
            return True

        broad_score = self._semantic_score(
            text,
            "origin_broad_certainty",
        )

        inconclusive_score = self._semantic_score(
            text,
            "origin_inconclusive",
        )

        return broad_score >= 0.74 and (broad_score - inconclusive_score) >= 0.03

    def _positive_certainty_assertion(
        self,
        text: str,
    ):
        if self._negative_establishment(text):
            return False

        certainty = any(
            value in text
            for value in (
                "conclusive",
                "conclusively",
                "definitive",
                "definitively",
                "definite",
                "certain",
                "certainty",
                "beyond doubt",
                "without doubt",
                "complete certainty",
                "absolute certainty",
                "fully established",
                "completely established",
            )
        )

        establishment = any(
            value in text
            for value in (
                "proven",
                "proved",
                "established",
                "demonstrated",
                "confirmed",
                "known",
                "settled",
                "resolved",
                "determined",
                "identified",
            )
        )

        exactness = any(
            value in text
            for value in (
                "exact",
                "exactly",
                "precise",
                "precisely",
            )
        )

        direct_certainty = any(
            value in text
            for value in (
                "beyond doubt",
                "without doubt",
                "proven origin",
                "proved origin",
                "certain origin",
                "definite origin",
                "origin has been settled",
                "origin is settled",
                "origin has been resolved",
                "origin is resolved",
                "exact origin is known",
                "origin is known exactly",
                "know exactly how",
                "knows exactly how",
                "know the exact origin",
                "knows the exact origin",
            )
        )

        return (
            direct_certainty
            or (certainty and establishment)
            or (exactness and establishment)
        )

    def _lexical_lab_uncertainty(
        self,
        text: str,
    ):
        cannot = any(
            value in text
            for value in (
                "cannot",
                "can not",
                "could not",
                "couldn't",
                "unable to",
            )
        )

        exclusion = any(
            value in text
            for value in (
                "rule out",
                "ruled out",
                "exclude",
                "excluded",
                "dismiss",
                "dismissed",
                "eliminate",
                "eliminated",
                "reject",
                "rejected",
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
                "verify",
                "verified",
            )
        )

        possibility = any(
            value in text
            for value in (
                "possible",
                "possibly",
                "plausible",
                "plausibly",
                "remains possible",
                "remains plausible",
                "could be",
                "may be",
            )
        )

        non_establishment = any(
            value in text
            for value in (
                "unproven",
                "not proven",
                "not been proven",
                "not conclusively proven",
                "not been conclusively proven",
                "not demonstrated",
                "not been demonstrated",
                "not established",
                "not been established",
                "not conclusively established",
                "not been conclusively established",
                "not confirmed",
                "not been confirmed",
                "unconfirmed",
                "not verified",
                "not been verified",
            )
        )

        paired_uncertainty = cannot and exclusion and establishment

        possibility_uncertainty = possibility and non_establishment

        neither_pattern = "neither" in text and establishment and exclusion

        return paired_uncertainty or possibility_uncertainty or neither_pattern

    def _lexical_uncertainty_guard(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "cannot rule out",
                "cannot be ruled out",
                "can not rule out",
                "can not be ruled out",
                "could not rule out",
                "couldn't rule out",
                "cannot exclude",
                "cannot be excluded",
                "can not exclude",
                "can not be excluded",
                "not ruled out",
                "has not been ruled out",
                "not excluded",
                "has not been excluded",
                "not dismissed",
                "has not been dismissed",
                "not eliminated",
                "has not been eliminated",
            )
        )

    def _lexical_ruled_out(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "ruled out",
                "completely ruled out",
                "definitively ruled out",
                "excluded as an origin",
                "excluded as the origin",
                "excluded as a possible origin",
                "has been excluded",
                "was excluded",
                "is excluded",
                "dismissed as impossible",
                "dismissed as an origin",
                "eliminated as a possibility",
                "eliminated as an origin",
                "shown impossible",
                "demonstrated impossible",
                "impossible as an origin",
            )
        )

    def _negative_establishment(
        self,
        text: str,
    ):
        return any(
            value in text
            for value in (
                "not proven",
                "not been proven",
                "not conclusively proven",
                "not been conclusively proven",
                "not definitively proven",
                "not been definitively proven",
                "unproven",
                "not proved",
                "not been proved",
                "not established",
                "not been established",
                "not conclusively established",
                "not been conclusively established",
                "not definitively established",
                "not been definitively established",
                "not demonstrated",
                "not been demonstrated",
                "not confirmed",
                "not been confirmed",
                "not known",
                "do not know",
                "don't know",
                "does not know",
                "doesn't know",
                "cannot determine",
                "can't determine",
                "not been determined",
                "not determined",
                "have not determined",
                "has not determined",
                "cannot identify",
                "can't identify",
                "not identified",
                "not been identified",
                "have not identified",
                "has not identified",
                "did not identify",
                "not settled",
                "unsettled",
                "not resolved",
                "unresolved",
                "uncertain",
                "inconclusive",
            )
        )

    def _is_question(
        self,
        text: str,
    ):
        stripped = text.strip()

        if stripped.endswith("?"):
            return True

        normalized = stripped.lower()

        return normalized.startswith(
            (
                "what ",
                "which ",
                "who ",
                "where ",
                "when ",
                "why ",
                "how ",
                "is ",
                "are ",
                "was ",
                "were ",
                "do ",
                "does ",
                "did ",
                "can ",
                "could ",
                "has ",
                "have ",
                "had ",
                "will ",
                "would ",
                "should ",
            )
        )

    def _semantic_score(
        self,
        text: str,
        label: str,
    ):
        scores = self._semantic_scores(text)

        return scores.get(
            label,
            0.0,
        )

    def _semantic_scores(
        self,
        text: str,
    ):
        if text in self.semantic_cache:
            return self.semantic_cache[text]

        matcher = get_verification_semantic_matcher()

        rankings = matcher.rank_origin_propositions(text)

        scores = {item["label"]: item["score"] for item in rankings}

        if len(self.semantic_cache) >= 256:
            self.semantic_cache.clear()

        self.semantic_cache[text] = scores

        return scores
