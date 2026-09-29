import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.db import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectRepository:
    def __init__(self, database=None):
        self.db = database or db

    def create(
        self,
        *,
        project_id: str,
        name: str,
        project_type: str,
        description: str,
        hindsight_bank_id: str,
    ) -> Dict[str, Any]:
        conn = self.db.get_connection()
        try:
            created_at = now_iso()
            updated_at = created_at
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, project_type, description,
                    hindsight_bank_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name,
                    project_type,
                    description,
                    hindsight_bank_id,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            return {
                "project_id": project_id,
                "name": name,
                "project_type": project_type,
                "description": description,
                "hindsight_bank_id": hindsight_bank_id,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        finally:
            conn.close()

    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_all(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete(self, project_id: str) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM projects WHERE project_id = ?",
                (project_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
