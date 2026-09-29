from app.services.memory_service import MemoryService
from app.services.memory_context import MemoryContextBuilder


BANK_ID = "demo-project-001"


def run_test(memory, builder, label, query):

    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)

    print("\nQUERY:")
    print(query)

    result = memory.hindsight.client.recall(
        bank_id=BANK_ID,
        query=query,
        types=["observation"],
        prefer_observations=True,
        budget="mid",
    )

    context = builder.build(result.results)

    print("\nHINDSIGHT RESULT COUNT:")
    print(len(result.results))

    print("\nMAX SCORE:")
    print(context["max_score"])

    print("\nHAS RELEVANT MEMORY:")
    print(context["has_memory"])

    print("\nFINAL MEMORY COUNT:")
    print(context["memory_count"])

    print("\nCONTEXT:")
    print(context["context"])

    print("\nMEMORIES PASSED TO CONTEXT:")
    for memory in context["memories"]:
        print(memory)


def main():

    memory = MemoryService()

    builder = MemoryContextBuilder(
        relevance_threshold=0.002
    )

    run_test(
        memory,
        builder,
        "UNRELATED",
        "What is the difference between TCP and UDP?",
    )

    run_test(
        memory,
        builder,
        "DIRECTLY RELEVANT",
        "What happened previously with the concurrent wallet update failures?",
    )

    run_test(
        memory,
        builder,
        "RELATED INCIDENT",
        (
            "The wallet update is failing concurrently again. "
            "What should we investigate based on what happened previously?"
        ),
    )

    run_test(
        memory,
        builder,
        "SOLUTION-FOCUSED",
        "How was the concurrent wallet update problem solved previously?",
    )

    memory.close()


if __name__ == "__main__":
    main()