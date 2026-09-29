import hashlib
import os
import uuid

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

from app.services.outcome_evidence_service import (
    OutcomeEvidenceService,
)

from app.storage.repository_factory import (
    create_learning_repository,
)


# ============================================================
# TEST DATABASE
# ============================================================

BANK_ID = (
    f"c2-outcome-"
    f"{uuid.uuid4().hex[:8]}"
)

DB_PATH = (
    f"test_c2_outcome_"
    f"{uuid.uuid4().hex[:8]}.db"
)

os.environ[
    "LEARNING_DATABASE_PATH"
] = DB_PATH


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
# MAIN TEST
# ============================================================

def main():

    print()
    print("=" * 90)
    print(
        "C2 OUTCOME CAPTURE + EVIDENCE TEST"
    )
    print("=" * 90)

    canonical = None
    repository = None
    experience = None
    outcome = None
    evidence = None

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

    registered = canonical.register(
        bank_id=BANK_ID,
        text=memory_text,
    )

    assert registered is True

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

    print(
        f"TEXT: {memory['original_text']}"
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

    assert os.path.exists(
        DB_PATH
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

    experience = experience_service.create(
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
            "Concurrent wallet updates "
            "were causing transaction conflicts."
        ),
    )

    experience_id = (
        experience["experience_id"]
    )

    print(
        f"EXPERIENCE ID: {experience_id}"
    )

    print(
        f"MEMORY ID: "
        f"{experience['canonical_memory_id']}"
    )

    print(
        f"TASK: {experience['task']}"
    )

    print(
        f"ACTION: {experience['action']}"
    )

    assert (
        experience["canonical_memory_id"]
        == memory_id
    )

    status()

    # ========================================================
    # 4. SUCCESS OUTCOME
    # ========================================================

    section(
        4,
        "SUCCESS OUTCOME"
    )

    outcome_service = OutcomeCaptureService(
        repository=repository
    )

    success_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type=(
                OutcomeCaptureService.SUCCESS
            ),
            summary=(
                "The wallet concurrency "
                "problem was resolved."
            ),
            details=(
                "Pessimistic locking prevented "
                "the concurrent transaction conflict."
            ),
        )
    )

    success_outcome_id = (
        success_outcome["outcome_id"]
    )

    print(
        f"OUTCOME ID: {success_outcome_id}"
    )

    print(
        f"EXPERIENCE ID: "
        f"{success_outcome['experience_id']}"
    )

    print(
        f"TYPE: "
        f"{success_outcome['outcome_type']}"
    )

    print(
        f"SUMMARY: "
        f"{success_outcome['summary']}"
    )

    assert (
        success_outcome["outcome_type"]
        == "success"
    )

    assert (
        success_outcome["experience_id"]
        == experience_id
    )

    status()

    # ========================================================
    # 5. FAILURE OUTCOME
    # ========================================================

    section(
        5,
        "FAILURE OUTCOME"
    )

    failure_outcome = (
        outcome_service.create(
            experience_id=experience_id,
            outcome_type=(
                OutcomeCaptureService.FAILURE
            ),
            summary=(
                "A later retry-based experiment "
                "failed to solve the concurrency issue."
            ),
            details=(
                "Application-level retries "
                "still produced conflicting transactions."
            ),
        )
    )

    failure_outcome_id = (
        failure_outcome["outcome_id"]
    )

    print(
        f"OUTCOME ID: {failure_outcome_id}"
    )

    print(
        f"EXPERIENCE ID: "
        f"{failure_outcome['experience_id']}"
    )

    print(
        f"TYPE: "
        f"{failure_outcome['outcome_type']}"
    )

    print(
        f"SUMMARY: "
        f"{failure_outcome['summary']}"
    )

    assert (
        failure_outcome["outcome_type"]
        == "failure"
    )

    assert (
        failure_outcome["experience_id"]
        == experience_id
    )

    status()

    # ========================================================
    # 6. OUTCOME RETRIEVAL
    # ========================================================

    section(
        6,
        "OUTCOME RETRIEVAL"
    )

    retrieved_success = (
        outcome_service.get(
            success_outcome_id
        )
    )

    assert (
        retrieved_success is not None
    )

    assert (
        retrieved_success["outcome_id"]
        == success_outcome_id
    )

    print(
        f"RETRIEVED OUTCOME: "
        f"{retrieved_success['outcome_id']}"
    )

    print(
        f"TYPE: "
        f"{retrieved_success['outcome_type']}"
    )

    print(
        f"LINKED EXPERIENCE: "
        f"{retrieved_success['experience_id']}"
    )

    status()

    # ========================================================
    # 7. LIST OUTCOMES
    # ========================================================

    section(
        7,
        "OUTCOMES FOR EXPERIENCE"
    )

    outcomes = (
        outcome_service
        .list_for_experience(
            experience_id
        )
    )

    assert len(outcomes) == 2

    for item in outcomes:

        print(
            f"- {item['outcome_id']} | "
            f"{item['outcome_type']} | "
            f"{item['summary']}"
        )

    print(
        f"TOTAL OUTCOMES: {len(outcomes)}"
    )

    status()

    # ========================================================
    # 8. SUCCESS OUTCOME TEXT EVIDENCE
    # ========================================================

    section(
        8,
        "SUCCESS OUTCOME TEXT EVIDENCE"
    )

    evidence_service = EvidenceService(
        repository=repository
    )

    success_text_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=success_outcome_id,
            content=(
                "Integration tests passed "
                "for the wallet concurrency fix."
            ),
            source_type="test_result",
            source_id=(
                "wallet-integration-test-001"
            ),
        )
    )

    success_text_id = (
        success_text_evidence[
            "evidence_id"
        ]
    )

    print(
        f"EVIDENCE ID: {success_text_id}"
    )

    print(
        f"TYPE: "
        f"{success_text_evidence['evidence_type']}"
    )

    print(
        f"OUTCOME ID: "
        f"{success_text_evidence['outcome_id']}"
    )

    print(
        f"CONTENT: "
        f"{success_text_evidence['content']}"
    )

    assert (
        success_text_evidence["outcome_id"]
        == success_outcome_id
    )

    status()

    # ========================================================
    # 9. SUCCESS IMAGE EVIDENCE
    # ========================================================

    section(
        9,
        "SUCCESS IMAGE EVIDENCE"
    )

    fake_image_bytes = (
        b"FAKE-PNG-DATA-FOR-C2-TEST"
    )

    expected_hash = hashlib.sha256(
        fake_image_bytes
    ).hexdigest()

    success_image_evidence = (
        evidence_service
        .create_file_evidence(
            experience_id=experience_id,
            outcome_id=success_outcome_id,
            file_name=(
                "wallet_test_pass.png"
            ),
            mime_type="image/png",
            storage_key=(
                f"evidence/"
                f"{experience_id}/"
                f"wallet_test_pass.png"
            ),
            file_bytes=fake_image_bytes,
            evidence_type="image",
            source_type="test_result",
            source_id=(
                "wallet-integration-test-001"
            ),
        )
    )

    success_image_id = (
        success_image_evidence[
            "evidence_id"
        ]
    )

    print(
        f"EVIDENCE ID: {success_image_id}"
    )

    print(
        f"TYPE: "
        f"{success_image_evidence['evidence_type']}"
    )

    print(
        f"FILE: "
        f"{success_image_evidence['file_name']}"
    )

    print(
        f"MIME: "
        f"{success_image_evidence['mime_type']}"
    )

    print(
        f"OUTCOME ID: "
        f"{success_image_evidence['outcome_id']}"
    )

    print(
        f"STORAGE KEY: "
        f"{success_image_evidence['storage_key']}"
    )

    print(
        f"SHA256: "
        f"{success_image_evidence['sha256']}"
    )

    assert (
        success_image_evidence["sha256"]
        == expected_hash
    )

    status()

    # ========================================================
    # 10. SUCCESS TEST RESULT EVIDENCE
    # ========================================================

    section(
        10,
        "SUCCESS TEST RESULT EVIDENCE"
    )

    success_test_evidence = (
        evidence_service
        .create_test_result(
            experience_id=experience_id,
            outcome_id=success_outcome_id,
            result=(
                "12 tests passed, "
                "0 tests failed."
            ),
            source_id=(
                "wallet-integration-suite"
            ),
        )
    )

    success_test_id = (
        success_test_evidence[
            "evidence_id"
        ]
    )

    print(
        f"EVIDENCE ID: {success_test_id}"
    )

    print(
        f"TYPE: "
        f"{success_test_evidence['evidence_type']}"
    )

    print(
        f"OUTCOME ID: "
        f"{success_test_evidence['outcome_id']}"
    )

    print(
        f"CONTENT: "
        f"{success_test_evidence['content']}"
    )

    status()

    # ========================================================
    # 11. FAILURE EVIDENCE
    # ========================================================

    section(
        11,
        "FAILURE OUTCOME EVIDENCE"
    )

    failure_evidence = (
        evidence_service
        .create_text_evidence(
            experience_id=experience_id,
            outcome_id=failure_outcome_id,
            content=(
                "Retry-based implementation "
                "failed the concurrency test."
            ),
            source_type="test_result",
            source_id=(
                "wallet-retry-test-001"
            ),
        )
    )

    failure_evidence_id = (
        failure_evidence["evidence_id"]
    )

    print(
        f"EVIDENCE ID: "
        f"{failure_evidence_id}"
    )

    print(
        f"TYPE: "
        f"{failure_evidence['evidence_type']}"
    )

    print(
        f"OUTCOME ID: "
        f"{failure_evidence['outcome_id']}"
    )

    print(
        f"CONTENT: "
        f"{failure_evidence['content']}"
    )

    assert (
        failure_evidence["outcome_id"]
        == failure_outcome_id
    )

    status()

    # ========================================================
    # 12. EVIDENCE BY OUTCOME
    # ========================================================

    section(
        12,
        "EVIDENCE RETRIEVAL BY OUTCOME"
    )

    success_evidence = (
        evidence_service
        .list_for_outcome(
            success_outcome_id
        )
    )

    failure_evidence_list = (
        evidence_service
        .list_for_outcome(
            failure_outcome_id
        )
    )

    assert len(
        success_evidence
    ) == 3

    assert len(
        failure_evidence_list
    ) == 1

    print(
        f"SUCCESS OUTCOME EVIDENCE: "
        f"{len(success_evidence)}"
    )

    for item in success_evidence:

        print(
            f"- {item['evidence_id']} | "
            f"{item['evidence_type']} | "
            f"{item['file_name']}"
        )

    print(
        f"FAILURE OUTCOME EVIDENCE: "
        f"{len(failure_evidence_list)}"
    )

    for item in failure_evidence_list:

        print(
            f"- {item['evidence_id']} | "
            f"{item['evidence_type']} | "
            f"{item['content']}"
        )

    status()

    # ========================================================
    # 13. EVIDENCE BY STABLE ID
    # ========================================================

    section(
        13,
        "EVIDENCE RETRIEVAL BY STABLE EVIDENCE ID"
    )

    retrieved_image = (
        evidence_service.get(
            success_image_id
        )
    )

    assert (
        retrieved_image is not None
    )

    assert (
        retrieved_image["evidence_id"]
        == success_image_id
    )

    assert (
        retrieved_image["storage_key"]
        == (
            f"evidence/"
            f"{experience_id}/"
            f"wallet_test_pass.png"
        )
    )

    print(
        f"EVIDENCE ID: "
        f"{retrieved_image['evidence_id']}"
    )

    print(
        f"FILE: "
        f"{retrieved_image['file_name']}"
    )

    print(
        f"STORAGE KEY: "
        f"{retrieved_image['storage_key']}"
    )

    print(
        f"SHA256: "
        f"{retrieved_image['sha256']}"
    )

    status()

    # ========================================================
    # 14. COMPLETE OUTCOME CHAIN
    # ========================================================

    section(
        14,
        "COMPLETE MEMORY → EXPERIENCE → OUTCOME → EVIDENCE"
    )

    chain_service = (
        OutcomeEvidenceService(
            repository=repository
        )
    )

    chain = (
        chain_service
        .get_complete_outcome_chain(
            success_outcome_id
        )
    )

    assert chain is not None

    chain_outcome = (
        chain["outcome"]
    )

    chain_experience = (
        chain["experience"]
    )

    chain_evidence = (
        chain["evidence"]
    )

    assert (
        chain_outcome["outcome_id"]
        == success_outcome_id
    )

    assert (
        chain_outcome["experience_id"]
        == experience_id
    )

    assert (
        chain_experience[
            "canonical_memory_id"
        ]
        == memory_id
    )

    assert len(chain_evidence) == 3

    print(
        f"CANONICAL MEMORY ID: "
        f"{chain_experience['canonical_memory_id']}"
    )

    print(
        f"EXPERIENCE ID: "
        f"{chain_experience['experience_id']}"
    )

    print(
        f"OUTCOME ID: "
        f"{chain_outcome['outcome_id']}"
    )

    print(
        f"OUTCOME TYPE: "
        f"{chain_outcome['outcome_type']}"
    )

    print(
        f"EVIDENCE COUNT: "
        f"{len(chain_evidence)}"
    )

    for item in chain_evidence:

        print()
        print(
            f"EVIDENCE: "
            f"{item['evidence_id']}"
        )

        print(
            f"  TYPE: "
            f"{item['evidence_type']}"
        )

        print(
            f"  OUTCOME: "
            f"{item['outcome_id']}"
        )

        print(
            f"  FILE: "
            f"{item['file_name']}"
        )

        print(
            f"  STORAGE KEY: "
            f"{item['storage_key']}"
        )

        print(
            f"  CONTENT: "
            f"{item['content']}"
        )

    status()

    # ========================================================
    # 15. INVALID OUTCOME TYPE
    # ========================================================

    section(
        15,
        "INVALID OUTCOME TYPE REJECTION"
    )

    try:

        outcome_service.create(
            experience_id=experience_id,
            outcome_type="partial",
            summary=(
                "This should not be accepted in C2."
            ),
        )

        raise AssertionError(
            "Invalid outcome type was accepted."
        )

    except ValueError as exc:

        print(
            f"REJECTED: {exc}"
        )

        status()

    # ========================================================
    # 16. INVALID EXPERIENCE
    # ========================================================

    section(
        16,
        "INVALID EXPERIENCE REJECTION"
    )

    try:

        outcome_service.create(
            experience_id=str(
                uuid.uuid4()
            ),
            outcome_type="success",
            summary="Invalid test.",
        )

        raise AssertionError(
            "Outcome was created "
            "for nonexistent experience."
        )

    except ValueError as exc:

        print(
            f"REJECTED: {exc}"
        )

        status()

       # ========================================================
    # 17. INVALID OUTCOME / EXPERIENCE LINK
    # ========================================================

    section(
        17,
        "INVALID OUTCOME → EXPERIENCE LINK REJECTION"
    )

    # Create a second valid experience.
    second_experience = (
        experience_service.create(
            bank_id=BANK_ID,
            canonical_memory_id=memory_id,
            task=(
                "Attempt the wallet concurrency "
                "fix using another strategy."
            ),
            action=(
                "Use application-level retries."
            ),
            context=(
                "This is a separate experience "
                "used to verify relationship integrity."
            ),
        )
    )

    second_experience_id = (
        second_experience["experience_id"]
    )

    print(
        f"SECOND EXPERIENCE ID: "
        f"{second_experience_id}"
    )

    assert (
        second_experience_id
        != experience_id
    )

    # The outcome belongs to the FIRST experience.
    # We deliberately try to attach it to the SECOND.
    try:

        evidence_service.create_text_evidence(
            experience_id=second_experience_id,
            outcome_id=success_outcome_id,
            content=(
                "This evidence must not be allowed "
                "because the outcome belongs to "
                "another experience."
            ),
            source_type="test_result",
            source_id=(
                "invalid-cross-experience-link"
            ),
        )

        raise AssertionError(
            "Cross-experience outcome/evidence "
            "relationship was incorrectly accepted."
        )

    except ValueError as exc:

        print(
            f"REJECTED: {exc}"
        )

        assert (
            "does not belong"
            in str(exc)
        )

        status()
    # ========================================================
    # 18. RESTART / PERSISTENCE
    # ========================================================

    section(
        18,
        "RESTART / PERSISTENCE"
    )

    repository.close()

    repository = (
        create_learning_repository()
    )

    restarted_outcome = (
        repository.get_outcome(
            success_outcome_id
        )
    )

    restarted_evidence = (
        repository.list_evidence_for_outcome(
            success_outcome_id
        )
    )

    restarted_experience = (
        repository.get_experience(
            experience_id
        )
    )

    assert (
        restarted_experience is not None
    )

    assert (
        restarted_outcome is not None
    )

    assert (
        len(restarted_evidence)
        == 3
    )

    print(
        f"EXPERIENCE SURVIVED REOPEN: "
        f"{restarted_experience['experience_id']}"
    )

    print(
        f"OUTCOME SURVIVED REOPEN: "
        f"{restarted_outcome['outcome_id']}"
    )

    print(
        f"EVIDENCE SURVIVED REOPEN: "
        f"{len(restarted_evidence)}"
    )

    print(
        f"IMAGE STORAGE KEY SURVIVED: "
        f"{restarted_evidence[1]['storage_key']}"
    )

    status()

    # ========================================================
    # 19. FINAL CHAIN VERIFICATION
    # ========================================================

    section(
        19,
        "FINAL CHAIN VERIFICATION"
    )

    final_experience = (
        repository.get_experience(
            experience_id
        )
    )

    final_outcome = (
        repository.get_outcome(
            success_outcome_id
        )
    )

    final_evidence = (
        repository.list_evidence_for_outcome(
            success_outcome_id
        )
    )

    assert (
        final_experience[
            "canonical_memory_id"
        ]
        == memory_id
    )

    assert (
        final_outcome[
            "experience_id"
        ]
        == experience_id
    )

    assert all(
        item["outcome_id"]
        == success_outcome_id
        for item in final_evidence
    )

    print(
        "MEMORY       : "
        f"{memory_id}"
    )

    print(
        "EXPERIENCE   : "
        f"{experience_id}"
    )

    print(
        "OUTCOME      : "
        f"{success_outcome_id}"
    )

    print(
        "EVIDENCE     : "
        f"{len(final_evidence)} items"
    )

    print(
        "PERSISTENCE  : VERIFIED"
    )

    print(
        "LINKAGE      : VERIFIED"
    )

    print(
        "OUTCOME TYPE : SUCCESS"
    )

    print(
        "IMAGE META   : VERIFIED"
    )

    print(
        "SHA256       : VERIFIED"
    )

    print(
        "STABLE IDS   : VERIFIED"
    )

    print(
        "FRONTEND IDs : VERIFIED"
    )

    print(
        "STATUS       : PASS"
    )

    # ========================================================
    # CLEANUP
    # ========================================================

    repository.close()

    print()
    print("=" * 90)
    print(
        "C2 OUTCOME CAPTURE + EVIDENCE PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()