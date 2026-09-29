import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class MemoryRelationship:
    relationship: str
    similarity: Optional[float]
    reason: str


class MemoryRelationshipService:

    EXACT_DUPLICATE = "exact_duplicate"
    SEMANTIC_DUPLICATE = "semantic_duplicate"
    RELATED_NEW = "related_new"
    CONTRADICTION = "contradiction"

    # Words that indicate positive outcome.
    POSITIVE_OUTCOME_WORDS = {
        "resolved",
        "resolve",
        "fixed",
        "fix",
        "worked",
        "works",
        "succeeded",
        "successful",
        "success",
        "passed",
        "pass",
        "completed",
        "complete",
        "improved",
        "achieved",
    }

    # Words that indicate negative outcome.
    NEGATIVE_OUTCOME_WORDS = {
        "failed",
        "fail",
        "failure",
        "unsuccessful",
        "unsuccessfully",
        "broken",
        "blocked",
        "rejected",
        "regressed",
    }

    def __init__(self):
        pass

    @staticmethod
    def normalize(text: str) -> str:
        if not isinstance(text, str):
            raise TypeError(
                "Memory text must be a string."
            )

        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)

        return text.strip(
            " \t\r\n.,;:!?"
        )

    @classmethod
    def token_set(cls, text: str) -> set:
        normalized = cls.normalize(text)

        return set(
            re.findall(
                r"\b[a-z0-9]+\b",
                normalized,
            )
        )

    @classmethod
    def remove_stop_words(cls, tokens: set) -> set:
        stop_words = {
            "the",
            "a",
            "an",
            "was",
            "were",
            "is",
            "are",
            "to",
            "of",
            "and",
            "in",
            "on",
            "for",
            "with",
            "using",
            "successfully",
        }

        return tokens - stop_words

    @classmethod
    def calculate_token_overlap(
        cls,
        candidate: str,
        existing: str,
    ) -> float:

        candidate_tokens = cls.remove_stop_words(
            cls.token_set(candidate)
        )

        existing_tokens = cls.remove_stop_words(
            cls.token_set(existing)
        )

        if not candidate_tokens or not existing_tokens:
            return 0.0

        intersection = (
            candidate_tokens.intersection(
                existing_tokens
            )
        )

        union = (
            candidate_tokens.union(
                existing_tokens
            )
        )

        if not union:
            return 0.0

        return len(intersection) / len(union)

    @classmethod
    def outcome_polarity(
        cls,
        text: str,
    ) -> str:

        tokens = cls.token_set(text)

        positive = bool(
            tokens.intersection(
                cls.POSITIVE_OUTCOME_WORDS
            )
        )

        negative = bool(
            tokens.intersection(
                cls.NEGATIVE_OUTCOME_WORDS
            )
        )

        if positive and not negative:
            return "positive"

        if negative and not positive:
            return "negative"

        return "neutral"

    @classmethod
    def has_explicit_negation(
        cls,
        text: str,
    ) -> bool:

        normalized = cls.normalize(text)

        patterns = [
            r"\bnot\b",
            r"\bnever\b",
            r"\bdid not\b",
            r"\bdidn't\b",
            r"\bdoes not\b",
            r"\bdoesn't\b",
            r"\bwas not\b",
            r"\bwasn't\b",
            r"\bwere not\b",
            r"\bweren't\b",
            r"\bcould not\b",
            r"\bcouldn't\b",
            r"\bfailed to\b",
            r"\bfail to\b",
        ]

        return any(
            re.search(
                pattern,
                normalized,
            )
            for pattern in patterns
        )

    @classmethod
    def detect_contradiction(
    cls,
    candidate: str,
    existing: str,
    semantic_similarity: Optional[float],
) -> bool:

    # If semantic similarity is available, require
    # the memories to be meaningfully related.
        if semantic_similarity is not None:
            if semantic_similarity < 0.75:
                return False

        candidate_polarity = cls.outcome_polarity(candidate)
        existing_polarity = cls.outcome_polarity(existing)

    # Conflicting explicit outcomes.
        if (
        candidate_polarity != "neutral"
        and existing_polarity != "neutral"
        and candidate_polarity != existing_polarity
    ):
            return True

        candidate_negation = cls.has_explicit_negation(candidate)
        existing_negation = cls.has_explicit_negation(existing)

    # One statement is explicitly negated while the other is not.
        if candidate_negation != existing_negation:
            return True

        return False
    def classify(
        self,
        candidate: str,
        existing: str,
        semantic_similarity: Optional[float],
    ) -> MemoryRelationship:

        candidate_normalized = (
            self.normalize(candidate)
        )

        existing_normalized = (
            self.normalize(existing)
        )

        # --------------------------------------------------
        # 1. Exact duplicate
        # --------------------------------------------------

        if candidate_normalized == existing_normalized:
            return MemoryRelationship(
                relationship=self.EXACT_DUPLICATE,
                similarity=semantic_similarity,
                reason=(
                    "Candidate and existing memory "
                    "have identical normalized text."
                ),
            )

        # --------------------------------------------------
        # 2. Contradiction
        # --------------------------------------------------

        if self.detect_contradiction(
            candidate=candidate,
            existing=existing,
            semantic_similarity=semantic_similarity,
        ):
            return MemoryRelationship(
                relationship=self.CONTRADICTION,
                similarity=semantic_similarity,
                reason=(
                    "Candidate and existing memory "
                    "express conflicting outcomes."
                ),
            )

        # --------------------------------------------------
        # 3. Lexical factual overlap
        # --------------------------------------------------

        overlap = (
            self.calculate_token_overlap(
                candidate,
                existing,
            )
        )

        # --------------------------------------------------
        # 4. Semantic duplicate
        #
        # We intentionally do NOT require the old
        # 0.88 Hindsight threshold.
        #
        # A high semantic score OR strong factual
        # lexical overlap can support duplication.
        # --------------------------------------------------

        if (
            (
        semantic_similarity is not None
        and semantic_similarity >= 0.80
        and overlap >= 0.40
    )
    or (
        semantic_similarity is None
        and overlap >= 0.40
    )
        ):
            return MemoryRelationship(
                relationship=self.SEMANTIC_DUPLICATE,
                similarity=semantic_similarity,
                reason=(
                    "Memory has strong semantic similarity "
                    "and substantial factual token overlap."
                ),
            )

        # --------------------------------------------------
        # 5. Related but new
        # --------------------------------------------------

        return MemoryRelationship(
            relationship=self.RELATED_NEW,
            similarity=semantic_similarity,
            reason=(
                "Memory is related but does not provide "
                "enough evidence to treat it as the same fact."
            ),
        )