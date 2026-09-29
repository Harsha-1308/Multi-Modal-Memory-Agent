import uuid

from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.services.memory_relationship_service import (
    MemoryRelationshipService,
)
from app.services.memory_deduplication_service import (
    MemoryDeduplicationService,
)


BASE_MEMORY = (
    "Pessimistic database locking resolved "
    "the wallet concurrency problem."
)

TEST_CASES = [
    {
        "name": "EXACT DUPLICATE",
        "candidate": BASE_MEMORY,
        "expected": "exact_duplicate",
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


def run_test(test_number, test_case):
    print("\n")
    print("=" * 90)
    print(
        f"TEST {test_number}: "
        f"{test_case['name']}"
    )
    print("=" * 90)

    bank_id = (
        f"b6-controlled-"
        f"{uuid.uuid4().hex[:8]}"
    )

    print("\nBANK:")
    print(bank_id)

    memory_service = MemoryService()

    canonical_service = CanonicalMemoryService(
        db_path=(
            f"b6_controlled_"
            f"{uuid.uuid4().hex[:8]}.db"
        )
    )

    relationship_service = (
    MemoryRelationshipService()
)

    deduplication_service = (
        MemoryDeduplicationService(
            memory_service=memory_service,
            canonical_memory_service=canonical_service,
            relationship_service=relationship_service,
        )
    )

    try:
        print("\nCREATING BANK...")

        memory_service.create_project_bank(
            bank_id=bank_id,
            project_name="B6 Controlled Test",
            project_description=(
                "Controlled B6 relationship test."
            ),
        )

        print("\nRETAINING BASE MEMORY...")

        first = deduplication_service.retain_if_new(
            bank_id=bank_id,
            candidate=BASE_MEMORY,
        )

        print("\nBASE RESULT:")
        print(first)

        print("\nTESTING CANDIDATE:")

        result = deduplication_service.analyze(
            bank_id=bank_id,
            candidate=test_case["candidate"],
        )

        print(result)

        print("\nEXPECTED:")
        print(test_case["expected"])

        print("\nACTUAL:")
        print(result.relationship)

        assert (
            result.relationship
            == test_case["expected"]
        )

        print("\nPASS")

    finally:
        deduplication_service.close()


def main():
    print("=" * 90)
    print("B6 CONTROLLED INTEGRATION TEST")
    print("=" * 90)

    for index, test_case in enumerate(
        TEST_CASES,
        start=1,
    ):
        run_test(
            test_number=index,
            test_case=test_case,
        )

    print("\n")
    print("=" * 90)
    print("ALL CONTROLLED B6 TESTS PASSED")
    print("=" * 90)


if __name__ == "__main__":
    main()