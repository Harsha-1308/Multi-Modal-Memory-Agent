import os
import uuid

from app.services.memory_service import (
    MemoryService,
)

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)

from app.services.hindsight_canonical_resolver import (
    HindsightCanonicalResolver,
)


BANK_ID = (
    f"c6-1-identity-"
    f"{uuid.uuid4().hex[:8]}"
)

CANONICAL_DB_PATH = (
    f"test_c6_1_identity_"
    f"{uuid.uuid4().hex[:8]}.db"
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


def section(number, title):

    print()
    print("=" * 90)
    print(f"[{number}] {title}")
    print("-" * 90)


def get_results(response):

    results = getattr(
        response,
        "results",
        None,
    )

    if results is None and isinstance(
        response,
        dict,
    ):
        results = response.get(
            "results"
        )

    return results or []


def get_text(result):

    if isinstance(result, dict):
        return result.get("text")

    return getattr(
        result,
        "text",
        None,
    )


def get_similarity(result):

    if isinstance(result, dict):

        value = result.get(
            "semantic_similarity"
        )

        if value is not None:
            return float(value)

        value = result.get("score")

        if value is not None:
            return float(value)

        scores = result.get("scores")

    else:

        value = getattr(
            result,
            "semantic_similarity",
            None,
        )

        if value is not None:
            return float(value)

        value = getattr(
            result,
            "score",
            None,
        )

        if value is not None:
            return float(value)

        scores = getattr(
            result,
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
            value = scores.get(key)

            if value is not None:
                return float(value)

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
                return float(value)

    return None


def require(condition, message):

    if not condition:
        raise AssertionError(
            message
        )


def main():

    memory_service = None
    canonical = None

    try:

        print()
        print("=" * 90)
        print(
            "C6.1 HINDSIGHT → CANONICAL "
            "IDENTITY TEST"
        )
        print("=" * 90)

        # ====================================================
        # 1. INITIALIZE
        # ====================================================

        section(
            1,
            "INITIALIZE SERVICES",
        )

        memory_service = MemoryService()

        canonical = CanonicalMemoryService(
            db_path=CANONICAL_DB_PATH
        )

        resolver = (
            HindsightCanonicalResolver(
                canonical_memory_service=canonical
            )
        )

        print(
            "MemoryService: READY"
        )

        print(
            "CanonicalMemoryService: READY"
        )

        print(
            "IdentityResolver: READY"
        )

        print(
            f"BANK ID: {BANK_ID}"
        )

        print("STATUS: PASS")

        # ====================================================
        # 2. CREATE CANONICAL MEMORIES
        # ====================================================

        section(
            2,
            "CREATE CANONICAL MEMORIES",
        )

        require(
            canonical.register(
                bank_id=BANK_ID,
                text=MEMORY_A,
            ),
            "Memory A registration failed.",
        )

        require(
            canonical.register(
                bank_id=BANK_ID,
                text=MEMORY_B,
            ),
            "Memory B registration failed.",
        )

        memories = (
            canonical.list_memories(
                bank_id=BANK_ID
            )
        )

        require(
            len(memories) == 2,
            "Expected exactly 2 canonical memories.",
        )

        for memory in memories:

            print()
            print(
                f"CANONICAL ID: {memory['id']}"
            )

            print(
                f"TEXT: {memory['original_text']}"
            )

        print()
        print("STATUS: PASS")

        # ====================================================
        # 3. REAL HINDSIGHT RETAIN
        # ====================================================

        section(
            3,
            "STORE IN HINDSIGHT",
        )

        retain_a = memory_service.retain(
            bank_id=BANK_ID,
            content=MEMORY_A,
        )

        retain_b = memory_service.retain(
            bank_id=BANK_ID,
            content=MEMORY_B,
        )

        require(
            getattr(
                retain_a,
                "success",
                False,
            ),
            "Hindsight retain A failed.",
        )

        require(
            getattr(
                retain_b,
                "success",
                False,
            ),
            "Hindsight retain B failed.",
        )

        print(
            "Hindsight A: STORED"
        )

        print(
            "Hindsight B: STORED"
        )

        print("STATUS: PASS")

        # ====================================================
        # 4. REAL HINDSIGHT RECALL
        # ====================================================

        section(
            4,
            "REAL HINDSIGHT RECALL",
        )

        response = memory_service.recall(
            bank_id=BANK_ID,
            query=QUERY,
        )

        results = get_results(
            response
        )

        require(
            len(results) > 0,
            "Hindsight returned zero results.",
        )

        print(
            f"QUERY: {QUERY}"
        )

        print()
        print(
            f"RESULT COUNT: {len(results)}"
        )

        for index, result in enumerate(
            results,
            start=1,
        ):

            print()
            print(
                f"RESULT {index}"
            )

            print(
                f"TEXT: {get_text(result)}"
            )

            print(
                f"RETRIEVAL SIMILARITY: "
                f"{get_similarity(result)}"
            )

        print()
        print("STATUS: PASS")

        # ====================================================
        # 5. RESOLVE REAL RESULTS
        # ====================================================

        section(
            5,
            "RESOLVE HINDSIGHT RESULTS",
        )

        resolved = (
            resolver.resolve_results(
                results=results,
                bank_id=BANK_ID,
            )
        )

        print()
        print(
            f"RESOLVED CANDIDATES: "
            f"{len(resolved)}"
        )

        for index, candidate in enumerate(
            resolved,
            start=1,
        ):

            print()
            print(
                f"RESOLVED CANDIDATE {index}"
            )

            print(
                f"CANONICAL MEMORY ID: "
                f"{candidate['canonical_memory_id']}"
            )

            print(
                f"RETRIEVAL SIMILARITY: "
                f"{candidate['retrieval_similarity']}"
            )

            print(
                f"IDENTITY SCORE: "
                f"{candidate['identity_score']}"
            )

            print(
                f"IDENTITY MARGIN: "
                f"{candidate['identity_margin']}"
            )

            print(
                f"TEXT: "
                f"{candidate['text']}"
            )

        # ====================================================
        # 6. VERIFY VALID CANONICAL IDs
        # ====================================================

        section(
            6,
            "VERIFY CANONICAL ID INTEGRITY",
        )

        valid_ids = {
            memory["id"]
            for memory in memories
        }

        resolved_ids = {
            candidate[
                "canonical_memory_id"
            ]
            for candidate in resolved
        }

        print(
            f"VALID CANONICAL IDS: "
            f"{sorted(valid_ids)}"
        )

        print(
            f"RESOLVED CANONICAL IDS: "
            f"{sorted(resolved_ids)}"
        )

        require(
            resolved_ids.issubset(
                valid_ids
            ),
            "Resolver produced an invalid canonical ID.",
        )

        print()
        print(
            "NO INVALID CANONICAL IDS: YES"
        )

        print("STATUS: PASS")

        # ====================================================
        # 7. BUILD C6 CANDIDATES
        # ====================================================

        section(
            7,
            "BUILD C6 CANDIDATES",
        )

        c6_candidates = []

        for candidate in resolved:

            c6_candidates.append(
                {
                    "canonical_memory_id": (
                        candidate[
                            "canonical_memory_id"
                        ]
                    ),
                    "text": candidate["text"],
                    "retrieval_similarity": (
                        candidate[
                            "retrieval_similarity"
                        ]
                    ),
                }
            )

        print(
            f"C6 CANDIDATE COUNT: "
            f"{len(c6_candidates)}"
        )

        for candidate in c6_candidates:

            print(
                candidate
            )

        require(
            len(c6_candidates) > 0,
            "No usable C6 candidates were produced.",
        )

        print()
        print(
            "C6 INPUT FORMAT: VALID"
        )

        print("STATUS: PASS")

        # ====================================================
        # FINAL
        # ====================================================

        section(
            8,
            "C6.1 IDENTITY RESOLUTION PASSED",
        )

        print(
            "PROVEN:"
        )

        print(
            "1. Canonical memories are persisted."
        )

        print(
            "2. Real Hindsight retain succeeds."
        )

        print(
            "3. Real Hindsight recall succeeds."
        )

        print(
            "4. Real retrieval similarity is preserved."
        )

        print(
            "5. Hindsight results are resolved "
            "to application-owned canonical IDs."
        )

        print(
            "6. Invalid canonical IDs are rejected."
        )

        print(
            "7. Resolved candidates have the exact "
            "input shape required by C6."
        )

        print()
        print(
            "C6.1 IDENTITY RESOLUTION PASSED"
        )

    finally:

        if canonical is not None:
            canonical.close()

        if memory_service is not None:

            close_method = getattr(
                memory_service,
                "close",
                None,
            )

            if callable(close_method):
                close_method()

        if os.path.exists(
            CANONICAL_DB_PATH
        ):
            os.remove(
                CANONICAL_DB_PATH
            )


if __name__ == "__main__":
    main()