import uuid

from app.services.memory_service import MemoryService


BANK_ID = f"b6-retain-{uuid.uuid4().hex[:8]}"

MEMORY = (
    "Pessimistic database locking resolved "
    "the wallet concurrency problem."
)


def main():

    service = MemoryService()

    try:

        service.create_project_bank(
            bank_id=BANK_ID,
            project_name="B6 Retain Structure Test",
            project_description=(
                "Inspect Hindsight retain response."
            ),
        )

        result = service.retain(
            bank_id=BANK_ID,
            content=MEMORY,
        )

        print("=" * 80)
        print("B6 RETAIN STRUCTURE")
        print("=" * 80)

        print("\nTYPE:")
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