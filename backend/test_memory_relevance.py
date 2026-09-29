from app.services.memory_service import MemoryService


BANK_ID = "demo-project-001"


def test_query(memory, label, query):
    print("\n")
    print("=" * 80)
    print(label)
    print("=" * 80)

    print("QUERY:")
    print(query)

    result = memory.hindsight.client.recall(
        bank_id=BANK_ID,
        query=query,
        types=["observation"],
        prefer_observations=True,
        budget="mid",
    )

    print("\nRESULT COUNT:", len(result.results))

    max_score = 0.0

    for index, item in enumerate(result.results, start=1):
        score = item.scores.final

        if score > max_score:
            max_score = score

        print("\n" + "-" * 80)
        print("MEMORY", index)
        print("TEXT:", item.text)
        print("FINAL SCORE:", score)

    print("\nMAX FINAL SCORE:", max_score)


def main():
    memory = MemoryService()

    test_query(
        memory,
        "UNRELATED",
        "What is the difference between TCP and UDP?",
    )

    test_query(
        memory,
        "DIRECTLY RELEVANT",
        "What happened previously with the concurrent wallet update failures?",
    )

    test_query(
        memory,
        "RELATED INCIDENT",
        (
            "The wallet update is failing concurrently again. "
            "What should we investigate based on what happened previously?"
        ),
    )

    test_query(
        memory,
        "SOLUTION-FOCUSED",
        "How was the concurrent wallet update problem solved previously?",
    )

    memory.close()


if __name__ == "__main__":
    main()