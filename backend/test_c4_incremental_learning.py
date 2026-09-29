import os
import uuid

from app.repositories.sqlite.learning_repository import (
    SQLiteLearningRepository,
)

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)

from app.services.experience_service import (
    ExperienceService,
)

from app.services.outcome_capture_service import (
    OutcomeCaptureService,
)

from app.services.outcome_classification_service import (
    OutcomeClassificationService,
)

from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)

from app.services.evidence_service import (
    EvidenceService,
)


# ============================================================
# TEST DATABASE
# ============================================================

BANK_ID = f"c4-incremental-{uuid.uuid4().hex[:8]}"

DB_PATH = (
    f"test_c4_incremental_"
    f"{uuid.uuid4().hex[:8]}.db"
)

os.environ["LEARNING_DATABASE_PATH"] = DB_PATH


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print("C4 INCREMENTAL LEARNING TEST")
    print("=" * 90)

    repository = None

    try:

        # ====================================================
        # 1. CANONICAL MEMORY
        # ====================================================

        print()
        print("=" * 90)
        print("[1] CANONICAL MEMORY")
        print("-" * 90)

        canonical = CanonicalMemoryService(
            db_path=DB_PATH
        )

        memory_text = (
            "Pessimistic database locking "
            "resolved wallet concurrency problems."
        )

        assert canonical.register(
            bank_id=BANK_ID,
            text=memory_text,
        )

        memory = canonical.list_memories(
            bank_id=BANK_ID
        )[0]

        memory_id = memory["id"]

        print(f"MEMORY ID: {memory_id}")
        print("STATUS: PASS")

        canonical.close()

        # ====================================================
        # 2. SERVICES
        # ====================================================

        print()
        print("=" * 90)
        print("[2] SERVICES")
        print("-" * 90)

        repository = SQLiteLearningRepository(
            db_path=DB_PATH
        )

        experience_service = ExperienceService(
            repository=repository,
            canonical_memory_service=CanonicalMemoryService(
                db_path=DB_PATH
            ),
        )

        outcome_service = OutcomeCaptureService(
            repository=repository
        )

        evidence_service = EvidenceService(
            repository=repository
        )

        classifier = OutcomeClassificationService(
            repository=repository
        )

        learning_service = MemoryLearningStateService(
            repository=repository
        )

        print("Experience service: READY")
        print("Outcome service: READY")
        print("Evidence service: READY")
        print("Classification service: READY")
        print("Learning service: READY")
        print("STATUS: PASS")

        # ====================================================
        # 3. FIRST SUCCESS
        # ====================================================

        print()
        print("=" * 90)
        print("[3] FIRST SUCCESS")
        print("-" * 90)

        experience_1 = experience_service.create(
            bank_id=BANK_ID,
            canonical_memory_id=memory_id,
            task="Resolve wallet concurrency.",
            action="Use pessimistic database locking.",
            context="Concurrent wallet updates were failing.",
        )

        outcome_1 = outcome_service.create(
            experience_id=experience_1["experience_id"],
            outcome_type="success",
            summary="Locking solved the concurrency issue.",
        )

        evidence_1 = evidence_service.create_text_evidence(
            experience_id=experience_1["experience_id"],
            outcome_id=outcome_1["outcome_id"],
            content=(
                "All integration tests passed successfully."
            ),
            source_type="test_result",
            source_id="c4-incremental-success-1",
        )

        result_1 = classifier.classify(
            outcome_1["outcome_id"]
        )

        assert (
            result_1["classification"]
            == OutcomeClassificationService.SUCCESS
        )

        state_1 = learning_service.learn(
            memory_id
        )

        print(
            f"CLASSIFICATION: "
            f"{result_1['classification']}"
        )

        print(
            f"TOTAL OUTCOMES: "
            f"{state_1['total_outcomes']}"
        )

        print(
            f"SUCCESS: "
            f"{state_1['successes']}"
        )

        print(
            f"FAILURE: "
            f"{state_1['failures']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{state_1['learning_signal']}"
        )

        assert state_1["total_outcomes"] == 1
        assert state_1["successes"] == 1
        assert state_1["failures"] == 0
        assert state_1["learning_signal"] == 1.0

        print("STATUS: PASS")

        # ====================================================
        # 4. SECOND SUCCESS
        # ====================================================

        print()
        print("=" * 90)
        print("[4] SECOND SUCCESS")
        print("-" * 90)

        experience_2 = experience_service.create(
            bank_id=BANK_ID,
            canonical_memory_id=memory_id,
            task="Repeat concurrency fix.",
            action="Reuse pessimistic locking.",
            context="A second concurrency scenario occurred.",
        )

        outcome_2 = outcome_service.create(
            experience_id=experience_2["experience_id"],
            outcome_type="success",
            summary="The second scenario also succeeded.",
        )

        evidence_service.create_text_evidence(
            experience_id=experience_2["experience_id"],
            outcome_id=outcome_2["outcome_id"],
            content="Regression tests passed successfully.",
            source_type="test_result",
            source_id="c4-incremental-success-2",
        )

        result_2 = classifier.classify(
            outcome_2["outcome_id"]
        )

        assert (
            result_2["classification"]
            == OutcomeClassificationService.SUCCESS
        )

        state_2 = learning_service.learn(
            memory_id
        )

        print(
            f"TOTAL OUTCOMES: "
            f"{state_2['total_outcomes']}"
        )

        print(
            f"SUCCESS: "
            f"{state_2['successes']}"
        )

        print(
            f"FAILURE: "
            f"{state_2['failures']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{state_2['learning_signal']}"
        )

        assert state_2["total_outcomes"] == 2
        assert state_2["successes"] == 2
        assert state_2["failures"] == 0
        assert state_2["learning_signal"] == 1.0

        print("STATUS: PASS")

        # ====================================================
        # 5. NEW FAILURE CHANGES LEARNING
        # ====================================================

        print()
        print("=" * 90)
        print("[5] NEW FAILURE CHANGES LEARNING")
        print("-" * 90)

        experience_3 = experience_service.create(
            bank_id=BANK_ID,
            canonical_memory_id=memory_id,
            task="Repeat concurrency fix.",
            action="Reuse pessimistic locking.",
            context="A new environment was tested.",
        )

        outcome_3 = outcome_service.create(
            experience_id=experience_3["experience_id"],
            outcome_type="failure",
            summary="The approach failed in the new environment.",
        )

        evidence_service.create_text_evidence(
            experience_id=experience_3["experience_id"],
            outcome_id=outcome_3["outcome_id"],
            content=(
                "The concurrency test failed and "
                "the transaction was rolled back."
            ),
            source_type="test_result",
            source_id="c4-incremental-failure-1",
        )

        result_3 = classifier.classify(
            outcome_3["outcome_id"]
        )

        assert (
            result_3["classification"]
            == OutcomeClassificationService.FAILURE
        )

        state_3 = learning_service.learn(
            memory_id
        )

        print(
            f"TOTAL OUTCOMES: "
            f"{state_3['total_outcomes']}"
        )

        print(
            f"SUCCESS: "
            f"{state_3['successes']}"
        )

        print(
            f"FAILURE: "
            f"{state_3['failures']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{state_3['learning_signal']}"
        )

        assert state_3["total_outcomes"] == 3
        assert state_3["successes"] == 2
        assert state_3["failures"] == 1

        assert state_3["learning_signal"] < state_2[
            "learning_signal"
        ]

        assert state_3["learning_signal"] == (
            1.0 / 3.0
        )

        print("STATUS: PASS")

        # ====================================================
        # 6. LEARNING ACTUALLY CHANGED
        # ====================================================

        print()
        print("=" * 90)
        print("[6] LEARNING STATE CHANGED")
        print("-" * 90)

        print(
            f"BEFORE NEW FAILURE: "
            f"{state_2['learning_signal']}"
        )

        print(
            f"AFTER NEW FAILURE: "
            f"{state_3['learning_signal']}"
        )

        assert (
            state_2["learning_signal"]
            != state_3["learning_signal"]
        )

        print(
            "NEW FAILURE CHANGED THE LEARNING STATE"
        )

        print("STATUS: PASS")

        # ====================================================
        # 7. RESTART
        # ====================================================

        print()
        print("=" * 90)
        print("[7] RESTART / PERSISTENCE")
        print("-" * 90)

        repository.close()

        repository = SQLiteLearningRepository(
            db_path=DB_PATH
        )

        learning_service = MemoryLearningStateService(
            repository=repository
        )

        persisted = learning_service.get_state(
            memory_id
        )

        assert persisted is not None

        assert (
            persisted["total_outcomes"]
            == state_3["total_outcomes"]
        )

        assert (
            persisted["successes"]
            == state_3["successes"]
        )

        assert (
            persisted["failures"]
            == state_3["failures"]
        )

        assert (
            persisted["learning_signal"]
            == state_3["learning_signal"]
        )

        print(
            f"TOTAL OUTCOMES: "
            f"{persisted['total_outcomes']}"
        )

        print(
            f"SUCCESS: "
            f"{persisted['successes']}"
        )

        print(
            f"FAILURE: "
            f"{persisted['failures']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{persisted['learning_signal']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 8. FINAL
        # ====================================================

        print()
        print("=" * 90)
        print("C4 INCREMENTAL LEARNING PASSED")
        print("=" * 90)

    finally:

        if repository is not None:
            try:
                repository.close()
            except Exception:
                pass

        try:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
        except Exception:
            pass


if __name__ == "__main__":
    main()