import json
import sqlite3
from pathlib import Path
from typing import Optional

class SQLiteLearningRepository:

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)

        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        self._create_schema()
        self._migrate_schema()

    # ============================================================
    # SCHEMA
    # ============================================================

    def _create_schema(self):

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS experiences (
                experience_id TEXT PRIMARY KEY,
                bank_id TEXT NOT NULL,
                canonical_memory_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                action TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outcomes (
                outcome_id TEXT PRIMARY KEY,
                experience_id TEXT NOT NULL,
                outcome_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (experience_id)
                    REFERENCES experiences(experience_id)
                    ON DELETE CASCADE
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,

                experience_id TEXT NOT NULL,

                outcome_id TEXT,

                evidence_type TEXT NOT NULL,

                content TEXT,

                file_name TEXT,

                mime_type TEXT,

                storage_key TEXT,

                sha256 TEXT,

                source_type TEXT NOT NULL,

                source_id TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (experience_id)
                    REFERENCES experiences(experience_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (outcome_id)
                    REFERENCES outcomes(outcome_id)
                    ON DELETE CASCADE
            )
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_experiences_memory
            ON experiences(
                bank_id,
                canonical_memory_id
            )
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_outcomes_experience
            ON outcomes(experience_id)
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_evidence_experience
            ON evidence(experience_id)
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_evidence_outcome
            ON evidence(outcome_id)
            """
        )

        # ========================================================
        # C4 MEMORY LEARNING STATE
        # ========================================================

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_learning_states (
                canonical_memory_id INTEGER PRIMARY KEY,

                total_outcomes INTEGER NOT NULL DEFAULT 0,

                successes INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0,
                partial INTEGER NOT NULL DEFAULT 0,
                unknown INTEGER NOT NULL DEFAULT 0,

                informative_outcomes INTEGER NOT NULL DEFAULT 0,

                success_rate REAL NOT NULL DEFAULT 0.0,
                failure_rate REAL NOT NULL DEFAULT 0.0,
                partial_rate REAL NOT NULL DEFAULT 0.0,

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

        self.connection.commit()

    # ============================================================
    # MIGRATION
    # ============================================================

    def _migrate_schema(self):

        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(evidence)"
            ).fetchall()
        }

        if "outcome_id" not in columns:

            self.connection.execute(
                """
                ALTER TABLE evidence
                ADD COLUMN outcome_id TEXT
                """
            )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_evidence_outcome
            ON evidence(outcome_id)
            """
        )

        # ----------------------------------------------------
        # C3 OUTCOME CLASSIFICATION MIGRATION
        # ----------------------------------------------------

        outcome_columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(outcomes)"
            ).fetchall()
        }

        if "classification" not in outcome_columns:

            self.connection.execute(
                """
                ALTER TABLE outcomes
                ADD COLUMN classification TEXT
                """
            )

        if "classification_reason" not in outcome_columns:

            self.connection.execute(
                """
                ALTER TABLE outcomes
                ADD COLUMN classification_reason TEXT
                """
            )

        if "classification_evidence_count" not in outcome_columns:

            self.connection.execute(
                """
                ALTER TABLE outcomes
                ADD COLUMN classification_evidence_count INTEGER
                """
            )

        if "classification_evidence_ids" not in outcome_columns:

            self.connection.execute(
                """
                ALTER TABLE outcomes
                ADD COLUMN classification_evidence_ids TEXT
                """
            )

        if "classification_version" not in outcome_columns:

            self.connection.execute(
                """
                ALTER TABLE outcomes
                ADD COLUMN classification_version TEXT
                """
            )

        if "classified_at" not in outcome_columns:

            self.connection.execute(
                """
                ALTER TABLE outcomes
                ADD COLUMN classified_at TIMESTAMP
                """
            )

        self.connection.commit()
    # ============================================================
    # EXPERIENCE
    # ============================================================

    def create_experience(
        self,
        experience_id: str,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: Optional[str],
    ):

        self.connection.execute(
            """
            INSERT INTO experiences (
                experience_id,
                bank_id,
                canonical_memory_id,
                task,
                action,
                context
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                experience_id,
                bank_id,
                canonical_memory_id,
                task,
                action,
                context,
            ),
        )

        self.connection.commit()

        return self.get_experience(
            experience_id
        )

    def get_experience(
        self,
        experience_id: str,
    ):

        row = self.connection.execute(
            """
            SELECT
                experience_id,
                bank_id,
                canonical_memory_id,
                task,
                action,
                context,
                created_at
            FROM experiences
            WHERE experience_id = ?
            """,
            (experience_id,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    def list_experiences_for_memory(
        self,
        bank_id: str,
        canonical_memory_id: int,
    ):

        rows = self.connection.execute(
            """
            SELECT
                experience_id,
                bank_id,
                canonical_memory_id,
                task,
                action,
                context,
                created_at
            FROM experiences
            WHERE bank_id = ?
              AND canonical_memory_id = ?
            ORDER BY created_at ASC
            """,
            (
                bank_id,
                canonical_memory_id,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    # ============================================================
    # OUTCOME
    # ============================================================

    def create_outcome(
        self,
        outcome_id: str,
        experience_id: str,
        outcome_type: str,
        summary: str,
        details: Optional[str],
    ):

        experience = self.get_experience(
            experience_id
        )

        if experience is None:
            raise ValueError(
                "Cannot create outcome: "
                "experience does not exist."
            )

        self.connection.execute(
            """
            INSERT INTO outcomes (
                outcome_id,
                experience_id,
                outcome_type,
                summary,
                details
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                outcome_id,
                experience_id,
                outcome_type,
                summary,
                details,
            ),
        )

        self.connection.commit()

        return self.get_outcome(
            outcome_id
        )

    def get_outcome(
    self,
    outcome_id: str,
):

        row = self.connection.execute(
        """
        SELECT
            outcome_id,
            experience_id,
            outcome_type,
            summary,
            details,
            classification,
            classification_reason,
            classification_evidence_count,
            classification_evidence_ids,
            classification_version,
            classified_at,
            created_at
        FROM outcomes
        WHERE outcome_id = ?
        """,
        (outcome_id,),
    ).fetchone()

        if row is None:
            return None

        return dict(row)
    def list_outcomes_for_experience(
        self,
        experience_id: str,
    ):

        rows = self.connection.execute(
            """
            SELECT
                outcome_id,
                experience_id,
                outcome_type,
                summary,
                details,
                classification,
                classification_reason,
                classification_evidence_count,
                classification_evidence_ids,
                classification_version,
                classified_at,
                created_at
            FROM outcomes
            WHERE experience_id = ?
            ORDER BY created_at ASC
            """,
            (experience_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]
    # ============================================================
    # EVIDENCE
    # ============================================================

    def create_evidence(
        self,
        evidence_id: str,
        experience_id: str,
        outcome_id: Optional[str],
        evidence_type: str,
        content: Optional[str],
        file_name: Optional[str],
        mime_type: Optional[str],
        storage_key: Optional[str],
        sha256: Optional[str],
        source_type: str,
        source_id: Optional[str],
    ):

        experience = self.get_experience(
            experience_id
        )

        if experience is None:
            raise ValueError(
                "Cannot create evidence: "
                "experience does not exist."
            )

        if outcome_id is not None:

            outcome = self.get_outcome(
                outcome_id
            )

            if outcome is None:
                raise ValueError(
                    "Cannot create evidence: "
                    "outcome does not exist."
                )

            if outcome["experience_id"] != experience_id:
                raise ValueError(
                    "Evidence outcome does not belong "
                    "to the supplied experience."
                )

        if not content and not storage_key:
            raise ValueError(
                "Evidence must contain content "
                "or a storage_key."
            )

        self.connection.execute(
            """
            INSERT INTO evidence (
                evidence_id,
                experience_id,
                outcome_id,
                evidence_type,
                content,
                file_name,
                mime_type,
                storage_key,
                sha256,
                source_type,
                source_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                experience_id,
                outcome_id,
                evidence_type,
                content,
                file_name,
                mime_type,
                storage_key,
                sha256,
                source_type,
                source_id,
            ),
        )

        self.connection.commit()

        return self.get_evidence(
            evidence_id
        )

    def get_evidence(
        self,
        evidence_id: str,
    ):

        row = self.connection.execute(
            """
            SELECT
                evidence_id,
                experience_id,
                outcome_id,
                evidence_type,
                content,
                file_name,
                mime_type,
                storage_key,
                sha256,
                source_type,
                source_id,
                created_at
            FROM evidence
            WHERE evidence_id = ?
            """,
            (evidence_id,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    def list_evidence_for_experience(
        self,
        experience_id: str,
    ):

        rows = self.connection.execute(
            """
            SELECT
                evidence_id,
                experience_id,
                outcome_id,
                evidence_type,
                content,
                file_name,
                mime_type,
                storage_key,
                sha256,
                source_type,
                source_id,
                created_at
            FROM evidence
            WHERE experience_id = ?
            ORDER BY created_at ASC
            """,
            (experience_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def list_evidence_for_outcome(
        self,
        outcome_id: str,
    ):

        rows = self.connection.execute(
            """
            SELECT
                evidence_id,
                experience_id,
                outcome_id,
                evidence_type,
                content,
                file_name,
                mime_type,
                storage_key,
                sha256,
                source_type,
                source_id,
                created_at
            FROM evidence
            WHERE outcome_id = ?
            ORDER BY created_at ASC
            """,
            (outcome_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]
        # ============================================================
    # C3 CLASSIFICATION
    # ============================================================

        # ============================================================
    # C3 CLASSIFICATION
    # ============================================================

    def update_outcome_classification(
        self,
        outcome_id: str,
        classification: str,
        classification_reason: str,
        classification_evidence_count: int,
        classification_evidence_ids: str,
        classification_version: str,
    ):

        outcome = self.get_outcome(
            outcome_id
        )

        if outcome is None:
            raise ValueError(
                "Cannot classify outcome: "
                "outcome does not exist."
            )

        self.connection.execute(
            """
            UPDATE outcomes
            SET
                classification = ?,
                classification_reason = ?,
                classification_evidence_count = ?,
                classification_evidence_ids = ?,
                classification_version = ?,
                classified_at = CURRENT_TIMESTAMP
            WHERE outcome_id = ?
            """,
            (
                classification,
                classification_reason,
                classification_evidence_count,
                classification_evidence_ids,
                classification_version,
                outcome_id,
            ),
        )

        self.connection.commit()

        return self.get_outcome(
            outcome_id
        )        

    # ============================================================
    # CLOSE
    # ============================================================
        # ============================================================
    # C4 MEMORY LEARNING
    # ============================================================

       # ============================================================
    # C4 MEMORY LEARNING
    # ============================================================

    @staticmethod
    def _dump_learning_ids(values):
        """
        Store ID lists as deterministic JSON.
        """
        return json.dumps(
            list(values),
            separators=(",", ":"),
        )

    @staticmethod
    def _load_learning_ids(value):
        """
        Load an ID list from JSON safely.
        """
        if not value:
            return []

        try:
            result = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []

        if not isinstance(result, list):
            return []

        return result

    def _get_outcomes_for_memory(
        self,
        canonical_memory_id: int,
    ):
        """
        Get all outcomes connected to a canonical memory.

        canonical memory
            ↓
        experience
            ↓
        outcome
        """

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
            WHERE e.canonical_memory_id = ?
            ORDER BY
                o.created_at ASC,
                o.outcome_id ASC
            """,
            (canonical_memory_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def _get_evidence_ids_for_outcome(
        self,
        outcome_id: str,
    ):
        """
        Get all evidence IDs attached to an outcome.
        """

        rows = self.connection.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE outcome_id = ?
            ORDER BY
                created_at ASC,
                evidence_id ASC
            """,
            (outcome_id,),
        ).fetchall()

        return [
            row["evidence_id"]
            for row in rows
        ]

    def refresh_memory_learning_state(
        self,
        canonical_memory_id: int,
    ):
        """
        Rebuild the C4 learning state from source data.

        IMPORTANT:

        C4 learns ONLY from C3 classification.

        outcome_type is NOT used as the learning signal.

        success  -> +1
        failure  -> -1
        partial  ->  0
        unknown  -> excluded from informative rates
        """

        outcomes = self._get_outcomes_for_memory(
            canonical_memory_id
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

        allowed_classifications = {
            "success",
            "failure",
            "partial",
            "unknown",
        }

        for outcome in outcomes:

            classification = outcome["classification"]

            if classification not in allowed_classifications:
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

            if classification == "success":

                successes += 1

                success_outcome_ids.append(
                    outcome_id
                )

                success_evidence_ids.extend(
                    evidence_ids
                )

            elif classification == "failure":

                failures += 1

                failure_outcome_ids.append(
                    outcome_id
                )

                failure_evidence_ids.extend(
                    evidence_ids
                )

            elif classification == "partial":

                partial += 1

                partial_outcome_ids.append(
                    outcome_id
                )

                partial_evidence_ids.extend(
                    evidence_ids
                )

            elif classification == "unknown":

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
                successes - failures
            ) / informative_outcomes

        else:

            success_rate = 0.0
            failure_rate = 0.0
            partial_rate = 0.0
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
                canonical_memory_id,

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
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )

            ON CONFLICT(canonical_memory_id)
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
                canonical_memory_id,

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

                self._dump_learning_ids(
                    success_outcome_ids
                ),

                self._dump_learning_ids(
                    failure_outcome_ids
                ),

                self._dump_learning_ids(
                    partial_outcome_ids
                ),

                self._dump_learning_ids(
                    unknown_outcome_ids
                ),

                self._dump_learning_ids(
                    success_evidence_ids
                ),

                self._dump_learning_ids(
                    failure_evidence_ids
                ),

                self._dump_learning_ids(
                    partial_evidence_ids
                ),

                self._dump_learning_ids(
                    unknown_evidence_ids
                ),

                last_outcome_id,
                last_classification,
            ),
        )

        self.connection.commit()

        return self.get_memory_learning_state(
            canonical_memory_id
        )

    def get_memory_learning_state(
        self,
        canonical_memory_id: int,
    ):
        """
        Retrieve the persisted C4 learning state.
        """

        row = self.connection.execute(
            """
            SELECT *
            FROM memory_learning_states
            WHERE canonical_memory_id = ?
            """,
            (canonical_memory_id,),
        ).fetchone()

        if row is None:
            return None

        result = dict(row)

        json_fields = [
            "success_outcome_ids",
            "failure_outcome_ids",
            "partial_outcome_ids",
            "unknown_outcome_ids",
            "success_evidence_ids",
            "failure_evidence_ids",
            "partial_evidence_ids",
            "unknown_evidence_ids",
        ]

        for field in json_fields:

            result[field] = (
                self._load_learning_ids(
                    result[field]
                )
            )

        return result
    
    def get_memory_learning_provenance(
        self,
        canonical_memory_id: int,
    ):
        # """
        # Return grouped provenance for the C4 learning state.

        # Shape:

        # {
        #     "memory_id": 1,

        #     "success": {
        #         "outcome_ids": [...],
        #         "evidence_ids": [...]
        #     },

        #     "failure": {
        #         "outcome_ids": [...],
        #         "evidence_ids": [...]
        #     },

        #     "partial": {
        #         "outcome_ids": [...],
        #         "evidence_ids": [...]
        #     },

        #     "unknown": {
        #         "outcome_ids": [...],
        #         "evidence_ids": [...]
        #     }
        # }

        # The grouping comes directly from the persisted
        # C4 learning state.
        # """

        state = self.get_memory_learning_state(
            canonical_memory_id
        )

        if state is None:
                return None

        return {
            "memory_id": canonical_memory_id,

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
    

        # CLOSE
    # ============================================================

    def close(self):
        self.connection.close()