import os
import uuid


# ============================================================
# TEST DATABASE
# ============================================================

BANK_ID = (
    f"c5-closed-loop-"
    f"{uuid.uuid4().hex[:8]}"
)

DB_PATH = (
    f"test_c5_closed_loop_"
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

from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)

from app.services.closed_learning_loop_service import (
    ClosedLearningLoopService,
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
    print(f"[{number}] {title}")
    print("-" * 90)


def require(condition, message):

    if not condition:
        raise AssertionError(message)


# ============================================================
# DETERMINISTIC TEST AGENT
# ============================================================

def test_agent(context):

    query = context["query"]

    memory = context["memory"]

    decision = context["decision"]

    learning = context["learning"]

    memory_text = memory["text"]

    behavior = decision["behavior"]

    signal = learning[
        "state"
    ]["learning_signal"]

    if behavior == (
        ClosedLearningLoopService.PREFER
    ):

        return (
            "Based on the historical memory, "
            "the previously recorded approach is "
            "supported by successful outcomes. "
            f"Relevant memory: {memory_text} "
            f"Learning signal: {signal:.4f}. "
            f"Question: {query}"
        )

    if behavior == (
        ClosedLearningLoopService.CAUTIOUS
    ):

        return (
            "The historical memory has more "
            "unsuccessful than successful outcomes, "
            "so the previous approach should be "
            "treated cautiously rather than assumed "
            "to be reliable. "
            f"Relevant memory: {memory_text} "
            f"Learning signal: {signal:.4f}. "
            f"Question: {query}"
        )

    if behavior == (
        ClosedLearningLoopService.NEUTRAL
    ):

        return (
            "The historical evidence is mixed, "
            "so the previous approach should be "
            "considered without strong preference. "
            f"Relevant memory: {memory_text} "
            f"Learning signal: {signal:.4f}. "
            f"Question: {query}"
        )

    return (
        "There is not enough informative historical "
        "outcome data to rely strongly on this memory. "
        f"Relevant memory: {memory_text} "
        f"Question: {query}"
    )


# ============================================================
# CREATE EXPERIENCE + OUTCOME + EVIDENCE
# ============================================================

def create_outcome(
    experience_service,
    outcome_service,
    evidence_service,
    classifier,
    bank_id,
    memory_id,
    action,
    outcome_type,
    summary,
    evidence_text,
    source_id,
):

    experience = experience_service.create(
        bank_id=bank_id,
        canonical_memory_id=memory_id,
        task=(
            "Evaluate the historical concurrency "
            "resolution approach."
        ),
        action=action,
        context=(
            "C5 closed-loop integration test."
        ),
    )

    outcome = outcome_service.create(
        experience_id=(
            experience["experience_id"]
        ),
        outcome_type=outcome_type,
        summary=summary,
    )

    evidence = (
        evidence_service.create_text_evidence(
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
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print("C5 CLOSED LEARNING LOOP TEST")
    print("=" * 90)

    repository = None
    canonical = None

    try:

        # ====================================================
        # 1. CANONICAL MEMORY
        # ====================================================

        section(
            1,
            "CANONICAL MEMORY",
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
            f"BANK ID: {BANK_ID}"
        )

        print(
            f"MEMORY ID: {memory_id}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 2. EXISTING C1-C4 SERVICES
        # ====================================================

        section(
            2,
            "C1-C4 SERVICES",
        )

        repository = create_learning_repository()

        experience_service = (
            ExperienceService(
                repository=repository,
                canonical_memory_service=canonical,
            )
        )

        outcome_service = (
            OutcomeCaptureService(
                repository=repository
            )
        )

        evidence_service = (
            EvidenceService(
                repository=repository
            )
        )

        classifier = (
            OutcomeClassificationService(
                repository=repository
            )
        )

        learning_service = (
            MemoryLearningStateService(
                repository=repository
            )
        )

        closed_loop = (
            ClosedLearningLoopService(
                learning_service=learning_service,
                canonical_memory_service=canonical,
            )
        )

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

        print("STATUS: PASS")

        # ====================================================
        # 3. FIRST SUCCESS
        # ====================================================

        section(
            3,
            "FIRST HISTORICAL SUCCESS",
        )

        first = create_outcome(
            experience_service=experience_service,
            outcome_service=outcome_service,
            evidence_service=evidence_service,
            classifier=classifier,
            bank_id=BANK_ID,
            memory_id=memory_id,
            action=(
                "Use pessimistic database locking."
            ),
            outcome_type="success",
            summary=(
                "The locking strategy solved "
                "the concurrency issue."
            ),
            evidence_text=(
                "All integration tests passed."
            ),
            source_id=(
                "c5-first-success"
            ),
        )

        require(
            first["classification"][
                "classification"
            ] == "success",
            "First outcome was not classified as success."
        )

        state = learning_service.learn(
            memory_id
        )

        require(
            state["successes"] == 1,
            "Expected one success."
        )

        require(
            state["failures"] == 0,
            "Expected zero failures."
        )

        print(
            "C3 CLASSIFICATION: success"
        )

        print(
            f"C4 LEARNING SIGNAL: "
            f"{state['learning_signal']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 4. SECOND SUCCESS
        # ====================================================

        section(
            4,
            "SECOND HISTORICAL SUCCESS",
        )

        second = create_outcome(
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
            summary=(
                "The second concurrency test succeeded."
            ),
            evidence_text=(
                "Regression tests passed successfully."
            ),
            source_id=(
                "c5-second-success"
            ),
        )

        require(
            second["classification"][
                "classification"
            ] == "success",
            "Second outcome was not classified as success."
        )

        state = learning_service.learn(
            memory_id
        )

        require(
            state["successes"] == 2,
            "Expected two successes."
        )

        require(
            state["failures"] == 0,
            "Expected zero failures."
        )

        print(
            "C3 CLASSIFICATION: success"
        )

        print(
            f"C4 LEARNING SIGNAL: "
            f"{state['learning_signal']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 5. C5 FIRST FUTURE QUERY
        # ====================================================

        section(
            5,
            "C5 FUTURE QUERY — LEARNING-AWARE",
        )

        result_1 = closed_loop.run_turn(
            canonical_memory_id=memory_id,
            query=(
                "Which approach should be considered "
                "for the wallet concurrency problem?"
            ),
            answer_generator=test_agent,
            memory_text=memory_text,
        )

        require(
            result_1["behavior"]
            == ClosedLearningLoopService.PREFER,
            (
                "Two successful outcomes should "
                "produce PREFER behavior."
            ),
        )

        require(
            "historical memory"
            in result_1["answer"].lower(),
            "Answer did not use learning context."
        )

        print(
            f"BEHAVIOR: {result_1['behavior']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{result_1['learning_state']['learning_signal']}"
        )

        print(
            "ANSWER:"
        )

        print(
            result_1["answer"]
        )

        print("STATUS: PASS")

        # ====================================================
        # 6. NEW FAILURE
        # ====================================================

        section(
            6,
            "NEW FAILURE ENTERS THE LOOP",
        )

        third = create_outcome(
            experience_service=experience_service,
            outcome_service=outcome_service,
            evidence_service=evidence_service,
            classifier=classifier,
            bank_id=BANK_ID,
            memory_id=memory_id,
            action=(
                "Reuse pessimistic database locking "
                "in a different environment."
            ),
            outcome_type="failure",
            summary=(
                "The locking approach failed "
                "in the new environment."
            ),
            evidence_text=(
                "The concurrency test failed and "
                "the transaction was rolled back."
            ),
            source_id=(
                "c5-new-failure"
            ),
        )

        require(
            third["classification"][
                "classification"
            ] == "failure",
            "New failure was not classified as failure."
        )

        updated = (
            closed_loop.refresh_after_outcome(
                canonical_memory_id=memory_id
            )
        )

        updated_state = (
            updated["learning_state"]
        )

        require(
            updated_state["successes"] == 2,
            "Expected two successes after failure."
        )

        require(
            updated_state["failures"] == 1,
            "Expected one failure."
        )

        require(
            updated_state[
                "learning_signal"
            ] < state["learning_signal"],
            "Learning signal did not decrease."
        )

        print(
            "C3 CLASSIFICATION: failure"
        )

        print(
            f"C4 SUCCESS: "
            f"{updated_state['successes']}"
        )

        print(
            f"C4 FAILURE: "
            f"{updated_state['failures']}"
        )

        print(
            f"C4 NEW LEARNING SIGNAL: "
            f"{updated_state['learning_signal']}"
        )

        print(
            f"C5 NEW BEHAVIOR: "
            f"{updated['decision']['behavior']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 7. C5 FUTURE QUERY AFTER FAILURE
        # ====================================================

        section(
            7,
            "C5 FUTURE QUERY AFTER NEW FAILURE",
        )

        result_2 = closed_loop.run_turn(
            canonical_memory_id=memory_id,
            query=(
                "Should the historical concurrency "
                "approach be relied on?"
            ),
            answer_generator=test_agent,
            memory_text=memory_text,
        )

        require(
            result_2["behavior"]
            == ClosedLearningLoopService.PREFER,
            (
                "Two successes versus one failure "
                "should remain historically positive."
            ),
        )

        require(
            result_2["learning_state"][
                "successes"
            ] == 2,
            "Future query did not see two successes."
        )

        require(
            result_2["learning_state"][
                "failures"
            ] == 1,
            "Future query did not see the new failure."
        )

        require(
            result_2["learning_state"][
                "learning_signal"
            ] == (1.0 / 3.0),
            "Future query has incorrect learning signal."
        )

        print(
            f"BEHAVIOR: "
            f"{result_2['behavior']}"
        )

        print(
            f"SUCCESS RATE: "
            f"{result_2['learning_state']['success_rate']}"
        )

        print(
            f"FAILURE RATE: "
            f"{result_2['learning_state']['failure_rate']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{result_2['learning_state']['learning_signal']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 8. CONTRADICTORY HISTORY
        # ====================================================

        section(
            8,
            "CONTRADICTORY HISTORY",
        )

        fourth = create_outcome(
            experience_service=experience_service,
            outcome_service=outcome_service,
            evidence_service=evidence_service,
            classifier=classifier,
            bank_id=BANK_ID,
            memory_id=memory_id,
            action=(
                "Reuse pessimistic database locking "
                "again."
            ),
            outcome_type="failure",
            summary=(
                "The approach failed again."
            ),
            evidence_text=(
                "The transaction failed and "
                "the expected result was not produced."
            ),
            source_id=(
                "c5-second-failure"
            ),
        )

        require(
            fourth["classification"][
                "classification"
            ] == "failure",
            "Second failure was not classified correctly."
        )

        updated_2 = (
            closed_loop.refresh_after_outcome(
                canonical_memory_id=memory_id
            )
        )

        state_4 = updated_2[
            "learning_state"
        ]

        require(
            state_4["successes"] == 2,
            "Expected two successes."
        )

        require(
            state_4["failures"] == 2,
            "Expected two failures."
        )

        require(
            abs(
                state_4["learning_signal"]
            ) < 1e-9,
            (
                "Two successes and two failures "
                "should produce neutral signal."
            ),
        )

        require(
            updated_2["decision"][
                "behavior"
            ] == ClosedLearningLoopService.NEUTRAL,
            (
                "Balanced history should produce "
                "neutral behavior."
            ),
        )

        print(
            f"SUCCESS: {state_4['successes']}"
        )

        print(
            f"FAILURE: {state_4['failures']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{state_4['learning_signal']}"
        )

        print(
            f"BEHAVIOR: "
            f"{updated_2['decision']['behavior']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 9. FUTURE QUERY MUST NOW CHANGE BEHAVIOR
        # ====================================================

        section(
            9,
            "FUTURE QUERY AFTER BALANCING HISTORY",
        )

        result_3 = closed_loop.run_turn(
            canonical_memory_id=memory_id,
            query=(
                "What should the agent say about "
                "this historical approach now?"
            ),
            answer_generator=test_agent,
            memory_text=memory_text,
        )

        require(
            result_3["behavior"]
            == ClosedLearningLoopService.NEUTRAL,
            (
                "Future behavior did not change "
                "after history became balanced."
            ),
        )

        require(
            "mixed"
            in result_3["answer"].lower(),
            "Agent answer did not reflect neutral behavior."
        )

        print(
            f"BEHAVIOR: "
            f"{result_3['behavior']}"
        )

        print(
            "ANSWER:"
        )

        print(
            result_3["answer"]
        )

        print("STATUS: PASS")

        # ====================================================
        # 10. PROVENANCE
        # ====================================================

        section(
            10,
            "ANSWER → MEMORY → LEARNING → EVIDENCE",
        )

        explanation = closed_loop.explain(
            result_3
        )

        require(
            explanation["memory_id"]
            == memory_id,
            "Memory provenance is incorrect."
        )

        require(
            "provenance"
            in explanation,
            "Learning provenance missing."
        )

        require(
            len(
                explanation[
                    "provenance"
                ]["success"]["outcome_ids"]
            ) == 2,
            "Success provenance count incorrect."
        )

        require(
            len(
                explanation[
                    "provenance"
                ]["failure"]["outcome_ids"]
            ) == 2,
            "Failure provenance count incorrect."
        )

        require(
            len(
                explanation[
                    "provenance"
                ]["success"]["evidence_ids"]
            ) == 2,
            "Success evidence provenance incorrect."
        )

        require(
            len(
                explanation[
                    "provenance"
                ]["failure"]["evidence_ids"]
            ) == 2,
            "Failure evidence provenance incorrect."
        )

        print(
            "MEMORY ID:",
            explanation["memory_id"]
        )

        print(
            "BEHAVIOR:",
            explanation["behavior"]
        )

        print(
            "LEARNING SIGNAL:",
            explanation["learning_signal"]
        )

        print(
            "SUCCESS OUTCOMES:",
            explanation[
                "provenance"
            ]["success"]["outcome_ids"]
        )

        print(
            "FAILURE OUTCOMES:",
            explanation[
                "provenance"
            ]["failure"]["outcome_ids"]
        )

        print(
            "SUCCESS EVIDENCE:",
            explanation[
                "provenance"
            ]["success"]["evidence_ids"]
        )

        print(
            "FAILURE EVIDENCE:",
            explanation[
                "provenance"
            ]["failure"]["evidence_ids"]
        )

        print("STATUS: PASS")

        # ====================================================
        # 11. RESTART
        # ====================================================

        section(
            11,
            "RESTART / PERSISTENCE",
        )

        repository.close()

        repository = create_learning_repository()

        learning_service = (
            MemoryLearningStateService(
                repository=repository
            )
        )

        closed_loop = (
            ClosedLearningLoopService(
                learning_service=learning_service,
                canonical_memory_service=canonical,
            )
        )

        persisted_result = (
            closed_loop.run_turn(
                canonical_memory_id=memory_id,
                query=(
                    "What does the historical "
                    "record indicate?"
                ),
                answer_generator=test_agent,
                memory_text=memory_text,
            )
        )

        persisted_state = (
            persisted_result[
                "learning_state"
            ]
        )

        require(
            persisted_state["successes"] == 2,
            "Success count did not survive restart."
        )

        require(
            persisted_state["failures"] == 2,
            "Failure count did not survive restart."
        )

        require(
            abs(
                persisted_state[
                    "learning_signal"
                ]
            ) < 1e-9,
            "Learning signal did not survive restart."
        )

        require(
            persisted_result[
                "behavior"
            ] == ClosedLearningLoopService.NEUTRAL,
            "Behavior did not survive restart."
        )

        print(
            f"SUCCESS: "
            f"{persisted_state['successes']}"
        )

        print(
            f"FAILURE: "
            f"{persisted_state['failures']}"
        )

        print(
            f"LEARNING SIGNAL: "
            f"{persisted_state['learning_signal']}"
        )

        print(
            f"BEHAVIOR: "
            f"{persisted_result['behavior']}"
        )

        print("STATUS: PASS")

        # ====================================================
        # FINAL
        # ====================================================

        print()
        print("=" * 90)
        print("C5 CLOSED LEARNING LOOP PASSED")
        print("=" * 90)

    finally:

        try:
            if repository is not None:
                repository.close()
        except Exception:
            pass

        try:
            if canonical is not None:
                canonical.close()
        except Exception:
            pass

        try:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
        except Exception:
            pass


if __name__ == "__main__":
    main()