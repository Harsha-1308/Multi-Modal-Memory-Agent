import hashlib
import os
import uuid


# ============================================================
# TEST DATABASE
# ============================================================

BANK_ID = (
    f"c3-classification-"
    f"{uuid.uuid4().hex[:8]}"
)

DB_PATH = (
    f"test_c3_classification_"
    f"{uuid.uuid4().hex[:8]}.db"
)

os.environ[
    "LEARNING_DATABASE_PATH"
] = DB_PATH


# ============================================================
# APPLICATION IMPORTS
# ============================================================

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)

from app.services.experience_service import (
    ExperienceService,
)

from app.services.outcome_capture_service import (
    OutcomeCaptureService,
)

from app.services.evidence_service import (
    EvidenceService,
)

from app.services.outcome_classification_service import (
    OutcomeClassificationService,
)

from app.storage.repository_factory import (
    create_learning_repository,
)


# ============================================================
# HELPERS
# ============================================================

def section(number, title):

    print()
    print("=" * 90)
    print(
        f"[{number}] {title}"
    )
    print("-" * 90)


def status():

    print(
        "STATUS: PASS"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print(
        "C3 OUTCOME CLASSIFICATION TEST"
    )
    print("=" * 90)

    repository = None

    # ========================================================
    # 1. CANONICAL MEMORY
    # ========================================================

    section(
        1,
        "CANONICAL MEMORY"
    )

    canonical = CanonicalMemoryService(
        db_path=DB_PATH
    )

    memory_text = (
        "Pessimistic database locking "
        "resolved the wallet concurrency problem."
    )

    assert canonical.register(
        bank_id=BANK_ID,
        text=memory_text,
    )

    memory = canonical.list_memories(
        bank_id=BANK_ID
    )[0]

    memory_id = memory["id"]

    print(
        f"BANK ID: {BANK_ID}"
    )

    print(
        f"MEMORY ID: {memory_id}"
    )

    status()

    canonical.close()

    # ========================================================
    # 2. STORAGE
    # ========================================================

    section(
        2,
        "STORAGE ADAPTER"
    )

    repository = (
        create_learning_repository()
    )

    print(
        "BACKEND: SQLite"
    )

    print(
        f"DATABASE: {DB_PATH}"
    )

    status()

    # ========================================================
    # 3. EXPERIENCE
    # ========================================================

    section(
        3,
        "EXPERIENCE"
    )

    experience_service = ExperienceService(
        repository=repository,
        canonical_memory_service=CanonicalMemoryService(
            db_path=DB_PATH
        ),
    )

    experience = (
        experience_service.create(
            bank_id=BANK_ID,
            canonical_memory_id=memory_id,
            task=(
                "Resolve wallet concurrency "
                "during integration testing."
            ),
            action=(
                "Use pessimistic database locking."
            ),
            context=(
                "Concurrency conflicts were "
                "observed during integration tests."
            ),
        )
    )

    experience_id = (
        experience["experience_id"]
    )

    print(
        f"EXPERIENCE ID: {experience_id}"
    )

    status()

    # ========================================================
    # 4. SERVICES
    # ========================================================

    section(
        4,
        "C3 SERVICES"
    )

    outcome_service = (
        OutcomeCaptureService(
            repository=repository
        )
    )

    evidence_service = EvidenceService(
        repository=repository
    )

    classifier = (
        OutcomeClassificationService(
            repository=repository
        )
    )

    print(
        "Outcome capture: READY"
    )

    print(
        "Evidence service: READY"
    )

    print(
        "Classification service: READY"
    )

    status()

    # ========================================================
    # 5. UNKNOWN — NO EVIDENCE
    # ========================================================

    section(
        5,
        "UNKNOWN — NO EVIDENCE"
    )

    unknown_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Caller reported success "
                "without attaching evidence."
            ),
        )
    )

    unknown_outcome_id = (
        unknown_outcome["outcome_id"]
    )

    unknown_result = classifier.classify(
        unknown_outcome_id
    )

    print(
        f"REPORTED OUTCOME: "
        f"{unknown_result['reported_outcome']}"
    )

    print(
        f"CLASSIFICATION: "
        f"{unknown_result['classification']}"
    )

    print(
        f"REASON: "
        f"{unknown_result['reason']}"
    )

    assert (
        unknown_result["classification"]
        == OutcomeClassificationService.UNKNOWN
    )

    assert (
        unknown_result["reported_outcome"]
        == "success"
    )

    status()

    # ========================================================
    # 6. SUCCESS
    # ========================================================

    section(
        6,
        "SUCCESS — POSITIVE EVIDENCE"
    )

    success_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Locking approach succeeded."
            ),
        )
    )

    success_id = (
        success_outcome["outcome_id"]
    )

    success_evidence = (
        evidence_service
        .create_test_result(
            experience_id=experience_id,
            outcome_id=success_id,
            result=(
                "12 tests passed, "
                "0 tests failed."
            ),
            source_id=(
                "c3-success-test"
            ),
        )
    )

    success_result = classifier.classify(
        success_id
    )

    print(
        f"REPORTED OUTCOME: "
        f"{success_result['reported_outcome']}"
    )

    print(
        f"CLASSIFICATION: "
        f"{success_result['classification']}"
    )

    print(
        f"EVIDENCE COUNT: "
        f"{success_result['evidence_count']}"
    )

    print(
        f"POSITIVE EVIDENCE: "
        f"{success_result['positive_evidence_ids']}"
    )

    print(
        f"NEGATIVE EVIDENCE: "
        f"{success_result['negative_evidence_ids']}"
    )

    assert (
        success_result["classification"]
        == OutcomeClassificationService.SUCCESS
    )

    assert (
        success_evidence["evidence_id"]
        in success_result["positive_evidence_ids"]
    )

    status()

    # ========================================================
    # 7. FAILURE
    # ========================================================

    section(
        7,
        "FAILURE — NEGATIVE EVIDENCE"
    )

    failure_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="failure",
            summary=(
                "Retry strategy failed."
            ),
        )
    )

    failure_id = (
        failure_outcome["outcome_id"]
    )

    failure_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=failure_id,
            content=(
                "The retry-based implementation "
                "failed the concurrency test."
            ),
            source_type="test_result",
            source_id=(
                "c3-failure-test"
            ),
        )
    )

    failure_result = classifier.classify(
        failure_id
    )

    print(
        f"REPORTED OUTCOME: "
        f"{failure_result['reported_outcome']}"
    )

    print(
        f"CLASSIFICATION: "
        f"{failure_result['classification']}"
    )

    print(
        f"EVIDENCE COUNT: "
        f"{failure_result['evidence_count']}"
    )

    print(
        f"NEGATIVE EVIDENCE: "
        f"{failure_result['negative_evidence_ids']}"
    )

    assert (
        failure_result["classification"]
        == OutcomeClassificationService.FAILURE
    )

    assert (
        failure_evidence["evidence_id"]
        in failure_result["negative_evidence_ids"]
    )

    status()

    # ========================================================
    # 8. PARTIAL — MIXED EVIDENCE
    # ========================================================

    section(
        8,
        "PARTIAL — MIXED POSITIVE + NEGATIVE EVIDENCE"
    )

    partial_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Mixed integration test result."
            ),
        )
    )

    partial_id = (
        partial_outcome["outcome_id"]
    )

    positive_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=partial_id,
            content=(
                "The main concurrency test "
                "passed successfully."
            ),
            source_type="test_result",
            source_id=(
                "c3-partial-positive"
            ),
        )
    )

    negative_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=partial_id,
            content=(
                "A secondary concurrency "
                "test failed."
            ),
            source_type="test_result",
            source_id=(
                "c3-partial-negative"
            ),
        )
    )

    partial_result = classifier.classify(
        partial_id
    )

    print(
        f"REPORTED OUTCOME: "
        f"{partial_result['reported_outcome']}"
    )

    print(
        f"CLASSIFICATION: "
        f"{partial_result['classification']}"
    )

    print(
        f"POSITIVE EVIDENCE: "
        f"{partial_result['positive_evidence_ids']}"
    )

    print(
        f"NEGATIVE EVIDENCE: "
        f"{partial_result['negative_evidence_ids']}"
    )

    assert (
        partial_result["classification"]
        == OutcomeClassificationService.PARTIAL
    )

    assert (
        positive_evidence["evidence_id"]
        in partial_result[
            "positive_evidence_ids"
        ]
    )

    assert (
        negative_evidence["evidence_id"]
        in partial_result[
            "negative_evidence_ids"
        ]
    )

    status()

    # ========================================================
    # 9. REPORTED LABEL MUST NOT OVERRIDE EVIDENCE
    # ========================================================

    section(
        9,
        "REPORTED LABEL CANNOT OVERRIDE EVIDENCE"
    )

    contradiction_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Caller claims this worked."
            ),
        )
    )

    contradiction_id = (
        contradiction_outcome[
            "outcome_id"
        ]
    )

    contradiction_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=contradiction_id,
            content=(
                "The implementation failed "
                "the required concurrency test."
            ),
            source_type="test_result",
            source_id=(
                "c3-contradiction-test"
            ),
        )
    )

    contradiction_result = (
        classifier.classify(
            contradiction_id
        )
    )

    print(
        f"REPORTED OUTCOME: "
        f"{contradiction_result['reported_outcome']}"
    )

    print(
        f"CLASSIFICATION: "
        f"{contradiction_result['classification']}"
    )

    print(
        f"EVIDENCE ID: "
        f"{contradiction_evidence['evidence_id']}"
    )

    assert (
        contradiction_result[
            "reported_outcome"
        ]
        == "success"
    )

    assert (
        contradiction_result[
            "classification"
        ]
        == OutcomeClassificationService.FAILURE
    )

    status()

    # ========================================================
    # 10. IMAGE-ONLY EVIDENCE
    # ========================================================

    section(
        10,
        "IMAGE-ONLY EVIDENCE WITHOUT TEXTUAL RESULT"
    )

    image_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Caller attached a screenshot."
            ),
        )
    )

    image_outcome_id = (
        image_outcome["outcome_id"]
    )

    image_bytes = (
        b"FAKE-PNG-BYTES-FOR-C3"
    )

    image_evidence = (
        evidence_service
        .create_file_evidence(
            experience_id=experience_id,
            outcome_id=image_outcome_id,
            file_name=(
                "result.png"
            ),
            mime_type="image/png",
            storage_key=(
                f"evidence/"
                f"{experience_id}/"
                f"result.png"
            ),
            file_bytes=image_bytes,
            evidence_type="image",
            source_type="user_upload",
        )
    )

    image_result = classifier.classify(
        image_outcome_id
    )

    print(
        f"CLASSIFICATION: "
        f"{image_result['classification']}"
    )

    print(
        f"NEUTRAL EVIDENCE: "
        f"{image_result['neutral_evidence_ids']}"
    )

    assert (
        image_result["classification"]
        == OutcomeClassificationService.UNKNOWN
    )

    assert (
        image_evidence["evidence_id"]
        in image_result[
            "neutral_evidence_ids"
        ]
    )

    status()

    # ========================================================
    # 11. SAME EVIDENCE ITEM CAN CONTAIN MIXED SIGNALS
    # ========================================================

    section(
        11,
        "SINGLE EVIDENCE ITEM WITH MIXED SIGNALS"
    )

    mixed_single_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Single report contains mixed results."
            ),
        )
    )

    mixed_single_id = (
        mixed_single_outcome[
            "outcome_id"
        ]
    )

    mixed_single_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=mixed_single_id,
            content=(
                "8 tests passed, "
                "but 4 tests failed."
            ),
            source_type="test_result",
            source_id=(
                "c3-mixed-single"
            ),
        )
    )

    mixed_single_result = (
        classifier.classify(
            mixed_single_id
        )
    )

    print(
        f"CLASSIFICATION: "
        f"{mixed_single_result['classification']}"
    )

    print(
        f"POSITIVE: "
        f"{mixed_single_result['positive_evidence_ids']}"
    )

    print(
        f"NEGATIVE: "
        f"{mixed_single_result['negative_evidence_ids']}"
    )

    assert (
        mixed_single_result[
            "classification"
        ]
        == OutcomeClassificationService.PARTIAL
    )

    assert (
        mixed_single_evidence[
            "evidence_id"
        ]
        in mixed_single_result[
            "positive_evidence_ids"
        ]
    )

    assert (
        mixed_single_evidence[
            "evidence_id"
        ]
        in mixed_single_result[
            "negative_evidence_ids"
        ]
    )

    status()

    # ========================================================
    # 12. NEUTRAL TEXT
    # ========================================================

    section(
        12,
        "NEUTRAL TEXT EVIDENCE"
    )

    neutral_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type="success",
            summary=(
                "Experiment was executed."
            ),
        )
    )

    neutral_id = (
        neutral_outcome["outcome_id"]
    )

    neutral_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=neutral_id,
            content=(
                "The concurrency experiment "
                "was executed in the staging environment."
            ),
            source_type="agent_observation",
        )
    )

    neutral_result = classifier.classify(
        neutral_id
    )

    print(
        f"CLASSIFICATION: "
        f"{neutral_result['classification']}"
    )

    print(
        f"NEUTRAL EVIDENCE: "
        f"{neutral_result['neutral_evidence_ids']}"
    )

    assert (
        neutral_result["classification"]
        == OutcomeClassificationService.UNKNOWN
    )

    assert (
        neutral_evidence["evidence_id"]
        in neutral_result[
            "neutral_evidence_ids"
        ]
    )

    status()

    # ========================================================
    # 13. PERSISTED CLASSIFICATION
    # ========================================================

    section(
        13,
        "CLASSIFICATION PERSISTENCE"
    )

    persisted = classifier.get_classification(
        success_id
    )

    print(
        f"OUTCOME ID: "
        f"{persisted['outcome_id']}"
    )

    print(
        f"REPORTED: "
        f"{persisted['reported_outcome']}"
    )

    print(
        f"CLASSIFICATION: "
        f"{persisted['classification']}"
    )

    print(
        f"EVIDENCE COUNT: "
        f"{persisted['evidence_count']}"
    )

    print(
        f"EVIDENCE IDS: "
        f"{persisted['evidence_ids']}"
    )

    print(
        f"VERSION: "
        f"{persisted['classification_version']}"
    )

    assert (
        persisted["classification"]
        == "success"
    )

    assert (
        persisted["evidence_count"]
        == 1
    )

    assert (
        success_evidence[
            "evidence_id"
        ]
        in persisted["evidence_ids"]
    )

    assert (
        persisted[
            "classification_version"
        ]
        == "c3-v1"
    )

    status()

    # ========================================================
    # 14. RESTART PERSISTENCE
    # ========================================================

    section(
        14,
        "RESTART / PERSISTENCE"
    )

    repository.close()

    repository = (
        create_learning_repository()
    )

    restarted = (
        repository.get_outcome(
            success_id
        )
    )

    assert restarted is not None

    assert (
        restarted["classification"]
        == "success"
    )

    assert (
        restarted[
            "classification_version"
        ]
        == "c3-v1"
    )

    print(
        f"OUTCOME SURVIVED REOPEN: "
        f"{restarted['outcome_id']}"
    )

    print(
        f"CLASSIFICATION SURVIVED: "
        f"{restarted['classification']}"
    )

    print(
        f"VERSION SURVIVED: "
        f"{restarted['classification_version']}"
    )

    status()

    # ========================================================
    # 15. RECLASSIFICATION / IDEMPOTENCE
    # ========================================================

    section(
        15,
        "RECLASSIFICATION CONSISTENCY"
    )

    classifier_after_restart = (
        OutcomeClassificationService(
            repository=repository
        )
    )

    repeated = (
        classifier_after_restart.classify(
            success_id
        )
    )

    assert (
        repeated["classification"]
        == "success"
    )

    assert (
        repeated["evidence_count"]
        == 1
    )

    assert (
        repeated["evidence_ids"]
        == [
            success_evidence[
                "evidence_id"
            ]
        ]
    )

    print(
        f"RECLASSIFICATION: "
        f"{repeated['classification']}"
    )

    print(
        f"EVIDENCE COUNT: "
        f"{repeated['evidence_count']}"
    )

    print(
        f"EVIDENCE IDS: "
        f"{repeated['evidence_ids']}"
    )

    status()

    # ========================================================
    # 16. EVIDENCE ISOLATION
    # ========================================================

    section(
        16,
        "EVIDENCE ISOLATION BETWEEN OUTCOMES"
    )

    success_evidence_after = (
        repository.list_evidence_for_outcome(
            success_id
        )
    )

    failure_evidence_after = (
        repository.list_evidence_for_outcome(
            failure_id
        )
    )

    success_ids = {
        item["evidence_id"]
        for item in success_evidence_after
    }

    failure_ids = {
        item["evidence_id"]
        for item in failure_evidence_after
    }

    assert (
        success_ids.isdisjoint(
            failure_ids
        )
    )

    print(
        f"SUCCESS EVIDENCE: "
        f"{len(success_ids)}"
    )

    print(
        f"FAILURE EVIDENCE: "
        f"{len(failure_ids)}"
    )

    print(
        "CROSS-OUTCOME EVIDENCE LEAK: NONE"
    )

    status()

    # ========================================================
    # 17. COMPLETE C3 CHAIN
    # ========================================================

    section(
        17,
        "COMPLETE C3 CHAIN"
    )

    final_outcome = (
        repository.get_outcome(
            contradiction_id
        )
    )

    final_evidence = (
        repository.list_evidence_for_outcome(
            contradiction_id
        )
    )

    print(
        f"MEMORY ID: "
        f"{memory_id}"
    )

    print(
        f"EXPERIENCE ID: "
        f"{experience_id}"
    )

    print(
        f"OUTCOME ID: "
        f"{final_outcome['outcome_id']}"
    )

    print(
        f"REPORTED OUTCOME: "
        f"{final_outcome['outcome_type']}"
    )

    print(
        f"CLASSIFIED OUTCOME: "
        f"{final_outcome['classification']}"
    )

    print(
        f"EVIDENCE COUNT: "
        f"{len(final_evidence)}"
    )

    print(
        f"CLASSIFICATION EVIDENCE IDS: "
        f"{final_outcome['classification_evidence_ids']}"
    )

    assert (
        final_outcome[
            "classification"
        ]
        == "failure"
    )

    assert (
        len(final_evidence)
        == 1
    )

    status()

    # ========================================================
    # FINAL
    # ========================================================

    repository.close()

    print()
    print("=" * 90)
    print(
        "C3 OUTCOME CLASSIFICATION PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()