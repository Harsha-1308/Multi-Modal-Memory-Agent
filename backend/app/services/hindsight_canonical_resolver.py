from typing import Any, Dict, List, Optional
import re
from difflib import SequenceMatcher


class HindsightCanonicalResolver:
    """
    Resolve a Hindsight recall result to an application-owned
    canonical memory.

    Important architecture:
    - Hindsight owns retrieval relevance.
    - CanonicalMemoryService owns application identity.
    - This resolver creates the bridge between them.
    - Ambiguous results are rejected rather than guessed.

    This is intentionally conservative. A bad canonical identity
    would corrupt the learning loop, so "ambiguous" is safer than
    inventing an ID.
    """

    DEFAULT_MIN_SCORE = 0.35
    DEFAULT_MIN_MARGIN = 0.10

    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "be",
        "been",
        "being",
        "but",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "were",
        "with",
        "using",
        "used",
        "use",
    }

    def __init__(
        self,
        canonical_memory_service,
        min_score: float = DEFAULT_MIN_SCORE,
        min_margin: float = DEFAULT_MIN_MARGIN,
    ):
        self.canonical_memory_service = (
            canonical_memory_service
        )

        self.min_score = float(min_score)
        self.min_margin = float(min_margin)

    @classmethod
    def _tokens(cls, text: str) -> set:
        if not text:
            return set()

        text = text.lower()

        words = re.findall(
            r"[a-z0-9]+",
            text,
        )

        return {
            word
            for word in words
            if word not in cls.STOP_WORDS
        }

    @classmethod
    def _token_overlap(
        cls,
        left: str,
        right: str,
    ) -> float:
        left_tokens = cls._tokens(left)
        right_tokens = cls._tokens(right)

        if not left_tokens or not right_tokens:
            return 0.0

        intersection = (
            left_tokens & right_tokens
        )

        union = (
            left_tokens | right_tokens
        )

        if not union:
            return 0.0

        return len(intersection) / len(union)

    @classmethod
    def _sequence_similarity(
        cls,
        left: str,
        right: str,
    ) -> float:
        left_normalized = " ".join(
            sorted(cls._tokens(left))
        )

        right_normalized = " ".join(
            sorted(cls._tokens(right))
        )

        if not left_normalized or not right_normalized:
            return 0.0

        return SequenceMatcher(
            None,
            left_normalized,
            right_normalized,
        ).ratio()

    @classmethod
    def _identity_score(
        cls,
        hindsight_text: str,
        canonical_text: str,
    ) -> float:
        """
        Combine lexical overlap and token-level sequence similarity.

        This score is ONLY for identity resolution.
        It is NOT the Hindsight retrieval similarity.
        """

        overlap = cls._token_overlap(
            hindsight_text,
            canonical_text,
        )

        sequence = cls._sequence_similarity(
            hindsight_text,
            canonical_text,
        )

        return (
            0.60 * overlap
            + 0.40 * sequence
        )

    @staticmethod
    def _get_text(result: Any) -> Optional[str]:
        if isinstance(result, dict):
            return result.get("text")

        return getattr(
            result,
            "text",
            None,
        )

    @staticmethod
    def _get_retrieval_similarity(
        result: Any,
    ) -> Optional[float]:

        if isinstance(result, dict):

            value = result.get(
                "semantic_similarity"
            )

            if value is not None:
                return float(value)

            value = result.get("score")

            if value is not None:
                return float(value)

            scores = result.get("scores")

        else:

            value = getattr(
                result,
                "semantic_similarity",
                None,
            )

            if value is not None:
                return float(value)

            value = getattr(
                result,
                "score",
                None,
            )

            if value is not None:
                return float(value)

            scores = getattr(
                result,
                "scores",
                None,
            )

        if scores is None:
            return None

        if isinstance(scores, dict):

            for key in (
                "semantic",
                "similarity",
                "final",
            ):
                value = scores.get(key)

                if value is not None:
                    return float(value)

        else:

            for key in (
                "semantic",
                "similarity",
                "final",
            ):
                value = getattr(
                    scores,
                    key,
                    None,
                )

                if value is not None:
                    return float(value)

        return None

    def resolve_result(
        self,
        result: Any,
        canonical_memories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        hindsight_text = self._get_text(result)

        retrieval_similarity = (
            self._get_retrieval_similarity(
                result
            )
        )

        if not hindsight_text:
            return {
                "status": "unresolved",
                "reason": "Hindsight result has no text.",
                "canonical_memory_id": None,
                "text": None,
                "retrieval_similarity": (
                    retrieval_similarity
                ),
                "identity_score": 0.0,
                "margin": 0.0,
                "ranked_matches": [],
            }

        if not canonical_memories:
            return {
                "status": "unresolved",
                "reason": (
                    "No canonical memories exist "
                    "for this bank."
                ),
                "canonical_memory_id": None,
                "text": hindsight_text,
                "retrieval_similarity": (
                    retrieval_similarity
                ),
                "identity_score": 0.0,
                "margin": 0.0,
                "ranked_matches": [],
            }

        ranked_matches = []

        for memory in canonical_memories:

            canonical_text = memory.get(
                "original_text"
            )

            if not canonical_text:
                continue

            identity_score = (
                self._identity_score(
                    hindsight_text,
                    canonical_text,
                )
            )

            ranked_matches.append(
                {
                    "canonical_memory_id": memory[
                        "id"
                    ],
                    "canonical_text": canonical_text,
                    "identity_score": identity_score,
                }
            )

        ranked_matches.sort(
            key=lambda item: (
                item["identity_score"],
                -item["canonical_memory_id"],
            ),
            reverse=True,
        )

        if not ranked_matches:
            return {
                "status": "unresolved",
                "reason": (
                    "Canonical memories had no "
                    "usable text."
                ),
                "canonical_memory_id": None,
                "text": hindsight_text,
                "retrieval_similarity": (
                    retrieval_similarity
                ),
                "identity_score": 0.0,
                "margin": 0.0,
                "ranked_matches": [],
            }

        best = ranked_matches[0]

        if len(ranked_matches) == 1:
            margin = best["identity_score"]
        else:
            margin = (
                best["identity_score"]
                - ranked_matches[1][
                    "identity_score"
                ]
            )

        if best["identity_score"] < self.min_score:

            return {
                "status": "unresolved",
                "reason": (
                    "Best canonical identity score "
                    "is below the minimum threshold."
                ),
                "canonical_memory_id": None,
                "text": hindsight_text,
                "retrieval_similarity": (
                    retrieval_similarity
                ),
                "identity_score": (
                    best["identity_score"]
                ),
                "margin": margin,
                "ranked_matches": ranked_matches,
            }

        if (
            len(ranked_matches) > 1
            and margin < self.min_margin
        ):

            return {
                "status": "ambiguous",
                "reason": (
                    "Top canonical matches are too "
                    "close to distinguish safely."
                ),
                "canonical_memory_id": None,
                "text": hindsight_text,
                "retrieval_similarity": (
                    retrieval_similarity
                ),
                "identity_score": (
                    best["identity_score"]
                ),
                "margin": margin,
                "ranked_matches": ranked_matches,
            }

        return {
            "status": "resolved",
            "reason": (
                "Hindsight result was resolved to "
                "one canonical memory."
            ),
            "canonical_memory_id": (
                best["canonical_memory_id"]
            ),
            "text": hindsight_text,
            "retrieval_similarity": (
                retrieval_similarity
            ),
            "identity_score": (
                best["identity_score"]
            ),
            "margin": margin,
            "ranked_matches": ranked_matches,
        }
    @staticmethod
    def _get_source_fact_ids(
    result: Any,
) -> List[str]:
        if isinstance(result, dict):
            value = result.get(
            "source_fact_ids"
        )
        else:
            value = getattr(
            result,
            "source_fact_ids",
            None,
        )

        if not value:
            return []

        return [
        str(item)
        for item in value
    ]

    def resolve_results(
    self,
    results: List[Any],
    bank_id: str,
    source_facts: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:

        canonical_memories = (
        self.canonical_memory_service.list_memories(
            bank_id=bank_id
        )
    )

        source_facts = source_facts or {}

        resolved = []

        for result in results:

        # ==================================================
        # PATH 1:
        # Hindsight returned a synthesized observation.
        #
        # Instead of trying to assign the synthesized text
        # to exactly one canonical memory, use Hindsight's
        # own source-fact provenance.
        # ==================================================

            source_fact_ids = (
            self._get_source_fact_ids(
                result
            )
        )

            source_fact_resolved = False

            if source_fact_ids:

                parent_retrieval_similarity = (
                self._get_retrieval_similarity(
                    result
                )
            )

            for source_fact_id in source_fact_ids:

                source_fact = source_facts.get(
                    source_fact_id
                )

                if source_fact is None:
                    continue

                identity = self.resolve_result(
                    result=source_fact,
                    canonical_memories=canonical_memories,
                )

                if identity["status"] != "resolved":
                    continue

                source_fact_resolved = True

                resolved.append(
                    {
                        "canonical_memory_id": (
                            identity[
                                "canonical_memory_id"
                            ]
                        ),

                        # This text belongs to exactly one
                        # source fact, unlike the synthesized
                        # parent observation.
                        "text": identity["text"],

                        # Retrieval relevance belongs to the
                        # parent Hindsight observation.
                        "retrieval_similarity": (
                            parent_retrieval_similarity
                            if parent_retrieval_similarity
                            is not None
                            else 0.0
                        ),

                        "identity_score": (
                            identity["identity_score"]
                        ),

                        "identity_margin": (
                            identity["margin"]
                        ),

                        "identity_status": (
                            "resolved"
                        ),

                        "resolution_mode": (
                            "source_fact"
                        ),
                    }
                )

            # IMPORTANT:
            #
            # Once source facts successfully gave us canonical
            # identities, DO NOT also resolve the synthesized
            # parent result. Doing that would reintroduce the
            # ambiguity problem and could duplicate candidates.
            if source_fact_resolved:
                continue

        # ==================================================
        # PATH 2:
        # Normal Hindsight result.
        #
        # Existing conservative single-memory resolution
        # remains completely unchanged.
        # ==================================================

            identity = self.resolve_result(
            result=result,
            canonical_memories=canonical_memories,
        )

            if identity["status"] != "resolved":
                continue

            resolved.append(
            {
                "canonical_memory_id": (
                    identity[
                        "canonical_memory_id"
                    ]
                ),

                "text": identity["text"],

                "retrieval_similarity": (
                    identity[
                        "retrieval_similarity"
                    ]
                    if identity[
                        "retrieval_similarity"
                    ] is not None
                    else 0.0
                ),

                "identity_score": (
                    identity["identity_score"]
                ),

                "identity_margin": (
                    identity["margin"]
                ),

                "identity_status": (
                    identity["status"]
                ),

                "resolution_mode": (
                    "single_memory"
                ),
            }
        )

        return resolved