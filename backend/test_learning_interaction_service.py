import uuid

from app.repositories.sqlite.learning_repository import (
    SQLiteLearningRepository,
)
from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.services.hindsight_canonical_resolver import (
    HindsightCanonicalResolver,
)
from app.services.retrieval_quality_gate import (
    RetrievalQualityGate,
)
from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)
from app.services.adaptive_memory_selector import (
    AdaptiveMemorySelector,
)
from app.services.closed_learning_loop_service import (
    ClosedLearningLoopService,
)
from app.services.learning_agent_service import (
    LearningAgentService,
)
from app.services.learning_feedback_service import (
    LearningFeedbackService,
)
from app.services.learning_aware_groq_agent import (
    LearningAwareGroqAgent,
)
from app.services.learning_interaction_service import (
    LearningInteractionService,
)
from app.services.experience_service import ExperienceService
from app.services.outcome_capture_service import OutcomeCaptureService
from app.services.outcome_classification_service import (
    OutcomeClassificationService,
)
from app.services.evidence_service import EvidenceService

# ======================================================================
# TEST CONFIGURATION
# ======================================================================

BANK_ID = f"d2-real-learning-{uuid.uuid4().hex[:10]}"

QUERY = (
    "Which approach should be used to resolve the "
    "wallet concurrency problem?"
)

MEMORY_A_TEXT = (
    "Application-level retries were attempted to resolve "
    "the wallet concurrency problem, but the approach failed."
)

MEMORY_B_TEXT = (
    "Pessimistic database locking resolved the wallet "
    "concurrency problem."
)


# ======================================================================
# OUTPUT HELPERS
# ======================================================================

def section(number, title):
    print()
    print("=" * 95)
    print(f"[{number}] {title}")
    print("-" * 95)


def passed():
    print("STATUS: PASS")


def get_memory_id(value):
    """
    Extract canonical memory ID from the representations
    used by the existing pipeline.
    """

    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, dict):
        for key in (
            "canonical_memory_id",
            "memory_id",
            "id",
        ):
            candidate = value.get(key)

            if isinstance(candidate, int):
                return candidate

    for key in (
        "canonical_memory_id",
        "memory_id",
        "id",
    ):
        candidate = getattr(
            value,
            key,
            None,
        )

        if isinstance(candidate, int):
            return candidate

    return None


def print_selection(result, label):
    print()
    print(label)

    selected = result.get(
        "selected_memory"
    )

    selected_id = get_memory_id(
        selected
    )

    print(
        "  Selected memory:",
        selected_id,
    )

    print(
        "  Behavior:",
        result.get("behavior"),
    )

    selection = result.get(
    "selection"
)
    if isinstance(selection, dict):

        selected = selection.get(
        "selected"
    ) or {}

        print(
        "Retrieval similarity:",
        selected.get(
            "retrieval_similarity"
        )
    )

        print(
        "Learning signal:",
        selected.get(
            "learning_signal"
        )
    )

        print(
        "Learning multiplier:",
        selected.get(
            "learning_multiplier"
        )
    )

        print(
        "Adjusted score:",
        selected.get(
            "adjusted_score"
        )
    )


# ======================================================================
# MAIN TEST
# ======================================================================

def main():

    print()
    print("=" * 95)
    print("D2 REAL MULTI-INTERACTION LEARNING EXPERIMENT")
    print("=" * 95)

    memory_service = None
    canonical_memory_service = None
    learning_service = None
    feedback_service = None
    groq_agent = None
    repository = None

    try:

        # ==============================================================
        # 1. INITIALIZE ALL SERVICES
        # ==============================================================

        section(
            1,
            "INITIALIZE ALL SERVICES",
        )
        repository = SQLiteLearningRepository(
    db_path=f"d2_learning_{uuid.uuid4().hex[:8]}.db"
)

        memory_service = MemoryService()

        canonical_memory_service = (
            CanonicalMemoryService()
        )

        learning_service = (
    MemoryLearningStateService(
        repository=repository
    )
)

        resolver = HindsightCanonicalResolver(
            canonical_memory_service=(
                canonical_memory_service
            )
        )

        quality_gate = (
            RetrievalQualityGate()
        )

        closed_loop = (
            ClosedLearningLoopService(
                learning_service=learning_service,
            )
        )

        selector = (
            AdaptiveMemorySelector(
                learning_service=learning_service,
                closed_loop_service=closed_loop,
            )
        )

        experience_service = ExperienceService(
    repository=repository,
    canonical_memory_service=canonical_memory_service,
)
        outcome_service = OutcomeCaptureService(
    repository=repository
)

        classification_service = (
    OutcomeClassificationService(
        repository=repository
    )
)

        evidence_service = EvidenceService(
    repository=repository
)

        feedback_service = (
    LearningFeedbackService(
        experience_service=experience_service,
        outcome_service=outcome_service,
        classification_service=classification_service,
        learning_service=learning_service,
        evidence_service=evidence_service,
        closed_loop_service=closed_loop,
    )
)

        groq_agent = (
            LearningAwareGroqAgent()
        )

        learning_agent = (
            LearningAgentService(
                memory_service=memory_service,
                resolver=resolver,
                selector=selector,
                closed_loop=closed_loop,
                quality_gate=quality_gate,
                answer_generator=groq_agent,
            )
        )

        interaction_service = (
            LearningInteractionService(
                learning_agent=learning_agent,
                feedback_service=feedback_service,
                answer_generator=groq_agent,
            )
        )

        print(
            "MemoryService: READY"
        )

        print(
            "CanonicalMemoryService: READY"
        )

        print(
            "MemoryLearningStateService: READY"
        )

        print(
            "HindsightCanonicalResolver: READY"
        )

        print(
            "RetrievalQualityGate: READY"
        )

        print(
            "ClosedLearningLoopService: READY"
        )

        print(
            "AdaptiveMemorySelector: READY"
        )

        print(
            "LearningFeedbackService: READY"
        )

        print(
            "LearningAwareGroqAgent: READY"
        )

        print(
            "LearningAgentService: READY"
        )

        print(
            "LearningInteractionService: READY"
        )

        print(
            "BANK ID:",
            BANK_ID,
        )

        passed()

        # ==============================================================
        # 2. CREATE REAL HINDSIGHT BANK
        # ==============================================================

        section(
            2,
            "CREATE REAL HINDSIGHT BANK",
        )

        memory_service.create_project_bank(
            bank_id=BANK_ID,
            project_name=(
                "D2 Real Learning Experiment"
            ),
            project_description=(
                "Controlled experiment proving that "
                "historical interaction outcomes change "
                "future memory selection."
            ),
        )

        print(
            "HINDSIGHT BANK CREATED"
        )

        passed()

        # ==============================================================
        # 3. CREATE CANONICAL MEMORIES
        # ==============================================================

        section(
            3,
            "CREATE CANONICAL MEMORIES",
        )

        canonical_memory_service.register(
            BANK_ID,
            MEMORY_A_TEXT,
        )

        canonical_memory_service.register(
            BANK_ID,
            MEMORY_B_TEXT,
        )

        canonical_memories = (
            canonical_memory_service.list_memories(
                bank_id=BANK_ID
            )
        )

        if len(canonical_memories) != 2:
            raise AssertionError(
                "Expected exactly 2 canonical memories, "
                f"got {len(canonical_memories)}"
            )

        memory_by_text = {
            memory["original_text"]: memory
            for memory in canonical_memories
        }

        if MEMORY_A_TEXT not in memory_by_text:
            raise AssertionError(
                "Memory A missing from canonical registry"
            )

        if MEMORY_B_TEXT not in memory_by_text:
            raise AssertionError(
                "Memory B missing from canonical registry"
            )

        memory_a_id = (
            memory_by_text[
                MEMORY_A_TEXT
            ]["id"]
        )

        memory_b_id = (
            memory_by_text[
                MEMORY_B_TEXT
            ]["id"]
        )

        print(
            "MEMORY A ID:",
            memory_a_id,
        )

        print(
            "MEMORY B ID:",
            memory_b_id,
        )

        passed()

        # ==============================================================
        # 4. STORE BOTH MEMORIES IN HINDSIGHT
        # ==============================================================

        section(
            4,
            "STORE MEMORIES IN REAL HINDSIGHT",
        )

        memory_service.retain(
            bank_id=BANK_ID,
            content=MEMORY_A_TEXT,
        )

        memory_service.retain(
            bank_id=BANK_ID,
            content=MEMORY_B_TEXT,
        )

        print(
            "HINDSIGHT MEMORY A: STORED"
        )

        print(
            "HINDSIGHT MEMORY B: STORED"
        )

        passed()

        # ==============================================================
# 5. INITIALIZE C4 LEARNING STATE
# ==============================================================
        section(
    5,
    "INITIALIZE C4 LEARNING STATE",
)

# C5 requires a persisted C4 state even when
# the memory has never been evaluated before.
#
# learn() creates/refreshes the state with:
#   total_outcomes = 0
#   informative_outcomes = 0
#   learning_signal = 0.0
#
# This gives C5 a valid neutral starting point.

        learning_service.learn(
    canonical_memory_id=memory_a_id
)

        learning_service.learn(
    canonical_memory_id=memory_b_id
)

        state_a = learning_service.get_state(
    memory_a_id
)

        state_b = learning_service.get_state(
    memory_b_id
)

        print(
    "MEMORY A STATE:",
    state_a,
)

        print(
    "MEMORY B STATE:",
    state_b,
)

        if state_a is None:
            raise AssertionError(
        "Memory A C4 learning state was not initialized."
    )
        if state_b is None:
            raise AssertionError(
        "Memory B C4 learning state was not initialized."
    )
        if state_a["total_outcomes"] != 0:
            raise AssertionError(
        "Memory A must start with zero outcomes."
    )

        if state_b["total_outcomes"] != 0:
            raise AssertionError(
        "Memory B must start with zero outcomes."
    )

        if state_a["learning_signal"] != 0.0:
            raise AssertionError(
        "Memory A must start with learning signal 0.0."
    )

        if state_b["learning_signal"] != 0.0:
            raise AssertionError(
        "Memory B must start with learning signal 0.0."
    )

        passed()
        # ==============================================================
        # 6. INTERACTION 1
        # ==============================================================

        section(
            6,
            "INTERACTION 1 — BEFORE LEARNING",
        )
        print()
        print("=" * 80)
        print("DEBUG: RAW HINDSIGHT RETRIEVAL")
        print("-" * 80)

        raw_results = memory_service.recall(
    bank_id=BANK_ID,
    query=QUERY,
)

        print("RAW RESULT COUNT:", len(raw_results))

        for i, item in enumerate(raw_results, 1):
            print()
            print("RESULT", i)
            print("TEXT:", getattr(item, "text", None))
            print("TYPE:", getattr(item, "type", None))
            print("SIMILARITY:", getattr(item, "similarity", None))
            print("SCORES:", getattr(item, "scores", None))
            print("SEMANTIC_SIMILARITY:", getattr(item, "semantic_similarity", None))

        print("=" * 80)
                 

        first = (
            interaction_service.interact(
                bank_id=BANK_ID,
                query=QUERY,
            )
        )

        print(
            "ANSWER:"
        )

        print(
            first["answer"]
        )

        print_selection(
            first,
            "INITIAL SELECTION",
        )

        first_selected_id = (
            get_memory_id(
                first["selected_memory"]
            )
        )

        if first_selected_id not in {
            memory_a_id,
            memory_b_id,
        }:
            raise AssertionError(
                "Initial selection is not one "
                "of the two canonical memories"
            )

        print()
        print(
            "INITIAL SELECTED MEMORY:",
            first_selected_id,
        )

        passed()

        # ==============================================================
        # 7. RECORD FIVE REAL FAILURE EXPERIENCES
        # ==============================================================

        section(
            7,
            "RECORD FIVE FAILURE EXPERIENCES",
        )

        selected_text = (
            MEMORY_A_TEXT
            if first_selected_id == memory_a_id
            else MEMORY_B_TEXT
        )

        for attempt in range(
            1,
            6,
        ):

            evidence = [
    {
        "evidence_type": "text",
        "content": (
            "The selected approach did not resolve "
            "the wallet concurrency problem."
        ),
        "file_name": None,
        "mime_type": None,
        "storage_key": (
            "d2/feedback/"
            f"{uuid.uuid4().hex}.txt"
        ),
        "source_type": "test_result",
        "source_id": (
            f"d2-failure-"
            f"{uuid.uuid4().hex}"
        ),
    }
]
            feedback = feedback_service.record_feedback(
    bank_id=BANK_ID,
    canonical_memory_id=first_selected_id,
    task=QUERY,
    action=first["answer"],
    context=(
        f"D2 controlled multi-interaction experiment. "
        f"Attempt {attempt}. "
        f"Selected memory: {selected_text}"
    ),
    outcome_type="failure",
    outcome_summary=(
        f"Controlled failure experiment #{attempt}: "
        f"the selected approach failed."
    ),
    evidence=evidence,
)
            classification_result = feedback.get("classification")
            print(
    f"FAILURE {attempt}: "
    f"classification={classification_result}"
)
            if not isinstance(classification_result, dict):
                raise AssertionError(
        "D1 feedback did not return the C3 classification result."
    )
            classification = classification_result.get("classification")
            if classification != "failure":
                raise AssertionError(
        "Expected C3 classification "
        "to be failure, "
        f"got {classification!r}"
    )

        passed()

        # ==============================================================
        # 8. VERIFY C4 LEARNING STATE
        # ==============================================================

        section(
            8,
            "VERIFY C4 LEARNING STATE AFTER FIVE FAILURES",
        )

        learned_state = (
            learning_service.get_state(
                first_selected_id
            )
        )

        if learned_state is None:
            raise AssertionError(
                "Learning state was not created"
            )

        print(
            "LEARNED STATE:",
            learned_state,
        )

        if learned_state["total_outcomes"] != 5:
            raise AssertionError(
                "Expected 5 total outcomes"
            )

        if learned_state["failures"] != 5:
            raise AssertionError(
                "Expected 5 failures"
            )

        if learned_state[
            "informative_outcomes"
        ] != 5:
            raise AssertionError(
                "Expected 5 informative outcomes"
            )

        if learned_state[
            "learning_signal"
        ] != -1.0:
            raise AssertionError(
                "Five failures should produce "
                "learning signal -1.0"
            )

        passed()

        # ==============================================================
        # 9. VERIFY C5 BEHAVIOR
        # ==============================================================

        section(
            9,
            "VERIFY C5 UPDATED BEHAVIOR",
        )

        behavior_result = closed_loop.decide_behavior(
    learned_state
)

        print(
    "LEARNING SIGNAL:",
    learned_state[
        "learning_signal"
    ],
)

        print(
    "C5 BEHAVIOR:",
    behavior_result,
)

        if not isinstance(behavior_result, dict):
            raise AssertionError(
        "C5 behavior result must be a dictionary."
    )

        behavior_after_failure = behavior_result.get(
    "behavior"
)

        if behavior_after_failure != "cautious":
            raise AssertionError(
        "Five failures must produce "
        f"CAUTIOUS behavior, got "
        f"{behavior_after_failure!r}"
    )


        passed()

        # ==============================================================
        # 10. VERIFY ALTERNATIVE MEMORY REMAINS UNLEARNED
        # ==============================================================

        section(
            10,
            "VERIFY ALTERNATIVE MEMORY STATE",
        )

        alternative_id = (
            memory_b_id
            if first_selected_id == memory_a_id
            else memory_a_id
        )

        alternative_state = (
            learning_service.get_state(
                alternative_id
            )
        )

        print(
            "ALTERNATIVE MEMORY ID:",
            alternative_id,
        )

        print(
            "ALTERNATIVE STATE:",
            alternative_state,
        )

        if alternative_state is not None:

            if alternative_state[
                "total_outcomes"
            ] != 0:

                raise AssertionError(
                    "Alternative memory was "
                    "incorrectly modified"
                )

        passed()

        # ==============================================================
        # 11. INTERACTION 2
        # ==============================================================

        section(
            11,
            "INTERACTION 2 — AFTER LEARNING",
        )

        second = (
            interaction_service.interact(
                bank_id=BANK_ID,
                query=QUERY,
            )
        )

        print(
            "ANSWER:"
        )

        print(
            second["answer"]
        )

        print_selection(
            second,
            "POST-LEARNING SELECTION",
        )

        second_selected_id = (
            get_memory_id(
                second["selected_memory"]
            )
        )

        print()
        print(
            "FIRST SELECTION:",
            first_selected_id,
        )

        print(
            "SECOND SELECTION:",
            second_selected_id,
        )

        passed()

        # ==============================================================
        # 12. PROVE C6 ADAPTATION
        # ==============================================================

        section(
            12,
            "PROVE C6 CHANGED FUTURE SELECTION",
        )

        if (
            second_selected_id
            == first_selected_id
        ):
            raise AssertionError(
                "C6 did not change the selected "
                "memory after five failures"
            )

        if second_selected_id not in {
            memory_a_id,
            memory_b_id,
        }:
            raise AssertionError(
                "Second selection is not canonical"
            )

        print(
            "BEFORE LEARNING:",
            first_selected_id,
        )

        print(
            "AFTER LEARNING:",
            second_selected_id,
        )

        print()
        print(
            "C6 ADAPTATION CONFIRMED:"
        )

        print(
            "The memory with five recorded "
            "failures was no longer selected."
        )

        passed()

        # ==============================================================
        # 13. VERIFY PERSISTENCE
        # ==============================================================

        section(
            13,
            "VERIFY LEARNING PERSISTENCE",
        )

        persisted_state = (
            learning_service.get_state(
                first_selected_id
            )
        )

        if persisted_state is None:
            raise AssertionError(
                "Persisted state missing"
            )

        print(
            "PERSISTED STATE:",
            persisted_state,
        )

        if persisted_state[
            "failures"
        ] != 5:
            raise AssertionError(
                "Persisted failure count incorrect"
            )

        if persisted_state[
            "learning_signal"
        ] != -1.0:
            raise AssertionError(
                "Persisted learning signal incorrect"
            )

        passed()

        # ==============================================================
        # 14. FINAL PROOF
        # ==============================================================

        section(
            14,
            "D2 CLOSED-LOOP PROOF",
        )

        print(
            "INTERACTION 1"
        )

        print(
            "  Selected memory:",
            first_selected_id,
        )

        print(
            "  Behavior:",
            first["behavior"],
        )

        print()

        print(
            "LEARNING"
        )

        print(
            "  Failures:",
            persisted_state[
                "failures"
            ],
        )

        print(
            "  Learning signal:",
            persisted_state[
                "learning_signal"
            ],
        )

        print(
            "  Updated behavior:",
            behavior_after_failure,
        )

        print()

        print(
            "INTERACTION 2"
        )

        print(
            "  Selected memory:",
            second_selected_id,
        )

        print(
            "  Behavior:",
            second["behavior"],
        )

        print()

        print(
            "D2 COMPONENT PROOF"
        )

        print(
            "  Hindsight bank                  PASS"
        )

        print(
            "  Canonical memory registry       PASS"
        )

        print(
            "  Hindsight retrieval             PASS"
        )

        print(
            "  Canonical resolution            PASS"
        )

        print(
            "  Retrieval quality gate          PASS"
        )

        print(
            "  C6 adaptive selection           PASS"
        )

        print(
            "  C5 learning behavior            PASS"
        )

        print(
            "  Real Groq answer                PASS"
        )

        print(
            "  D1 feedback                     PASS"
        )

        print(
            "  C3 classification               PASS"
        )

        print(
            "  C4 learning update              PASS"
        )

        print(
            "  Future selection                PASS"
        )

        print(
            "  Persistence                     PASS"
        )

        print()
        print("=" * 95)
        print(
            "D2 REAL MULTI-INTERACTION "
            "LEARNING: PASSED"
        )
        print("=" * 95)

    except Exception as exc:

        print()
        print("=" * 95)
        print(
            "D2 REAL MULTI-INTERACTION "
            "LEARNING: FAILED"
        )
        print("=" * 95)

        print(
            type(exc).__name__
        )

        print(
            str(exc)
        )

        raise

    finally:

        print()
        print("=" * 95)
        print("CLEANUP")
        print("=" * 95)

        for name, service in (
            (
                "MemoryService",
                memory_service,
            ),
            (
                "CanonicalMemoryService",
                canonical_memory_service,
            ),
            (
                "MemoryLearningStateService",
                learning_service,
            ),
            (
                "LearningFeedbackService",
                feedback_service,
            ),
            (
                "LearningAwareGroqAgent",
                groq_agent,
            ),
        ):

            if service is None:
                continue

            try:

                close = getattr(
                    service,
                    "close",
                    None,
                )

                if callable(close):
                    close()

                print(
                    f"{name}: CLOSED"
                )

            except Exception as exc:

                print(
                    f"{name} close warning:",
                    repr(exc),
                )
        
        if repository is not None:
            try:
                repository.close()
                print("LearningRepository: CLOSED")
            except Exception as exc:
                print(
            "LearningRepository close warning:",
            repr(exc),
        )


if __name__ == "__main__":
    main()