from app.services.memory_service import MemoryService

BANK_ID = "demo-project-001"


def main():
    memory = MemoryService()

    result = memory.recall(
        bank_id=BANK_ID,
        query="What is the difference between TCP and UDP?",
    )

    print("=" * 70)
    print("RECALL METADATA INSPECTION")
    print("=" * 70)

    print("Number of results:", len(result.results))

    for index, item in enumerate(result.results, start=1):
        print("\n" + "-" * 70)
        print("MEMORY", index)

        print("\nTYPE:")
        print(getattr(item, "type", None))

        print("\nTEXT:")
        print(getattr(item, "text", None))

        print("\nID:")
        print(getattr(item, "id", None))

        print("\nMENTIONED AT:")
        print(getattr(item, "mentioned_at", None))

        print("\nCONTEXT:")
        print(getattr(item, "context", None))

        print("\nENTITIES:")
        print(getattr(item, "entities", None))

        print("\nALL ATTRIBUTES:")
        print(vars(item))

    print("\n")
    print("=" * 70)
    print("RESULT OBJECT ATTRIBUTES")
    print("=" * 70)

    print(vars(result))

    memory.close()


if __name__ == "__main__":
    main()