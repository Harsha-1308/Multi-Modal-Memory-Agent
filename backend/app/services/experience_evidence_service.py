from app.services.experience_service import (
    ExperienceService,
)
from app.services.evidence_service import (
    EvidenceService,
)


class ExperienceEvidenceService:

    def __init__(
        self,
        experience_service=None,
        evidence_service=None,
    ):
        self.experience = (
            experience_service
            if experience_service is not None
            else ExperienceService()
        )

        self.evidence = (
            evidence_service
            if evidence_service is not None
            else EvidenceService()
        )

    def get_complete_experience(
        self,
        experience_id: str,
    ) -> dict:

        experience = self.experience.get(
            experience_id
        )

        if experience is None:
            raise ValueError(
                "Experience not found."
            )

        evidence = self.evidence.list_for_experience(
            experience_id
        )

        return {
            "experience": experience,
            "evidence": evidence,
        }

    def close(self):
        self.experience.close()
        self.evidence.close()