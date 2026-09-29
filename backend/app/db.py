import os
import sqlite3
from pathlib import Path
from typing import Optional
from app.core.config import settings


def get_db_path(custom_path: Optional[str] = None) -> str:
    db_path = custom_path or settings.sqlite_db_path
    path = Path(db_path)
    if not path.is_absolute():
        backend_dir = Path(__file__).resolve().parent.parent
        path = backend_dir / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


class AppDatabase:
    """Manages SQLite schema and connections for the application."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = get_db_path(db_path)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        conn = self.get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    project_type TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    hindsight_bank_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chats (
                    chat_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    memory_enabled BOOLEAN NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    canonical_memory_id INTEGER,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_id TEXT,
                    kind TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    storage_key TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    user_description TEXT,
                    semantic_description TEXT,
                    combined_understanding TEXT,
                    canonical_memory_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
                    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
                    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chats_project_id ON chats(project_id);
                CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_project_id ON evidence(project_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_chat_id ON evidence(chat_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_message_id ON evidence(message_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON evidence(sha256);
                """
            )
            # Lightweight migration for databases created before evidence
            # was linked to canonical memory.
            evidence_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(evidence)").fetchall()
            }
            if "canonical_memory_id" not in evidence_columns:
                conn.execute(
                    "ALTER TABLE evidence ADD COLUMN canonical_memory_id INTEGER"
                )
            conn.commit()
        finally:
            conn.close()


db = AppDatabase()
