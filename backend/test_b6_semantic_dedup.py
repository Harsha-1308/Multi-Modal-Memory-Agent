import time
import uuid

from app.services.memory_service import MemoryService


BASE_MEMORY = (
    "Pessimistic database locking resolved the "
    "wallet concurrency problem."
)


TEST_CASES = [
    {
        "name": "EXACT DUPLICATE",
        "candidate": (
            "Pessimistic database locking resolved the "
            "wallet concurrency problem."
        ),
        "expected": "semantic_duplicate",
    },
    {
        "name": "PARAPHRASE",
        "candidate": (
            "The wallet concurrency issue was fixed "
            "successfully using pessimistic locking."
        ),
        "expected": "semantic_duplicate",
    },
    {
        "name": "RELATED BUT NEW",
        "candidate": (
            "Pessimistic locking increased database "
            "contention during high-volume transactions."
        ),
        "expected": "related_new",
    },
    {
        "name": "CONTRADICTION",
        "candidate": (
            "Pessimistic database locking failed to "
            "resolve the wallet concurrency problem."
        ),
        "expected": "contradiction",
    },
]


def get_memory_units(response):
    """
    Extract memory units from list_memories().
    """

    items = getattr(response, "items", None)

    if items is None and isinstance(response, dict):
        items = response.get("items")

    return items or []


def get_recall_results(response):
    """
    Extract recall results from recall().
    """

    results = getattr(response, "results", None)

    if results is None and isinstance(response, dict):
        results = response.get("results")

    return results or []


def get_text(item):
    """
    Extract memory text.
    """

    if isinstance(item, dict):
        return item.get("text")

    return getattr(item, "text", None)


def get_semantic_similarity(item):
    """
    Extract Hindsight semantic similarity.
    """

    if isinstance(item, dict):

        value = item.get("semantic_similarity")

        if value is not None:
            return value

        scores = item.get("scores")

    else:

        value = getattr(item, "semantic_similarity", None)

        if value is not None:
            return value

        scores = getattr(item, "scores", None)

    if scores is not None:

        if isinstance(scores, dict):
            return scores.get("semantic")

        return getattr(scores, "semantic", None)

    return None


def get_fact_type(item):
    """
    Extract Hindsight fact type.
    """

    if isinstance(item, dict):
        return item.get("fact_type")

    return getattr(item, "fact_type", None)


def wait_for_memory(
    memory_service,
    bank_id,
    max_wait_seconds=30,
):
    """
    Wait until Hindsight exposes the retained memory
    through list_memories().
    """

    print("\nWAITING FOR HINDSIGHT MEMORY PROCESSING...")

    start_time = time.time()

    attempt = 0

    while time.time() - start_time < max_wait_seconds:

        attempt += 1

        try:

            response = memory_service.list_memories(
                bank_id=bank_id,
                limit=50,
            )

            items = get_memory_units(response)

            print(
                f"Attempt {attempt}: "
                f"{len(items)} memory units available."
            )

            if items:

                print(
                    "HINDSIGHT MEMORY PROCESSING COMPLETE."
                )

                return items

        except Exception as error:

            print(
                f"Attempt {attempt}: "
                f"list_memories failed: {error}"
            )

        time.sleep(2)

    print(
        "\nWARNING: Memory did not become visible "
        "within the waiting period."
    )

    return []


def print_memory_list(items):

    print("\nCURRENT HINDSIGHT MEMORY UNITS:")

    print("-" * 90)

    for index, item in enumerate(items, start=1):

        print(f"\nMEMORY {index}")

        print("-" * 90)

        print("TEXT:")
        print(get_text(item))

        print("\nTYPE:")
        print(get_fact_type(item))


def run_pair_test(
    memory_service,
    pair_number,
    test_case,
):

    bank_id = (
        f"b6-semantic-{pair_number}-"
        f"{uuid.uuid4().hex[:8]}"
    )

    print("\n")
    print("=" * 90)
    print(f"TEST {pair_number}: {test_case['name']}")
    print("=" * 90)

    print("\nBANK:")
    print(bank_id)

    print("\nBASE MEMORY:")
    print(BASE_MEMORY)

    print("\nCANDIDATE MEMORY:")
    print(test_case["candidate"])

    print("\nEXPECTED:")
    print(test_case["expected"])

    # --------------------------------------------------
    # CREATE BANK
    # --------------------------------------------------

    print("\nCREATING BANK...")

    memory_service.create_project_bank(
        bank_id=bank_id,
        project_name="B6 Semantic Dedup Test",
        project_description=(
            "Controlled experiment for semantic "
            "duplicate detection."
        ),
    )

    print("BANK CREATED")

    # --------------------------------------------------
    # RETAIN BASE MEMORY
    # --------------------------------------------------

    print("\nRETAINING BASE MEMORY...")

    base_result = memory_service.retain(
        bank_id=bank_id,
        content=BASE_MEMORY,
    )

    print("BASE RETAIN RESULT:")
    print(base_result)

    # --------------------------------------------------
    # WAIT FOR HINDSIGHT PROCESSING
    # --------------------------------------------------

    items = wait_for_memory(
        memory_service=memory_service,
        bank_id=bank_id,
        max_wait_seconds=30,
    )

    if not items:

        print(
            "\nERROR:"
            "\nHindsight did not expose the retained "
            "memory for this test."
        )

        return

    print_memory_list(items)

    # --------------------------------------------------
    # RECALL
    # --------------------------------------------------

    print("\nRECALLING USING CANDIDATE AS QUERY...")

    response = memory_service.recall(
        bank_id=bank_id,
        query=test_case["candidate"],
    )
    print("\nRECALL RESPONSE TYPE:")
    print(type(response))
    print("\nRAW RECALL RESPONSE:")
    print(response)

    items = get_recall_results(response)

    print("\nRECALL COUNT:")
    print(len(items))

    if not items:

        print(
            "\nNO RESULTS RETURNED EVEN AFTER "
            "MEMORY PROCESSING."
        )

        return

    # --------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------

    print("\nRETRIEVED MEMORIES:")

    print("-" * 90)

    for index, item in enumerate(items, start=1):

        print(f"\nRESULT {index}")

        print("-" * 90)

        print("TEXT:")
        print(get_text(item))

        print("\nTYPE:")
        print(get_fact_type(item))

        print("\nSEMANTIC SIMILARITY:")
        print(get_semantic_similarity(item))

    print("\n")
    print("=" * 90)
    print(f"END TEST {pair_number}")
    print("=" * 90)


def main():

    print("=" * 90)
    print("B6.2 SEMANTIC DUPLICATE EXPERIMENT")
    print("=" * 90)

    print("\nPurpose:")

    print(
        "Measure Hindsight semantic similarity between "
        "a known memory and four candidate categories."
    )

    print("\nCategories:")

    print("1. Exact duplicate")
    print("2. Paraphrase")
    print("3. Related but new")
    print("4. Contradiction")

    print(
        "\nImportant:"
        "\nThe experiment waits for Hindsight memory "
        "processing before recall."
    )

    memory_service = MemoryService()

    try:

        for index, test_case in enumerate(
            TEST_CASES,
            start=1,
        ):

            run_pair_test(
                memory_service=memory_service,
                pair_number=index,
                test_case=test_case,
            )

    finally:

        memory_service.close()

    print("\n")
    print("=" * 90)
    print("B6.2 EXPERIMENT COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()