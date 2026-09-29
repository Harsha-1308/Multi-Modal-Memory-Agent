import re
import sqlite3
from pathlib import Path
from typing import Optional

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)


class OutcomeLearningService:
    """
    C1 Outcome Learning layer.

    Responsibilities:
    - Classify outcome evidence.
    - Resolve outcomes to canonical memory identity.
    - Record outcomes against canonical memory IDs.
    - Track success/failure/neutral outcomes.
    - Calculate aggregate learning state.
    - Provide a stable learning signal.

    CanonicalMemoryService remains the source of truth
    for memory identity.

    This service does NOT:
    - extract memories
    - decide whether memories should be retained
    - perform deduplication
    - store memories in Hindsight
    """

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"

    POSITIVE_OUTCOME_WORDS = {
        "success",
        "successful",
        "succeeded",
        "works",
        "worked",
        "working",
        "resolved",
        "resolve",
        "fixed",
        "fix",
        "passed",
        "pass",
        "completed",
        "complete",
        "improved",
        "achieved",
        "verified",
        "validated",
        "correct",
        "correctly",
        "effective",
    }

    NEGATIVE_OUTCOME_WORDS = {
        "failed",
        "failure",
        "fail",
        "broken",
        "break",
        "blocked",
        "rejected",
        "regressed",
        "incorrect",
        "wrong",
        "unsuccessful",
        "unsuccessfully",
        "crashed",
        "crash",
        "error",
        "errors",
        "exception",
        "exceptions",
        "timeout",
        "timed",
    }

    def __init__(
        self,
        db_path: str = "memory_learning.db",
        canonical_memory_service: Optional[
            CanonicalMemoryService
        ] = None,
    ):
        self.db_path = Path(db_path)

        self.connection = sqlite3.connect(
            self.db_path
        )

        self.canonical_memory_service = (
            canonical_memory_service
            if canonical_memory_service is not None
            else CanonicalMemoryService()
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id TEXT NOT NULL,
                memory_id INTEGER,
                memory_text TEXT NOT NULL,
                outcome TEXT NOT NULL,
                evidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.connection.commit()

    # ==========================================================
    # TEXT NORMALIZATION
    # ==========================================================

    @staticmethod
    def normalize(text: str) -> str:
        if not isinstance(text, str):
            raise TypeError(
                "Text must be a string."
            )

        text = text.strip().lower()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    # ==========================================================
    # OUTCOME CLASSIFICATION
    # ==========================================================

    @classmethod
    def classify_outcome(
        cls,
        evidence: str,
    ) -> str:

        normalized = cls.normalize(
            evidence
        )

        tokens = set(
            re.findall(
                r"\b[a-z0-9]+\b",
                normalized,
            )
        )

        positive_matches = (
            tokens.intersection(
                cls.POSITIVE_OUTCOME_WORDS
            )
        )

        negative_matches = (
            tokens.intersection(
                cls.NEGATIVE_OUTCOME_WORDS
            )
        )

        # Conflicting evidence is intentionally
        # treated as neutral at this stage.
        if positive_matches and negative_matches:
            return cls.NEUTRAL

        if positive_matches:
            return cls.SUCCESS

        if negative_matches:
            return cls.FAILURE

        return cls.NEUTRAL

    # ==========================================================
    # RESOLVE CANONICAL MEMORY
    # ==========================================================

    def resolve_canonical_memory(
        self,
        bank_id: str,
        memory_text: str,
    ) -> dict:
        """
        Resolve a memory candidate to an existing canonical
        memory.

        The memory MUST already exist in the canonical
        registry.

        This prevents outcome records from silently
        creating a second identity system.
        """

        memory = (
            self.canonical_memory_service.get_memory(
                bank_id=bank_id,
                text=memory_text,
            )
        )

        if memory is None:
            raise ValueError(
                "Memory is not registered in the "
                "canonical memory registry."
            )

        return memory

    # ==========================================================
    # RECORD OUTCOME BY CANONICAL MEMORY
    # ==========================================================

    def record_for_memory(
        self,
        bank_id: str,
        memory_text: str,
        outcome: str,
        evidence: Optional[str] = None,
    ) -> dict:
        """
        Record an outcome against an existing canonical memory.

        The canonical memory ID is resolved automatically.
        """

        canonical_memory = (
            self.resolve_canonical_memory(
                bank_id=bank_id,
                memory_text=memory_text,
            )
        )

        outcome_id = self.record_outcome(
            bank_id=bank_id,
            memory_text=canonical_memory[
                "original_text"
            ],
            outcome=outcome,
            evidence=evidence,
            memory_id=canonical_memory["id"],
        )

        return {
            "id": outcome_id,
            "memory_id": canonical_memory["id"],
            "memory_text": canonical_memory[
                "original_text"
            ],
            "outcome": outcome,
            "evidence": evidence,
        }

    # ==========================================================
    # RECORD FROM EVIDENCE
    # ==========================================================

    def record_from_evidence(
        self,
        bank_id: str,
        memory_text: str,
        evidence: str,
    ) -> dict:
        """
        Classify evidence and record it against the
        canonical memory.
        """

        outcome = self.classify_outcome(
            evidence
        )

        return self.record_for_memory(
            bank_id=bank_id,
            memory_text=memory_text,
            outcome=outcome,
            evidence=evidence,
        )

    # ==========================================================
    # LOW-LEVEL OUTCOME INSERT
    # ==========================================================

    def record_outcome(
        self,
        bank_id: str,
        memory_text: str,
        outcome: str,
        evidence: Optional[str] = None,
        memory_id: Optional[int] = None,
    ) -> int:

        if not isinstance(
            memory_text,
            str,
        ):
            raise TypeError(
                "memory_text must be a string."
            )

        if outcome not in {
            self.SUCCESS,
            self.FAILURE,
            self.NEUTRAL,
        }:
            raise ValueError(
                "Outcome must be one of: "
                "success, failure, neutral."
            )

        cursor = self.connection.execute(
            """
            INSERT INTO memory_outcomes (
                bank_id,
                memory_id,
                memory_text,
                outcome,
                evidence
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                bank_id,
                memory_id,
                memory_text,
                outcome,
                evidence,
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    # ==========================================================
    # GET OUTCOMES BY CANONICAL MEMORY ID
    # ==========================================================

    def get_outcomes_for_memory(
        self,
        bank_id: str,
        memory_id: int,
    ):
        rows = self.connection.execute(
            """
            SELECT
                id,
                bank_id,
                memory_id,
                memory_text,
                outcome,
                evidence,
                created_at
            FROM memory_outcomes
            WHERE bank_id = ?
              AND memory_id = ?
            ORDER BY id ASC
            """,
            (
                bank_id,
                memory_id,
            ),
        ).fetchall()

        return [
            {
                "id": row[0],
                "bank_id": row[1],
                "memory_id": row[2],
                "memory_text": row[3],
                "outcome": row[4],
                "evidence": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

    # ==========================================================
    # GET OUTCOMES BY TEXT
    # ==========================================================

    def get_outcomes(
        self,
        bank_id: str,
        memory_text: str,
    ):
        canonical_memory = (
            self.resolve_canonical_memory(
                bank_id=bank_id,
                memory_text=memory_text,
            )
        )

        return self.get_outcomes_for_memory(
            bank_id=bank_id,
            memory_id=canonical_memory["id"],
        )

    # ==========================================================
    # LEARNING STATE BY CANONICAL MEMORY ID
    # ==========================================================

    def get_learning_state_for_memory(
        self,
        bank_id: str,
        memory_id: int,
    ):
        row = self.connection.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN outcome = ?
                        THEN 1
                        ELSE 0
                    END
                ) AS successes,

                SUM(
                    CASE
                        WHEN outcome = ?
                        THEN 1
                        ELSE 0
                    END
                ) AS failures,

                SUM(
                    CASE
                        WHEN outcome = ?
                        THEN 1
                        ELSE 0
                    END
                ) AS neutral

            FROM memory_outcomes

            WHERE bank_id = ?
              AND memory_id = ?
            """,
            (
                self.SUCCESS,
                self.FAILURE,
                self.NEUTRAL,
                bank_id,
                memory_id,
            ),
        ).fetchone()

        total = row[0] or 0
        successes = row[1] or 0
        failures = row[2] or 0
        neutral = row[3] or 0

        if total == 0:
            success_rate = None
            learning_signal = 0.0

        else:
            success_rate = (
                successes / total
            )

            learning_signal = (
                successes - failures
            ) / total

        return {
            "memory_id": memory_id,
            "total_outcomes": total,
            "successes": successes,
            "failures": failures,
            "neutral": neutral,
            "success_rate": success_rate,
            "learning_signal": learning_signal,
        }

    # ==========================================================
    # LEARNING STATE BY MEMORY TEXT
    # ==========================================================

    def get_learning_state(
        self,
        bank_id: str,
        memory_text: str,
    ):
        canonical_memory = (
            self.resolve_canonical_memory(
                bank_id=bank_id,
                memory_text=memory_text,
            )
        )

        state = (
            self.get_learning_state_for_memory(
                bank_id=bank_id,
                memory_id=canonical_memory["id"],
            )
        )

        return {
            "memory_id": canonical_memory["id"],
            "memory_text": canonical_memory[
                "original_text"
            ],
            **{
                key: value
                for key, value in state.items()
                if key != "memory_id"
            },
        }

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self):
        self.canonical_memory_service.close()
        self.connection.close()