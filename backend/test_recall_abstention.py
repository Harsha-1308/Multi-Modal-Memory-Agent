from app.services.memory_service import MemoryService

BANK_ID = "demo-project-001"


def run_test(memory, label, query, min_final):
    print("\n")
    print("=" * 80)
    print(label)
    print("=" * 80)

    print("QUERY:")
    print(query)

    print("MIN FINAL SCORE:")
    print(min_final)

    result = memory.hindsight.client.recall(
        bank_id=BANK_ID,
        query=query,
        types=["observation"],
        prefer_observations=True,
        budget="mid",
        min_scores={
            "final": min_final
        },
    )

    print("\nRESULT COUNT:", len(result.results))

    for index, item in enumerate(result.results, start=1):
        print("\n" + "-" * 80)
        print("MEMORY", index)
        print("TEXT:", item.text)
        print("SCORES:", item.scores)


def main():
    memory = MemoryService()

    run_test(
        memory,
        "UNRELATED",
        "What is the difference between TCP and UDP?",
        0.002,
    )

    run_test(
        memory,
        "DIRECTLY RELEVANT",
        "What happened previously with the concurrent wallet update failures?",
        0.002,
    )

    run_test(
        memory,
        "RELATED INCIDENT",
        (
            "The wallet update is failing concurrently again. "
            "What should we investigate based on what happened previously?"
        ),
        0.002,
    )
    run_test(
    memory,
    "SOLUTION-FOCUSED",
    "How was the concurrent wallet update problem solved previously?",
    0.002,
)

    memory.close()


if __name__ == "__main__":
    main()