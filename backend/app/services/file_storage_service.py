import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple
from app.core.config import settings


class FileStorageService:
    def __init__(self, root_dir: Optional[str] = None):
        self.root_path = Path(root_dir or settings.STORAGE_ROOT)
        if not self.root_path.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent.parent
            self.root_path = (backend_dir / self.root_path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def store_evidence_file(
        self,
        *,
        project_id: str,
        evidence_id: str,
        file_bytes: bytes,
    ) -> Tuple[str, str, int]:
        """
        Stores original file at:
        projects/<project_id>/evidence/<evidence_id>/original_file

        Returns (storage_key, sha256, size_bytes).
        """
        # Validate IDs to prevent path traversal
        self._validate_id(project_id)
        self._validate_id(evidence_id)

        rel_key = f"projects/{project_id}/evidence/{evidence_id}/original_file"
        dest_path = (self.root_path / rel_key).resolve()

        # Security check: ensure path is within root_path
        if not str(dest_path).startswith(str(self.root_path)):
            raise ValueError("Path traversal attempt detected")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(file_bytes)

        sha256 = self.compute_sha256(file_bytes)
        size_bytes = len(file_bytes)

        return rel_key, sha256, size_bytes

    def resolve_path(self, storage_key: str, project_id: Optional[str] = None) -> Path:
        """
        Resolves storage_key safely. Ensures it stays within root_path
        and matches project_id if provided.
        """
        if ".." in storage_key or storage_key.startswith("/") or "\\" in storage_key:
            # Normalize slashes
            clean_key = storage_key.replace("\\", "/").strip("/")
            if ".." in clean_key.split("/"):
                raise ValueError("Path traversal attempt detected")
        else:
            clean_key = storage_key

        resolved = (self.root_path / clean_key).resolve()

        if not str(resolved).startswith(str(self.root_path)):
            raise ValueError("Unauthorized path access")

        if project_id:
            expected_prefix = (self.root_path / "projects" / project_id).resolve()
            if not str(resolved).startswith(str(expected_prefix)):
                raise ValueError("Cross-project storage access rejected")

        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError("Storage file not found")

        return resolved

    def read_bytes(self, storage_key: str, project_id: Optional[str] = None) -> bytes:
        path = self.resolve_path(storage_key, project_id)
        return path.read_bytes()

    def _validate_id(self, id_str: str) -> None:
        if not id_str or "/" in id_str or "\\" in id_str or ".." in id_str:
            raise ValueError(f"Invalid identifier for storage: {id_str}")
