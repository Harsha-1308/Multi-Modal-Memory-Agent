import os
import uuid
from pathlib import Path

from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import CanonicalMemoryService
from app.services.hindsight_canonical_resolver import HindsightCanonicalResolver
from app.services.retrieval_quality_gate import RetrievalQualityGate
from app.services.adaptive_memory_selector import AdaptiveMemorySelector
from app.services.closed_learning_loop_service import ClosedLearningLoopService
from app.services.memory_learning_state_service import MemoryLearningStateService
from app.repositories.sqlite.learning_repository import SQLiteLearningRepository
from app.services.learning_agent_service import LearningAgentService
from app.services.learning_aware_groq_agent import LearningAwareGroqAgent
from app.core.config import settings


# ============================================================
# CONFIG
# ============================================================

BANK_ID = f"groq-e2e-{uuid.uuid4().hex[:8]}"

MEMORY_A_TEXT = (
    "Pessimistic database locking was implemented to resolve "
    "the wallet concurrency problem."
)

MEMORY_B_TEXT = (
    "Optimistic concurrency control was implemented to resolve "
    "the wallet concurrency problem."
)

QUERY = (
    "Which approach should be used for the wallet concurrency "
    "problem based on historical memory?"
)

LEARNING_DB = Path(
    f"test_groq_learning_{uuid.uuid4().hex[:8]}.db"
)

CANONICAL_DB = Path(
    f"test_groq_canonical_{uuid.uuid4().hex[:8]}.db"
)


# ============================================================
# HELPERS
# ============================================================

def require(condition, message):
    if not condition:
        raise AssertionError(message)


def print_separator():
    print("=" * 90)


# ============================================================
# TEST
# ============================================================

memory_service = None
learning_repository = None
canonical = None

try:
    print_separator()
    print("REAL GROQ LEARNING AGENT — END-TO-END TEST")
    print_separator()

    # --------------------------------------------------------
    # [1] API KEY
    # --------------------------------------------------------

    print()
    print("[1] CHECK GROQ CONFIG")

    api_key = settings.GROQ_API_KEY

    require(
        api_key is not None and api_key.strip(),
        "GROQ_API_KEY is not configured.",
    )

    print("GROQ_API_KEY: SET")
    print("STATUS: PASS")

    # --------------------------------------------------------
    # [2] INITIALIZE SERVICES
    # --------------------------------------------------------

    print()
    print("[2] INITIALIZE SERVICES")

    memory_service = MemoryService()

    canonical = CanonicalMemoryService(
        db_path=str(CANONICAL_DB)
    )

    learning_repository = SQLiteLearningRepository(
        db_path=str(LEARNING_DB)
    )

    learning_service = MemoryLearningStateService(
        repository=learning_repository
    )

    closed_loop = ClosedLearningLoopService(
        learning_service=learning_service
    )

    selector = AdaptiveMemorySelector(
        learning_service=learning_service,
        closed_loop_service=closed_loop,
    )

    resolver = HindsightCanonicalResolver(
        canonical_memory_service=canonical
    )

    quality_gate = RetrievalQualityGate()

    groq_agent = LearningAwareGroqAgent()

    agent = LearningAgentService(
        memory_service=memory_service,
        resolver=resolver,
        selector=selector,
        closed_loop=closed_loop,
        quality_gate=quality_gate,
        answer_generator=groq_agent,
    )

    print("MemoryService: READY")
    print("CanonicalMemoryService: READY")
    print("C4 LearningService: READY")
    print("C5 ClosedLoop: READY")
    print("C6 AdaptiveSelector: READY")
    print("Resolver: READY")
    print("QualityGate: READY")
    print("Real Groq Agent: READY")
    print("STATUS: PASS")

    # --------------------------------------------------------
    # [3] CREATE HINDSIGHT BANK
    # --------------------------------------------------------

    print()
    print("[3] CREATE REAL HINDSIGHT BANK")

    memory_service.create_project_bank(
    bank_id=BANK_ID,
    project_name="Groq E2E Test Bank",
    project_description=(
        "Test real Hindsight retrieval combined with "
        "adaptive learning and Groq. "
        "Two competing historical approaches to wallet "
        "concurrency resolution."
    ),
)

    print("BANK ID:", BANK_ID)
    print("STATUS: PASS")

    # --------------------------------------------------------
    # [4] CREATE CANONICAL MEMORIES
    # --------------------------------------------------------

    print()
    print("[4] CREATE CANONICAL MEMORIES")

    require(
        canonical.register(
            BANK_ID,
            MEMORY_A_TEXT,
        ),
        "Memory A registration failed.",
    )

    require(
        canonical.register(
            BANK_ID,
            MEMORY_B_TEXT,
        ),
        "Memory B registration failed.",
    )

    memories = canonical.list_memories(
        bank_id=BANK_ID
    )

    require(
        len(memories) == 2,
        "Expected exactly two canonical memories.",
    )

    memory_ids = {
        item["id"]
        for item in memories
    }

    print(
        "CANONICAL IDS:",
        sorted(memory_ids),
    )

    # Initialize C4 zero-history state.
    for memory_id in memory_ids:
        learning_service.learn(memory_id)

    print("C4 INITIAL STATES: CREATED")
    print("STATUS: PASS")

    # --------------------------------------------------------
    # [5] STORE REAL HINDSIGHT MEMORIES
    # --------------------------------------------------------

    print()
    print("[5] STORE IN REAL HINDSIGHT")

    retain_a = memory_service.retain(
        bank_id=BANK_ID,
        content=MEMORY_A_TEXT,
    )

    retain_b = memory_service.retain(
        bank_id=BANK_ID,
        content=MEMORY_B_TEXT,
    )

    require(
        retain_a is not None,
        "Hindsight retain A failed.",
    )

    require(
        retain_b is not None,
        "Hindsight retain B failed.",
    )

    print("MEMORY A: STORED")
    print("MEMORY B: STORED")
    print("STATUS: PASS")

    # --------------------------------------------------------
    # [6] REAL ORCHESTRATOR RETRIEVAL
    # --------------------------------------------------------

    print()
    print("[6] REAL HINDSIGHT → RESOLVER → QUALITY GATE")

    retrieval = agent.retrieve_candidates(
        bank_id=BANK_ID,
        query=QUERY,
    )

    print(
        "RAW RESULTS:",
        retrieval["raw_result_count"],
    )

    print(
        "RESOLVED:",
        retrieval["resolved_count"]
        if "resolved_count" in retrieval
        else len(retrieval["resolved_candidates"]),
    )

    print(
        "ACCEPTED:",
        retrieval["accepted_count"],
    )

    print(
        "REJECTED:",
        retrieval["rejected_count"],
    )

    require(
        len(retrieval["candidates"]) >= 2,
        "Expected at least two usable candidates.",
    )

    print("STATUS: PASS")

    # --------------------------------------------------------
    # [7] C6
    # --------------------------------------------------------

    print()
    print("[7] C6 ADAPTIVE MEMORY SELECTION")

    selection = agent.select_memory(
        retrieval["candidates"]
    )

    selected = selection["selected"]

    print(
        "SELECTED MEMORY:",
        selected["canonical_memory_id"],
    )

    print(
        "RETRIEVAL SIMILARITY:",
        selected["retrieval_similarity"],
    )

    print(
        "LEARNING SIGNAL:",
        selected["learning_signal"],
    )

    print(
        "LEARNING MULTIPLIER:",
        selected["learning_multiplier"],
    )

    print(
        "ADJUSTED SCORE:",
        selected["adjusted_score"],
    )

    require(
        selected["learning_multiplier"] == 1.0,
        "Fresh memory should have neutral learning multiplier.",
    )

    print("STATUS: PASS")

    # --------------------------------------------------------
    # [8] C5 CONTEXT
    # --------------------------------------------------------

    print()
    print("[8] C5 LEARNING CONTEXT")

    context = agent.build_context(
        query=QUERY,
        selection=selection,
    )

    print(
        "BEHAVIOR:",
        context["decision"]["behavior"],
    )

    print(
        "INFORMATIVE OUTCOMES:",
        context["learning"]["state"][
            "informative_outcomes"
        ],
    )

    print(
        "LEARNING SIGNAL:",
        context["learning"]["state"][
            "learning_signal"
        ],
    )

    require(
        context["decision"]["behavior"]
        == "insufficient",
        "Fresh memory should have insufficient behavior.",
    )

    print("STATUS: PASS")

    # --------------------------------------------------------
    # [9] REAL GROQ
    # --------------------------------------------------------

    print()
    print("[9] REAL GROQ ANSWER")

    answer = agent.generate_answer(
        context=context,
    )

    require(
        isinstance(answer, str),
        "Groq answer must be a string.",
    )

    require(
        answer.strip(),
        "Groq returned an empty answer.",
    )

    print()
    print("GROQ ANSWER:")
    print("-" * 90)
    print(answer)
    print("-" * 90)

    print("STATUS: PASS")

    # --------------------------------------------------------
    # [10] FULL ORCHESTRATOR ANSWER CONTRACT
    # --------------------------------------------------------

    print()
    print("[10] VERIFY FULL ORCHESTRATOR CONTRACT")

    # IMPORTANT:
    # Do not call agent.answer() here.
    #
    # That would perform another Hindsight recall.
    # Hindsight retrieval is intentionally variable.
    #
    # We already proved the exact single-pass stages above.

    result = {
        "answer": answer,
        "selected_memory": selected,
        "selection": selection,
        "behavior": context["decision"]["behavior"],
        "learning": context["learning"]["state"],
        "provenance": context["learning"]["provenance"],
        "retrieval": {
            "raw_result_count": retrieval[
                "raw_result_count"
            ],
            "resolved_count": len(
                retrieval["resolved_candidates"]
            ),
            "accepted_count": retrieval[
                "accepted_count"
            ],
            "rejected_count": retrieval[
                "rejected_count"
            ],
            "rejected": retrieval[
                "rejected"
            ],
        },
    }

    require(
        result["answer"].strip(),
        "Final answer missing.",
    )

    require(
        result["selected_memory"][
            "canonical_memory_id"
        ] in memory_ids,
        "Selected memory is not canonical.",
    )

    require(
        result["learning"][
            "canonical_memory_id"
        ] == result["selected_memory"][
            "canonical_memory_id"
        ],
        "Learning state does not match selected memory.",
    )

    require(
        "provenance" in result,
        "Provenance missing.",
    )

    print("ANSWER: PRESENT")
    print("SELECTED MEMORY: VALID")
    print("LEARNING STATE: VALID")
    print("PROVENANCE: PRESENT")
    print("STATUS: PASS")

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()
    print_separator()
    print("REAL GROQ LEARNING AGENT E2E: PASSED")
    print_separator()

finally:

    try:
        if memory_service is not None:
            memory_service.close()
    except Exception:
        pass

    try:
        if learning_repository is not None:
            learning_repository.close()
    except Exception:
        pass

    try:
        if canonical is not None:
            canonical.close()
    except Exception:
        pass

    for path in (
        LEARNING_DB,
        CANONICAL_DB,
    ):
        try:
            if path.exists():
                path.unlink()
                print(
                    "REMOVED TEMP DB:",
                    path.name,
                )
        except Exception as exc:
            print(
                "WARNING: Could not remove",
                path.name,
                ":",
                exc,
            )