import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from app.repositories.memory_learning_repository import (
    MemoryLearningRepository,
)


class SQLiteMemoryLearningRepository(
    MemoryLearningRepository
):
    """
    C4 SQLite learning-state repository.

    Important architectural rule:

    The outcomes table remains the source of truth.

    memory_learning_states is a persisted derived snapshot.

    Therefore the learning state can always be rebuilt from:
        experiences
            +
        outcomes
            +
        evidence
    """

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)

        self.connection = sqlite3.connect(
            self.db_path
        )

        self.connection.row_factory = sqlite3.Row

        self._create_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_schema(self):

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_learning_states (
                memory_id INTEGER PRIMARY KEY,

                total_outcomes INTEGER NOT NULL DEFAULT 0,

                successes INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0,
                partial INTEGER NOT NULL DEFAULT 0,
                unknown INTEGER NOT NULL DEFAULT 0,

                informative_outcomes INTEGER NOT NULL DEFAULT 0,

                success_rate REAL,
                failure_rate REAL,
                partial_rate REAL,

                learning_signal REAL NOT NULL DEFAULT 0.0,

                total_evidence INTEGER NOT NULL DEFAULT 0,
                outcomes_with_evidence INTEGER NOT NULL DEFAULT 0,
                evidence_coverage REAL NOT NULL DEFAULT 0.0,

                success_outcome_ids TEXT NOT NULL DEFAULT '[]',
                failure_outcome_ids TEXT NOT NULL DEFAULT '[]',
                partial_outcome_ids TEXT NOT NULL DEFAULT '[]',
                unknown_outcome_ids TEXT NOT NULL DEFAULT '[]',

                success_evidence_ids TEXT NOT NULL DEFAULT '[]',
                failure_evidence_ids TEXT NOT NULL DEFAULT '[]',
                partial_evidence_ids TEXT NOT NULL DEFAULT '[]',
                unknown_evidence_ids TEXT NOT NULL DEFAULT '[]',

                last_outcome_id TEXT,
                last_classification TEXT,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.connection.commit()

    # ------------------------------------------------------------------
    # Read source outcomes
    # ------------------------------------------------------------------

    def _get_outcomes_for_memory(
        self,
        memory_id: int,
    ) -> List[sqlite3.Row]:

        rows = self.connection.execute(
            """
            SELECT
                o.outcome_id,
                o.experience_id,
                o.outcome_type,
                o.summary,
                o.details,
                o.classification,
                o.classification_reason,
                o.classification_evidence_count,
                o.classification_evidence_ids,
                o.classification_version,
                o.classified_at,
                o.created_at
            FROM outcomes o
            INNER JOIN experiences e
                ON e.experience_id = o.experience_id
            WHERE e.memory_id = ?
            ORDER BY
                o.created_at ASC,
                o.outcome_id ASC
            """,
            (memory_id,),
        ).fetchall()

        return rows

    # ------------------------------------------------------------------
    # Evidence IDs
    # ------------------------------------------------------------------

    def _get_evidence_ids_for_outcome(
        self,
        outcome_id: str,
    ) -> List[str]:

        rows = self.connection.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE outcome_id = ?
            ORDER BY created_at ASC, evidence_id ASC
            """,
            (outcome_id,),
        ).fetchall()

        return [
            row["evidence_id"]
            for row in rows
        ]

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dump_ids(ids: List[str]) -> str:
        return json.dumps(
            ids,
            separators=(",", ":"),
        )

    @staticmethod
    def _load_ids(raw) -> List[str]:

        if not raw:
            return []

        try:
            value = json.loads(raw)

            if isinstance(value, list):
                return value

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

        return []

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh_learning_state(
        self,
        memory_id: int,
    ) -> Dict:

        outcomes = self._get_outcomes_for_memory(
            memory_id
        )

        successes = 0
        failures = 0
        partial = 0
        unknown = 0

        success_outcome_ids = []
        failure_outcome_ids = []
        partial_outcome_ids = []
        unknown_outcome_ids = []

        success_evidence_ids = []
        failure_evidence_ids = []
        partial_evidence_ids = []
        unknown_evidence_ids = []

        total_evidence = 0
        outcomes_with_evidence = 0

        last_outcome_id = None
        last_classification = None

        for outcome in outcomes:

            classification = outcome["classification"]

            # ----------------------------------------------------------
            # C4 requires a C3 classification.
            #
            # Do NOT fall back to outcome_type.
            # ----------------------------------------------------------

            if classification not in {
                self.SUCCESS,
                self.FAILURE,
                self.PARTIAL,
                self.UNKNOWN,
            }:
                raise ValueError(
                    "C4 cannot learn from outcome "
                    f"{outcome['outcome_id']}: "
                    "missing or invalid C3 classification."
                )

            outcome_id = outcome["outcome_id"]

            evidence_ids = (
                self._get_evidence_ids_for_outcome(
                    outcome_id
                )
            )

            total_evidence += len(evidence_ids)

            if evidence_ids:
                outcomes_with_evidence += 1

            last_outcome_id = outcome_id
            last_classification = classification

            if classification == self.SUCCESS:

                successes += 1
                success_outcome_ids.append(
                    outcome_id
                )
                success_evidence_ids.extend(
                    evidence_ids
                )

            elif classification == self.FAILURE:

                failures += 1
                failure_outcome_ids.append(
                    outcome_id
                )
                failure_evidence_ids.extend(
                    evidence_ids
                )

            elif classification == self.PARTIAL:

                partial += 1
                partial_outcome_ids.append(
                    outcome_id
                )
                partial_evidence_ids.extend(
                    evidence_ids
                )

            elif classification == self.UNKNOWN:

                unknown += 1
                unknown_outcome_ids.append(
                    outcome_id
                )
                unknown_evidence_ids.extend(
                    evidence_ids
                )

        total_outcomes = len(outcomes)

        informative_outcomes = (
            successes
            + failures
            + partial
        )

        if informative_outcomes > 0:

            success_rate = (
                successes
                / informative_outcomes
            )

            failure_rate = (
                failures
                / informative_outcomes
            )

            partial_rate = (
                partial
                / informative_outcomes
            )

            learning_signal = (
                (successes - failures)
                / informative_outcomes
            )

        else:

            success_rate = None
            failure_rate = None
            partial_rate = None
            learning_signal = 0.0

        if total_outcomes > 0:

            evidence_coverage = (
                outcomes_with_evidence
                / total_outcomes
            )

        else:

            evidence_coverage = 0.0

        self.connection.execute(
            """
            INSERT INTO memory_learning_states (
                memory_id,

                total_outcomes,

                successes,
                failures,
                partial,
                unknown,

                informative_outcomes,

                success_rate,
                failure_rate,
                partial_rate,

                learning_signal,

                total_evidence,
                outcomes_with_evidence,
                evidence_coverage,

                success_outcome_ids,
                failure_outcome_ids,
                partial_outcome_ids,
                unknown_outcome_ids,

                success_evidence_ids,
                failure_evidence_ids,
                partial_evidence_ids,
                unknown_evidence_ids,

                last_outcome_id,
                last_classification,

                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT(memory_id)
            DO UPDATE SET

                total_outcomes =
                    excluded.total_outcomes,

                successes =
                    excluded.successes,

                failures =
                    excluded.failures,

                partial =
                    excluded.partial,

                unknown =
                    excluded.unknown,

                informative_outcomes =
                    excluded.informative_outcomes,

                success_rate =
                    excluded.success_rate,

                failure_rate =
                    excluded.failure_rate,

                partial_rate =
                    excluded.partial_rate,

                learning_signal =
                    excluded.learning_signal,

                total_evidence =
                    excluded.total_evidence,

                outcomes_with_evidence =
                    excluded.outcomes_with_evidence,

                evidence_coverage =
                    excluded.evidence_coverage,

                success_outcome_ids =
                    excluded.success_outcome_ids,

                failure_outcome_ids =
                    excluded.failure_outcome_ids,

                partial_outcome_ids =
                    excluded.partial_outcome_ids,

                unknown_outcome_ids =
                    excluded.unknown_outcome_ids,

                success_evidence_ids =
                    excluded.success_evidence_ids,

                failure_evidence_ids =
                    excluded.failure_evidence_ids,

                partial_evidence_ids =
                    excluded.partial_evidence_ids,

                unknown_evidence_ids =
                    excluded.unknown_evidence_ids,

                last_outcome_id =
                    excluded.last_outcome_id,

                last_classification =
                    excluded.last_classification,

                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                memory_id,

                total_outcomes,

                successes,
                failures,
                partial,
                unknown,

                informative_outcomes,

                success_rate,
                failure_rate,
                partial_rate,

                learning_signal,

                total_evidence,
                outcomes_with_evidence,
                evidence_coverage,

                self._dump_ids(
                    success_outcome_ids
                ),
                self._dump_ids(
                    failure_outcome_ids
                ),
                self._dump_ids(
                    partial_outcome_ids
                ),
                self._dump_ids(
                    unknown_outcome_ids
                ),

                self._dump_ids(
                    success_evidence_ids
                ),
                self._dump_ids(
                    failure_evidence_ids
                ),
                self._dump_ids(
                    partial_evidence_ids
                ),
                self._dump_ids(
                    unknown_evidence_ids
                ),

                last_outcome_id,
                last_classification,
            ),
        )

        self.connection.commit()

        return self.get_learning_state(
            memory_id
        )

    # ------------------------------------------------------------------
    # Get state
    # ------------------------------------------------------------------

    def get_learning_state(
        self,
        memory_id: int,
    ) -> Optional[Dict]:

        row = self.connection.execute(
            """
            SELECT *
            FROM memory_learning_states
            WHERE memory_id = ?
            """,
            (memory_id,),
        ).fetchone()

        if row is None:
            return None

        result = dict(row)

        for field in [
            "success_outcome_ids",
            "failure_outcome_ids",
            "partial_outcome_ids",
            "unknown_outcome_ids",
            "success_evidence_ids",
            "failure_evidence_ids",
            "partial_evidence_ids",
            "unknown_evidence_ids",
        ]:
            result[field] = self._load_ids(
                result[field]
            )

        return result

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    def get_learning_provenance(
        self,
        memory_id: int,
    ) -> Optional[Dict]:

        state = self.get_learning_state(
            memory_id
        )

        if state is None:
            return None

        return {
            "memory_id": memory_id,

            "success": {
                "outcome_ids": state[
                    "success_outcome_ids"
                ],
                "evidence_ids": state[
                    "success_evidence_ids"
                ],
            },

            "failure": {
                "outcome_ids": state[
                    "failure_outcome_ids"
                ],
                "evidence_ids": state[
                    "failure_evidence_ids"
                ],
            },

            "partial": {
                "outcome_ids": state[
                    "partial_outcome_ids"
                ],
                "evidence_ids": state[
                    "partial_evidence_ids"
                ],
            },

            "unknown": {
                "outcome_ids": state[
                    "unknown_outcome_ids"
                ],
                "evidence_ids": state[
                    "unknown_evidence_ids"
                ],
            },
        }

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def close(self):
        self.connection.close()