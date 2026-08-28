import re

from spacy.language import Language

from app.interpretation.proposition_semantics import PropositionSemantics


class ResponseClaimExtractor:
    LIST_SCOPE_HEADER = re.compile(
        (
            r"^\s*"
            r"(?P<subject>.+?)\s+"
            r"(?P<aux>do|does)\s*"
            r"(?P<neg>not)?"
            r"\s*:\s*$"
        ),
        flags=re.IGNORECASE,
    )
    TRANSITION_START = re.compile(
        (
            r"^\s*(?:"
            r"so\b"
            r"|overall\b"
            r"|in short\b"
            r"|in summary\b"
            r"|however\b"
            r"|importantly\b"
            r"|the main\b"
            r")"
        ),
        flags=re.IGNORECASE,
    )
    CONTRAST_SEPARATOR = re.compile(
        (
            r",?\s+"
            r"(?:although|though|but)"
            r"\s+"
        ),
        flags=re.IGNORECASE,
    )
    TOPIC_LABEL = re.compile(
        (
            r"^"
            r"(?P<label>[^:\n]{1,60})"
            r":\s+"
            r"(?P<content>.+)$"
        )
    )
    PRONOUN_START = re.compile(
        (
            r"^(?P<pronoun>"
            r"it|they|this|that|these|those"
            r")\b"
        ),
        flags=re.IGNORECASE,
    )
    BLOCKED_INHERITANCE_STARTS = {
        "because",
        "for",
        "if",
        "unless",
        "when",
        "where",
        "while",
        "which",
        "who",
        "whose",
    }

    def __init__(
        self,
        nlp,
    ):
        self._init_core(nlp)

        self.semantics = PropositionSemantics()

    def extract(
        self,
        text: str,
    ):
        base_claims = self._extract_core(text)

        (
            section_ranges,
            section_claims,
        ) = self._section_claims(text)

        candidates = []

        for claim in base_claims:
            if self._inside_ranges(
                claim["start"],
                section_ranges,
            ):
                continue

            cleaned = self._clean_topic_label(claim)

            if self.semantics.is_discourse_only(cleaned["text"]):
                continue

            candidates.extend(self._split_contrast_claim(cleaned))

        candidates.extend(section_claims)

        candidates.sort(
            key=lambda value: (
                value["start"],
                value["end"],
            )
        )

        claims = []
        seen = set()

        for claim in candidates:
            claim_text = claim["text"].strip()

            if not claim_text:
                continue

            if self.semantics.is_discourse_only(claim_text):
                continue

            key = self._normalize(claim_text)

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)

            claims.append(
                {
                    "index": (len(claims) + 1),
                    "text": claim_text,
                    "start": claim["start"],
                    "end": claim["end"],
                    "method": claim["method"],
                }
            )

        return claims

    def _section_claims(
        self,
        text: str,
    ):
        ranges = []
        claims = []

        subject = None
        negated = False

        for match in re.finditer(
            r"[^\r\n]+",
            text,
        ):
            raw = match.group(0)

            stripped = raw.strip()

            if not stripped:
                continue

            heading = self.LIST_SCOPE_HEADER.match(stripped)

            if heading:
                subject = heading.group("subject").strip()

                negated = bool(heading.group("neg"))

                ranges.append(
                    (
                        match.start(),
                        match.end(),
                    )
                )

                continue

            if subject is None:
                continue

            if stripped.endswith(":") or self.TRANSITION_START.match(stripped):
                subject = None
                negated = False
                continue

            list_prefix = self.LIST_PREFIX.match(stripped)

            if list_prefix:
                stripped = stripped[list_prefix.end() :].strip()

            if not stripped:
                continue

            reconstructed = self._reconstruct_section_claim(
                subject=subject,
                text=stripped,
                negated=negated,
            )

            if not reconstructed:
                continue

            if not self._is_factual_text(reconstructed):
                continue

            ranges.append(
                (
                    match.start(),
                    match.end(),
                )
            )

            claims.append(
                {
                    "text": reconstructed,
                    "start": (match.start()),
                    "end": (match.end()),
                    "method": ("list_scope_rule"),
                }
            )

        return (
            ranges,
            claims,
        )

    def _reconstruct_section_claim(
        self,
        subject: str,
        text: str,
        negated: bool,
    ):
        normalized_subject = self._normalize(subject)

        normalized_text = self._normalize(text)

        if not normalized_text:
            return None

        if normalized_text.startswith(normalized_subject):
            return text

        first = text[:1].lower() + text[1:] if text else text

        if negated:
            return f"{subject} do not {first}"

        return f"{subject} {first}"

    def _clean_topic_label(
        self,
        claim: dict,
    ):
        match = self.TOPIC_LABEL.match(claim["text"])

        if not match:
            return claim

        label = match.group("label")

        if not self._is_topic_label(label):
            return claim

        content = match.group("content").strip()

        if not content:
            return claim

        offset = match.start("content")

        return {
            **claim,
            "text": content,
            "start": (claim["start"] + offset),
        }

    def _split_contrast_claim(
        self,
        claim: dict,
    ):
        text = claim["text"]

        separator = self.CONTRAST_SEPARATOR.search(text)

        if not separator:
            return [claim]

        left_text = text[: separator.start()].strip(" ,;")

        right_text = text[separator.end() :].strip(" ,;")

        if not left_text or not right_text:
            return [claim]

        left_doc = self.nlp(left_text)

        subject = self._subject_phrase(left_doc)

        if subject:
            pronoun = self.PRONOUN_START.match(right_text)

            if pronoun:
                right_text = subject + right_text[pronoun.end() :]

        if not self._is_factual_text(left_text) or not self._is_factual_text(
            right_text
        ):
            return [claim]

        right_offset = separator.end()

        return [
            {
                **claim,
                "text": left_text,
                "end": (claim["start"] + separator.start()),
                "method": ("contrast_clause_rule"),
            },
            {
                **claim,
                "text": right_text,
                "start": (claim["start"] + right_offset),
                "method": ("contrast_clause_rule"),
            },
        ]

    def _is_factual_text(
        self,
        text: str,
    ):
        doc = self.nlp(text)

        return self._is_factual(
            doc,
            text,
        )

    def _inside_ranges(
        self,
        start: int,
        ranges: list[tuple[int, int]],
    ):
        return any(
            range_start <= start < range_end
            for (
                range_start,
                range_end,
            ) in ranges
        )

    def _can_inherit_subject(
        self,
        doc,
    ):
        meaningful = [
            token for token in doc if not token.is_space and not token.is_punct
        ]

        if meaningful:
            if meaningful[0].lower_ in self.BLOCKED_INHERITANCE_STARTS:
                return False

        return self._can_inherit_subject_core(doc)

    NON_FACTUAL_PREFIXES = (
        "i think",
        "i believe",
        "i hope",
        "i m sorry",
        "i am sorry",
        "i m not sure",
        "i am not sure",
        "not sure",
        "i m unsure",
        "i am unsure",
        "i don t know",
        "i do not know",
        "i can t say",
        "i cannot say",
        "i don t have enough information",
        "i do not have enough information",
        "let me know",
        "hope this helps",
        "thanks",
        "thank you",
    )

    META_TERMS = {
        "answer",
        "answers",
        "discussion",
        "overview",
        "point",
        "points",
        "recap",
        "response",
        "responses",
        "summary",
        "summarize",
        "summarizes",
        "summarized",
        "summarise",
        "summarises",
        "summarised",
    }

    PRESENTATIONAL_PREFIXES = (
        "here is",
        "here are",
        "here s",
        "below is",
        "below are",
        "the following is",
        "the following are",
        "this is a summary",
        "this is an overview",
        "this is a recap",
        "to summarize",
        "to summarise",
        "in summary",
        "in this summary",
        "in this overview",
        "in this recap",
    )

    CLAUSE_SEPARATOR = re.compile(
        (
            r"(?:,\s*)?"
            r"\b(?:and|but|although|though|whereas)\b\s+"
            r"|;\s*"
        ),
        flags=re.IGNORECASE,
    )

    LIST_PREFIX = re.compile(
        (
            r"^\s*(?:"
            r"[-*•▪◦]\s+"
            r"|\d+[.)]\s+"
            r")"
        )
    )

    FACTUAL_PREDICATE_PATTERN = re.compile(
        (
            r"\b(?:"
            r"cause(?:s|d)?"
            r"|spread(?:s)?"
            r"|transmit(?:s|ted)?"
            r"|reduce(?:s|d)?"
            r"|lower(?:s|ed)?"
            r"|protect(?:s|ed)?"
            r"|prevent(?:s|ed)?"
            r"|treat(?:s|ed)?"
            r"|cure(?:s|d)?"
            r"|guarantee(?:s|d)?"
            r"|stop(?:s|ped)?"
            r"|remain(?:s|ed)?"
            r"|support(?:s|ed)?"
            r"|favor(?:s|ed)?"
            r"|favour(?:s|ed)?"
            r"|increase(?:s|d)?"
            r"|damage(?:s|d)?"
            r"|identify|identifies|identified"
            r"|report|reports|reported"
            r"|characterize|characterizes|characterized"
            r"|characterise|characterises|characterised"
            r")\b"
        ),
        flags=re.IGNORECASE,
    )

    SUBJECT_DEPS = {
        "nsubj",
        "nsubjpass",
        "csubj",
        "csubjpass",
    }

    SUBJECT_PRONOUNS = {
        "he",
        "her",
        "hers",
        "him",
        "his",
        "it",
        "its",
        "she",
        "that",
        "their",
        "theirs",
        "them",
        "they",
        "this",
        "those",
        "these",
    }

    INHERITABLE_STARTS = {
        "am",
        "are",
        "can",
        "cannot",
        "could",
        "did",
        "do",
        "does",
        "had",
        "has",
        "have",
        "is",
        "may",
        "might",
        "must",
        "should",
        "was",
        "were",
        "will",
        "would",
    }

    NON_SUBJECT_PREFIX_WORDS = {
        "also",
        "always",
        "can",
        "cannot",
        "could",
        "did",
        "do",
        "does",
        "especially",
        "generally",
        "had",
        "has",
        "have",
        "is",
        "mainly",
        "may",
        "might",
        "must",
        "never",
        "not",
        "often",
        "possibly",
        "potentially",
        "probably",
        "should",
        "sometimes",
        "usually",
        "was",
        "were",
        "will",
        "would",
    }

    def _init_core(
        self,
        nlp: Language,
    ):
        self.nlp = nlp

    def _extract_core(
        self,
        text: str,
    ):
        claims = []
        seen = set()

        for block in self._logical_blocks(text):
            doc = self.nlp(block["text"])

            for sentence in doc.sents:
                prepared = self._prepare_sentence(
                    sentence.text,
                    (block["start"] + sentence.start_char),
                )

                if not prepared["text"]:
                    continue

                segments = self._sentence_segments(
                    prepared["text"],
                    prepared["start"],
                )

                for segment in segments:
                    claim_text = segment["text"]

                    claim_doc = self.nlp(claim_text)

                    if not self._is_factual(
                        claim_doc,
                        claim_text,
                    ):
                        continue

                    key = self._normalize(claim_text)

                    if key in seen:
                        continue

                    seen.add(key)

                    claims.append(
                        {
                            "index": (len(claims) + 1),
                            "text": claim_text,
                            "start": segment["start"],
                            "end": segment["end"],
                            "method": segment["method"],
                        }
                    )

        return claims

    def _logical_blocks(
        self,
        text: str,
    ):
        blocks = []

        for match in re.finditer(
            r"[^\r\n]+",
            text,
        ):
            raw_text = match.group(0)

            list_prefix = self.LIST_PREFIX.match(raw_text)

            prefix_end = list_prefix.end() if list_prefix else 0

            remaining = raw_text[prefix_end:]

            leading = re.match(
                r"^\s+",
                remaining,
            )

            leading_end = leading.end() if leading else 0

            cleaned = remaining[leading_end:].rstrip()

            (
                cleaned,
                correction_offset,
            ) = self._rejected_claim_correction_text(cleaned)

            if not cleaned:
                continue

            blocks.append(
                {
                    "text": cleaned,
                    "start": (
                        match.start() + prefix_end + leading_end + correction_offset
                    ),
                }
            )

        return blocks

    def _rejected_claim_correction_text(
        self,
        text: str,
    ):
        match = re.search(
            (
                r"\b(?:misconception|misconceptions|"
                r"myth|myths)\b"
                r".*?;\s*"
                r"(?:(?:all|these|those)(?:\s+\w+)?"
                r"|that(?:\s+claim)?"
                r"|the\s+(?:claim|statement))"
                r"\s+(?:are|is|were|was)\s+"
                r"(?:false|wrong|incorrect)"
                r"\s*[—–:-]\s*"
                r"(?P<content>.+)$"
            ),
            text,
            flags=re.IGNORECASE,
        )

        if match is None:
            return (
                text,
                0,
            )

        return (
            match.group("content").strip(),
            match.start("content"),
        )

    def _prepare_sentence(
        self,
        raw_text: str,
        absolute_start: int,
    ):
        trimmed = self._trim_segment(
            raw_text,
            absolute_start,
            strip_punctuation=False,
            method="sentence_rule",
        )

        text = trimmed["text"]

        if not text:
            return trimmed

        reality_match = re.match(
            (
                r"^(?:in reality|in fact|actually)"
                r"\b[^:]{0,180}:\s*"
                r"(?P<content>.+)$"
            ),
            text,
            flags=re.IGNORECASE,
        )

        if reality_match:
            content = reality_match.group("content")

            content_start = trimmed["start"] + reality_match.start("content")

            return self._trim_segment(
                content,
                content_start,
                strip_punctuation=False,
                method="sentence_rule",
            )

        label_match = re.match(
            r"^([^:\n]{1,80}):\s+(.+)$",
            text,
        )

        if not label_match:
            return trimmed

        label = label_match.group(1)

        if not self._is_topic_label(label):
            return trimmed

        content = label_match.group(2)

        content_start = trimmed["start"] + label_match.start(2)

        return self._trim_segment(
            content,
            content_start,
            strip_punctuation=False,
            method="sentence_rule",
        )

    def _is_topic_label(
        self,
        text: str,
    ):
        doc = self.nlp(text)

        meaningful = [
            token
            for token in doc
            if any(character.isalpha() for character in token.text)
        ]

        if not meaningful or len(meaningful) > 7:
            return False

        if any(token.pos_ == "AUX" for token in doc):
            return False

        if any(
            (
                token.pos_ == "VERB"
                and token.tag_
                not in {
                    "VBG",
                    "VBN",
                }
            )
            for token in doc
        ):
            return False

        return True

    def _sentence_segments(
        self,
        raw_text: str,
        absolute_start: int,
    ):
        unsplit = self._trim_segment(
            raw_text,
            absolute_start,
            strip_punctuation=False,
            method="sentence_rule",
        )

        separators = list(self.CLAUSE_SEPARATOR.finditer(raw_text))

        if not separators:
            return [unsplit]

        raw_segments = []
        cursor = 0

        for separator in separators:
            raw_segments.append(
                (
                    raw_text[cursor : separator.start()],
                    (absolute_start + cursor),
                )
            )

            cursor = separator.end()

        raw_segments.append(
            (
                raw_text[cursor:],
                (absolute_start + cursor),
            )
        )

        segments = [
            self._trim_segment(
                segment_text,
                segment_start,
                strip_punctuation=True,
                method="clause_rule",
            )
            for (
                segment_text,
                segment_start,
            ) in raw_segments
        ]

        if any(not segment["text"] for segment in segments):
            return [unsplit]

        resolved_segments = []
        previous_subject = None

        for segment in segments:
            resolved = self._resolve_segment_subject(
                segment,
                previous_subject,
            )

            resolved_doc = self.nlp(resolved["text"])

            if not self._is_factual(
                resolved_doc,
                resolved["text"],
            ):
                return [unsplit]

            subject = self._subject_phrase(resolved_doc)

            if subject and not self._is_pronoun_phrase(subject):
                previous_subject = subject
            elif previous_subject is None:
                previous_subject = self._lexical_subject_phrase(resolved["text"])

            resolved_segments.append(resolved)

        return resolved_segments

    def _resolve_segment_subject(
        self,
        segment: dict,
        previous_subject: str | None,
    ):
        if not previous_subject:
            return segment

        doc = self.nlp(segment["text"])

        subject_token = self._subject_token(doc)

        if subject_token and subject_token.lower_ in self.SUBJECT_PRONOUNS:
            start = subject_token.idx
            end = subject_token.idx + len(subject_token.text)

            resolved_text = (
                segment["text"][:start] + previous_subject + segment["text"][end:]
            )

            return {
                **segment,
                "text": resolved_text,
            }

        if subject_token:
            return segment

        if self._has_lexical_subject(segment["text"]):
            return segment

        if not self._can_inherit_subject(doc):
            return segment

        return {
            **segment,
            "text": (f"{previous_subject} {segment['text']}"),
        }

    def _can_inherit_subject_core(
        self,
        doc,
    ):
        if self._subject_token(doc):
            return False

        meaningful = [
            token for token in doc if not token.is_space and not token.is_punct
        ]

        if not meaningful:
            return False

        first = meaningful[0]

        if first.lower_ in self.INHERITABLE_STARTS:
            return True

        return any(token.pos_ == "VERB" for token in meaningful[:2])

    def _subject_token(
        self,
        doc,
    ):
        subjects = [token for token in doc if token.dep_ in self.SUBJECT_DEPS]

        if not subjects:
            return None

        return min(
            subjects,
            key=lambda token: token.i,
        )

    def _subject_phrase(
        self,
        doc,
    ):
        subject = self._subject_token(doc)

        if not subject:
            return None

        subtree = list(subject.subtree)

        if not subtree:
            return subject.text

        start = min(token.i for token in subtree)

        end = max(token.i for token in subtree) + 1

        if end - start > 8:
            return subject.text

        return doc[start:end].text.strip()

    def _lexical_subject_phrase(
        self,
        text: str,
    ):
        normalized = self._normalize(text)

        match = self.FACTUAL_PREDICATE_PATTERN.search(normalized)

        if not match:
            return None

        prefix = normalized[: match.start()].strip()

        if not prefix:
            return None

        words = prefix.split()

        content_words = [
            word for word in words if word not in self.NON_SUBJECT_PREFIX_WORDS
        ]

        if not content_words:
            return None

        if len(content_words) > 8:
            return None

        return " ".join(content_words)

    def _has_lexical_subject(
        self,
        text: str,
    ):
        return self._lexical_subject_phrase(text) is not None

    def _is_pronoun_phrase(
        self,
        text: str,
    ):
        normalized = self._normalize(text)

        return normalized in self.SUBJECT_PRONOUNS

    def _trim_segment(
        self,
        raw_text: str,
        absolute_start: int,
        strip_punctuation: bool,
        method: str,
    ):
        if strip_punctuation:
            leading = re.match(
                r"^[\s,;:.!?]+",
                raw_text,
            )

            trailing = re.search(
                r"[\s,;:.!?]+$",
                raw_text,
            )
        else:
            leading = re.match(
                r"^\s+",
                raw_text,
            )

            trailing = re.search(
                r"\s+$",
                raw_text,
            )

        left_trim = leading.end() if leading else 0

        right_trim = len(raw_text) - trailing.start() if trailing else 0

        end_index = len(raw_text) - right_trim

        claim_text = raw_text[left_trim:end_index]

        return {
            "text": claim_text,
            "start": (absolute_start + left_trim),
            "end": (absolute_start + end_index),
            "method": method,
        }

    def _is_factual(
        self,
        sentence,
        text: str,
    ):
        normalized = self._normalize(text)

        if not normalized:
            return False

        if self._is_non_asserted_context(normalized):
            return False

        if text.rstrip().endswith("?"):
            return False

        if any(normalized.startswith(prefix) for prefix in self.NON_FACTUAL_PREFIXES):
            return False

        if self._is_meta_discourse(
            normalized,
            text,
        ):
            return False

        meaningful_tokens = [
            token
            for token in sentence
            if any(character.isalpha() for character in token.text)
        ]

        if len(meaningful_tokens) < 2:
            return False

        if not self._has_subject(
            sentence,
            normalized,
        ):
            return False

        return self._has_predicate(
            sentence,
            normalized,
        )

    def _is_non_asserted_context(
        self,
        normalized: str,
    ):
        if normalized.startswith("if ") and re.search(
            r"\b(?:would|could|might)\b",
            normalized,
        ):
            return True

        if re.search(
            r"\bwould then\b",
            normalized,
        ):
            return True

        if re.match(
            (
                r"^(?:some|many) people "
                r"(?:claim|say|believe) that\b"
            ),
            normalized,
        ):
            return True

        if re.match(
            (
                r"^(?:\w+\s+){0,5}"
                r"misconceptions? "
                r"(?:are|include) that\b"
            ),
            normalized,
        ):
            return True

        return False

    def _is_meta_discourse(
        self,
        normalized: str,
        text: str,
    ):
        words = set(normalized.split())

        if any(
            normalized.startswith(prefix) for prefix in self.PRESENTATIONAL_PREFIXES
        ):
            if words & self.META_TERMS:
                return True

        if (
            normalized.startswith("here ")
            or normalized.startswith("the following ")
            or normalized.startswith("below ")
        ) and (words & self.META_TERMS):
            return True

        if text.rstrip().endswith(":"):
            if words & self.META_TERMS:
                return True

        return False

    def _has_subject(
        self,
        sentence,
        normalized: str,
    ):
        if self._subject_token(sentence):
            return True

        if re.match(
            (
                r"^there "
                r"(?:is|are|was|were|has been|have been)\b"
            ),
            normalized,
        ):
            return True

        return self._has_lexical_subject(normalized)

    def _has_predicate(
        self,
        sentence,
        normalized: str,
    ):
        syntactic_predicate = any(
            token.pos_
            in {
                "VERB",
                "AUX",
            }
            for token in sentence
        )

        if syntactic_predicate:
            return True

        return self.FACTUAL_PREDICATE_PATTERN.search(normalized) is not None

    def _normalize(
        self,
        text: str,
    ):
        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s\-]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()
