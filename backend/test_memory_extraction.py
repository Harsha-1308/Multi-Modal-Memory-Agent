from app.services.memory_extraction import MemoryExtractionService


def run_test(extractor, test_name, content):
    print("\n" + "=" * 80)
    print(test_name)
    print("=" * 80)

    print("\nINPUT:")
    print(content)

    result = extractor.extract(content)

    print("\nEXTRACTED MEMORIES:")
    print(result)

    print("\nMEMORY COUNT:")
    print(len(result))


def main():

    extractor = MemoryExtractionService()

    # ============================================================
    # TEST 1 - GREETING
    # ============================================================

    run_test(
        extractor,
        "TEST 1 - GREETING",
        "Hello",
    )

    # ============================================================
    # TEST 2 - GENERIC KNOWLEDGE
    # ============================================================

    run_test(
        extractor,
        "TEST 2 - GENERIC KNOWLEDGE",
        "TCP is a transport-layer protocol.",
    )

    # ============================================================
    # TEST 3 - SINGLE PROJECT FACT
    # ============================================================

    run_test(
        extractor,
        "TEST 3 - SINGLE PROJECT FACT",
        "Our payment service uses PostgreSQL for transaction storage.",
    )

    # ============================================================
    # TEST 4 - MULTIPLE PIECES OF INFORMATION
    # ============================================================

    run_test(
        extractor,
        "TEST 4 - MULTIPLE MEMORIES",
        (
            "We tried application-level retries for the wallet "
            "concurrency problem, but they failed. We then used "
            "pessimistic database locking and the integration "
            "tests passed."
        ),
    )

    # ============================================================
    # TEST 5 - EXPERIMENT
    # ============================================================

    run_test(
        extractor,
        "TEST 5 - EXPERIMENT",
        (
            "Experiment A achieved 82% accuracy, while Experiment B "
            "achieved 91% accuracy. We decided to continue with "
            "Experiment B."
        ),
    )

    # ============================================================
    # TEST 6 - PREFERENCE
    # ============================================================

    run_test(
        extractor,
        "TEST 6 - PREFERENCE",
        "The team prefers using PostgreSQL migrations instead of manually modifying production schemas.",
    )

    # ============================================================
    # TEST 7 - CASUAL CONVERSATION
    # ============================================================

    run_test(
        extractor,
        "TEST 7 - CASUAL CONVERSATION",
        "Okay, thanks. That makes sense.",
    )

    extractor.close()


if __name__ == "__main__":
    main()