from typing import Any, Callable, Dict, List, Optional


class ClosedLearningLoopService:
    """
    C5 CLOSED LEARNING LOOP

    Connects the already-tested layers:

        memory
            ↓
        learning state
            ↓
        provenance
            ↓
        learning decision
            ↓
        agent context
            ↓
        answer
            ↓
        later outcome
            ↓
        C3 classification
            ↓
        C4 learning refresh

    Important design rule:

        C5 DOES NOT replace C3 or C4.

        C3 remains the authority for outcome classification.
        C4 remains the authority for aggregate learning state.
        C5 only consumes their results and uses them for future
        agent behavior.
    """

    # ------------------------------------------------------------
    # BEHAVIOR STATES
    # ------------------------------------------------------------

    PREFER = "prefer"
    CAUTIOUS = "cautious"
    NEUTRAL = "neutral"
    INSUFFICIENT = "insufficient"

    # ------------------------------------------------------------
    # OUTCOME STATES
    # ------------------------------------------------------------

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

    def __init__(
        self,
        learning_service,
        canonical_memory_service=None,
    ):
        if learning_service is None:
            raise ValueError(
                "learning_service is required."
            )

        self.learning_service = learning_service

        self.canonical_memory_service = (
            canonical_memory_service
        )

    # ============================================================
    # C5.1 — GET LEARNING-AWARE MEMORY VIEW
    # ============================================================

    def get_learning_view(
        self,
        canonical_memory_id: int,
    ) -> Dict[str, Any]:
        """
        Return the complete C4 learning view for one canonical
        memory.

        This is the bridge from C4 -> C5.
        """

        view = self.learning_service.get_learning_view(
            canonical_memory_id=canonical_memory_id
        )

        if view is None:
            raise ValueError(
                "No persisted learning state exists for "
                f"canonical memory {canonical_memory_id}."
            )

        return view

    # ============================================================
    # C5.2 — DECIDE FUTURE BEHAVIOR
    # ============================================================

    def decide_behavior(
        self,
        learning_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert C4 learning state into a conservative behavior
        instruction.

        We deliberately do NOT claim that a memory is objectively
        correct.

        We only describe what historical outcomes support.
        """

        total = int(
            learning_state.get(
                "total_outcomes",
                0,
            )
            or 0
        )

        informative = int(
            learning_state.get(
                "informative_outcomes",
                0,
            )
            or 0
        )

        success_rate = float(
            learning_state.get(
                "success_rate",
                0.0,
            )
            or 0.0
        )

        failure_rate = float(
            learning_state.get(
                "failure_rate",
                0.0,
            )
            or 0.0
        )

        partial_rate = float(
            learning_state.get(
                "partial_rate",
                0.0,
            )
            or 0.0
        )

        signal = float(
            learning_state.get(
                "learning_signal",
                0.0,
            )
            or 0.0
        )

        # --------------------------------------------------------
        # No historical experience.
        # --------------------------------------------------------

        if total == 0 or informative == 0:
            return {
                "behavior": self.INSUFFICIENT,
                "reason": (
                    "There is insufficient informative historical "
                    "outcome data for this memory."
                ),
                "learning_signal": signal,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "partial_rate": partial_rate,
                "informative_outcomes": informative,
            }

        # --------------------------------------------------------
        # Strong historical success.
        #
        # Require both:
        #   - positive signal
        #   - more successes than failures
        #
        # This prevents one isolated success from being treated
        # as strong evidence.
        # --------------------------------------------------------

        if (
            signal > 0
            and success_rate > failure_rate
        ):
            return {
                "behavior": self.PREFER,
                "reason": (
                    "Historical outcomes contain more successful "
                    "than unsuccessful informative results."
                ),
                "learning_signal": signal,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "partial_rate": partial_rate,
                "informative_outcomes": informative,
            }

        # --------------------------------------------------------
        # Strong historical failure.
        # --------------------------------------------------------

        if (
            signal < 0
            and failure_rate > success_rate
        ):
            return {
                "behavior": self.CAUTIOUS,
                "reason": (
                    "Historical outcomes contain more unsuccessful "
                    "than successful informative results."
                ),
                "learning_signal": signal,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "partial_rate": partial_rate,
                "informative_outcomes": informative,
            }

        # --------------------------------------------------------
        # Mixed / balanced history.
        # --------------------------------------------------------

        return {
            "behavior": self.NEUTRAL,
            "reason": (
                "Historical outcomes are mixed or balanced; "
                "the memory should not receive a strong preference."
            ),
            "learning_signal": signal,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "partial_rate": partial_rate,
            "informative_outcomes": informative,
        }

    # ============================================================
    # C5.3 — BUILD AGENT CONTEXT
    # ============================================================

    def build_agent_context(
        self,
        canonical_memory_id: int,
        query: str,
        memory_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Construct the complete context that an agent should receive.

        The agent receives:

            query
            memory
            learning state
            provenance
            behavior instruction
        """

        if not query or not query.strip():
            raise ValueError(
                "query must not be empty."
            )

        view = self.get_learning_view(
            canonical_memory_id
        )

        learning_state = view[
            "learning_state"
        ]

        provenance = view[
            "provenance"
        ]

        decision = self.decide_behavior(
            learning_state
        )

        return {
            "query": query,

            "memory": {
                "canonical_memory_id": (
                    canonical_memory_id
                ),
                "text": memory_text,
            },

            "learning": {
                "state": learning_state,
                "provenance": provenance,
            },

            "decision": decision,
        }

    # ============================================================
    # C5.4 — GENERATE ANSWER USING LEARNING CONTEXT
    # ============================================================

    def answer(
        self,
        canonical_memory_id: int,
        query: str,
        answer_generator: Callable[
            [Dict[str, Any]],
            str,
        ],
        memory_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an answer from the learning-aware context.

        answer_generator is intentionally injected.

        This lets us:

        1. test C5 without depending on Groq/network calls;
        2. later plug the existing grounded/Groq agent into the
           exact same C5 interface.
        """

        if not callable(answer_generator):
            raise ValueError(
                "answer_generator must be callable."
            )

        context = self.build_agent_context(
            canonical_memory_id=canonical_memory_id,
            query=query,
            memory_text=memory_text,
        )

        answer_text = answer_generator(
            context
        )

        if not isinstance(answer_text, str):
            raise TypeError(
                "answer_generator must return a string."
            )

        answer_text = answer_text.strip()

        if not answer_text:
            raise ValueError(
                "answer_generator returned an empty answer."
            )

        return {
            "query": query,
            "answer": answer_text,
            "memory_id": canonical_memory_id,
            "behavior": context[
                "decision"
            ]["behavior"],
            "learning_state": context[
                "learning"
            ]["state"],
            "provenance": context[
                "learning"
            ]["provenance"],
            "context": context,
        }

    # ============================================================
    # C5.5 — RECORD NEW LEARNING
    # ============================================================

    def refresh_after_outcome(
        self,
        canonical_memory_id: int,
    ) -> Dict[str, Any]:
        """
        Refresh C4 after a new outcome has already been captured
        and classified.

        IMPORTANT:

        C5 does not classify the outcome.

        The correct order is:

            Outcome
                ↓
            C3 classify
                ↓
            C5 refresh C4
        """

        updated_state = (
            self.learning_service.refresh(
                canonical_memory_id=canonical_memory_id
            )
        )

        provenance = (
            self.learning_service.get_provenance(
                canonical_memory_id=canonical_memory_id
            )
        )

        decision = self.decide_behavior(
            updated_state
        )

        return {
            "memory_id": canonical_memory_id,
            "learning_state": updated_state,
            "provenance": provenance,
            "decision": decision,
        }

    # ============================================================
    # C5.6 — COMPLETE CLOSED TURN
    # ============================================================

    def run_turn(
        self,
        canonical_memory_id: int,
        query: str,
        answer_generator: Callable[
            [Dict[str, Any]],
            str,
        ],
        memory_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the C5 read side of the closed loop.

        This method intentionally does NOT create an outcome,
        because an outcome should be created from what actually
        happened after the answer was used.

        Return:

            answer
            learning state used
            behavior used
            provenance
        """

        return self.answer(
            canonical_memory_id=canonical_memory_id,
            query=query,
            answer_generator=answer_generator,
            memory_text=memory_text,
        )

    # ============================================================
    # C5.7 — EXPLAIN WHY THE MEMORY WAS USED
    # ============================================================

    def explain(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Produce a machine-readable explanation/provenance object.
        """

        return {
            "memory_id": result["memory_id"],
            "behavior": result["behavior"],
            "learning_signal": result[
                "learning_state"
            ]["learning_signal"],
            "success_rate": result[
                "learning_state"
            ]["success_rate"],
            "failure_rate": result[
                "learning_state"
            ]["failure_rate"],
            "partial_rate": result[
                "learning_state"
            ]["partial_rate"],
            "provenance": result[
                "provenance"
            ],
        }