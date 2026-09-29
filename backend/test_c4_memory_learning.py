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


DB_PATH = (
    f"test_c4_learning_"
    f"{uuid.uuid4().hex[:8]}.db"
)

CANONICAL_DB_PATH = (
    f"test_c4_canonical_"
    f"{uuid.uuid4().hex[:8]}.db"
)

BANK_ID = (
    f"c4-learning-"
    f"{uuid.uuid4().hex[:8]}"
)


def section(number, title):
    print()
    print("=" * 90)
    print(f"[{number}] {title}")
    print("-" * 90)


def require(condition, message):

    if not condition:
        raise AssertionError(message)


print()
print("=" * 90)
print("C4 MEMORY LEARNING TEST")
print("=" * 90)


repository = SQLiteLearningRepository(
    db_path=DB_PATH
)

canonical = CanonicalMemoryService(
    db_path=CANONICAL_DB_PATH
)


try:

    # ================================================================
    # 1. CANONICAL MEMORY
    # ================================================================

    section(
        1,
        "CANONICAL MEMORY"
    )

    canonical.register(
        bank_id=BANK_ID,
        text=(
            "Pessimistic database locking "
            "resolved the wallet concurrency problem."
        ),
    )

    memories = canonical.list_memories(
        bank_id=BANK_ID
    )

    require(
        len(memories) == 1,
        "Canonical memory was not created."
    )

    memory_id = memories[0]["id"]

    print(
        f"MEMORY ID: {memory_id}"
    )

    print("STATUS: PASS")


    # ================================================================
    # 2. SERVICES
    # ================================================================

    section(
        2,
        "C4 SERVICES"
    )

    experience_service = ExperienceService(
        repository=repository,
        canonical_memory_service=canonical,
    )

    outcome_service = OutcomeCaptureService(
        repository=repository
    )

    classification_service = (
        OutcomeClassificationService(
            repository=repository
        )
    )

    learning_service = (
        MemoryLearningStateService(
            repository=repository
        )
    )

    print(
        "Experience service: READY"
    )

    print(
        "Outcome service: READY"
    )

    print(
        "Classification service: READY"
    )

    print(
        "Learning service: READY"
    )

    print("STATUS: PASS")


    # ================================================================
    # 3. SUCCESS EXPERIENCE
    # ================================================================

    section(
        3,
        "SUCCESS EXPERIENCE"
    )

    exp_success = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task=(
            "Resolve concurrent wallet updates."
        ),
        action=(
            "Apply pessimistic database locking."
        ),
        context=(
            "Integration test environment."
        ),
    )

    outcome_success = outcome_service.create(
        experience_id=exp_success[
            "experience_id"
        ],
        outcome_type="success",
        summary=(
            "Locking solved the concurrency issue."
        ),
    )

    evidence_success = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=exp_success[
            "experience_id"
        ],
        outcome_id=outcome_success[
            "outcome_id"
        ],
        evidence_type="test_result",
        content=(
            "12 tests passed."
        ),
        file_name=None,
        mime_type=None,
        storage_key=None,
        sha256=None,
        source_type="test_result",
        source_id="c4-test-success",
    )

    classified_success = (
        classification_service.classify(
            outcome_success["outcome_id"]
        )
    )

    require(
        classified_success[
            "classification"
        ] == "success",
        "Success evidence was not classified as success."
    )

    print(
        "OUTCOME:",
        outcome_success["outcome_id"]
    )

    print(
        "CLASSIFICATION:",
        classified_success["classification"]
    )

    print(
        "EVIDENCE:",
        evidence_success["evidence_id"]
    )

    print("STATUS: PASS")


    # ================================================================
    # 4. FAILURE EXPERIENCE
    # ================================================================

    section(
        4,
        "FAILURE EXPERIENCE"
    )

    exp_failure = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task=(
            "Resolve concurrent wallet updates."
        ),
        action=(
            "Use application-level retries."
        ),
        context=(
            "Integration test environment."
        ),
    )

    outcome_failure = outcome_service.create(
        experience_id=exp_failure[
            "experience_id"
        ],
        outcome_type="failure",
        summary=(
            "Retry strategy did not resolve the issue."
        ),
    )

    evidence_failure = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=exp_failure[
            "experience_id"
        ],
        outcome_id=outcome_failure[
            "outcome_id"
        ],
        evidence_type="test_result",
        content=(
            "3 tests failed."
        ),
        file_name=None,
        mime_type=None,
        storage_key=None,
        sha256=None,
        source_type="test_result",
        source_id="c4-test-failure",
    )

    classified_failure = (
        classification_service.classify(
            outcome_failure["outcome_id"]
        )
    )

    require(
        classified_failure[
            "classification"
        ] == "failure",
        "Failure evidence was not classified as failure."
    )

    print(
        "OUTCOME:",
        outcome_failure["outcome_id"]
    )

    print(
        "CLASSIFICATION:",
        classified_failure["classification"]
    )

    print(
        "EVIDENCE:",
        evidence_failure["evidence_id"]
    )

    print("STATUS: PASS")


    # ================================================================
    # 5. PARTIAL EXPERIENCE
    # ================================================================

    section(
        5,
        "PARTIAL EXPERIENCE"
    )

    exp_partial = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task=(
            "Resolve concurrent wallet updates."
        ),
        action=(
            "Apply locking with additional retry handling."
        ),
        context=(
            "Mixed integration test environment."
        ),
    )

    outcome_partial = outcome_service.create(
        experience_id=exp_partial[
            "experience_id"
        ],
        outcome_type="success",
        summary=(
            "Some tests passed while some failed."
        ),
    )

    evidence_partial = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=exp_partial[
            "experience_id"
        ],
        outcome_id=outcome_partial[
            "outcome_id"
        ],
        evidence_type="test_result",
        content=(
            "8 tests passed but 2 tests failed."
        ),
        file_name=None,
        mime_type=None,
        storage_key=None,
        sha256=None,
        source_type="test_result",
        source_id="c4-test-partial",
    )

    classified_partial = (
        classification_service.classify(
            outcome_partial["outcome_id"]
        )
    )

    require(
        classified_partial[
            "classification"
        ] == "partial",
        "Mixed evidence was not classified as partial."
    )

    print(
        "OUTCOME:",
        outcome_partial["outcome_id"]
    )

    print(
        "CLASSIFICATION:",
        classified_partial["classification"]
    )

    print(
        "POSITIVE EVIDENCE:",
        classified_partial[
            "positive_evidence_ids"
        ]
    )

    print(
        "NEGATIVE EVIDENCE:",
        classified_partial[
            "negative_evidence_ids"
        ]
    )

    print("STATUS: PASS")


    # ================================================================
    # 6. UNKNOWN EXPERIENCE
    # ================================================================

    section(
        6,
        "UNKNOWN EXPERIENCE"
    )

    exp_unknown = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task=(
            "Resolve concurrent wallet updates."
        ),
        action=(
            "Inspect visual diagnostic output."
        ),
        context=(
            "Visual debugging session."
        ),
    )

    outcome_unknown = outcome_service.create(
        experience_id=exp_unknown[
            "experience_id"
        ],
        outcome_type="failure",
        summary=(
            "Visual diagnostic was captured."
        ),
    )

    evidence_unknown = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=exp_unknown[
            "experience_id"
        ],
        outcome_id=outcome_unknown[
            "outcome_id"
        ],
        evidence_type="image",
        content=None,
        file_name="diagnostic.png",
        mime_type="image/png",
        storage_key=(
            f"c4/{uuid.uuid4()}.png"
        ),
        sha256=(
            "fake-sha256-for-c4-test"
        ),
        source_type="user_upload",
        source_id="c4-test-image",
    )

    classified_unknown = (
        classification_service.classify(
            outcome_unknown["outcome_id"]
        )
    )

    require(
        classified_unknown[
            "classification"
        ] == "unknown",
        "Image-only evidence should be unknown."
    )

    print(
        "OUTCOME:",
        outcome_unknown["outcome_id"]
    )

    print(
        "REPORTED:",
        classified_unknown[
            "reported_outcome"
        ]
    )

    print(
        "CLASSIFICATION:",
        classified_unknown[
            "classification"
        ]
    )

    print(
        "EVIDENCE:",
        evidence_unknown["evidence_id"]
    )

    print("STATUS: PASS")


    # ================================================================
    # 7. SECOND SUCCESS
    # ================================================================

    section(
        7,
        "SECOND SUCCESS EXPERIENCE"
    )

    exp_success_2 = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task=(
            "Verify locking under repeated concurrency."
        ),
        action=(
            "Reuse pessimistic locking."
        ),
        context=(
            "Regression environment."
        ),
    )

    outcome_success_2 = outcome_service.create(
        experience_id=exp_success_2[
            "experience_id"
        ],
        outcome_type="success",
        summary=(
            "Regression verification succeeded."
        ),
    )

    evidence_success_2 = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=exp_success_2[
            "experience_id"
        ],
        outcome_id=outcome_success_2[
            "outcome_id"
        ],
        evidence_type="test_result",
        content=(
            "All regression tests passed successfully."
        ),
        file_name=None,
        mime_type=None,
        storage_key=None,
        sha256=None,
        source_type="test_result",
        source_id="c4-test-success-2",
    )

    classified_success_2 = (
        classification_service.classify(
            outcome_success_2["outcome_id"]
        )
    )

    require(
        classified_success_2[
            "classification"
        ] == "success",
        "Second success was not classified correctly."
    )

    print(
        "OUTCOME:",
        outcome_success_2["outcome_id"]
    )

    print(
        "CLASSIFICATION:",
        classified_success_2[
            "classification"
        ]
    )

    print("STATUS: PASS")


    # ================================================================
    # 8. LEARN
    # ================================================================

    section(
        8,
        "C4 LEARNING STATE"
    )

    state = learning_service.learn(
        canonical_memory_id=memory_id
    )

    require(
        state["total_outcomes"] == 5,
        "Expected 5 outcomes."
    )

    require(
        state["successes"] == 2,
        "Expected 2 successes."
    )

    require(
        state["failures"] == 1,
        "Expected 1 failure."
    )

    require(
        state["partial"] == 1,
        "Expected 1 partial outcome."
    )

    require(
        state["unknown"] == 1,
        "Expected 1 unknown outcome."
    )

    require(
        state["informative_outcomes"] == 4,
        "Expected 4 informative outcomes."
    )

    require(
        abs(
            state["success_rate"]
            - 0.5
        ) < 1e-9,
        "Unexpected success rate."
    )

    require(
        abs(
            state["failure_rate"]
            - 0.25
        ) < 1e-9,
        "Unexpected failure rate."
    )

    require(
        abs(
            state["partial_rate"]
            - 0.25
        ) < 1e-9,
        "Unexpected partial rate."
    )

    require(
        abs(
            state["learning_signal"]
            - 0.25
        ) < 1e-9,
        "Unexpected learning signal."
    )

    require(
        state["total_evidence"] == 5,
        "Expected five evidence records."
    )

    require(
        state["outcomes_with_evidence"] == 5,
        "Every test outcome should have evidence."
    )

    require(
        abs(
            state["evidence_coverage"]
            - 1.0
        ) < 1e-9,
        "Evidence coverage should be 1.0."
    )

    print(
        "TOTAL OUTCOMES:",
        state["total_outcomes"]
    )

    print(
        "SUCCESS:",
        state["successes"]
    )

    print(
        "FAILURE:",
        state["failures"]
    )

    print(
        "PARTIAL:",
        state["partial"]
    )

    print(
        "UNKNOWN:",
        state["unknown"]
    )

    print(
        "INFORMATIVE:",
        state["informative_outcomes"]
    )

    print(
        "SUCCESS RATE:",
        state["success_rate"]
    )

    print(
        "FAILURE RATE:",
        state["failure_rate"]
    )

    print(
        "PARTIAL RATE:",
        state["partial_rate"]
    )

    print(
        "LEARNING SIGNAL:",
        state["learning_signal"]
    )

    print(
        "EVIDENCE COVERAGE:",
        state["evidence_coverage"]
    )

    print("STATUS: PASS")


    # ================================================================
    # 9. PROVENANCE
    # ================================================================

    section(
        9,
        "LEARNING PROVENANCE"
    )

    provenance = (
        learning_service.get_provenance(
            canonical_memory_id=memory_id
        )
    )

    require(
        len(
            provenance["success"]["outcome_ids"]
        ) == 2,
        "Expected two success outcomes."
    )

    require(
        len(
            provenance["failure"]["outcome_ids"]
        ) == 1,
        "Expected one failure outcome."
    )

    require(
        len(
            provenance["partial"]["outcome_ids"]
        ) == 1,
        "Expected one partial outcome."
    )

    require(
        len(
            provenance["unknown"]["outcome_ids"]
        ) == 1,
        "Expected one unknown outcome."
    )

    require(
        len(
            provenance["success"]["evidence_ids"]
        ) == 2,
        "Expected two success evidence IDs."
    )

    require(
        len(
            provenance["failure"]["evidence_ids"]
        ) == 1,
        "Expected one failure evidence ID."
    )

    require(
        len(
            provenance["partial"]["evidence_ids"]
        ) == 1,
        "Expected one partial evidence ID."
    )

    require(
        len(
            provenance["unknown"]["evidence_ids"]
        ) == 1,
        "Expected one unknown evidence ID."
    )

    print(
        "SUCCESS OUTCOMES:",
        provenance["success"]["outcome_ids"]
    )

    print(
        "SUCCESS EVIDENCE:",
        provenance["success"]["evidence_ids"]
    )

    print(
        "FAILURE OUTCOMES:",
        provenance["failure"]["outcome_ids"]
    )

    print(
        "FAILURE EVIDENCE:",
        provenance["failure"]["evidence_ids"]
    )

    print(
        "PARTIAL OUTCOMES:",
        provenance["partial"]["outcome_ids"]
    )

    print(
        "PARTIAL EVIDENCE:",
        provenance["partial"]["evidence_ids"]
    )

    print(
        "UNKNOWN OUTCOMES:",
        provenance["unknown"]["outcome_ids"]
    )

    print(
        "UNKNOWN EVIDENCE:",
        provenance["unknown"]["evidence_ids"]
    )

    print("STATUS: PASS")


    # ================================================================
    # 10. CRITICAL TEST:
    # REPORTED LABEL MUST NOT AFFECT LEARNING
    # ================================================================

        # ================================================================
    # 10. CRITICAL TEST:
    # REPORTED LABEL MUST NOT AFFECT LEARNING
    #
    # This test intentionally creates disagreement:
    #
    # Reported outcome_type = SUCCESS
    # Evidence = FAILURE
    # C3 classification = FAILURE
    #
    # C4 MUST learn FAILURE because C3 is authoritative.
    # ================================================================

    section(
        10,
        "REPORTED LABEL CANNOT OVERRIDE C3 FOR LEARNING"
    )

    # ------------------------------------------------------------
    # Create a new experience using the SAME canonical memory.
    # ------------------------------------------------------------

    disagreement_experience = experience_service.create(
    bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Test whether reported success can override failure evidence.",
        action="Use a reported success label with failure evidence.",
        context="C4 authority test.",
    )

    # ------------------------------------------------------------
    # IMPORTANT:
    #
    # The caller reports SUCCESS.
    #
    # This is deliberately NOT the same as the normal
    # failure experience above.
    # ------------------------------------------------------------

    disagreement_outcome = outcome_service.create(
        experience_id=disagreement_experience["experience_id"],
        outcome_type="success",
        summary="The caller reported that the operation succeeded.",
        details="This reported label is intentionally unreliable.",
    )

    # ------------------------------------------------------------
    # Attach explicit FAILURE evidence.
    # ------------------------------------------------------------

    disagreement_evidence = repository.create_evidence(
    evidence_id=str(uuid.uuid4()),
    experience_id=disagreement_experience["experience_id"],
    outcome_id=disagreement_outcome["outcome_id"],
    evidence_type="text",
    content=(
        "The operation failed. "
        "The transaction was rolled back and the expected "
        "result was not produced."
    ),
    file_name=None,
    mime_type=None,
    storage_key=None,
    sha256=None,
    source_type="test",
    source_id="c4-reported-label-authority-test",
)

    # ------------------------------------------------------------
    # C3 must classify the evidence as FAILURE.
    # ------------------------------------------------------------

    disagreement_classification = (
        classification_service.classify(
            outcome_id=disagreement_outcome["outcome_id"]
        )
    )

    require(
        disagreement_classification["classification"]
        == "failure",
        (
            "C3 must classify the outcome as failure "
            "when the evidence is negative."
        ),
    )

    # ------------------------------------------------------------
    # Re-read the persisted outcome.
    # ------------------------------------------------------------

    persisted_disagreement_outcome = (
        outcome_service.get(
            disagreement_outcome["outcome_id"]
        )
    )

    require(
        persisted_disagreement_outcome["outcome_type"]
        == "success",
        (
            "The reported outcome_type must remain success "
            "because that is what the caller originally reported."
        ),
    )

    require(
        persisted_disagreement_outcome["classification"]
        == "failure",
        (
            "C3 classification must be failure even though "
            "the reported outcome_type is success."
        ),
    )

    # ------------------------------------------------------------
    # Refresh C4 from SOURCE DATA.
    # ------------------------------------------------------------

    updated_state = learning_service.refresh(
        canonical_memory_id=memory_id
    )

    # ------------------------------------------------------------
    # The original state was:
    #
    # SUCCESS  = 2
    # FAILURE  = 1
    # PARTIAL  = 1
    # UNKNOWN  = 1
    #
    # The new disagreement outcome is classified FAILURE.
    #
    # Therefore:
    #
    # SUCCESS  = 2
    # FAILURE  = 2
    # PARTIAL  = 1
    # UNKNOWN  = 1
    #
    # Informative = 2 + 2 + 1 = 5
    # Learning signal = (2 - 2) / 5 = 0
    # ------------------------------------------------------------

    require(
        updated_state["successes"] == 2,
        "C4 should still contain two successful outcomes.",
    )

    require(
        updated_state["failures"] == 2,
        (
            "C4 must learn the new outcome as FAILURE "
            "from the C3 classification."
        ),
    )

    require(
        updated_state["partial"] == 1,
        "C4 should contain one partial outcome.",
    )

    require(
        updated_state["unknown"] == 1,
        "C4 should contain one unknown outcome.",
    )

    require(
        updated_state["informative_outcomes"] == 5,
        "Expected five informative outcomes.",
    )

    require(
        abs(
            updated_state["learning_signal"] - 0.0
        ) < 1e-9,
        (
            "Expected learning signal to become 0.0 "
            "after two successes and two failures."
        ),
    )

    # ------------------------------------------------------------
    # Verify provenance.
    # The new outcome MUST appear under FAILURE, not SUCCESS.
    # ------------------------------------------------------------

    updated_provenance = (
        learning_service.get_provenance(
            canonical_memory_id=memory_id
        )
    )

    require(
        disagreement_outcome["outcome_id"]
        in updated_provenance["failure"]["outcome_ids"],
        (
            "The disagreement outcome must appear "
            "in C4 failure provenance."
        ),
    )

    require(
        disagreement_outcome["outcome_id"]
        not in updated_provenance["success"]["outcome_ids"],
        (
            "The disagreement outcome must NOT appear "
            "in C4 success provenance."
        ),
    )

    require(
        disagreement_evidence["evidence_id"]
        in updated_provenance["failure"]["evidence_ids"],
        (
            "Failure evidence must appear in "
            "C4 failure provenance."
        ),
    )
    require(
    disagreement_evidence["evidence_id"]
    not in updated_provenance["success"]["evidence_ids"],
    (
        "Failure evidence must NOT appear "
        "in C4 success provenance."
    ),
)

    print(
        "REPORTED OUTCOME:",
        persisted_disagreement_outcome["outcome_type"],
    )

    print(
        "C3 CLASSIFICATION:",
        persisted_disagreement_outcome["classification"],
    )

    print(
        "C4 SUCCESS COUNT:",
        updated_state["successes"],
    )

    print(
        "C4 FAILURE COUNT:",
        updated_state["failures"],
    )

    print(
        "C4 LEARNING SIGNAL:",
        updated_state["learning_signal"],
    )

    print(
        "C4 SOURCE: C3 classification",
    )

    print("STATUS: PASS")


    # ================================================================
    # 11. RESTART
    # ================================================================

    section(
        11,
        "RESTART / PERSISTENCE"
    )

    repository.close()
    canonical.close()

    repository = SQLiteLearningRepository(
        db_path=DB_PATH
    )

    learning_service = (
        MemoryLearningStateService(
            repository=repository
        )
    )

    persisted_state = (
        learning_service.get_state(
            canonical_memory_id=memory_id
        )
    )

    require(
    persisted_state["total_outcomes"] == 6,
    "Persisted total outcome count incorrect."
)
    require(
    persisted_state["successes"] == 2,
    "Persisted successes incorrect."
)
    require(
    persisted_state["failures"] == 2,
    "Persisted failures incorrect."
)

    require(
    persisted_state["partial"] == 1,
    "Persisted partial count incorrect."
)

    require(
    persisted_state["unknown"] == 1,
    "Persisted unknown count incorrect."
)

    require(
    persisted_state["informative_outcomes"] == 5,
    "Persisted informative outcome count incorrect."
)

    require(
    abs(
        persisted_state["success_rate"] - 0.4
    ) < 1e-9,
    "Persisted success rate incorrect."
)

    require(
    abs(
        persisted_state["failure_rate"] - 0.4
    ) < 1e-9,
    "Persisted failure rate incorrect."
)

    require(
    abs(
        persisted_state["partial_rate"] - 0.2
    ) < 1e-9,
    "Persisted partial rate incorrect."
)

    require(
    abs(
        persisted_state["learning_signal"] - 0.0
    ) < 1e-9,
    "Persisted learning signal incorrect."
)

    print(
        "MEMORY ID:",
        memory_id
    )

    print(
        "SUCCESS:",
        persisted_state["successes"]
    )

    print(
        "FAILURE:",
        persisted_state["failures"]
    )

    print(
        "PARTIAL:",
        persisted_state["partial"]
    )

    print(
        "UNKNOWN:",
        persisted_state["unknown"]
    )

    print(
        "LEARNING SIGNAL:",
        persisted_state["learning_signal"]
    )

    print("STATUS: PASS")


    # ================================================================
    # 12. FINAL LEARNING VIEW
    # ================================================================

    section(
        12,
        "COMPLETE C4 LEARNING VIEW"
    )

    final_view = (
        learning_service.get_learning_view(
            canonical_memory_id=memory_id
        )
    )

    require(
        final_view is not None,
        "Final learning view missing."
    )

    require(
        final_view["memory_id"] == memory_id,
        "Memory ID mismatch."
    )

    require(
    final_view[
        "learning_state"
    ]["total_outcomes"] == 6,
    "Final outcome count mismatch."
)
    require(
    final_view[
        "learning_state"
    ]["successes"] == 2,
    "Final success count mismatch."
)
    require(
    final_view[
        "learning_state"
    ]["failures"] == 2,
    "Final failure count mismatch."
)

    require(
        len(
            final_view[
                "provenance"
            ]["success"]["evidence_ids"]
        ) == 2,
        "Final success provenance mismatch."
    )

    print(
        "MEMORY ID:",
        final_view["memory_id"]
    )

    print(
        "LEARNING STATE:",
        final_view[
            "learning_state"
        ]
    )

    print(
        "PROVENANCE:",
        final_view[
            "provenance"
        ]
    )

    print("STATUS: PASS")


    print()
    print("=" * 90)
    print("C4 MEMORY LEARNING PASSED")
    print("=" * 90)


finally:

    try:
        repository.close()
    except Exception:
        pass

    try:
        canonical.close()
    except Exception:
        pass

    for path in [
        DB_PATH,
        CANONICAL_DB_PATH,
    ]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass