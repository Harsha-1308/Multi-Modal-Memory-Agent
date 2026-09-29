from typing import Any, Dict, List, Optional

from app.services.experience_service import ExperienceService
from app.services.outcome_capture_service import OutcomeCaptureService
from app.services.outcome_classification_service import (
    OutcomeClassificationService,
)
from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)
from app.services.evidence_service import EvidenceService


class LearningFeedbackService:
    """
    D1: Orchestrates the existing C2 -> C3 -> C4 -> C5 feedback pipeline.

    Pipeline:

        Experience
            ↓
        Outcome
            ↓
        Evidence
            ↓
        C3 Classification
            ↓
        C4 Learning
            ↓
        C5 Behavior

    This service is an orchestration layer.

    It does NOT reimplement:
        - C3 classification rules
        - C4 learning formulas
        - C5 behavior rules
    """

    def __init__(
        self,
        experience_service: ExperienceService,
        outcome_service: OutcomeCaptureService,
        classification_service: OutcomeClassificationService,
        learning_service: MemoryLearningStateService,
        evidence_service: Optional[EvidenceService] = None,
        closed_loop_service: Any = None,
    ):
        self.experience_service = experience_service
        self.outcome_service = outcome_service
        self.classification_service = classification_service
        self.learning_service = learning_service
        self.evidence_service = evidence_service
        self.closed_loop_service = closed_loop_service

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _require_text(
        value: Any,
        field_name: str,
    ) -> str:

        if value is None:
            raise ValueError(
                f"{field_name} is required."
            )

        value = str(value).strip()

        if not value:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return value

    @staticmethod
    def _validate_memory_id(
        canonical_memory_id: Any,
    ) -> int:

        try:
            value = int(
                canonical_memory_id
            )
        except (
            TypeError,
            ValueError,
        ):
            raise ValueError(
                "canonical_memory_id must be an integer."
            )

        if value <= 0:
            raise ValueError(
                "canonical_memory_id must be positive."
            )

        return value

    # ============================================================
    # EVIDENCE NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_evidence_item(
        item: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(item, dict):
            raise ValueError(
                "Each evidence item must be a dictionary."
            )

        evidence_type = (
            item.get("evidence_type")
            or item.get("type")
        )

        if evidence_type is None:
            raise ValueError(
                "Each evidence item requires evidence_type."
            )

        evidence_type = str(
            evidence_type
        ).strip()

        if not evidence_type:
            raise ValueError(
                "evidence_type cannot be empty."
            )

        return {
            "evidence_type": evidence_type,
            "content": item.get("content"),
            "file_name": item.get("file_name"),
            "mime_type": item.get("mime_type"),
            "storage_key": item.get("storage_key"),
            "file_bytes": item.get("file_bytes"),
            "sha256": item.get("sha256"),
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
        }

    # ============================================================
    # EVIDENCE PERSISTENCE ADAPTER
    # ============================================================

    def _create_evidence(
        self,
        *,
        experience_id: str,
        outcome_id: str,
        item: Dict[str, Any],
    ) -> Dict[str, Any]:

        if self.evidence_service is None:
            raise RuntimeError(
                "EvidenceService is required when evidence is supplied."
            )

        evidence_type = item["evidence_type"]

        # --------------------------------------------------------
        # TEXT
        # --------------------------------------------------------

        if evidence_type == "text":

            content = item.get("content")

            return self.evidence_service.create_text_evidence(
                experience_id=experience_id,
                outcome_id=outcome_id,
                content=content,
                source_type=(
                    item.get("source_type")
                    or "agent_observation"
                ),
                source_id=item.get("source_id"),
            )

        # --------------------------------------------------------
        # TEST RESULT
        # --------------------------------------------------------

        if evidence_type == "test_result":

            content = item.get("content")

            return self.evidence_service.create_test_result(
                experience_id=experience_id,
                outcome_id=outcome_id,
                result=content,
                source_id=item.get("source_id"),
            )

        # --------------------------------------------------------
        # TOOL OUTPUT
        # --------------------------------------------------------

        if evidence_type == "tool_output":

            content = item.get("content")

            return self.evidence_service.create_tool_output(
                experience_id=experience_id,
                outcome_id=outcome_id,
                output=content,
                source_id=item.get("source_id"),
            )

        # --------------------------------------------------------
        # IMAGE / FILE / CODE
        # --------------------------------------------------------

        if evidence_type in {
            "image",
            "file",
            "code",
        }:

            file_bytes = item.get(
                "file_bytes"
            )

            if file_bytes is None:
                raise ValueError(
                    f"{evidence_type} evidence requires "
                    "file_bytes."
                )

            return self.evidence_service.create_file_evidence(
                experience_id=experience_id,
                outcome_id=outcome_id,
                file_name=item.get("file_name"),
                mime_type=item.get("mime_type"),
                storage_key=item.get("storage_key"),
                file_bytes=file_bytes,
                evidence_type=evidence_type,
                source_type=(
                    item.get("source_type")
                    or "user_upload"
                ),
                source_id=item.get("source_id"),
            )

        # --------------------------------------------------------
        # UNSUPPORTED
        # --------------------------------------------------------

        raise ValueError(
            f"Unsupported evidence type: "
            f"{evidence_type}"
        )

    # ============================================================
    # MAIN FEEDBACK PIPELINE
    # ============================================================

    def record_feedback(
        self,
        *,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: str,
        outcome_type: str,
        outcome_summary: str,
        outcome_details: Optional[str] = None,
        evidence: Optional[
            List[Dict[str, Any]]
        ] = None,
    ) -> Dict[str, Any]:

        # --------------------------------------------------------
        # VALIDATE
        # --------------------------------------------------------

        bank_id = self._require_text(
            bank_id,
            "bank_id",
        )

        canonical_memory_id = (
            self._validate_memory_id(
                canonical_memory_id
            )
        )

        task = self._require_text(
            task,
            "task",
        )

        action = self._require_text(
            action,
            "action",
        )

        context = self._require_text(
            context,
            "context",
        )

        outcome_type = self._require_text(
            outcome_type,
            "outcome_type",
        )

        outcome_summary = self._require_text(
            outcome_summary,
            "outcome_summary",
        )

        if outcome_details is not None:
            outcome_details = str(
                outcome_details
            )

        if evidence is None:
            evidence = []

        if not isinstance(
            evidence,
            list,
        ):
            raise ValueError(
                "evidence must be a list."
            )

        normalized_evidence = [
            self._normalize_evidence_item(
                item
            )
            for item in evidence
        ]

        # --------------------------------------------------------
        # C2.1 EXPERIENCE
        # --------------------------------------------------------

        experience = (
            self.experience_service.create(
                bank_id=bank_id,
                canonical_memory_id=canonical_memory_id,
                task=task,
                action=action,
                context=context,
            )
        )

        experience_id = (
            experience["experience_id"]
        )

        # --------------------------------------------------------
        # C2.2 OUTCOME
        # --------------------------------------------------------

        outcome_kwargs = {
            "experience_id": experience_id,
            "outcome_type": outcome_type,
            "summary": outcome_summary,
        }

        if outcome_details is not None:
            outcome_kwargs[
                "details"
            ] = outcome_details

        outcome = (
            self.outcome_service.create(
                **outcome_kwargs
            )
        )

        outcome_id = (
            outcome["outcome_id"]
        )

        # --------------------------------------------------------
        # C2.3 EVIDENCE
        # --------------------------------------------------------

        persisted_evidence = []

        for item in normalized_evidence:

            evidence_record = (
                self._create_evidence(
                    experience_id=experience_id,
                    outcome_id=outcome_id,
                    item=item,
                )
            )

            persisted_evidence.append(
                evidence_record
            )

        # --------------------------------------------------------
        # C3
        # --------------------------------------------------------

        classification = (
            self.classification_service.classify(
                outcome_id=outcome_id
            )
        )

        # --------------------------------------------------------
        # C4
        # --------------------------------------------------------

        learning_state = (
            self.learning_service.refresh(
                canonical_memory_id=canonical_memory_id
            )
        )

        provenance = (
            self.learning_service.get_provenance(
                canonical_memory_id=canonical_memory_id
            )
        )

        # --------------------------------------------------------
        # C5
        # --------------------------------------------------------

        decision = None

        if self.closed_loop_service is not None:

            decision = (
                self.closed_loop_service.decide_behavior(
                    learning_state
                )
            )

        # --------------------------------------------------------
        # FINAL CONTRACT
        # --------------------------------------------------------

        return {
            "experience": experience,
            "outcome": outcome,
            "evidence": persisted_evidence,
            "classification": classification,
            "learning_state": learning_state,
            "provenance": provenance,
            "decision": decision,
        }

    # ============================================================
    # CONVENIENCE METHODS
    # ============================================================

    def record_success(
        self,
        *,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: str,
        outcome_summary: str,
        evidence: List[Dict[str, Any]],
        outcome_details: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.record_feedback(
            bank_id=bank_id,
            canonical_memory_id=canonical_memory_id,
            task=task,
            action=action,
            context=context,
            outcome_type="success",
            outcome_summary=outcome_summary,
            outcome_details=outcome_details,
            evidence=evidence,
        )

    def record_failure(
        self,
        *,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: str,
        outcome_summary: str,
        evidence: List[Dict[str, Any]],
        outcome_details: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.record_feedback(
            bank_id=bank_id,
            canonical_memory_id=canonical_memory_id,
            task=task,
            action=action,
            context=context,
            outcome_type="failure",
            outcome_summary=outcome_summary,
            outcome_details=outcome_details,
            evidence=evidence,
        )

    def record_partial(
        self,
        *,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: str,
        outcome_summary: str,
        evidence: List[Dict[str, Any]],
        outcome_details: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.record_feedback(
            bank_id=bank_id,
            canonical_memory_id=canonical_memory_id,
            task=task,
            action=action,
            context=context,
            outcome_type="partial",
            outcome_summary=outcome_summary,
            outcome_details=outcome_details,
            evidence=evidence,
        )

    def record_unknown(
        self,
        *,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: str,
        outcome_summary: str,
        evidence: Optional[
            List[Dict[str, Any]]
        ] = None,
        outcome_details: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.record_feedback(
            bank_id=bank_id,
            canonical_memory_id=canonical_memory_id,
            task=task,
            action=action,
            context=context,
            outcome_type="unknown",
            outcome_summary=outcome_summary,
            outcome_details=outcome_details,
            evidence=evidence or [],
        )