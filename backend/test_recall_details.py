from app.services.memory_service import MemoryService


BANK_ID = "demo-project-001"


def main():
    memory = MemoryService()

    result = memory.recall(
        bank_id=BANK_ID,
        query=(
            "What happened previously with concurrent "
            "wallet update failures?"
        ),
    )

    print("=" * 70)
    print("RECALL RESULT")
    print("=" * 70)

    print("Number of results:", len(result.results))

    for index, item in enumerate(result.results, start=1):
        print("\n" + "-" * 70)
        print("MEMORY", index)

        print("TEXT:")
        print(getattr(item, "text", None))

        print("ID:")
        print(getattr(item, "id", None))

        print("TYPE:")
        print(getattr(item, "type", None))

        print("CONTEXT:")
        print(getattr(item, "context", None))

        print("MENTIONED AT:")
        print(getattr(item, "mentioned_at", None))

        print("ENTITIES:")
        print(getattr(item, "entities", None))

    memory.close()


if __name__ == "__main__":
    main()