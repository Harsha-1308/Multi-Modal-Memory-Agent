from app.services.memory_learning import MemoryLearningService
from app.services.memory_service import MemoryService


BANK_ID = "demo-project-001"


def main():

    learning = MemoryLearningService()
    memory = MemoryService()

    # ============================================================
    # 1. INFORMATION THAT SHOULD NOT BE RETAINED
    # ============================================================

    print("\n" + "=" * 80)
    print("TEST 1 - DO NOT RETAIN")
    print("=" * 80)

    content_1 = "Hello"

    result_1 = learning.process(
        bank_id=BANK_ID,
        content=content_1,
    )

    print("\nINPUT:")
    print(content_1)

    print("\nRESULT:")
    print(result_1)

    # ============================================================
    # 2. INFORMATION THAT SHOULD BE RETAINED
    # ============================================================

    print("\n" + "=" * 80)
    print("TEST 2 - RETAIN")
    print("=" * 80)

    content_2 = (
        "The payment service uses pessimistic database locking "
        "to prevent concurrent wallet update failures."
    )

    result_2 = learning.process(
        bank_id=BANK_ID,
        content=content_2,
    )

    print("\nINPUT:")
    print(content_2)

    print("\nRESULT:")
    print(result_2)

    # ============================================================
    # 3. VERIFY HINDSIGHT
    # ============================================================

    print("\n" + "=" * 80)
    print("TEST 3 - VERIFY HINDSIGHT")
    print("=" * 80)

    recall_result = memory.recall(
        bank_id=BANK_ID,
        query=(
            "How does the payment service handle "
            "concurrent wallet updates?"
        ),
    )

    print("\nRECALL COUNT:")
    print(len(recall_result.results))

    print("\nRECALLED MEMORIES:")

    for item in recall_result.results:
        print(
            {
                "text": item.text,
                "type": getattr(item, "type", "unknown"),
            }
        )

    learning.close()
    memory.close()


if __name__ == "__main__":
    main()