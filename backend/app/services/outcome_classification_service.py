import json
import re
from typing import Dict, List


class OutcomeClassificationService:

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

    CLASSIFICATION_VERSION = "c3-v1"

    TEXT_EVIDENCE_TYPES = {
        "text",
        "code",
        "url",
        "structured_data",
        "test_result",
        "tool_output",
    }

    POSITIVE_PATTERNS = [
        r"\btests?\s+passed\b",
        r"\b\d+\s+tests?\s+passed\b",
        r"\b0\s+tests?\s+failed\b",
        r"\b0\s+failures?\b",
        r"\bpassed\b",
        r"\bsuccess\b",
        r"\bsuccessful\b",
        r"\bsucceeded\b",
        r"\bworked\b",
        r"\bworks\b",
        r"\bworking\b",
        r"\bresolved\b",
        r"\bresolve(d)?\b",
        r"\bfixed\b",
        r"\bcompleted\b",
        r"\bcomplete\b",
        r"\bachieved\b",
        r"\bverified\b",
        r"\bvalidated\b",
        r"\bcorrect\b",
        r"\bcorrectly\b",
        r"\beffective\b",
    ]

    NEGATIVE_PATTERNS = [
        r"\btests?\s+failed\b",
        r"\b\d+\s+tests?\s+failed\b",
        r"\bfailure\b",
        r"\bfailed\b",
        r"\bunsuccessful\b",
        r"\bunsuccessfully\b",
        r"\bbroken\b",
        r"\bblocked\b",
        r"\brejected\b",
        r"\bregressed\b",
        r"\bcrashed\b",
        r"\bcrash\b",
        r"\bexception\b",
        r"\bexceptions\b",
        r"\btimeout\b",
        r"\btime\s*out\b",
        r"\bdid\s+not\s+work\b",
        r"\bdid\s+not\s+resolve\b",
        r"\bnot\s+resolved\b",
        r"\bnot\s+fixed\b",
        r"\bstill\s+failing\b",
        r"\bincorrect\b",
        r"\bwrong\b",
    ]

    def __init__(
        self,
        repository,
    ):
        self.repository = repository

    # ============================================================
    # PUBLIC API
    # ============================================================

    def classify(
        self,
        outcome_id: str,
    ) -> Dict:

        outcome = self.repository.get_outcome(
            outcome_id
        )

        if outcome is None:
            raise ValueError(
                "Cannot classify outcome: "
                "outcome does not exist."
            )

        evidence = (
            self.repository
            .list_evidence_for_outcome(
                outcome_id
            )
        )

        result = self._classify_evidence(
            evidence
        )

        evidence_ids = [
            item["evidence_id"]
            for item in evidence
        ]

        updated = (
            self.repository
            .update_outcome_classification(
                outcome_id=outcome_id,
                classification=result[
                    "classification"
                ],
                classification_reason=result[
                    "reason"
                ],
                classification_evidence_count=len(
                    evidence
                ),
                classification_evidence_ids=json.dumps(
                    evidence_ids
                ),
                classification_version=(
                    self.CLASSIFICATION_VERSION
                ),
            )
        )

        return {
            "outcome_id": outcome_id,
            "reported_outcome": (
                outcome["outcome_type"]
            ),
            "classification": (
                result["classification"]
            ),
            "reason": result["reason"],
            "evidence_count": len(evidence),
            "evidence_ids": evidence_ids,
            "positive_evidence_ids": result[
                "positive_evidence_ids"
            ],
            "negative_evidence_ids": result[
                "negative_evidence_ids"
            ],
            "neutral_evidence_ids": result[
                "neutral_evidence_ids"
            ],
            "classification_version": (
                self.CLASSIFICATION_VERSION
            ),
            "persisted_outcome": updated,
        }

    def get_classification(
        self,
        outcome_id: str,
    ):

        outcome = self.repository.get_outcome(
            outcome_id
        )

        if outcome is None:
            return None

        return {
            "outcome_id": outcome[
                "outcome_id"
            ],
            "reported_outcome": outcome[
                "outcome_type"
            ],
            "classification": outcome[
                "classification"
            ],
            "reason": outcome[
                "classification_reason"
            ],
            "evidence_count": outcome[
                "classification_evidence_count"
            ],
            "evidence_ids": self._parse_ids(
                outcome[
                    "classification_evidence_ids"
                ]
            ),
            "classification_version": outcome[
                "classification_version"
            ],
            "classified_at": outcome[
                "classified_at"
            ],
        }

    # ============================================================
    # CLASSIFICATION ENGINE
    # ============================================================

    def _classify_evidence(
        self,
        evidence: List[Dict],
    ) -> Dict:

        positive_ids = []
        negative_ids = []
        neutral_ids = []

        for item in evidence:

            evidence_id = item[
                "evidence_id"
            ]

            text = self._extract_text(
                item
            )

            if not text:
                neutral_ids.append(
                    evidence_id
                )
                continue

            positive = self._contains_positive(
                text
            )

            negative = self._contains_negative(
                text
            )

            if positive and negative:

                positive_ids.append(
                    evidence_id
                )

                negative_ids.append(
                    evidence_id
                )

            elif positive:

                positive_ids.append(
                    evidence_id
                )

            elif negative:

                negative_ids.append(
                    evidence_id
                )

            else:

                neutral_ids.append(
                    evidence_id
                )

        if positive_ids and negative_ids:

            return {
                "classification": self.PARTIAL,
                "reason": (
                    "Evidence contains both "
                    "positive and negative outcome "
                    "signals."
                ),
                "positive_evidence_ids": (
                    positive_ids
                ),
                "negative_evidence_ids": (
                    negative_ids
                ),
                "neutral_evidence_ids": (
                    neutral_ids
                ),
            }

        if positive_ids:

            return {
                "classification": self.SUCCESS,
                "reason": (
                    "Evidence contains positive "
                    "outcome signals and no "
                    "negative outcome signals."
                ),
                "positive_evidence_ids": (
                    positive_ids
                ),
                "negative_evidence_ids": (
                    negative_ids
                ),
                "neutral_evidence_ids": (
                    neutral_ids
                ),
            }

        if negative_ids:

            return {
                "classification": self.FAILURE,
                "reason": (
                    "Evidence contains negative "
                    "outcome signals and no "
                    "positive outcome signals."
                ),
                "positive_evidence_ids": (
                    positive_ids
                ),
                "negative_evidence_ids": (
                    negative_ids
                ),
                "neutral_evidence_ids": (
                    neutral_ids
                ),
            }

        return {
            "classification": self.UNKNOWN,
            "reason": (
                "No sufficient positive or "
                "negative outcome signal was "
                "found in the available evidence."
            ),
            "positive_evidence_ids": (
                positive_ids
            ),
            "negative_evidence_ids": (
                negative_ids
            ),
            "neutral_evidence_ids": (
                neutral_ids
            ),
        }

    # ============================================================
    # TEXT EXTRACTION
    # ============================================================

    def _extract_text(
        self,
        evidence: Dict,
    ):

        evidence_type = evidence[
            "evidence_type"
        ]

        if evidence_type not in (
            self.TEXT_EVIDENCE_TYPES
        ):
            return ""

        content = evidence.get(
            "content"
        )

        if not content:
            return ""

        if not isinstance(
            content,
            str,
        ):
            return str(content)

        return content.strip().lower()

    # ============================================================
    # SIGNAL DETECTION
    # ============================================================

    @classmethod
    def _contains_positive(
    cls,
    text: str,
) -> bool:

    # ------------------------------------------------------------
    # Remove positive words that are explicitly negated.
    #
    # Example:
    #   "did not resolve"
    #
    # The positive pattern "resolve" must NOT match here,
    # because the complete statement is negative.
    #
    # We mask the negated phrase instead of returning False
    # immediately, because one evidence item may legitimately
    # contain both:
    #
    #   "The first attempt did not resolve the issue,
    #    but the second attempt resolved it."
    #
    # That evidence should remain PARTIAL.
    # ------------------------------------------------------------

        negated_positive_patterns = [
        r"\bdid\s+not\s+(?:successfully\s+)?resolve(?:d)?\b",
        r"\bdidn't\s+(?:successfully\s+)?resolve(?:d)?\b",
        r"\bnot\s+resolve(?:d)?\b",
        r"\bnever\s+resolve(?:d)?\b",

        r"\bdid\s+not\s+(?:successfully\s+)?fix(?:ed)?\b",
        r"\bdidn't\s+(?:successfully\s+)?fix(?:ed)?\b",
        r"\bnot\s+fix(?:ed)?\b",
        r"\bnever\s+fix(?:ed)?\b",

        r"\bdid\s+not\s+(?:successfully\s+)?work(?:ed|ing)?\b",
        r"\bdidn't\s+(?:successfully\s+)?work(?:ed|ing)?\b",
        r"\bnot\s+work(?:ed|ing)?\b",
        r"\bnever\s+work(?:ed|ing)?\b",
    ]

        positive_text = text

        for pattern in negated_positive_patterns:
            positive_text = re.sub(
            pattern,
            " ",
            positive_text,
            flags=re.IGNORECASE,
        )

        return any(
        re.search(
            pattern,
            positive_text,
            flags=re.IGNORECASE,
        )
        for pattern in cls.POSITIVE_PATTERNS
    )

    @classmethod
    def _contains_negative(
        cls,
        text: str,
    ) -> bool:

        # Explicit successful test summary must
        # override the literal word "failed".
        #
        # Example:
        # "12 tests passed, 0 tests failed."
        #
        # This is positive evidence, not failure.
        if re.search(
            r"\b0\s+tests?\s+failed\b",
            text,
            flags=re.IGNORECASE,
        ):
            negative_matches = [
                pattern
                for pattern in cls.NEGATIVE_PATTERNS
                if pattern
                not in {
                    r"\btests?\s+failed\b",
                    r"\b\d+\s+tests?\s+failed\b",
                    r"\bfailed\b",
                }
            ]

            return any(
                re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )
                for pattern in negative_matches
            )

        return any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in cls.NEGATIVE_PATTERNS
        )

    @staticmethod
    def _parse_ids(
        raw,
    ):

        if not raw:
            return []

        try:
            parsed = json.loads(
                raw
            )

            if isinstance(
                parsed,
                list,
            ):
                return parsed

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

        return []