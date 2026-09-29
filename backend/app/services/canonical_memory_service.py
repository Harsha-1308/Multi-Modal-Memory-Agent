import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Optional


class CanonicalMemoryService:
    """
    B6 canonical memory layer.

    Current responsibility:
    - Normalize raw memory candidates.
    - Generate deterministic fingerprints.
    - Detect exact duplicates.
    - Register accepted memory candidates.

    Semantic duplicate detection will be added separately.
    """

    def __init__(self, db_path: str = "memory_registry.db"):
        self.db_path = Path(db_path)

        self.connection = sqlite3.connect(self.db_path)

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS canonical_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                original_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bank_id, fingerprint)
            )
            """
        )

        self.connection.commit()

    @staticmethod
    def normalize(text: str) -> str:
        """
        Convert equivalent formatting into one canonical form.

        This intentionally does NOT perform semantic rewriting.
        """

        if not isinstance(text, str):
            raise TypeError("Memory text must be a string.")

        text = text.strip().lower()

        # Normalize whitespace.
        text = re.sub(r"\s+", " ", text)

        # Normalize common surrounding punctuation.
        text = text.strip(" \t\r\n.,;:!?")

        return text

    @classmethod
    def fingerprint(cls, text: str) -> str:
        """
        Generate a deterministic SHA-256 fingerprint
        from normalized text.
        """

        normalized = cls.normalize(text)

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    def is_exact_duplicate(
        self,
        bank_id: str,
        text: str,
    ) -> bool:

        fingerprint = self.fingerprint(text)

        row = self.connection.execute(
            """
            SELECT 1
            FROM canonical_memories
            WHERE bank_id = ?
              AND fingerprint = ?
            LIMIT 1
            """,
            (bank_id, fingerprint),
        ).fetchone()

        return row is not None

    def register(
        self,
        bank_id: str,
        text: str,
    ) -> bool:
        """
        Register a memory candidate.

        Returns:
            True  -> newly registered
            False -> exact duplicate already registered
        """

        normalized = self.normalize(text)
        fingerprint = self.fingerprint(text)

        try:
            self.connection.execute(
                """
                INSERT INTO canonical_memories (
                    bank_id,
                    fingerprint,
                    normalized_text,
                    original_text
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    bank_id,
                    fingerprint,
                    normalized,
                    text,
                ),
            )

            self.connection.commit()

            return True

        except sqlite3.IntegrityError:
            return False

    def get_memory(
        self,
        bank_id: str,
        text: str,
    ) -> Optional[dict]:

        fingerprint = self.fingerprint(text)

        row = self.connection.execute(
            """
            SELECT
                id,
                bank_id,
                fingerprint,
                normalized_text,
                original_text,
                created_at
            FROM canonical_memories
            WHERE bank_id = ?
              AND fingerprint = ?
            LIMIT 1
            """,
            (bank_id, fingerprint),
        ).fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "bank_id": row[1],
            "fingerprint": row[2],
            "normalized_text": row[3],
            "original_text": row[4],
            "created_at": row[5],
        }
    def list_memories(
    self,
    bank_id: str,
):
        rows = self.connection.execute(
        """
        SELECT
            id,
            bank_id,
            fingerprint,
            normalized_text,
            original_text,
            created_at
        FROM canonical_memories
        WHERE bank_id = ?
        ORDER BY id ASC
        """,
        (bank_id,),
    ).fetchall()
        return [
        {
            "id": row[0],
            "bank_id": row[1],
            "fingerprint": row[2],
            "normalized_text": row[3],
            "original_text": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]
    def get_canonical_memory(
    self,
    bank_id: str,
    text: str,
):
        return self.get_memory(
        bank_id=bank_id,
        text=text,
    )
    def list_canonical_memories(
    self,
    bank_id: str,
):
        return self.list_memories(
        bank_id=bank_id,
    )

    def close(self):
        self.connection.close()