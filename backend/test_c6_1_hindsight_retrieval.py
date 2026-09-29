import os
import uuid
import shutil

from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import CanonicalMemoryService


# ============================================================
# TEST IDENTIFIERS
# ============================================================

BANK_ID = f"c6-1-retrieval-{uuid.uuid4().hex[:8]}"

CANONICAL_DB_PATH = (
    f"test_c6_1_canonical_{uuid.uuid4().hex[:8]}.db"
)

MEMORY_A = (
    "Pessimistic database locking resolved the "
    "wallet concurrency problem."
)

MEMORY_B = (
    "Optimistic concurrency control resolved the "
    "wallet concurrency problem."
)

QUERY = (
    "What approach should I use for the wallet "
    "concurrency problem?"
)


# ============================================================
# HELPERS
# ============================================================

def section(number, title):
    print()
    print("=" * 90)
    print(f"[{number}] {title}")
    print("-" * 90)


def get_results(response):
    """
    Extract Hindsight recall results regardless of whether
    the response is an object or dictionary.
    """

    results = getattr(response, "results", None)

    if results is None and isinstance(response, dict):
        results = response.get("results")

    return results or []


def get_text(item):
    if isinstance(item, dict):
        return item.get("text")

    return getattr(item, "text", None)


def get_similarity(item):
    """
    Hindsight has appeared in our previous tests with
    different score representations.

    Try the known possibilities in order.
    """

    if isinstance(item, dict):

        # Direct semantic similarity
        value = item.get("semantic_similarity")

        if value is not None:
            return value

        # Generic score
        value = item.get("score")

        if value is not None:
            return value

        scores = item.get("scores")

    else:

        value = getattr(
            item,
            "semantic_similarity",
            None,
        )

        if value is not None:
            return value

        value = getattr(
            item,
            "score",
            None,
        )

        if value is not None:
            return value

        scores = getattr(
            item,
            "scores",
            None,
        )

    if scores is None:
        return None

    if isinstance(scores, dict):

        for key in (
            "semantic",
            "similarity",
            "final",
        ):
            if scores.get(key) is not None:
                return scores.get(key)

    else:

        for key in (
            "semantic",
            "similarity",
            "final",
        ):
            value = getattr(
                scores,
                key,
                None,
            )

            if value is not None:
                return value

    return None


def normalize_text(text):
    if not text:
        return ""

    return " ".join(
        text.strip().lower().split()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print("C6.1 REAL HINDSIGHT RETRIEVAL DIAGNOSTIC")
    print("=" * 90)

    canonical = None

    try:

        # ====================================================
        # 1. INITIALIZE SERVICES
        # ====================================================

        section(
            1,
            "INITIALIZE HINDSIGHT + CANONICAL MEMORY"
        )

        memory_service = MemoryService()

        canonical = CanonicalMemoryService(
            db_path=CANONICAL_DB_PATH
        )

        print(
            f"BANK ID: {BANK_ID}"
        )

        print(
            f"CANONICAL DB: {CANONICAL_DB_PATH}"
        )

        print(
            "MemoryService: READY"
        )

        print(
            "CanonicalMemoryService: READY"
        )

        print(
            "STATUS: PASS"
        )

        # ====================================================
        # 2. CREATE CANONICAL MEMORIES
        # ====================================================

        section(
            2,
            "CREATE TWO CANONICAL MEMORIES"
        )

        registered_a = canonical.register(
            bank_id=BANK_ID,
            text=MEMORY_A,
        )

        registered_b = canonical.register(
            bank_id=BANK_ID,
            text=MEMORY_B,
        )

        assert registered_a is True
        assert registered_b is True

        memories = canonical.list_memories(
            bank_id=BANK_ID
        )

        print(
            f"CANONICAL MEMORY COUNT: {len(memories)}"
        )

        assert len(memories) == 2

        print()
        print("RAW CANONICAL MEMORY OBJECTS")
        print("-" * 90)

        for index, memory in enumerate(
            memories,
            start=1,
        ):

            print()
            print(
                f"CANONICAL MEMORY {index}"
            )

            print(
                f"TYPE: {type(memory).__name__}"
            )

            print(
                f"RAW OBJECT: {memory}"
            )

            if isinstance(memory, dict):
                print(
                    f"DICT KEYS: "
                    f"{list(memory.keys())}"
                )

        print()
        print(
            "STATUS: PASS"
        )
           
        

        # ====================================================
        # 3. STORE THE SAME MEMORIES IN HINDSIGHT
        # ====================================================

        section(
            3,
            "STORE MEMORIES IN HINDSIGHT"
        )

        hindsight_a = memory_service.retain(
            bank_id=BANK_ID,
            content=MEMORY_A,
        )

        hindsight_b = memory_service.retain(
            bank_id=BANK_ID,
            content=MEMORY_B,
        )

        print(
            "HINDSIGHT MEMORY A: STORED"
        )

        print(
            "HINDSIGHT MEMORY B: STORED"
        )

        print(
            f"A RETAIN RESULT TYPE: "
            f"{type(hindsight_a).__name__}"
        )

        print(
            f"B RETAIN RESULT TYPE: "
            f"{type(hindsight_b).__name__}"
        )
        print()
        print("RAW HINDSIGHT RETAIN RESULT A")
        print("-" * 90)
        print(hindsight_a)

        print()
        print("RAW HINDSIGHT RETAIN RESULT B")
        print("-" * 90)
        print(hindsight_b)

        print(
            "STATUS: PASS"
        )

        # ====================================================
        # 4. REAL HINDSIGHT RECALL
        # ====================================================

        section(
            4,
            "REAL HINDSIGHT RECALL"
        )

        print(
            f"QUERY: {QUERY}"
        )

        response = memory_service.recall(
            bank_id=BANK_ID,
            query=QUERY,
        )

        results = get_results(response)

        print()
        print(
            f"HINDSIGHT RESULT COUNT: {len(results)}"
        )

        assert len(results) > 0, (
            "Hindsight returned zero results."
        )

        # ====================================================
        # 5. INSPECT ACTUAL RESULT STRUCTURE
        # ====================================================

        section(
            5,
            "INSPECT REAL HINDSIGHT RESULTS"
        )

        usable_candidates = []

        for index, result in enumerate(
            results,
            start=1,
        ):

            text = get_text(result)

            similarity = get_similarity(
                result
            )

            print()
            print(
                f"RESULT {index}"
            )

            print(
                f"OBJECT TYPE: "
                f"{type(result).__name__}"
            )

            print(
                f"TEXT: {text}"
            )

            print(
                f"SIMILARITY: {similarity}"
            )

            if text:
                usable_candidates.append(
                    {
                        "text": text,
                        "retrieval_similarity": similarity,
                    }
                )

        print()
        print(
            f"USABLE CANDIDATES: "
            f"{len(usable_candidates)}"
        )

        assert len(usable_candidates) > 0

        print(
            "STATUS: PASS"
        )

        # ====================================================
        # 6. MAP REAL HINDSIGHT TEXT → CANONICAL MEMORY
        # ====================================================

        section(
            6,
            "MAP HINDSIGHT RESULTS TO CANONICAL MEMORY"
        )

        print()
        print("=" * 90)
        print("[6] INSPECT HINDSIGHT-TO-CANONICAL IDENTITY")
        print("-" * 90)

        print()
        print("AVAILABLE CANONICAL RECORDS")
        print("-" * 90)

        for memory in memories:
            print(
                f"ID: {memory['id']}"
            )

            print(
                f"FINGERPRINT: {memory['fingerprint']}"
            )

            print(
                f"NORMALIZED TEXT: "
                f"{memory['normalized_text']}"
            )

            print(
                f"ORIGINAL TEXT: "
                f"{memory['original_text']}"
            )

            print()

        print()
        print("HINDSIGHT RESULTS")
        print("-" * 90)

        for index, result in enumerate(
            results,
            start=1,
        ):
            hindsight_text = getattr(
                result,
                "text",
                None,
            )

            similarity = getattr(
                result,
                "similarity",
                None,
            )

            print()
            print(
                f"HINDSIGHT RESULT {index}"
            )

            print(
                f"TEXT: {hindsight_text}"
            )

            print(
                f"SIMILARITY: {similarity}"
            )

        print()
        print("STATUS: DIAGNOSTIC READY")
        print()
        print("=" * 90)
        print("C6.1 DIAGNOSTIC STOP")
        print("=" * 90)

        return

        # ====================================================
        # 7. VERIFY BOTH TARGET MEMORIES WERE RETRIEVED
        # ====================================================

        section(
            7,
            "VERIFY BOTH APPROACHES ARE RETRIEVABLE"
        )

        mapped_ids = {
            candidate["canonical_memory_id"]
            for candidate in mapped_candidates
        }

        id_a = canonical_ids[
            normalize_text(MEMORY_A)
        ]

        id_b = canonical_ids[
            normalize_text(MEMORY_B)
        ]

        print(
            f"MEMORY A ID: {id_a}"
        )

        print(
            f"MEMORY B ID: {id_b}"
        )

        print(
            f"RETRIEVED CANONICAL IDS: "
            f"{sorted(mapped_ids)}"
        )

        if id_a in mapped_ids:
            print(
                "MEMORY A RETRIEVED: YES"
            )
        else:
            print(
                "MEMORY A RETRIEVED: NO"
            )

        if id_b in mapped_ids:
            print(
                "MEMORY B RETRIEVED: YES"
            )
        else:
            print(
                "MEMORY B RETRIEVED: NO"
            )

        # We do NOT require both yet.
        #
        # This diagnostic is specifically designed to tell
        # us what Hindsight actually returns.
        #
        # Therefore this section does not artificially fail
        # when one approach is absent.

        print()
        print(
            "STATUS: PASS"
        )

        # ====================================================
        # 8. FINAL DIAGNOSTIC
        # ====================================================

        section(
            8,
            "C6.1 RETRIEVAL DIAGNOSTIC SUMMARY"
        )

        print(
            f"BANK: {BANK_ID}"
        )

        print(
            f"QUERY: {QUERY}"
        )

        print(
            f"HINDSIGHT RESULTS: {len(results)}"
        )

        print(
            f"USABLE TEXT RESULTS: "
            f"{len(usable_candidates)}"
        )

        print(
            f"CANONICAL MAPPED RESULTS: "
            f"{len(mapped_candidates)}"
        )

        print(
            f"MEMORY A FOUND: "
            f"{id_a in mapped_ids}"
        )

        print(
            f"MEMORY B FOUND: "
            f"{id_b in mapped_ids}"
        )

        print()
        print(
            "C6.1 RETRIEVAL DIAGNOSTIC COMPLETED"
        )

    finally:

        if canonical is not None:
            canonical.close()

        if os.path.exists(
            CANONICAL_DB_PATH
        ):
            os.remove(
                CANONICAL_DB_PATH
            )


if __name__ == "__main__":
    main()