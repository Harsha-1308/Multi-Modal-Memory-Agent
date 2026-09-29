import uuid
from typing import Optional

from app.storage.repository_factory import (
    create_learning_repository,
)


class OutcomeCaptureService:

    SUCCESS = "success"
    FAILURE = "failure"

    ALLOWED_OUTCOMES = {
        SUCCESS,
        FAILURE,
    }

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else create_learning_repository()
        )

    # ============================================================
    # CREATE
    # ============================================================

    def create(
        self,
        experience_id: str,
        outcome_type: str,
        summary: str,
        details: Optional[str] = None,
    ) -> dict:

        if outcome_type not in self.ALLOWED_OUTCOMES:
            raise ValueError(
                "C2 currently supports only "
                "'success' and 'failure'."
            )

        if not summary or not summary.strip():
            raise ValueError(
                "Outcome summary is required."
            )

        outcome_id = str(
            uuid.uuid4()
        )

        return self.repository.create_outcome(
            outcome_id=outcome_id,
            experience_id=experience_id,
            outcome_type=outcome_type,
            summary=summary.strip(),
            details=(
                details.strip()
                if isinstance(details, str)
                else details
            ),
        )

    # ============================================================
    # GET
    # ============================================================

    def get(
        self,
        outcome_id: str,
    ):

        return self.repository.get_outcome(
            outcome_id=outcome_id
        )

    # ============================================================
    # LIST
    # ============================================================

    def list_for_experience(
        self,
        experience_id: str,
    ):

        return (
            self.repository
            .list_outcomes_for_experience(
                experience_id=experience_id
            )
        )

    # ============================================================
    # COMPLETE OUTCOME CONTEXT
    # ============================================================

    def get_with_experience(
        self,
        outcome_id: str,
    ):

        outcome = self.get(
            outcome_id
        )

        if outcome is None:
            return None

        experience = (
            self.repository
            .get_experience(
                outcome["experience_id"]
            )
        )

        return {
            "outcome": outcome,
            "experience": experience,
        }

    # ============================================================
    # CLOSE
    # ============================================================

    def close(self):
        self.repository.close()