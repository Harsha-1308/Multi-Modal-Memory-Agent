from dataclasses import dataclass
from typing import Optional

from app.services.outcome_learning_service import (
    OutcomeLearningService,
)


@dataclass
class MemoryLearningProfile:
    memory_id: int
    total_outcomes: int
    successes: int
    failures: int
    neutral: int
    success_rate: Optional[float]
    learning_signal: float

    @property
    def has_evidence(self) -> bool:
        return self.total_outcomes > 0

    @property
    def is_positive(self) -> bool:
        return self.learning_signal > 0

    @property
    def is_negative(self) -> bool:
        return self.learning_signal < 0

    @property
    def is_neutral(self) -> bool:
        return self.learning_signal == 0.0

    @property
    def reliability(self) -> float:
        """
        Evidence-strength measure.

        This is NOT the probability that the memory is true.

        It only measures how much outcome evidence we have,
        bounded between 0 and 1.
        """

        if self.total_outcomes == 0:
            return 0.0

        return min(
            1.0,
            self.total_outcomes / 5.0,
        )


class MemoryLearningProfileService:

    def __init__(
        self,
        outcome_learning_service: OutcomeLearningService,
    ):
        self.outcome_learning = (
            outcome_learning_service
        )

    def get_profile(
        self,
        bank_id: str,
        memory_id: int,
    ) -> MemoryLearningProfile:

        state = (
            self.outcome_learning
            .get_learning_state_for_memory(
                bank_id=bank_id,
                memory_id=memory_id,
            )
        )

        return MemoryLearningProfile(
            memory_id=state["memory_id"],
            total_outcomes=state["total_outcomes"],
            successes=state["successes"],
            failures=state["failures"],
            neutral=state["neutral"],
            success_rate=state["success_rate"],
            learning_signal=state["learning_signal"],
        )