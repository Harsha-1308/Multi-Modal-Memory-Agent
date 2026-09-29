import uuid

from app.services.memory_service import MemoryService


BANK_ID = f"b6-recall-{uuid.uuid4().hex[:8]}"

MEMORY = (
    "Pessimistic database locking resolved "
    "the wallet concurrency problem."
)


def main():

    service = MemoryService()

    try:

        service.create_project_bank(
            bank_id=BANK_ID,
            project_name="B6 Recall Structure Test",
            project_description=(
                "Inspect Hindsight recall result structure."
            ),
        )

        service.retain(
            bank_id=BANK_ID,
            content=MEMORY,
        )

        response = service.recall(
            bank_id=BANK_ID,
            query=MEMORY,
        )

        print("=" * 80)
        print("B6 RECALL STRUCTURE")
        print("=" * 80)

        results = getattr(
            response,
            "results",
            [],
        )

        print("RESULT COUNT:", len(results))

        for index, result in enumerate(
            results,
            start=1,
        ):

            print("\n" + "-" * 80)
            print("RESULT", index)
            print("-" * 80)

            print("TYPE:")
            print(type(result))

            print("\nRAW RESULT:")
            print(result)

            print("\nATTRIBUTES:")
            print(
                getattr(
                    result,
                    "__dict__",
                    "NO __dict__",
                )
            )

    finally:
        service.close()


if __name__ == "__main__":
    main()