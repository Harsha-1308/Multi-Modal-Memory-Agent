from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.db import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceRepository:
    def __init__(self, database=None):
        self.db = database or db

    def create(
        self,
        *,
        evidence_id: str,
        project_id: str,
        chat_id: str,
        kind: str,
        original_filename: str,
        mime_type: str,
        storage_key: str,
        sha256: str,
        size_bytes: int,
        message_id: Optional[str] = None,
        user_description: Optional[str] = None,
        semantic_description: Optional[str] = None,
        combined_understanding: Optional[str] = None,
        canonical_memory_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        conn = self.db.get_connection()
        try:
            created_at = now_iso()
            conn.execute(
                """
                INSERT INTO evidence (
                    evidence_id, project_id, chat_id, message_id, kind,
                    original_filename, mime_type, storage_key, sha256,
                    size_bytes, user_description, semantic_description,
                    combined_understanding, canonical_memory_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    project_id,
                    chat_id,
                    message_id,
                    kind,
                    original_filename,
                    mime_type,
                    storage_key,
                    sha256,
                    size_bytes,
                    user_description,
                    semantic_description,
                    combined_understanding,
                    canonical_memory_id,
                    created_at,
                ),
            )
            conn.commit()
            return {
                "evidence_id": evidence_id,
                "project_id": project_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "kind": kind,
                "original_filename": original_filename,
                "mime_type": mime_type,
                "storage_key": storage_key,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "user_description": user_description,
                "semantic_description": semantic_description,
                "combined_understanding": combined_understanding,
                "canonical_memory_id": canonical_memory_id,
                "created_at": created_at,
            }
        finally:
            conn.close()

    def get(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM evidence WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_for_chat(self, chat_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM evidence WHERE chat_id = ? ORDER BY created_at ASC",
                (chat_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_for_message(self, message_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM evidence WHERE message_id = ? ORDER BY created_at ASC",
                (message_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def find_by_sha256(
        self, sha256: str, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM evidence WHERE sha256 = ? AND project_id = ?",
                    (sha256, project_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM evidence WHERE sha256 = ?",
                    (sha256,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_understanding(
        self,
        evidence_id: str,
        *,
        semantic_description: Optional[str] = None,
        combined_understanding: Optional[str] = None,
        canonical_memory_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            conn.execute(
                """
                UPDATE evidence
                SET semantic_description = COALESCE(?, semantic_description),
                    combined_understanding = COALESCE(?, combined_understanding),
                    canonical_memory_id = COALESCE(?, canonical_memory_id)
                WHERE evidence_id = ?
                """,
                (semantic_description, combined_understanding, canonical_memory_id, evidence_id),
            )
            conn.commit()
            return self.get(evidence_id)
        finally:
            conn.close()

    def attach_to_message(
        self,
        evidence_id: str,
        message_id: str,
    ) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            conn.execute(
                "UPDATE evidence SET message_id = ? WHERE evidence_id = ?",
                (message_id, evidence_id),
            )
            conn.commit()
            return self.get(evidence_id)
        finally:
            conn.close()