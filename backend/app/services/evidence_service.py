import hashlib
import uuid
from typing import Optional

from app.storage.repository_factory import (
    create_learning_repository,
)


class EvidenceService:

    ALLOWED_TYPES = {
        "text",
        "image",
        "file",
        "code",
        "url",
        "structured_data",
        "test_result",
        "tool_output",
    }

    ALLOWED_SOURCE_TYPES = {
        "user_upload",
        "agent_observation",
        "tool_result",
        "test_result",
        "system_event",
        "generated",
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
    # TEXT EVIDENCE
    # ============================================================

    def create_text_evidence(
        self,
        experience_id: str,
        content: str,
        source_type: str = "agent_observation",
        source_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
    ):

        if not content or not content.strip():
            raise ValueError(
                "Text evidence cannot be empty."
            )

        return self._create(
            experience_id=experience_id,
            outcome_id=outcome_id,
            evidence_type="text",
            content=content.strip(),
            source_type=source_type,
            source_id=source_id,
        )

    # ============================================================
    # FILE / IMAGE / CODE
    # ============================================================

    def create_file_evidence(
        self,
        experience_id: str,
        file_name: str,
        mime_type: str,
        storage_key: str,
        file_bytes: bytes,
        evidence_type: str = "file",
        source_type: str = "user_upload",
        source_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
    ):

        if evidence_type not in {
            "image",
            "file",
            "code",
        }:
            raise ValueError(
                "File evidence_type must be "
                "image, file, or code."
            )

        if not file_name:
            raise ValueError(
                "file_name is required."
            )

        if not mime_type:
            raise ValueError(
                "mime_type is required."
            )

        if not storage_key:
            raise ValueError(
                "storage_key is required."
            )

        if not isinstance(file_bytes, bytes):
            raise TypeError(
                "file_bytes must be bytes."
            )

        sha256 = hashlib.sha256(
            file_bytes
        ).hexdigest()

        return self._create(
            experience_id=experience_id,
            outcome_id=outcome_id,
            evidence_type=evidence_type,
            file_name=file_name,
            mime_type=mime_type,
            storage_key=storage_key,
            sha256=sha256,
            source_type=source_type,
            source_id=source_id,
        )

    # ============================================================
    # TEST RESULT
    # ============================================================

    def create_test_result(
        self,
        experience_id: str,
        result: str,
        source_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
    ):

        if not result or not result.strip():
            raise ValueError(
                "Test result cannot be empty."
            )

        return self._create(
            experience_id=experience_id,
            outcome_id=outcome_id,
            evidence_type="test_result",
            content=result.strip(),
            source_type="test_result",
            source_id=source_id,
        )

    # ============================================================
    # TOOL OUTPUT
    # ============================================================

    def create_tool_output(
        self,
        experience_id: str,
        output: str,
        source_id: Optional[str] = None,
        outcome_id: Optional[str] = None,
    ):

        if not output or not output.strip():
            raise ValueError(
                "Tool output cannot be empty."
            )

        return self._create(
            experience_id=experience_id,
            outcome_id=outcome_id,
            evidence_type="tool_output",
            content=output.strip(),
            source_type="tool_result",
            source_id=source_id,
        )

    # ============================================================
    # INTERNAL CREATE
    # ============================================================

    def _create(
        self,
        experience_id: str,
        outcome_id: Optional[str],
        evidence_type: str,
        content: Optional[str] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        storage_key: Optional[str] = None,
        sha256: Optional[str] = None,
        source_type: str = "agent_observation",
        source_id: Optional[str] = None,
    ):

        if evidence_type not in self.ALLOWED_TYPES:
            raise ValueError(
                f"Unsupported evidence type: "
                f"{evidence_type}"
            )

        if source_type not in self.ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"Unsupported source type: "
                f"{source_type}"
            )

        evidence_id = str(
            uuid.uuid4()
        )

        return self.repository.create_evidence(
            evidence_id=evidence_id,
            experience_id=experience_id,
            outcome_id=outcome_id,
            evidence_type=evidence_type,
            content=content,
            file_name=file_name,
            mime_type=mime_type,
            storage_key=storage_key,
            sha256=sha256,
            source_type=source_type,
            source_id=source_id,
        )

    # ============================================================
    # GET
    # ============================================================

    def get(
        self,
        evidence_id: str,
    ):

        return self.repository.get_evidence(
            evidence_id=evidence_id
        )

    # ============================================================
    # LIST FOR EXPERIENCE
    # ============================================================

    def list_for_experience(
        self,
        experience_id: str,
    ):

        return (
            self.repository
            .list_evidence_for_experience(
                experience_id=experience_id
            )
        )

    # ============================================================
    # LIST FOR OUTCOME
    # ============================================================

    def list_for_outcome(
        self,
        outcome_id: str,
    ):

        return (
            self.repository
            .list_evidence_for_outcome(
                outcome_id=outcome_id
            )
        )

    # ============================================================
    # CLOSE
    # ============================================================

    def close(self):
        self.repository.close()