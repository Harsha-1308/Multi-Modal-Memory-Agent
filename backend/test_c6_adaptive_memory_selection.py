import os
import uuid

from app.repositories.sqlite.learning_repository import SQLiteLearningRepository
from app.services.canonical_memory_service import CanonicalMemoryService
from app.services.experience_service import ExperienceService
from app.services.outcome_capture_service import OutcomeCaptureService
from app.services.outcome_classification_service import OutcomeClassificationService
from app.services.memory_learning_state_service import MemoryLearningStateService
from app.services.closed_learning_loop_service import ClosedLearningLoopService

from app.services.adaptive_memory_selector import AdaptiveMemorySelector


DB_PATH = f"test_c6_learning_{uuid.uuid4().hex[:8]}.db"
CANONICAL_DB_PATH = f"test_c6_canonical_{uuid.uuid4().hex[:8]}.db"
BANK_ID = f"c6-adaptive-{uuid.uuid4().hex[:8]}"


def section(number, title):
    print()
    print("=" * 90)
    print(f"[{number}] {title}")
    print("-" * 90)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def create_result(
    experience_service,
    outcome_service,
    classification_service,
    repository,
    memory_id,
    action,
    outcome_type,
    evidence_text,
):
    experience = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Resolve the wallet concurrency problem.",
        action=action,
        context="C6 adaptive selection test.",
    )

    outcome = outcome_service.create(
        experience_id=experience["experience_id"],
        outcome_type=outcome_type,
        summary=evidence_text,
    )

    evidence = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=experience["experience_id"],
        outcome_id=outcome["outcome_id"],
        evidence_type="test_result",
        content=evidence_text,
        file_name=None,
        mime_type=None,
        storage_key=None,
        sha256=None,
        source_type="test_result",
        source_id="c6-adaptive-selection",
    )

    classified = classification_service.classify(
        outcome["outcome_id"]
    )

    expected = outcome_type
    require(
        classified["classification"] == expected,
        f"Expected {expected}, got {classified['classification']}",
    )

    return {
        "experience": experience,
        "outcome": outcome,
        "evidence": evidence,
        "classification": classified,
    }


print()
print("=" * 90)
print("C6 ADAPTIVE MEMORY SELECTION / LEARNING TEST")
print("=" * 90)

repository = SQLiteLearningRepository(db_path=DB_PATH)
canonical = CanonicalMemoryService(db_path=CANONICAL_DB_PATH)

try:
    section(1, "CREATE TWO CANONICAL APPROACH MEMORIES")

    memory_a_text = (
        "Pessimistic database locking resolved the wallet concurrency problem."
    )
    memory_b_text = (
        "Optimistic concurrency control resolved the wallet concurrency problem."
    )

    require(
        canonical.register(BANK_ID, memory_a_text),
        "Memory A registration failed.",
    )
    require(
        canonical.register(BANK_ID, memory_b_text),
        "Memory B registration failed.",
    )

    memories = canonical.list_memories(bank_id=BANK_ID)
    require(len(memories) == 2, "Expected two canonical memories.")

    memory_a_id = memories[0]["id"]
    memory_b_id = memories[1]["id"]

    print("MEMORY A:", memory_a_id)
    print("MEMORY B:", memory_b_id)
    print("STATUS: PASS")

    section(2, "INITIALIZE C1-C6 SERVICES")

    experience_service = ExperienceService(
        repository=repository,
        canonical_memory_service=canonical,
    )
    outcome_service = OutcomeCaptureService(repository=repository)
    classification_service = OutcomeClassificationService(repository=repository)
    learning_service = MemoryLearningStateService(repository=repository)
    closed_loop = ClosedLearningLoopService(
        learning_service=learning_service,
        canonical_memory_service=canonical,
    )
    selector = AdaptiveMemorySelector(
        learning_service=learning_service,
        closed_loop_service=closed_loop,
    )

    print("Experience service: READY")
    print("Outcome service: READY")
    print("Classification service: READY")
    print("Learning service: READY")
    print("Closed learning loop: READY")
    print("Adaptive selector: READY")
    print("STATUS: PASS")

    candidates = [
        {
            "canonical_memory_id": memory_a_id,
            "text": memory_a_text,
            "retrieval_similarity": 0.82,
        },
        {
            "canonical_memory_id": memory_b_id,
            "text": memory_b_text,
            "retrieval_similarity": 0.78,
        },
    ]

    section(3, "BASELINE — RETRIEVAL ONLY")

    baseline = selector.select(candidates)
    require(
        baseline["selected"]["canonical_memory_id"] == memory_a_id,
        "Baseline should select the higher-relevance memory A.",
    )
    require(
        baseline["selected"]["learning_multiplier"] == 1.0,
        "Without learning, multiplier must be 1.0.",
    )

    print("SELECTED:", baseline["selected"]["canonical_memory_id"])
    print("ADJUSTED SCORE:", baseline["selected"]["adjusted_score"])
    print("STATUS: PASS")

    section(4, "LEARN FAILURE HISTORY FOR MEMORY A")

    for index in range(5):
        create_result(
            experience_service,
            outcome_service,
            classification_service,
            repository,
            memory_a_id,
            "Use pessimistic database locking.",
            "failure",
            f"Locking failed in regression run {index + 1}.",
        )

    state_a = learning_service.refresh(memory_a_id)
    require(state_a["failures"] == 5, "Memory A should have five failures.")
    require(state_a["successes"] == 0, "Memory A should have zero successes.")
    require(abs(state_a["learning_signal"] + 1.0) < 1e-9, "Memory A signal should be -1.")
    require(abs(state_a["evidence_coverage"] - 1.0) < 1e-9, "Memory A evidence coverage should be 1.")

    after_failure = selector.select(candidates)
    require(
        after_failure["selected"]["canonical_memory_id"] == memory_b_id,
        "Learning should move selection away from repeatedly failing memory A.",
    )
    require(
        after_failure["selected"]["canonical_memory_id"] != baseline["selected"]["canonical_memory_id"],
        "Selection did not change after learning failure history.",
    )

    scored_a = next(x for x in after_failure["ranked_candidates"] if x["canonical_memory_id"] == memory_a_id)
    require(
        scored_a["learning_multiplier"] == 0.0,
        "Five fully evidenced failures should produce zero multiplier under this C6 policy.",
    )

    print("MEMORY A SIGNAL:", state_a["learning_signal"])
    print("MEMORY A BEHAVIOR:", closed_loop.decide_behavior(state_a)["behavior"])
    print("NEW SELECTED MEMORY:", after_failure["selected"]["canonical_memory_id"])
    print("STATUS: PASS")

    section(5, "LEARN SUCCESS HISTORY FOR MEMORY B")

    for index in range(5):
        create_result(
            experience_service,
            outcome_service,
            classification_service,
            repository,
            memory_b_id,
            "Use optimistic concurrency control.",
            "success",
            f"Optimistic concurrency control passed regression run {index + 1}.",
        )

    state_b = learning_service.refresh(memory_b_id)
    require(state_b["successes"] == 5, "Memory B should have five successes.")
    require(state_b["failures"] == 0, "Memory B should have zero failures.")
    require(abs(state_b["learning_signal"] - 1.0) < 1e-9, "Memory B signal should be +1.")
    require(abs(state_b["evidence_coverage"] - 1.0) < 1e-9, "Memory B evidence coverage should be 1.")

    after_success = selector.select(candidates)
    require(
        after_success["selected"]["canonical_memory_id"] == memory_b_id,
        "Memory B should remain selected with strong successful history.",
    )

    scored_b = next(x for x in after_success["ranked_candidates"] if x["canonical_memory_id"] == memory_b_id)
    require(
        scored_b["learning_multiplier"] == 2.0,
        "Five fully evidenced successes should produce multiplier 2.0.",
    )

    print("MEMORY B SIGNAL:", state_b["learning_signal"])
    print("MEMORY B BEHAVIOR:", closed_loop.decide_behavior(state_b)["behavior"])
    print("MEMORY B MULTIPLIER:", scored_b["learning_multiplier"])
    print("SELECTED MEMORY:", after_success["selected"]["canonical_memory_id"])
    print("STATUS: PASS")

    section(6, "NEW FAILURES CHANGE FUTURE SELECTION")

    for index in range(5):
        create_result(
            experience_service,
            outcome_service,
            classification_service,
            repository,
            memory_b_id,
            "Use optimistic concurrency control.",
            "failure",
            f"Optimistic concurrency control failed regression run {index + 1}.",
        )

    state_b_balanced = learning_service.refresh(memory_b_id)
    require(state_b_balanced["successes"] == 5, "Memory B should still have five successes.")
    require(state_b_balanced["failures"] == 5, "Memory B should now have five failures.")
    require(abs(state_b_balanced["learning_signal"] - 0.0) < 1e-9, "Memory B signal should become neutral.")

    balanced = selector.select(candidates)
    selected_id = balanced["selected"]["canonical_memory_id"]

    require(
        selected_id == memory_b_id,
        "With A strongly negative and B neutral, B should remain selected.",
    )

    print("MEMORY B SUCCESS:", state_b_balanced["successes"])
    print("MEMORY B FAILURE:", state_b_balanced["failures"])
    print("MEMORY B SIGNAL:", state_b_balanced["learning_signal"])
    print("MEMORY B BEHAVIOR:", closed_loop.decide_behavior(state_b_balanced)["behavior"])
    print("SELECTED MEMORY:", selected_id)
    print("STATUS: PASS")

    section(7, "RECOVERY — MEMORY A LEARNS FROM NEW SUCCESS")

    for index in range(5):
        create_result(
            experience_service,
            outcome_service,
            classification_service,
            repository,
            memory_a_id,
            "Use pessimistic database locking.",
            "success",
            f"Locking passed recovery regression run {index + 1}.",
        )

    state_a_recovered = learning_service.refresh(memory_a_id)
    require(state_a_recovered["successes"] == 5, "Memory A should have five successes after recovery.")
    require(state_a_recovered["failures"] == 5, "Memory A should retain five historical failures.")
    require(abs(state_a_recovered["learning_signal"] - 0.0) < 1e-9, "Memory A should become neutral after balanced history.")

    recovered = selector.select(candidates)
    require(
        recovered["selected"]["canonical_memory_id"] == memory_a_id,
        "When both memories are neutral, higher retrieval relevance A should win again.",
    )

    print("MEMORY A SUCCESS:", state_a_recovered["successes"])
    print("MEMORY A FAILURE:", state_a_recovered["failures"])
    print("MEMORY A SIGNAL:", state_a_recovered["learning_signal"])
    print("FINAL SELECTED MEMORY:", recovered["selected"]["canonical_memory_id"])
    print("STATUS: PASS")

    section(8, "PERSISTENCE")

    repository.close()
    canonical.close()

    repository = SQLiteLearningRepository(db_path=DB_PATH)
    learning_service = MemoryLearningStateService(repository=repository)
    closed_loop = ClosedLearningLoopService(learning_service=learning_service)
    selector = AdaptiveMemorySelector(
        learning_service=learning_service,
        closed_loop_service=closed_loop,
    )

    persisted_a = learning_service.get_state(memory_a_id)
    persisted_b = learning_service.get_state(memory_b_id)

    require(persisted_a is not None, "Memory A learning state did not persist.")
    require(persisted_b is not None, "Memory B learning state did not persist.")
    require(persisted_a["successes"] == 5, "Persisted A successes incorrect.")
    require(persisted_a["failures"] == 5, "Persisted A failures incorrect.")
    require(persisted_b["successes"] == 5, "Persisted B successes incorrect.")
    require(persisted_b["failures"] == 5, "Persisted B failures incorrect.")

    persisted_selection = selector.select(candidates)
    require(
        persisted_selection["selected"]["canonical_memory_id"] == memory_a_id,
        "Selection changed after restart despite persisted learning state.",
    )

    print("PERSISTED A SIGNAL:", persisted_a["learning_signal"])
    print("PERSISTED B SIGNAL:", persisted_b["learning_signal"])
    print("PERSISTED SELECTED MEMORY:", persisted_selection["selected"]["canonical_memory_id"])
    print("STATUS: PASS")

    print()
    print("=" * 90)
    print("C6 ADAPTIVE MEMORY SELECTION PASSED")
    print("=" * 90)
    print()
    print("PROVEN:")
    print("1. Retrieval relevance selects a candidate when no learning exists.")
    print("2. Repeated evidenced failures reduce that memory's future selection score.")
    print("3. Repeated evidenced successes increase that memory's future selection score.")
    print("4. New outcomes change future candidate selection without changing stored memory text.")
    print("5. Balanced history returns the candidate to neutral learning influence.")
    print("6. Learning survives restart and still affects selection.")

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
