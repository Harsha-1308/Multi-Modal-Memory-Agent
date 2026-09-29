from app.services.memory_learning_service import MemoryLearningService


BANK_ID = "b6-learning-integration"


def print_result(label, result):
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)

    print("RETAINED MEMORIES:")
    for item in result["retained_memories"]:
        print(
            item["memory"]["content"],
            "->",
            item["relationship"].relationship,
        )

    print("\nDISCARDED MEMORIES:")
    for item in result["discarded_memories"]:
        print(
            item["memory"]["content"],
            "->",
            item.get("relationship"),
        )


def main():

    service = MemoryLearningService()

    try:

        print("=" * 90)
        print("B6 LEARNING INTEGRATION TEST")
        print("=" * 90)

        # --------------------------------------------------
        # CASE 1
        # --------------------------------------------------

        result1 = service.process(
            bank_id=BANK_ID,
            content=(
                "Pessimistic database locking resolved "
                "the wallet concurrency problem."
            ),
        )

        print_result(
            "CASE 1: BASE MEMORY",
            result1,
        )

        # --------------------------------------------------
        # CASE 2
        # --------------------------------------------------

        result2 = service.process(
            bank_id=BANK_ID,
            content=(
                "The wallet concurrency issue was fixed "
                "successfully using pessimistic locking."
            ),
        )

        print_result(
            "CASE 2: PARAPHRASE",
            result2,
        )

        # --------------------------------------------------
        # CASE 3
        # --------------------------------------------------

        result3 = service.process(
            bank_id=BANK_ID,
            content=(
                "Pessimistic locking increased database "
                "contention during high-volume transactions."
            ),
        )

        print_result(
            "CASE 3: RELATED BUT NEW",
            result3,
        )

        # --------------------------------------------------
        # CASE 4
        # --------------------------------------------------

        result4 = service.process(
            bank_id=BANK_ID,
            content=(
                "Pessimistic database locking failed to "
                "resolve the wallet concurrency problem."
            ),
        )

        print_result(
            "CASE 4: CONTRADICTION",
            result4,
        )

    finally:
        service.close()


if __name__ == "__main__":
    main()