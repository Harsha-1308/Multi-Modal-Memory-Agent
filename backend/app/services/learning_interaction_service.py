from typing import Any, Dict, List, Optional


class LearningInteractionService:
    """
    D2 - Real multi-interaction learning orchestrator.

    Responsibilities:

        Interaction
            ↓
        LearningAgentService
            ↓
        Hindsight retrieval
            ↓
        Resolver
            ↓
        Quality Gate
            ↓
        C6 adaptive selection
            ↓
        C5 behavior/context
            ↓
        Answer generator / Groq
            ↓
        User/tool outcome
            ↓
        D1 LearningFeedbackService
            ↓
        C3 classification
            ↓
        C4 learning state
            ↓
        C5 updated behavior

    Important design rule:
        This service does NOT duplicate C3/C4/C5/C6 logic.

    It orchestrates the already-tested services.
    """

    def __init__(
        self,
        learning_agent,
        feedback_service,
        answer_generator=None,
    ):
        if learning_agent is None:
            raise ValueError("learning_agent is required")

        if feedback_service is None:
            raise ValueError("feedback_service is required")

        self.learning_agent = learning_agent
        self.feedback_service = feedback_service
        self.answer_generator = answer_generator

    # ------------------------------------------------------------------
    # INTERACTION
    # ------------------------------------------------------------------

    def interact(
        self,
        bank_id: str,
        query: str,
        answer_generator=None,
    ) -> Dict[str, Any]:
        """
        Run one complete agent interaction.

        Flow:

            Hindsight
              ↓
            resolver
              ↓
            quality gate
              ↓
            C6
              ↓
            C5
              ↓
            answer generator / Groq
        """

        if not isinstance(bank_id, str) or not bank_id.strip():
            raise ValueError("bank_id must be a non-empty string")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        generator = (
            answer_generator
            if answer_generator is not None
            else self.answer_generator
        )

        result = self.learning_agent.answer(
            bank_id=bank_id,
            query=query,
            answer_generator=generator,
        )

        selection = result.get("selection")
        selected = (
            selection.get("selected")
            if isinstance(selection, dict)
            else None
        )

        selection_view = {
            "selected_memory_id": None,
            "retrieval_similarity": None,
            "learning_signal": None,
            "learning_multiplier": None,
            "adjusted_score": None,
            "behavior": result.get("behavior"),
            "learning_confidence": None,
            "informative_outcomes": None,
            "evidence_coverage": None,
        }

        if isinstance(selected, dict):
            selection_view.update(
                {
                    "selected_memory_id": selected.get(
                        "canonical_memory_id"
                    ),
                    "retrieval_similarity": selected.get(
                        "retrieval_similarity"
                    ),
                    "learning_signal": selected.get(
                        "learning_signal"
                    ),
                    "learning_multiplier": selected.get(
                        "learning_multiplier"
                    ),
                    "adjusted_score": selected.get(
                        "adjusted_score"
                    ),
                    "behavior": selected.get(
                        "behavior"
                    ),
                    "learning_confidence": selected.get(
                        "learning_confidence"
                    ),
                    "informative_outcomes": selected.get(
                        "informative_outcomes"
                    ),
                    "evidence_coverage": selected.get(
                        "evidence_coverage"
                    ),
                }
            )

        return {
            "query": query,
            "answer": result.get("answer"),
            "selected_memory": result.get("selected_memory"),
            "selection": selection,
            "selection_view": selection_view,
            "behavior": result.get("behavior"),
            "learning": result.get("learning"),
            "provenance": result.get("provenance"),
            "retrieval": result.get("retrieval"),
        }
    # ------------------------------------------------------------------
    # FEEDBACK
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        canonical_memory_id: int,
        query: str,
        answer: str,
        outcome_type: str,
        outcome_summary: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record the result of an interaction through D1.

        D1 owns:

            C2 → C3 → C4 → C5

        This service only supplies the interaction data.
        """

        if not isinstance(canonical_memory_id, int):
            raise ValueError("canonical_memory_id must be an integer")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        if not isinstance(answer, str):
            raise ValueError("answer must be a string")

        if outcome_type not in {"success", "failure"}:
            raise ValueError(
                "outcome_type must be 'success' or 'failure' "
                "because C2 currently accepts only those reported types"
            )

        if not isinstance(outcome_summary, str) or not outcome_summary.strip():
            raise ValueError("outcome_summary must be a non-empty string")

        if evidence is None:
            evidence = []

        if not isinstance(evidence, list):
            raise ValueError("evidence must be a list")

        result = self.feedback_service.record_feedback(
            canonical_memory_id=canonical_memory_id,
            query=query,
            answer=answer,
            outcome_type=outcome_type,
            outcome_summary=outcome_summary,
            evidence=evidence,
            metadata=metadata,
        )

        return result

    # ------------------------------------------------------------------
    # COMPLETE INTERACTION + FEEDBACK
    # ------------------------------------------------------------------

    def interact_and_record(
        self,
        bank_id: str,
        query: str,
        outcome_type: str,
        outcome_summary: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        answer_generator=None,
    ) -> Dict[str, Any]:
        """
        Run one interaction and immediately record its outcome.

        This is the main D2 method.

        It intentionally keeps the answer step and feedback step
        separate internally so that the resulting object clearly
        shows:

            BEFORE learning
            interaction
            feedback
            AFTER learning
        """

        interaction = self.interact(
            bank_id=bank_id,
            query=query,
            answer_generator=answer_generator,
        )

        selected_memory = interaction.get("selected_memory")

        if selected_memory is None:
            raise RuntimeError(
                "LearningAgentService returned no selected memory"
            )

        canonical_memory_id = self._extract_memory_id(selected_memory)

        if canonical_memory_id is None:
            raise RuntimeError(
                "Could not extract canonical_memory_id from selected memory"
            )

        feedback = self.record_outcome(
            canonical_memory_id=canonical_memory_id,
            query=query,
            answer=interaction.get("answer") or "",
            outcome_type=outcome_type,
            outcome_summary=outcome_summary,
            evidence=evidence,
            metadata=metadata,
        )

        return {
            "interaction": interaction,
            "feedback": feedback,
            "canonical_memory_id": canonical_memory_id,
        }

    # ------------------------------------------------------------------
    # LEARNING VIEW
    # ------------------------------------------------------------------

    def get_learning_view(
        self,
        canonical_memory_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the current C4/C5 learning state for a memory.

        D1 exposes the current learning state through its underlying
        MemoryLearningStateService/repository contract.
        """

        # D1 returns the updated C5 decision in feedback results.
        # For direct inspection we use the learning service attached
        # to D1 when available.

        learning_service = getattr(
            self.feedback_service,
            "learning_service",
            None,
        )

        if learning_service is not None:
            return learning_service.get_learning_view(
                canonical_memory_id
            )

        repository = getattr(
            self.feedback_service,
            "repository",
            None,
        )

        if repository is not None:
            state = repository.get_memory_learning_state(
                canonical_memory_id
            )
            provenance = repository.get_memory_learning_provenance(
                canonical_memory_id
            )

            if state is None:
                return None

            return {
                "memory_id": canonical_memory_id,
                "learning_state": state,
                "provenance": provenance,
            }

        return None

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_memory_id(memory: Any) -> Optional[int]:
        """
        Extract canonical memory ID from the different representations
        already used by the project.
        """

        if memory is None:
            return None

        if isinstance(memory, int):
            return memory

        if isinstance(memory, dict):
            for key in (
                "canonical_memory_id",
                "memory_id",
                "id",
            ):
                value = memory.get(key)

                if isinstance(value, int):
                    return value

        for attribute in (
            "canonical_memory_id",
            "memory_id",
            "id",
        ):
            value = getattr(memory, attribute, None)

            if isinstance(value, int):
                return value

        return None

    @staticmethod
    def close() -> None:
        """
        D2 does not own the lifecycle of the underlying services.

        Existing services are responsible for closing their own
        resources.
        """
        return None
    @staticmethod
    def _build_selection_view(
        selection: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Expose the important C6 selection information
        in a stable D2-friendly structure.
        """

        if not isinstance(selection, dict):
            return {
                "selected_memory_id": None,
                "retrieval_similarity": None,
                "learning_signal": None,
                "learning_multiplier": None,
                "adjusted_score": None,
                "behavior": None,
                "ranked_candidates": [],
            }

        selected = selection.get("selected")

        if not isinstance(selected, dict):
            selected = {}

        ranked_candidates = selection.get(
            "ranked_candidates",
            [],
        )

        if not isinstance(ranked_candidates, list):
            ranked_candidates = []

        return {
            "selected_memory_id": selected.get(
                "canonical_memory_id"
            ),
            "retrieval_similarity": selected.get(
                "retrieval_similarity"
            ),
            "learning_signal": selected.get(
                "learning_signal"
            ),
            "learning_multiplier": selected.get(
                "learning_multiplier"
            ),
            "adjusted_score": selected.get(
                "adjusted_score"
            ),
            "behavior": None,
            "ranked_candidates": ranked_candidates,
        }