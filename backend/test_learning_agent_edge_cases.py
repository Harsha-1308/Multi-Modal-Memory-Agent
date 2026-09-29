import uuid

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)

from app.services.adaptive_memory_selector import (
    AdaptiveMemorySelector,
)


DB_PATH = (
    f"test_edge_canonical_{uuid.uuid4().hex[:8]}.db"
)

BANK_ID = (
    f"edge-{uuid.uuid4().hex[:8]}"
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
print("LEARNING AGENT EDGE CASE TEST")
print("=" * 90)

canonical = CanonicalMemoryService(
    db_path=DB_PATH
)

try:

    # ========================================================
    # 1. EMPTY C6
    # ========================================================

    section(1, "EMPTY CANDIDATE LIST")

    selector = AdaptiveMemorySelector(
        learning_service=None,
        closed_loop_service=None,
    )

    try:
        selector.select([])
    except ValueError:
        print(
            "Empty candidate list correctly rejected."
        )
    else:
        raise AssertionError(
            "C6 accepted an empty candidate list."
        )

    print("STATUS: PASS")

    # ========================================================
    # 2. CANONICAL DUPLICATE
    # ========================================================

    section(
        2,
        "EXACT CANONICAL DUPLICATE",
    )

    text = (
        "Pessimistic database locking resolved "
        "the wallet concurrency problem."
    )

    first = canonical.register(
        BANK_ID,
        text,
    )

    second = canonical.register(
        BANK_ID,
        text,
    )

    require(
        first is True,
        "First registration should succeed.",
    )

    require(
        second is False,
        "Exact duplicate should be rejected.",
    )

    memories = canonical.list_memories(
        bank_id=BANK_ID
    )

    require(
        len(memories) == 1,
        "Duplicate canonical memory was inserted.",
    )

    print("STATUS: PASS")

    # ========================================================
    # 3. INVALID C6 CANDIDATE
    # ========================================================

    section(
        3,
        "MALFORMED C6 CANDIDATE",
    )

    # This must fail loudly rather than silently selecting
    # nonsense.

    class MinimalLearning:

        def get_state(
            self,
            canonical_memory_id,
        ):
            return None

    selector = AdaptiveMemorySelector(
        learning_service=MinimalLearning(),
        closed_loop_service=None,
    )

    try:

        selector.select(
            [
                {
                    "text": "memory without ID",
                    "retrieval_similarity": 0.8,
                }
            ]
        )

    except (KeyError, TypeError, ValueError):
        print(
            "Malformed candidate correctly rejected."
        )

    else:
        raise AssertionError(
            "Malformed candidate was silently accepted."
        )

    print("STATUS: PASS")

    # ========================================================
    # 4. SIMILARITY CLAMPING
    # ========================================================

    section(
        4,
        "RETRIEVAL SIMILARITY SAFETY",
    )

    candidate = {
        "canonical_memory_id": 123,
        "text": "test memory",
        "retrieval_similarity": 99.0,
    }

    result = selector.score_candidate(
        candidate
    )

    require(
        result[
            "retrieval_similarity"
        ] == 1.0,
        "Similarity was not clamped to 1.0.",
    )

    candidate_negative = {
        "canonical_memory_id": 124,
        "text": "test memory",
        "retrieval_similarity": -50.0,
    }

    result_negative = selector.score_candidate(
        candidate_negative
    )

    require(
        result_negative[
            "retrieval_similarity"
        ] == 0.0,
        "Negative similarity was not clamped to 0.0.",
    )

    print("STATUS: PASS")

    # ========================================================
    # 5. MISSING LEARNING STATE
    # ========================================================

    section(
        5,
        "MISSING LEARNING STATE",
    )

    result = selector.score_candidate(
        {
            "canonical_memory_id": 999,
            "text": "unknown memory",
            "retrieval_similarity": 0.7,
        }
    )

    require(
        result[
            "learning_signal"
        ] == 0.0,
        "Missing state should have neutral signal.",
    )

    require(
        result[
            "learning_multiplier"
        ] == 1.0,
        "Missing state should not change retrieval.",
    )

    require(
        result[
            "behavior"
        ] == "insufficient",
        "Missing state should be insufficient.",
    )

    print("STATUS: PASS")

    # ========================================================
    # 6. NEUTRAL HISTORY
    # ========================================================

    section(
        6,
        "NEUTRAL LEARNING",
    )

    class NeutralLearning:

        def get_state(
            self,
            canonical_memory_id,
        ):
            return {
                "learning_signal": 0.0,
                "informative_outcomes": 10,
                "evidence_coverage": 1.0,
            }

    neutral_selector = AdaptiveMemorySelector(
        learning_service=NeutralLearning(),
        closed_loop_service=None,
    )

    neutral_result = (
        neutral_selector.score_candidate(
            {
                "canonical_memory_id": 1,
                "text": "neutral",
                "retrieval_similarity": 0.8,
            }
        )
    )

    require(
        neutral_result[
            "learning_multiplier"
        ] == 1.0,
        "Neutral learning changed selection score.",
    )

    require(
        neutral_result[
            "adjusted_score"
        ] == 0.8,
        "Neutral learning changed retrieval score.",
    )

    print("STATUS: PASS")

    # ========================================================
    # FINAL
    # ========================================================

    section(
        7,
        "EDGE CASE TEST PASSED",
    )

    print(
        "EMPTY INPUT: PASS"
    )

    print(
        "DUPLICATE MEMORY: PASS"
    )

    print(
        "MALFORMED CANDIDATE: PASS"
    )

    print(
        "SIMILARITY SAFETY: PASS"
    )

    print(
        "MISSING LEARNING STATE: PASS"
    )

    print(
        "NEUTRAL LEARNING: PASS"
    )

    print()
    print(
        "LEARNING AGENT EDGE CASES: PASSED"
    )

finally:

    try:
        canonical.close()
    except Exception:
        pass