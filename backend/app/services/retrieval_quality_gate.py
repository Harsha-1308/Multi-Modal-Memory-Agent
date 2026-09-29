from typing import Any, Dict, List


class RetrievalQualityGate:
    """
    Validates and prepares resolved Hindsight candidates before C6.

    Pipeline position:

        Hindsight
            ↓
        Resolver
            ↓
        RetrievalQualityGate
            ↓
        C6

    Important:
    - retrieval_similarity is NOT identity_score
    - unresolved / ambiguous candidates must never reach C6
    - duplicate canonical IDs are collapsed
    - highest valid retrieval similarity wins
    """

    DEFAULT_MIN_SIMILARITY = 0.0

    def __init__(
        self,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ):
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError(
                "min_similarity must be between 0.0 and 1.0."
            )

        self.min_similarity = float(min_similarity)

    @staticmethod
    def _valid_similarity(value: Any) -> bool:
        if isinstance(value, bool):
            return False

        try:
            value = float(value)
        except (TypeError, ValueError):
            return False

        return 0.0 <= value <= 1.0

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def _normalize_id(value: Any):
        if isinstance(value, bool):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def filter_and_deduplicate(
        self,
        resolved_candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Returns accepted C6 candidates plus rejection diagnostics.

        Accepted candidate schema:

        {
            "canonical_memory_id": int,
            "text": str,
            "retrieval_similarity": float,
        }
        """

        if resolved_candidates is None:
            resolved_candidates = []

        accepted_by_id = {}

        rejected = []

        for index, candidate in enumerate(
            resolved_candidates
        ):
            if not isinstance(candidate, dict):
                rejected.append(
                    {
                        "index": index,
                        "reason": "candidate_not_dict",
                    }
                )
                continue

            memory_id = self._normalize_id(
                candidate.get("canonical_memory_id")
            )

            if memory_id is None:
                rejected.append(
                    {
                        "index": index,
                        "reason": "missing_or_invalid_canonical_memory_id",
                    }
                )
                continue

            text = self._normalize_text(
                candidate.get("text")
            )

            if not text:
                rejected.append(
                    {
                        "index": index,
                        "canonical_memory_id": memory_id,
                        "reason": "missing_text",
                    }
                )
                continue

            similarity = candidate.get(
                "retrieval_similarity"
            )

            if not self._valid_similarity(
                similarity
            ):
                rejected.append(
                    {
                        "index": index,
                        "canonical_memory_id": memory_id,
                        "reason": "invalid_retrieval_similarity",
                    }
                )
                continue

            similarity = float(similarity)

            if similarity < self.min_similarity:
                rejected.append(
                    {
                        "index": index,
                        "canonical_memory_id": memory_id,
                        "reason": "below_similarity_threshold",
                        "retrieval_similarity": similarity,
                    }
                )
                continue

            normalized = {
                "canonical_memory_id": memory_id,
                "text": text,
                "retrieval_similarity": similarity,
            }

            previous = accepted_by_id.get(
                memory_id
            )

            if previous is None:
                accepted_by_id[memory_id] = normalized
                continue

            # Same canonical memory appeared multiple times.
            # Keep the strongest retrieval result.
            if (
                similarity
                > previous["retrieval_similarity"]
            ):
                accepted_by_id[memory_id] = normalized

            rejected.append(
                {
                    "index": index,
                    "canonical_memory_id": memory_id,
                    "reason": "duplicate_canonical_memory",
                    "kept_similarity": max(
                        similarity,
                        previous["retrieval_similarity"],
                    ),
                }
            )

        candidates = list(
            accepted_by_id.values()
        )

        candidates.sort(
            key=lambda item: (
                item["retrieval_similarity"],
                -item["canonical_memory_id"],
            ),
            reverse=True,
        )

        return {
            "candidates": candidates,
            "accepted_count": len(candidates),
            "rejected_count": len(rejected),
            "rejected": rejected,
        }

    def prepare(
        self,
        resolved_candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Strict convenience method.

        Returns only candidates accepted by the gate.
        """

        return self.filter_and_deduplicate(
            resolved_candidates
        )["candidates"]