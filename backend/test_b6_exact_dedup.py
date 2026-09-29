from app.services.canonical_memory_service import CanonicalMemoryService


BANK_ID = "b6-exact-dedup-test"


def main():

    service = CanonicalMemoryService(
        db_path="b6_test_registry.db"
    )

    try:

        print("=" * 80)
        print("B6.1 EXACT DUPLICATE TEST")
        print("=" * 80)

        memory_1 = (
            "Pessimistic database locking resolved the "
            "wallet concurrency problem."
        )

        memory_2 = (
            "  Pessimistic database locking resolved the "
            "wallet concurrency problem.  "
        )

        memory_3 = (
            "Pessimistic database locking resolved the "
            "wallet concurrency issue."
        )

        print("\nMEMORY 1:")
        print(memory_1)

        print("\nNORMALIZED:")
        print(service.normalize(memory_1))

        print("\nFINGERPRINT:")
        print(service.fingerprint(memory_1))

        print("\nREGISTER MEMORY 1:")
        result_1 = service.register(
            bank_id=BANK_ID,
            text=memory_1,
        )

        print(result_1)

        print("\nIS MEMORY 1 DUPLICATE?")
        print(
            service.is_exact_duplicate(
                bank_id=BANK_ID,
                text=memory_1,
            )
        )

        print("\nMEMORY 2:")
        print(memory_2)

        print("\nIS MEMORY 2 DUPLICATE?")
        print(
            service.is_exact_duplicate(
                bank_id=BANK_ID,
                text=memory_2,
            )
        )

        print("\nREGISTER MEMORY 2:")
        result_2 = service.register(
            bank_id=BANK_ID,
            text=memory_2,
        )

        print(result_2)

        print("\nMEMORY 3:")
        print(memory_3)

        print("\nIS MEMORY 3 DUPLICATE?")
        print(
            service.is_exact_duplicate(
                bank_id=BANK_ID,
                text=memory_3,
            )
        )

        print("\nREGISTER MEMORY 3:")
        result_3 = service.register(
            bank_id=BANK_ID,
            text=memory_3,
        )

        print(result_3)

        print("\nEXPECTED:")
        print("Memory 1 -> False before registration")
        print("Memory 2 -> True")
        print("Memory 3 -> False")

    finally:
        service.close()


if __name__ == "__main__":
    main()