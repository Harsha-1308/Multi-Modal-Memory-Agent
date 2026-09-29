from app.services.memory_learning import MemoryLearningService
from app.services.memory_service import MemoryService


BANK_ID = "memory-integration-test-001"


def print_separator(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main():

    learning = MemoryLearningService()
    memory = MemoryService()

    # ============================================================
    # TEST SETUP
    # ============================================================

    print_separator("SETUP - CREATE CLEAN HINDSIGHT BANK")

    try:
        bank = memory.create_project_bank(
            bank_id=BANK_ID,
            project_name="Memory Integration Test",
            project_description=(
                "Temporary bank used to test universal "
                "multi-memory extraction, decision, and retention."
            ),
        )

        print("\nBANK CREATED:")
        print(bank)

    except Exception as exc:
        print("\nBANK CREATION RESULT:")
        print(type(exc).__name__, str(exc))

        print(
            "\nIf the bank already exists, that is acceptable "
            "for this test only if it was created by this script."
        )

    # ============================================================
    # TEST 1 - PURELY IRRELEVANT MESSAGE
    # ============================================================

    print_separator("TEST 1 - IRRELEVANT MESSAGE")

    content_1 = "Hello"

    result_1 = learning.process(
        bank_id=BANK_ID,
        content=content_1,
    )

    print("\nRESULT:")
    print(result_1)

    print("\nEXTRACTED COUNT:")
    print(len(result_1["extracted_memories"]))

    print("\nRETAINED COUNT:")
    print(len(result_1["retained_memories"]))

    # ============================================================
    # TEST 2 - MULTIPLE DURABLE MEMORIES
    # ============================================================

    print_separator("TEST 2 - MULTIPLE MEMORIES")

    content_2 = (
        "We tried application-level retries for the wallet "
        "concurrency problem, but they failed. We then used "
        "pessimistic database locking and the integration "
        "tests passed."
    )

    result_2 = learning.process(
        bank_id=BANK_ID,
        content=content_2,
    )

    print("\nINPUT:")
    print(content_2)

    print("\nEXTRACTED MEMORIES:")

    for index, item in enumerate(
        result_2["extracted_memories"],
        start=1,
    ):
        print(f"\n{index}.")
        print(item)

    print("\nDECISIONS:")

    for index, item in enumerate(
        result_2["decisions"],
        start=1,
    ):
        print(f"\n{index}.")
        print(item)

    print("\nRETAINED MEMORIES:")

    for index, item in enumerate(
        result_2["retained_memories"],
        start=1,
    ):
        print(f"\n{index}.")
        print(item)

    print("\nDISCARDED MEMORIES:")

    for index, item in enumerate(
        result_2["discarded_memories"],
        start=1,
    ):
        print(f"\n{index}.")
        print(item)

    # ============================================================
    # TEST 3 - VERIFY HINDSIGHT
    # ============================================================

    print_separator("TEST 3 - VERIFY HINDSIGHT")

    recall_result = memory.recall(
        bank_id=BANK_ID,
        query=(
            "What happened when we tried to solve "
            "the wallet concurrency problem?"
        ),
    )

    print("\nRECALL COUNT:")
    print(len(recall_result.results))

    print("\nRECALLED MEMORIES:")

    for index, item in enumerate(
        recall_result.results,
        start=1,
    ):
        print(
            f"\n{index}.",
            {
                "text": item.text,
                "type": getattr(item, "type", "unknown"),
            },
        )

    # ============================================================
    # FINAL SUMMARY
    # ============================================================

    print_separator("FINAL SUMMARY")

    print(
        "\nTEST 1 extracted:",
        len(result_1["extracted_memories"]),
    )

    print(
        "TEST 1 retained:",
        len(result_1["retained_memories"]),
    )

    print(
        "TEST 2 extracted:",
        len(result_2["extracted_memories"]),
    )

    print(
        "TEST 2 decisions:",
        len(result_2["decisions"]),
    )

    print(
        "TEST 2 retained:",
        len(result_2["retained_memories"]),
    )

    print(
        "TEST 2 discarded:",
        len(result_2["discarded_memories"]),
    )

    print(
        "Hindsight recall count:",
        len(recall_result.results),
    )

    learning.close()
    memory.close()


if __name__ == "__main__":
    main()