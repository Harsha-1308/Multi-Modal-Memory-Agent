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
from app.services.closed_learning_loop_service import (
    ClosedLearningLoopService,
)
from app.services.learning_feedback_service import (
    LearningFeedbackService,
)


DB_PATH = f"test_feedback_learning_{uuid.uuid4().hex[:8]}.db"
CANONICAL_DB_PATH = f"test_feedback_canonical_{uuid.uuid4().hex[:8]}.db"
BANK_ID = f"feedback-test-{uuid.uuid4().hex[:8]}"


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
print("D1 LEARNING FEEDBACK SERVICE — C2 → C3 → C4 → C5")
print("=" * 90)

repository = SQLiteLearningRepository(db_path=DB_PATH)
canonical = CanonicalMemoryService(db_path=CANONICAL_DB_PATH)

try:
    section(1, "INITIALIZE")

    canonical.register(
        bank_id=BANK_ID,
        text=(
            "Pessimistic database locking resolved the "
            "wallet concurrency problem."
        ),
    )

    memories = canonical.list_memories(bank_id=BANK_ID)

    require(
        len(memories) == 1,
        "Expected one canonical memory.",
    )

    memory_id = memories[0]["id"]

    experience_service = ExperienceService(
        repository=repository,
        canonical_memory_service=canonical,
    )

    outcome_service = OutcomeCaptureService(
        repository=repository,
    )

    classification_service = OutcomeClassificationService(
        repository=repository,
    )

    learning_service = MemoryLearningStateService(
        repository=repository,
    )

    evidence_service = EvidenceService(
        repository=repository,
    )

    closed_loop = ClosedLearningLoopService(
        learning_service=learning_service,
    )

    feedback = LearningFeedbackService(
        experience_service=experience_service,
        outcome_service=outcome_service,
        classification_service=classification_service,
        learning_service=learning_service,
        evidence_service=evidence_service,
        closed_loop_service=closed_loop,
    )

    print("Memory ID:", memory_id)
    print("Feedback service: READY")
    print("STATUS: PASS")

    section(2, "INITIAL EMPTY LEARNING STATE")

    initial = learning_service.learn(
        canonical_memory_id=memory_id,
    )

    require(initial["total_outcomes"] == 0, "Expected zero outcomes.")
    require(initial["informative_outcomes"] == 0, "Expected zero informative outcomes.")
    require(initial["learning_signal"] == 0.0, "Expected zero signal.")

    initial_decision = closed_loop.decide_behavior(initial)

    require(
        initial_decision["behavior"] == "insufficient",
        "Fresh memory should be insufficient.",
    )

    print("TOTAL OUTCOMES:", initial["total_outcomes"])
    print("BEHAVIOR:", initial_decision["behavior"])
    print("STATUS: PASS")

    section(3, "SUCCESS FEEDBACK")

    success = feedback.record_success(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Resolve concurrent wallet updates.",
        action="Apply pessimistic database locking.",
        context="Integration test environment.",
        outcome_summary="Locking solved the concurrency issue.",
        evidence=[
            {
                "evidence_type": "test_result",
                "content": "12 concurrency tests passed.",
                "source_type": "test_result",
                "source_id": "feedback-success-1",
            }
        ],
    )

    require(
        success["classification"]["classification"] == "success",
        "Success should classify as success.",
    )

    state = success["learning_state"]

    require(state["successes"] == 1, "Expected one success.")
    require(state["failures"] == 0, "Expected zero failures.")
    require(state["informative_outcomes"] == 1, "Expected one informative outcome.")
    require(abs(state["learning_signal"] - 1.0) < 1e-9, "Expected +1 learning signal.")
    require(
        success["decision"]["behavior"] == "prefer",
        "One fully evidenced success should produce PREFER.",
    )

    print("CLASSIFICATION:", success["classification"]["classification"])
    print("LEARNING SIGNAL:", state["learning_signal"])
    print("BEHAVIOR:", success["decision"]["behavior"])
    print("STATUS: PASS")

    section(4, "FAILURE FEEDBACK")

    failure = feedback.record_failure(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Resolve concurrent wallet updates.",
        action="Use application-level retries.",
        context="Integration test environment.",
        outcome_summary="Retry strategy did not resolve the issue.",
        evidence=[
            {
                "evidence_type": "test_result",
                "content": "3 concurrency tests failed.",
                "source_type": "test_result",
                "source_id": "feedback-failure-1",
            }
        ],
    )

    require(
        failure["classification"]["classification"] == "failure",
        "Failure should classify as failure.",
    )

    state = failure["learning_state"]

    require(state["successes"] == 1, "Expected one success.")
    require(state["failures"] == 1, "Expected one failure.")
    require(state["informative_outcomes"] == 2, "Expected two informative outcomes.")
    require(abs(state["learning_signal"] - 0.0) < 1e-9, "Expected neutral signal.")

    require(
        failure["decision"]["behavior"] == "neutral",
        "Balanced success/failure history should be NEUTRAL.",
    )

    print("CLASSIFICATION:", failure["classification"]["classification"])
    print("LEARNING SIGNAL:", state["learning_signal"])
    print("BEHAVIOR:", failure["decision"]["behavior"])
    print("STATUS: PASS")

    section(5, "PARTIAL + MULTI-EVIDENCE FEEDBACK")

    partial = feedback.record_feedback(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Run the locking strategy under mixed load.",
        action="Use locking plus retry handling.",
        context="Mixed regression environment.",
        outcome_type="success",
        outcome_summary="Some tests passed and some failed.",
        evidence=[
            {
                "evidence_type": "test_result",
                "content": "8 tests passed.",
                "source_type": "test_result",
                "source_id": "feedback-partial-positive",
            },
            {
                "evidence_type": "test_result",
                "content": "2 tests failed.",
                "source_type": "test_result",
                "source_id": "feedback-partial-negative",
            },
        ],
    )

    require(
        partial["classification"]["classification"] == "partial",
        "Mixed evidence should classify as partial.",
    )

    require(
        len(partial["evidence"]) == 2,
        "Expected two evidence records.",
    )

    state = partial["learning_state"]

    require(state["partial"] == 1, "Expected one partial outcome.")
    require(state["total_evidence"] == 4, "Expected four evidence records.")
    require(state["outcomes_with_evidence"] == 3, "Expected three outcomes with evidence.")
    require(abs(state["evidence_coverage"] - 1.0) < 1e-9, "Expected full evidence coverage.")

    print("CLASSIFICATION:", partial["classification"]["classification"])
    print("EVIDENCE COUNT:", len(partial["evidence"]))
    print("PARTIAL:", state["partial"])
    print("STATUS: PASS")

    section(6, "IMAGE-ONLY EVIDENCE → C3 UNKNOWN")

    unknown = feedback.record_feedback(
    bank_id=BANK_ID,
    canonical_memory_id=memory_id,
    task="Inspect visual diagnostic output.",
    action="Review the captured diagnostic image.",
    context="Visual debugging session.",
    outcome_type="success",
    outcome_summary="A diagnostic image was captured.",
    evidence=[
        {
            "evidence_type": "image",
            "file_name": "diagnostic.png",
            "mime_type": "image/png",
            "storage_key": f"feedback/{uuid.uuid4()}.png",
            "file_bytes": b"fake-image-bytes-for-test",
            "source_type": "user_upload",
            "source_id": "feedback-image-1",
        }
    ],
)
    require(
    unknown["outcome"]["outcome_type"] == "success",
    "C2 reported outcome should remain success.",
)

    require(
    unknown["classification"]["classification"] == "unknown",
    "Image-only evidence should classify as unknown.",
)

    state = unknown["learning_state"]

    require(
    state["unknown"] == 1,
    "Expected one unknown outcome.",
)

    require(
    state["informative_outcomes"] == 3,
    "UNKNOWN must not be informative.",
)

    print(
    "REPORTED:",
    unknown["outcome"]["outcome_type"],
)

    print(
    "C3 CLASSIFICATION:",
    unknown["classification"]["classification"],
)

    print(
    "INFORMATIVE OUTCOMES:",
    state["informative_outcomes"],
)

    print("STATUS: PASS")

    section(7, "REPORTED SUCCESS CANNOT OVERRIDE FAILURE EVIDENCE")

    disagreement = feedback.record_feedback(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Verify C3 authority.",
        action="Deliberately report success despite failure evidence.",
        context="Authority regression test.",
        outcome_type="success",
        outcome_summary="Caller says the operation succeeded.",
        evidence=[
            {
                "evidence_type": "text",
                "content": (
                    "The operation failed. The transaction was rolled back "
                    "and the expected result was not produced."
                ),
                "source_type": "test_result",
                "source_id": "feedback-authority-1",
            }
        ],
    )

    require(
        disagreement["outcome"]["outcome_type"] == "success",
        "Reported outcome type must remain success.",
    )

    require(
        disagreement["classification"]["classification"] == "failure",
        "C3 must classify the evidence as failure.",
    )

    state = disagreement["learning_state"]

    require(state["successes"] == 1, "Success count should remain one.")
    require(state["failures"] == 2, "C4 must learn the C3 failure.")
    require(state["partial"] == 1, "Partial count should remain one.")
    require(state["unknown"] == 1, "Unknown count should remain one.")
    require(state["informative_outcomes"] == 4, "Expected four informative outcomes.")
    require(abs(state["learning_signal"] - (-0.25)) < 1e-9, "Expected -0.25 signal.")

    provenance = disagreement["provenance"]

    require(
        disagreement["outcome"]["outcome_id"]
        in provenance["failure"]["outcome_ids"],
        "Disagreement outcome must be in failure provenance.",
    )

    require(
        disagreement["outcome"]["outcome_id"]
        not in provenance["success"]["outcome_ids"],
        "Disagreement outcome must not be in success provenance.",
    )

    require(
        disagreement["decision"]["behavior"] == "cautious",
        "Negative learning signal with more failures should be CAUTIOUS.",
    )

    print("REPORTED:", disagreement["outcome"]["outcome_type"])
    print("C3:", disagreement["classification"]["classification"])
    print("C4 FAILURES:", state["failures"])
    print("LEARNING SIGNAL:", state["learning_signal"])
    print("BEHAVIOR:", disagreement["decision"]["behavior"])
    print("STATUS: PASS")

    section(8, "PERSISTENCE / RESTART")

    repository.close()

    repository = SQLiteLearningRepository(db_path=DB_PATH)

    learning_service = MemoryLearningStateService(
        repository=repository,
    )

    persisted = learning_service.get_state(
        canonical_memory_id=memory_id,
    )

    require(persisted is not None, "Learning state did not persist.")
    require(persisted["successes"] == 1, "Persisted successes incorrect.")
    require(persisted["failures"] == 2, "Persisted failures incorrect.")
    require(persisted["partial"] == 1, "Persisted partial incorrect.")
    require(persisted["unknown"] == 1, "Persisted unknown incorrect.")
    require(
        abs(persisted["learning_signal"] - (-0.25)) < 1e-9,
        "Persisted learning signal incorrect.",
    )

    print("SUCCESS:", persisted["successes"])
    print("FAILURE:", persisted["failures"])
    print("PARTIAL:", persisted["partial"])
    print("UNKNOWN:", persisted["unknown"])
    print("LEARNING SIGNAL:", persisted["learning_signal"])
    print("STATUS: PASS")

    section(9, "FINAL PROVENANCE")

    final_provenance = learning_service.get_provenance(
        canonical_memory_id=memory_id,
    )

    require(
        len(final_provenance["success"]["outcome_ids"]) == 1,
        "Expected one success provenance entry.",
    )

    require(
        len(final_provenance["failure"]["outcome_ids"]) == 2,
        "Expected two failure provenance entries.",
    )

    require(
        len(final_provenance["partial"]["outcome_ids"]) == 1,
        "Expected one partial provenance entry.",
    )

    require(
        len(final_provenance["unknown"]["outcome_ids"]) == 1,
        "Expected one unknown provenance entry.",
    )

    print("SUCCESS OUTCOMES:", final_provenance["success"]["outcome_ids"])
    print("FAILURE OUTCOMES:", final_provenance["failure"]["outcome_ids"])
    print("PARTIAL OUTCOMES:", final_provenance["partial"]["outcome_ids"])
    print("UNKNOWN OUTCOMES:", final_provenance["unknown"]["outcome_ids"])
    print("STATUS: PASS")

    print()
    print("=" * 90)
    print("D1 LEARNING FEEDBACK SERVICE: PASSED")
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

    for path in (DB_PATH, CANONICAL_DB_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
