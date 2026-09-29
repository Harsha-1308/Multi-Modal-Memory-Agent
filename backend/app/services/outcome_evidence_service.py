from app.storage.repository_factory import (
    create_learning_repository,
)


class OutcomeEvidenceService:

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else create_learning_repository()
        )

    def get_complete_outcome_chain(
        self,
        outcome_id: str,
    ):

        outcome = (
            self.repository
            .get_outcome(
                outcome_id
            )
        )

        if outcome is None:
            return None

        experience = (
            self.repository
            .get_experience(
                outcome["experience_id"]
            )
        )

        if experience is None:
            raise RuntimeError(
                "Outcome exists but its "
                "experience does not exist."
            )

        evidence = (
            self.repository
            .list_evidence_for_outcome(
                outcome_id
            )
        )

        return {
            "outcome": outcome,
            "experience": experience,
            "evidence": evidence,
        }

    def close(self):
        self.repository.close()