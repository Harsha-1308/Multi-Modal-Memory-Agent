from typing import Any, Dict, List, Optional


class AdaptiveMemorySelector:
    """
    C6: choose among already-retrieved canonical memories using
    retrieval relevance plus learned historical outcomes.

    C5 answers with a learning-aware policy for one memory.

    C6 uses that learning to change WHICH memory/approach is
    preferred when several relevant memories are available.

    Learning never replaces retrieval relevance. It adjusts the
    relevance score according to persisted C4 evidence.
    """

    def __init__(
        self,
        learning_service,
        closed_loop_service=None,
    ):
        self.learning_service = learning_service
        self.closed_loop_service = closed_loop_service

    @staticmethod
    def _clamp(
        value: float,
        low: float,
        high: float,
    ) -> float:

        return max(
            low,
            min(high, float(value)),
        )

    def _get_state(
        self,
        canonical_memory_id: int,
    ) -> Optional[Dict[str, Any]]:

        return self.learning_service.get_state(
            canonical_memory_id=canonical_memory_id
        )

    def _behavior(
        self,
        state: Optional[Dict[str, Any]],
    ) -> str:

        if self.closed_loop_service is None:
            return "insufficient"

        if state is None:
            return "insufficient"

        return self.closed_loop_service.decide_behavior(
            state
        )["behavior"]

    def score_candidate(
        self,
        candidate: Dict[str, Any],
    ) -> Dict[str, Any]:

        memory_id = candidate[
            "canonical_memory_id"
        ]

        text = candidate.get("text")

        similarity = self._clamp(
            candidate.get(
                "retrieval_similarity",
                0.0,
            ),
            0.0,
            1.0,
        )

        state = self._get_state(
            memory_id
        )

        if state is None:

            learning_signal = 0.0
            informative = 0
            evidence_coverage = 0.0
            behavior = "insufficient"

        else:

            learning_signal = float(
                state.get(
                    "learning_signal",
                    0.0,
                )
                or 0.0
            )

            informative = int(
                state.get(
                    "informative_outcomes",
                    0,
                )
                or 0
            )

            evidence_coverage = self._clamp(
                state.get(
                    "evidence_coverage",
                    0.0,
                )
                or 0.0,
                0.0,
                1.0,
            )

            behavior = self._behavior(
                state
            )

        # Confidence grows with repeated
        # informative outcomes and requires
        # evidence coverage.

        confidence = (
            min(
                informative / 5.0,
                1.0,
            )
            * evidence_coverage
        )

        # Learning signal is in [-1, +1].
        #
        # Therefore:
        #
        # +1 -> multiplier can reach 2.0
        #  0 -> multiplier = 1.0
        # -1 -> multiplier can reach 0.0

        learning_multiplier = (
            1.0
            + (
                learning_signal
                * confidence
            )
        )

        learning_multiplier = self._clamp(
            learning_multiplier,
            0.0,
            2.0,
        )

        adjusted_score = (
            similarity
            * learning_multiplier
        )

        return {
            "canonical_memory_id": memory_id,
            "text": text,
            "retrieval_similarity": similarity,
            "learning_signal": learning_signal,
            "informative_outcomes": informative,
            "evidence_coverage": evidence_coverage,
            "behavior": behavior,
            "learning_confidence": confidence,
            "learning_multiplier": learning_multiplier,
            "adjusted_score": adjusted_score,
        }

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        scored = [
            self.score_candidate(candidate)
            for candidate in candidates
        ]

        scored.sort(
            key=lambda item: (
                item["adjusted_score"],
                item["retrieval_similarity"],
                -item["canonical_memory_id"],
            ),
            reverse=True,
        )

        return scored

    def select(
        self,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        ranked = self.rank_candidates(
            candidates
        )

        if not ranked:
            raise ValueError(
                "No memory candidates were supplied."
            )

        return {
            "selected": ranked[0],
            "ranked_candidates": ranked,
        }

    def build_learning_context(
        self,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        result = self.select(
            candidates
        )

        selected = result[
            "selected"
        ]

        return {
            "selected_memory": selected,
            "ranked_candidates": result[
                "ranked_candidates"
            ],
            "learning_changed_selection": (
                selected[
                    "learning_multiplier"
                ]
                != 1.0
            ),
        }