import os
import uuid
from app.core.config import settings

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

from app.services.evidence_service import (
    EvidenceService,
)

from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)

from app.services.closed_learning_loop_service import (
    ClosedLearningLoopService,
)

from app.services.learning_aware_groq_agent import (
    LearningAwareGroqAgent,
)


# ============================================================
# TEST DATABASES
# ============================================================

DB_PATH = (
    f"test_c5_groq_learning_"
    f"{uuid.uuid4().hex[:8]}.db"
)

CANONICAL_DB_PATH = (
    f"test_c5_groq_canonical_"
    f"{uuid.uuid4().hex[:8]}.db"
)

BANK_ID = (
    f"c5-groq-integration-"
    f"{uuid.uuid4().hex[:8]}"
)


MEMORY_TEXT = (
    "Pessimistic database locking resolved "
    "the wallet concurrency problem."
)


QUERY = (
    "Which approach should be considered "
    "for the wallet concurrency problem?"
)


# ============================================================
# HELPERS
# ============================================================

def section(number, title):
    print()
    print("=" * 90)
    print(f"[{number}] {title}")
    print("-" * 90)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def create_outcome(
    experience_service,
    outcome_service,
    evidence_service,
    classifier,
    bank_id,
    memory_id,
    action,
    outcome_type,
    evidence_text,
    source_id,
):
    experience = experience_service.create(
        bank_id=bank_id,
        canonical_memory_id=memory_id,
        task=(
            "Resolve the wallet concurrency problem."
        ),
        action=action,
        context=(
            "C5 real Groq learning integration test."
        ),
    )

    outcome = outcome_service.create(
        experience_id=(
            experience["experience_id"]
        ),
        outcome_type=outcome_type,
        summary=evidence_text,
    )

    evidence = evidence_service.create_text_evidence(
        experience_id=(
            experience["experience_id"]
        ),
        outcome_id=(
            outcome["outcome_id"]
        ),
        content=evidence_text,
        source_type="test_result",
        source_id=source_id,
    )

    classification = classifier.classify(
        outcome["outcome_id"]
    )

    return {
        "experience": experience,
        "outcome": outcome,
        "evidence": evidence,
        "classification": classification,
    }


# ============================================================
# START
# ============================================================

print()
print("=" * 90)
print("C5.1 REAL GROQ LEARNING-AWARE AGENT INTEGRATION")
print("=" * 90)


# ============================================================
# 0. GROQ CONFIGURATION
# ============================================================

section(
    0,
    "GROQ CONFIGURATION"
)

require(
    bool(settings.GROQ_API_KEY),
    (
        "GROQ_API_KEY is missing. "
        "Set it before running this test."
    ),
)

print(
    "GROQ API KEY: SET"
)

print(
    "MODEL:",
    os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-120b",
    ),
)

print("STATUS: PASS")


# ============================================================
# 1. SERVICES
# ============================================================

section(
    1,
    "INITIALIZE C1-C5 SERVICES"
)

repository = SQLiteLearningRepository(
    db_path=DB_PATH
)

canonical = CanonicalMemoryService(
    db_path=CANONICAL_DB_PATH
)

experience_service = ExperienceService(
    repository=repository,
    canonical_memory_service=canonical,
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

closed_loop = ClosedLearningLoopService(
    learning_service=learning_service,
    canonical_memory_service=canonical,
)

groq_agent = LearningAwareGroqAgent()


print(
    "Experience service: READY"
)

print(
    "Outcome service: READY"
)

print(
    "Evidence service: READY"
)

print(
    "Classification service: READY"
)

print(
    "Learning service: READY"
)

print(
    "Closed learning loop: READY"
)

print(
    "Real Groq agent: READY"
)

print("STATUS: PASS")


# ============================================================
# 2. CANONICAL MEMORY
# ============================================================

section(
    2,
    "CREATE CANONICAL MEMORY"
)

registered = canonical.register(
    bank_id=BANK_ID,
    text=MEMORY_TEXT,
)

require(
    registered,
    "Canonical memory registration failed."
)

memories = canonical.list_memories(
    bank_id=BANK_ID
)

require(
    len(memories) == 1,
    "Expected exactly one canonical memory."
)

memory_id = memories[0]["id"]

print(
    "BANK ID:",
    BANK_ID
)

print(
    "MEMORY ID:",
    memory_id
)

print(
    "MEMORY:",
    MEMORY_TEXT
)

print("STATUS: PASS")


# ============================================================
# 3. FIRST SUCCESS
# ============================================================

section(
    3,
    "HISTORICAL SUCCESS #1"
)

result_success_1 = create_outcome(
    experience_service=experience_service,
    outcome_service=outcome_service,
    evidence_service=evidence_service,
    classifier=classifier,
    bank_id=BANK_ID,
    memory_id=memory_id,
    action=(
        "Apply pessimistic database locking."
    ),
    outcome_type="success",
    evidence_text=(
        "12 concurrency tests passed."
    ),
    source_id="c5-groq-success-1",
)

require(
    result_success_1[
        "classification"
    ]["classification"] == "success",
    "First success was not classified as success.",
)

state = learning_service.learn(
    canonical_memory_id=memory_id
)

require(
    state["learning_signal"] == 1.0,
    "Expected learning signal 1.0.",
)

print(
    "CLASSIFICATION:",
    result_success_1[
        "classification"
    ]["classification"]
)

print(
    "LEARNING SIGNAL:",
    state["learning_signal"]
)

print("STATUS: PASS")


# ============================================================
# 4. SECOND SUCCESS
# ============================================================

section(
    4,
    "HISTORICAL SUCCESS #2"
)

result_success_2 = create_outcome(
    experience_service=experience_service,
    outcome_service=outcome_service,
    evidence_service=evidence_service,
    classifier=classifier,
    bank_id=BANK_ID,
    memory_id=memory_id,
    action=(
        "Reuse pessimistic database locking."
    ),
    outcome_type="success",
    evidence_text=(
        "Regression concurrency tests passed."
    ),
    source_id="c5-groq-success-2",
)

require(
    result_success_2[
        "classification"
    ]["classification"] == "success",
    "Second success was not classified as success.",
)

state = learning_service.learn(
    canonical_memory_id=memory_id
)

require(
    state["successes"] == 2,
    "Expected two successes.",
)

require(
    state["learning_signal"] == 1.0,
    "Expected learning signal 1.0.",
)

print(
    "SUCCESS COUNT:",
    state["successes"]
)

print(
    "FAILURE COUNT:",
    state["failures"]
)

print(
    "LEARNING SIGNAL:",
    state["learning_signal"]
)

print("STATUS: PASS")


# ============================================================
# 5. C5 DECISION
# ============================================================

section(
    5,
    "C5 LEARNING DECISION BEFORE GROQ"
)

context_before = (
    closed_loop.build_agent_context(
        canonical_memory_id=memory_id,
        query=QUERY,
        memory_text=MEMORY_TEXT,
    )
)

decision_before = (
    context_before["decision"]
)

require(
    decision_before["behavior"]
    == ClosedLearningLoopService.PREFER,
    "C5 should prefer the successful historical approach.",
)

print(
    "BEHAVIOR:",
    decision_before["behavior"]
)

print(
    "DECISION:",
    decision_before
)

print(
    "LEARNING SIGNAL:",
    context_before[
        "learning"
    ]["state"]["learning_signal"]
)

print("STATUS: PASS")


# ============================================================
# 6. REAL GROQ ANSWER — POSITIVE HISTORY
# ============================================================

section(
    6,
    "REAL GROQ ANSWER WITH POSITIVE HISTORY"
)

groq_positive_answer = (
    closed_loop.answer(
        canonical_memory_id=memory_id,
        query=QUERY,
        answer_generator=groq_agent.answer,
        memory_text=MEMORY_TEXT,
    )
)

require(
    isinstance(
        groq_positive_answer,
        dict,
    ),
    "C5 did not return an answer result.",
)

positive_answer = (
    groq_positive_answer["answer"]
)

require(
    positive_answer,
    "Groq returned an empty answer.",
)

require(
    groq_positive_answer[
        "behavior"
    ] == "prefer",
    "Expected PREFER behavior.",
)

print(
    "BEHAVIOR:",
    groq_positive_answer[
        "behavior"
    ]
)

print(
    "LEARNING SIGNAL:",
    groq_positive_answer[
        "learning_state"
    ]["learning_signal"]
)

print()
print("GROQ ANSWER:")
print("-" * 90)
print(positive_answer)
print("-" * 90)

print("STATUS: PASS")


# ============================================================
# 7. ADD FAILURE
# ============================================================

section(
    7,
    "NEW FAILURE ENTERS THE LEARNING LOOP"
)

result_failure_1 = create_outcome(
    experience_service=experience_service,
    outcome_service=outcome_service,
    evidence_service=evidence_service,
    classifier=classifier,
    bank_id=BANK_ID,
    memory_id=memory_id,
    action=(
        "Use pessimistic database locking again."
    ),
    outcome_type="failure",
    evidence_text=(
        "The locking implementation failed "
        "3 regression tests."
    ),
    source_id="c5-groq-failure-1",
)

require(
    result_failure_1[
        "classification"
    ]["classification"] == "failure",
    "Failure evidence was not classified as failure.",
)

state = learning_service.refresh(
    canonical_memory_id=memory_id
)

require(
    state["successes"] == 2,
    "Expected two successes.",
)

require(
    state["failures"] == 1,
    "Expected one failure.",
)

require(
    abs(
        state["learning_signal"]
        - (1.0 / 3.0)
    ) < 1e-9,
    "Unexpected learning signal after failure.",
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
    "LEARNING SIGNAL:",
    state["learning_signal"]
)

print("STATUS: PASS")


# ============================================================
# 8. GROQ ANSWER AFTER FAILURE
# ============================================================

section(
    8,
    "REAL GROQ ANSWER AFTER FAILURE"
)

groq_after_failure = (
    closed_loop.answer(
        canonical_memory_id=memory_id,
        query=QUERY,
        answer_generator=groq_agent.answer,
        memory_text=MEMORY_TEXT,
    )
)

require(
    groq_after_failure[
        "behavior"
    ] == "prefer",
    "2 successes vs 1 failure should still produce PREFER.",
)

print(
    "BEHAVIOR:",
    groq_after_failure[
        "behavior"
    ]
)

print(
    "SUCCESS RATE:",
    groq_after_failure[
        "learning_state"
    ]["success_rate"]
)

print(
    "FAILURE RATE:",
    groq_after_failure[
        "learning_state"
    ]["failure_rate"]
)

print(
    "LEARNING SIGNAL:",
    groq_after_failure[
        "learning_state"
    ]["learning_signal"]
)

print()
print("GROQ ANSWER:")
print("-" * 90)
print(
    groq_after_failure[
        "answer"
    ]
)
print("-" * 90)

print("STATUS: PASS")


# ============================================================
# 9. SECOND FAILURE
# ============================================================

section(
    9,
    "SECOND FAILURE — BALANCE THE HISTORY"
)

result_failure_2 = create_outcome(
    experience_service=experience_service,
    outcome_service=outcome_service,
    evidence_service=evidence_service,
    classifier=classifier,
    bank_id=BANK_ID,
    memory_id=memory_id,
    action=(
        "Use pessimistic database locking."
    ),
    outcome_type="failure",
    evidence_text=(
        "The implementation failed "
        "another concurrency regression suite."
    ),
    source_id="c5-groq-failure-2",
)

require(
    result_failure_2[
        "classification"
    ]["classification"] == "failure",
    "Second failure was not classified as failure.",
)

state = learning_service.refresh(
    canonical_memory_id=memory_id
)

require(
    state["successes"] == 2,
    "Expected two successes.",
)

require(
    state["failures"] == 2,
    "Expected two failures.",
)

require(
    state["learning_signal"] == 0.0,
    "Expected learning signal 0.0.",
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
    "LEARNING SIGNAL:",
    state["learning_signal"]
)

print("STATUS: PASS")


# ============================================================
# 10. C5 MUST BECOME NEUTRAL
# ============================================================

section(
    10,
    "C5 DECISION AFTER BALANCED HISTORY"
)

context_after_balance = (
    closed_loop.build_agent_context(
        canonical_memory_id=memory_id,
        query=QUERY,
        memory_text=MEMORY_TEXT,
    )
)

decision_after_balance = (
    context_after_balance[
        "decision"
    ]
)

require(
    decision_after_balance[
        "behavior"
    ] == ClosedLearningLoopService.NEUTRAL,
    (
        "Balanced success/failure history "
        "must produce NEUTRAL behavior."
    ),
)

print(
    "BEHAVIOR:",
    decision_after_balance[
        "behavior"
    ]
)

print(
    "LEARNING SIGNAL:",
    context_after_balance[
        "learning"
    ]["state"]["learning_signal"]
)

print("STATUS: PASS")


# ============================================================
# 11. REAL GROQ AFTER BALANCED HISTORY
# ============================================================

section(
    11,
    "REAL GROQ ANSWER WITH MIXED HISTORY"
)

groq_mixed_answer = (
    closed_loop.answer(
        canonical_memory_id=memory_id,
        query=QUERY,
        answer_generator=groq_agent.answer,
        memory_text=MEMORY_TEXT,
    )
)

require(
    groq_mixed_answer[
        "behavior"
    ] == "neutral",
    "Expected NEUTRAL C5 behavior.",
)

require(
    groq_mixed_answer[
        "learning_state"
    ]["learning_signal"] == 0.0,
    "Expected zero learning signal.",
)

mixed_answer = (
    groq_mixed_answer[
        "answer"
    ]
)

require(
    mixed_answer,
    "Groq returned an empty mixed-history answer.",
)

print(
    "BEHAVIOR:",
    groq_mixed_answer[
        "behavior"
    ]
)

print(
    "SUCCESS RATE:",
    groq_mixed_answer[
        "learning_state"
    ]["success_rate"]
)

print(
    "FAILURE RATE:",
    groq_mixed_answer[
        "learning_state"
    ]["failure_rate"]
)

print(
    "LEARNING SIGNAL:",
    groq_mixed_answer[
        "learning_state"
    ]["learning_signal"]
)

print()
print("GROQ ANSWER:")
print("-" * 90)
print(mixed_answer)
print("-" * 90)

print("STATUS: PASS")


# ============================================================
# 12. PROVENANCE
# ============================================================

section(
    12,
    "ANSWER → MEMORY → LEARNING → EVIDENCE"
)

provenance = (
    groq_mixed_answer[
        "provenance"
    ]
)

require(
    len(
        provenance[
            "success"
        ]["outcome_ids"]
    ) == 2,
    "Expected two success outcomes.",
)

require(
    len(
        provenance[
            "failure"
        ]["outcome_ids"]
    ) == 2,
    "Expected two failure outcomes.",
)

require(
    len(
        provenance[
            "success"
        ]["evidence_ids"]
    ) == 2,
    "Expected two success evidence records.",
)

require(
    len(
        provenance[
            "failure"
        ]["evidence_ids"]
    ) == 2,
    "Expected two failure evidence records.",
)

print(
    "MEMORY ID:",
    groq_mixed_answer[
        "memory_id"
    ]
)

print(
    "BEHAVIOR:",
    groq_mixed_answer[
        "behavior"
    ]
)

print(
    "SUCCESS OUTCOMES:",
    provenance[
        "success"
    ]["outcome_ids"]
)

print(
    "SUCCESS EVIDENCE:",
    provenance[
        "success"
    ]["evidence_ids"]
)

print(
    "FAILURE OUTCOMES:",
    provenance[
        "failure"
    ]["outcome_ids"]
)

print(
    "FAILURE EVIDENCE:",
    provenance[
        "failure"
    ]["evidence_ids"]
)

print("STATUS: PASS")


# ============================================================
# 13. RESTART / PERSISTENCE
# ============================================================

section(
    13,
    "RESTART / PERSISTENCE"
)

repository.close()
canonical.close()

repository = SQLiteLearningRepository(
    db_path=DB_PATH
)

learning_service = MemoryLearningStateService(
    repository=repository
)

closed_loop = ClosedLearningLoopService(
    learning_service=learning_service
)

persisted_state = (
    learning_service.get_state(
        canonical_memory_id=memory_id
    )
)

require(
    persisted_state is not None,
    "Learning state disappeared after restart.",
)

require(
    persisted_state[
        "successes"
    ] == 2,
    "Persisted success count is wrong.",
)

require(
    persisted_state[
        "failures"
    ] == 2,
    "Persisted failure count is wrong.",
)

require(
    persisted_state[
        "learning_signal"
    ] == 0.0,
    "Persisted learning signal is wrong.",
)

persisted_decision = (
    closed_loop.decide_behavior(
        persisted_state
    )
)

require(
    persisted_decision[
        "behavior"
    ] == "neutral",
    "Persisted C5 behavior is wrong.",
)

print(
    "PERSISTED SUCCESS:",
    persisted_state[
        "successes"
    ]
)

print(
    "PERSISTED FAILURE:",
    persisted_state[
        "failures"
    ]
)

print(
    "PERSISTED SIGNAL:",
    persisted_state[
        "learning_signal"
    ]
)

print(
    "PERSISTED BEHAVIOR:",
    persisted_decision[
        "behavior"
    ]
)

print("STATUS: PASS")


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 90)
print("C5.1 REAL GROQ LEARNING INTEGRATION PASSED")
print("=" * 90)
print()
print(
    "PROVEN:"
)
print(
    "1. C3 classified historical outcomes."
)
print(
    "2. C4 converted classifications into learning state."
)
print(
    "3. C5 converted learning state into behavior."
)
print(
    "4. Real Groq received the C5 context."
)
print(
    "5. Groq generated answers from that learning-aware context."
)
print(
    "6. New failures changed the learning state."
)
print(
    "7. Balanced history changed C5 from PREFER to NEUTRAL."
)
print(
    "8. Provenance survived through the answer."
)
print(
    "9. Learning state survived restart."
)
print()