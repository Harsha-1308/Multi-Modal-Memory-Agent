from app.services.memory_service import MemoryService

BANK_ID = "demo-project-001"


QUERIES = [
    (
        "UNRELATED",
        "What is the difference between TCP and UDP?",
    ),
    (
        "DIRECTLY RELEVANT",
        "What happened previously with the concurrent wallet update failures?",
    ),
    (
        "RELATED INCIDENT",
        "The wallet update is failing concurrently again. "
        "What should we investigate based on what happened previously?",
    ),
]


def main():
    memory = MemoryService()

    for label, query in QUERIES:

        print("\n")
        print("=" * 80)
        print(label)
        print("=" * 80)

        print("QUERY:")
        print(query)

        result = memory.recall(
            bank_id=BANK_ID,
            query=query,
        )

        print("\nRESULT COUNT:", len(result.results))

        for index, item in enumerate(result.results, start=1):

            scores = getattr(item, "scores", None)

            print("\n" + "-" * 80)
            print("MEMORY", index)

            print("TEXT:")
            print(item.text)

            print("\nTYPE:")
            print(item.type)

            print("\nSCORES:")
            print(scores)

            if scores:
                print("FINAL:", getattr(scores, "final", None))
                print("RERANKER:", getattr(scores, "reranker", None))
                print("SEMANTIC:", getattr(scores, "semantic", None))
                print("KEYWORD:", getattr(scores, "keyword", None))

    memory.close()


if __name__ == "__main__":
    main()