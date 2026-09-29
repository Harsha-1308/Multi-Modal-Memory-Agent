import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.db import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageRepository:
    def __init__(self, database=None):
        self.db = database or db

    def create(
        self,
        *,
        chat_id: str,
        role: str,
        content: str,
        message_type: str,
        message_id: Optional[str] = None,
        canonical_memory_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        conn = self.db.get_connection()
        try:
            mid = message_id or f"msg-{uuid.uuid4().hex[:12]}"
            created_at = now_iso()
            meta_str = json.dumps(metadata or {}, default=str)
            conn.execute(
                """
                INSERT INTO messages (
                    message_id, chat_id, role, content, message_type,
                    canonical_memory_id, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mid,
                    chat_id,
                    role,
                    content,
                    message_type,
                    canonical_memory_id,
                    meta_str,
                    created_at,
                ),
            )
            conn.commit()
            return {
                "message_id": mid,
                "chat_id": chat_id,
                "role": role,
                "content": content,
                "message_type": message_type,
                "canonical_memory_id": canonical_memory_id,
                "metadata": metadata or {},
                "created_at": created_at,
            }
        finally:
            conn.close()

    def get(self, message_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            return d
        finally:
            conn.close()

    def list_for_chat(self, chat_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
                (chat_id,),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["metadata"] = json.loads(d.get("metadata_json") or "{}")
                except Exception:
                    d["metadata"] = {}
                results.append(d)
            return results
        finally:
            conn.close()

    def list_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT m.*
                FROM messages m
                JOIN chats c ON c.chat_id = m.chat_id
                WHERE c.project_id = ?
                ORDER BY m.created_at ASC
                """,
                (project_id,),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["metadata"] = json.loads(d.get("metadata_json") or "{}")
                except Exception:
                    d["metadata"] = {}
                results.append(d)
            return results
        finally:
            conn.close()

    def update_metadata(
        self,
        message_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        canonical_memory_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            updates = []
            params = []
            if metadata is not None:
                updates.append("metadata_json = ?")
                params.append(json.dumps(metadata, default=str))
            if canonical_memory_id is not None:
                updates.append("canonical_memory_id = ?")
                params.append(canonical_memory_id)

            if updates:
                params.append(message_id)
                conn.execute(
                    f"UPDATE messages SET {', '.join(updates)} WHERE message_id = ?",
                    tuple(params),
                )
                conn.commit()
            return self.get(message_id)
        finally:
            conn.close()

    def recent_update_records(
        self,
        *,
        project_id: str,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT
                    m.message_id,
                    m.chat_id,
                    m.content,
                    m.canonical_memory_id,
                    m.created_at
                FROM messages m
                JOIN chats c ON c.chat_id = m.chat_id
                WHERE c.project_id = ?
                  AND m.role = 'user'
                  AND m.message_type = 'MEMORY_UPDATE'
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (project_id, int(limit)),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]
        finally:
            conn.close()

    def find_memory_source(
        self,
        *,
        project_id: str,
        canonical_memory_id: int,
    ) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT
                    m.message_id,
                    m.chat_id,
                    m.content,
                    m.created_at
                FROM messages m
                JOIN chats c ON c.chat_id = m.chat_id
                WHERE c.project_id = ?
                  AND m.role = 'user'
                  AND m.message_type = 'MEMORY_UPDATE'
                  AND m.canonical_memory_id = ?
                ORDER BY m.created_at ASC
                """,
                (project_id, int(canonical_memory_id)),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
