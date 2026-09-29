from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.db import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatRepository:
    def __init__(self, database=None):
        self.db = database or db

    def create(
        self,
        *,
        chat_id: str,
        project_id: str,
        name: str,
        memory_enabled: bool = True,
    ) -> Dict[str, Any]:
        conn = self.db.get_connection()
        try:
            created_at = now_iso()
            updated_at = created_at
            conn.execute(
                """
                INSERT INTO chats (
                    chat_id, project_id, name, memory_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    project_id,
                    name,
                    1 if memory_enabled else 0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            return {
                "chat_id": chat_id,
                "project_id": project_id,
                "name": name,
                "memory_enabled": bool(memory_enabled),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        finally:
            conn.close()

    def get(self, chat_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM chats WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            data["memory_enabled"] = bool(data["memory_enabled"])
            return data
        finally:
            conn.close()

    def list_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM chats WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["memory_enabled"] = bool(d["memory_enabled"])
                result.append(d)
            return result
        finally:
            conn.close()

    def update_settings(
        self, chat_id: str, *, memory_enabled: bool
    ) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            updated_at = now_iso()
            conn.execute(
                """
                UPDATE chats
                SET memory_enabled = ?, updated_at = ?
                WHERE chat_id = ?
                """,
                (1 if memory_enabled else 0, updated_at, chat_id),
            )
            conn.commit()
            return self.get(chat_id)
        finally:
            conn.close()

    def delete(self, chat_id: str) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM chats WHERE chat_id = ?",
                (chat_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
