import time
import uuid

from app.services.memory_service import MemoryService


BANK_ID = f"b6-diagnostic-{uuid.uuid4().hex[:8]}"

BASE_MEMORY = (
    "Pessimistic database locking resolved the "
    "wallet concurrency problem."
)


QUERY = (
    "Pessimistic database locking resolved the "
    "wallet concurrency problem."
)


def get_results(response):
    """
    Extract Recall results from Hindsight.
    """

    results = getattr(response, "results", None)

    if results is None and isinstance(response, dict):
        results = response.get("results")

    return results or []


def get_items(response):
    """
    Extract list_memories items.
    """

    items = getattr(response, "items", None)

    if items is None and isinstance(response, dict):
        items = response.get("items")

    return items or []


def print_recall(response, label):

    print("\n")
    print("=" * 90)
    print(label)
    print("=" * 90)

    print("\nRECALL RESPONSE TYPE:")
    print(type(response))

    print("\nRAW RECALL RESPONSE:")
    print(response)

    results = get_results(response)

    print("\nRECALL RESULTS COUNT:")
    print(len(results))

    for index, result in enumerate(results, start=1):

        print("\nRESULT", index)
        print("-" * 90)

        print("TEXT:")
        print(
            getattr(result, "text", None)
            if not isinstance(result, dict)
            else result.get("text")
        )

        print("\nSEMANTIC SIMILARITY:")

        if isinstance(result, dict):

            print(
                result.get("semantic_similarity")
            )

        else:

            print(
                getattr(
                    result,
                    "semantic_similarity",
                    None,
                )
            )


def print_list(response, label):

    print("\n")
    print("=" * 90)
    print(label)
    print("=" * 90)

    print("\nLIST RESPONSE TYPE:")
    print(type(response))

    print("\nRAW LIST RESPONSE:")
    print(response)

    items = get_items(response)

    print("\nMEMORY ITEMS COUNT:")
    print(len(items))


def main():

    memory_service = MemoryService()

    try:

        print("=" * 90)
        print("B6 HINDSIGHT RECALL DIAGNOSTIC")
        print("=" * 90)

        print("\nBANK:")
        print(BANK_ID)

        print("\nBASE MEMORY:")
        print(BASE_MEMORY)

        print("\nQUERY:")
        print(QUERY)

        # --------------------------------------------------
        # CREATE BANK
        # --------------------------------------------------

        print("\nCREATING BANK...")

        bank_result = memory_service.create_project_bank(
            bank_id=BANK_ID,
            project_name="B6 Hindsight Diagnostic",
            project_description=(
                "Diagnostic bank for testing Hindsight "
                "retain, list, and recall behavior."
            ),
        )

        print("\nBANK RESULT:")
        print(bank_result)

        # --------------------------------------------------
        # RETAIN
        # --------------------------------------------------

        print("\nRETAINING MEMORY...")

        retain_result = memory_service.retain(
            bank_id=BANK_ID,
            content=BASE_MEMORY,
        )

        print("\nRETAIN RESULT:")
        print(retain_result)

        # --------------------------------------------------
        # IMMEDIATE LIST
        # --------------------------------------------------

        list_response = memory_service.list_memories(
            bank_id=BANK_ID,
            limit=50,
        )

        print_list(
            list_response,
            "IMMEDIATE LIST_MEMORIES",
        )

        # --------------------------------------------------
        # IMMEDIATE RECALL
        # --------------------------------------------------

        recall_response = memory_service.recall(
            bank_id=BANK_ID,
            query=QUERY,
        )

        print_recall(
            recall_response,
            "IMMEDIATE RECALL",
        )

        # --------------------------------------------------
        # WAIT AND RETRY
        # --------------------------------------------------

        print("\n")
        print("=" * 90)
        print("WAITING FOR HINDSIGHT")
        print("=" * 90)

        for attempt in range(1, 11):

            time.sleep(3)

            print(
                f"\nWAIT ATTEMPT {attempt}"
            )

            # ------------------------------
            # LIST
            # ------------------------------

            list_response = (
                memory_service.list_memories(
                    bank_id=BANK_ID,
                    limit=50,
                )
            )

            items = get_items(list_response)

            print(
                "LIST MEMORY COUNT:",
                len(items),
            )

            # ------------------------------
            # RECALL
            # ------------------------------

            recall_response = (
                memory_service.recall(
                    bank_id=BANK_ID,
                    query=QUERY,
                )
            )

            results = get_results(
                recall_response
            )

            print(
                "RECALL RESULT COUNT:",
                len(results),
            )

            if items or results:

                print("\nMEMORY IS NOW AVAILABLE.")

                print_list(
                    list_response,
                    "LIST_MEMORIES AFTER WAIT",
                )

                print_recall(
                    recall_response,
                    "RECALL AFTER WAIT",
                )

                break

        else:

            print("\n")
            print("=" * 90)
            print("MEMORY NEVER BECAME AVAILABLE")
            print("=" * 90)

    finally:

        memory_service.close()


if __name__ == "__main__":
    main()