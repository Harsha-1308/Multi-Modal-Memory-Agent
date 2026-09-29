import uuid

from app.services.memory_service import MemoryService


BANK_ID = f"memory-quality-audit-b5-{uuid.uuid4().hex[:8]}"

def print_memory(memory, index):
    score = getattr(memory.scores, "final", 0.0) or 0.0
    semantic = getattr(memory.scores, "semantic", 0.0) or 0.0
    keyword = getattr(memory.scores, "keyword", 0.0) or 0.0
    reranker = getattr(memory.scores, "reranker", 0.0) or 0.0

    print(f"RANK      = {index}")
    print("-" * 70)

    print("TEXT:")
    print(memory.text)

    print("\nTYPE:")
    print(getattr(memory, "type", "unknown"))

    print("\nID:")
    print(getattr(memory, "id", "unknown"))

    print("\nSCORES:")
    print(f"final     = {score}")
    print(f"semantic  = {semantic}")
    print(f"keyword   = {keyword}")
    print(f"reranker  = {reranker}")

def run_query(
    memory_service,
    query,
    label,
    types,
    prefer_observations=True,
    trace=False,
):
    print("\n")
    print("=" * 80)
    print(f"RETRIEVAL TEST: {label}")
    print("=" * 80)

    print(f"QUERY: {query}")
    print(f"TYPES: {types}")
    print(f"PREFER OBSERVATIONS: {prefer_observations}")
    print(f"TRACE: {trace}")

    response = memory_service.hindsight.client.recall(
        bank_id=BANK_ID,
        query=query,
        types=types,
        prefer_observations=prefer_observations,
        budget="mid",
        trace=trace,
    )

    results = response.results

    print(f"\nRECALL COUNT: {len(results)}")

    for index, memory in enumerate(results, start=1):
        print_memory(memory, index)

    if trace:
        print("\n")
        print("=" * 80)
        print("TRACE")
        print("=" * 80)

        print(response.trace)

def main():

    memory_service = MemoryService()

    try:

        print("=" * 80)
        print("B5 MEMORY QUALITY AND RETRIEVAL AUDIT")
        print("=" * 80)

        # --------------------------------------------------
        # STEP 1 — CREATE CLEAN BANK
        # --------------------------------------------------

        print("\nCREATING TEST BANK...")

        bank = memory_service.create_project_bank(
            bank_id=BANK_ID,
            project_name="Memory Quality Audit",
            project_description=(
                "Temporary bank used to audit Hindsight "
                "retrieval quality and duplicate handling."
            ),
        )

        print("BANK CREATED:")
        print(bank)

        # --------------------------------------------------
        # STEP 2 — RETAIN CONTROLLED MEMORIES
        # --------------------------------------------------

        memories_to_store = [

            (
                "SUCCESS",
                "Pessimistic database locking resolved the "
                "wallet concurrency problem and integration "
                "tests passed."
            ),

            (
                "FAILURE",
                "Application-level retries were attempted "
                "for the wallet concurrency problem, but "
                "the approach failed."
            ),

            (
                "UNRELATED",
                "TCP is a connection-oriented transport-layer "
                "protocol."
            ),

            (
                "OTHER DOMAIN",
                "Experiment B achieved 91% accuracy and was "
                "selected for further evaluation."
            ),

            (
                "EXACT DUPLICATE",
                "Pessimistic database locking resolved the "
                "wallet concurrency problem and integration "
                "tests passed."
            ),

            (
                "PARAPHRASED DUPLICATE",
                "The wallet concurrency issue was fixed "
                "successfully using pessimistic locking, "
                "and the integration tests succeeded."
            ),
        ]

        print("\n")
        print("=" * 80)
        print("STORING CONTROLLED MEMORIES")
        print("=" * 80)

        for label, content in memories_to_store:

            print(f"\n[{label}]")
            print(content)

            result = memory_service.retain(
                bank_id=BANK_ID,
                content=content,
            )

            print("RETAIN RESULT:")
            print(result)

        # --------------------------------------------------
        # STEP 3 — RETRIEVAL TESTS
        # --------------------------------------------------

        queries = [
    (
        "QUERY 1 — VAGUE",
        "Which approach worked?",
    ),
    (
        "QUERY 2 — CONTEXTUAL",
        "Which approach successfully resolved the wallet concurrency problem?",
    ),
]
       
        print("\n")
        print("=" * 80)
        print("B5 RETRIEVAL TYPE AUDIT")
        print("=" * 80)

        for label, query in queries:
            print("\n")
            print("=" * 80)
            print(label)
            print("=" * 80)
            print(f"QUERY: {query}")
            print("=" * 80)

            run_query(
                memory_service=memory_service,
                query=query,
                label=f"{label} — CURRENT CONFIGURATION",
                types=["world", "experience", "observation"],
                prefer_observations=True,
        trace=False,
    )
            run_query(
        memory_service=memory_service,
        query=query,
        label=f"{label} — OBSERVATIONS ONLY",
        types=["observation"],
        prefer_observations=False,
        trace=False,
    )

            run_query(
        memory_service=memory_service,
        query=query,
        label=f"{label} — EXPERIENCE ONLY",
        types=["experience"],
        prefer_observations=False,
        trace=False,
    )

            run_query(
        memory_service=memory_service,
        query=query,
        label=f"{label} — WORLD ONLY",
        types=["world"],
        prefer_observations=False,
        trace=False,
    )

            run_query(
        memory_service=memory_service,
        query=query,
        label=f"{label} — OBSERVATION + EXPERIENCE",
        types=["observation", "experience"],
        prefer_observations=True,
        trace=False,
    )
        # --------------------------------------------------
# STEP 4 — B5 TRACE AUDIT
# --------------------------------------------------
        print("\n")
        print("=" * 80)
        print("B5 TRACE AUDIT")
        print("=" * 80)
        run_query(
    memory_service=memory_service,
    query="Which approach successfully resolved the wallet concurrency problem?",
    label="TRACE — CONTEXTUAL QUERY",
    types=["world", "experience", "observation"],
    prefer_observations=True,
    trace=True,
)
        

        # --------------------------------------------------
        # STEP 4 — LIST STORED MEMORIES
        # --------------------------------------------------

        print("\n")
        print("=" * 80)
        print("ALL STORED MEMORIES")
        print("=" * 80)

        stored = memory_service.list_memories(
            bank_id=BANK_ID,
            limit=50,
        )
        print("\nLIST MEMORIES RESPONSE TYPE:")
        print(type(stored))

        print("\nLIST MEMORIES RESPONSE:")
        print(stored)

        for index, memory in enumerate(stored.items, start=1):

            print("\n")
            print(f"MEMORY {index}")
            print("-" * 70)

            print("TEXT:")
            print(memory.text)

            print("TYPE:")
            print(getattr(memory, "fact_type", "unknown"))
        print("\n")
        print("=" * 80)
        print("TYPE FILTER AUDIT")
        print("=" * 80)
        query = "Which approach worked?"
        print("\nDEFAULT TYPES:")
        default_results = memory_service.recall(
    bank_id=BANK_ID,
    query=query,
)

#         for index, memory in enumerate(default_results, start=1):
#             print(
#         f"{index}. "
#         f"[{getattr(memory, 'type', 'unknown')}] "
#         f"{memory.text} "
#         f"| final="
#         f"{getattr(memory.scores, 'final', 0.0)}"
#     )
#         print("\nALL TYPES:")
#         all_results = memory_service.recall(
#     bank_id=BANK_ID,
#     query=query,
#     types=None,
# )
#         for index, memory in enumerate(all_results, start=1):
#             print(
#         f"{index}. "
#         f"[{getattr(memory, 'type', 'unknown')}] "
#         f"{memory.text} "
#         f"| final="
#         f"{getattr(memory.scores, 'final', 0.0)}"
#     )

    finally:

        memory_service.close()


if __name__ == "__main__":
    main()