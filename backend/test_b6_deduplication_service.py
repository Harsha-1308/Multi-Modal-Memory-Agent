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


BANK_ID = (
    f"b6-integration-{uuid.uuid4().hex[:8]}"
)

BASE_MEMORY = (
    "Pessimistic database locking resolved "
    "the wallet concurrency problem."
)

PARAPHRASE = (
    "The wallet concurrency issue was fixed "
    "successfully using pessimistic locking."
)

RELATED = (
    "Pessimistic locking increased database "
    "contention during high-volume transactions."
)

CONTRADICTION = (
    "Pessimistic database locking failed to "
    "resolve the wallet concurrency problem."
)


def main():
    print("=" * 90)
    print("B6 DEDUPLICATION SERVICE INTEGRATION TEST")
    print("=" * 90)

    memory_service = MemoryService()

    canonical_service = CanonicalMemoryService(
        db_path=(
            f"b6_integration_{uuid.uuid4().hex[:8]}.db"
        )
    )

    relationship_service = (
        MemoryRelationshipService(
            semantic_duplicate_threshold=0.88
        )
    )

    deduplication_service = (
        MemoryDeduplicationService(
            memory_service=memory_service,
            canonical_memory_service=canonical_service,
            relationship_service=relationship_service,
        )
    )

    try:
        print("\nBANK:")
        print(BANK_ID)

        print("\nCREATING BANK...")

        memory_service.create_project_bank(
            bank_id=BANK_ID,
            project_name="B6 Dedup Integration",
            project_description=(
                "Integration test for canonical memory "
                "deduplication."
            ),
        )

        # --------------------------------------------------
        # 1. First memory
        # --------------------------------------------------

        print("\n")
        print("-" * 90)
        print("CASE 1: FIRST MEMORY")
        print("-" * 90)

        result = deduplication_service.retain_if_new(
            bank_id=BANK_ID,
            candidate=BASE_MEMORY,
        )

        print(result)

        assert result["retained"] is True

        # --------------------------------------------------
        # 2. Exact duplicate
        # --------------------------------------------------

        print("\n")
        print("-" * 90)
        print("CASE 2: EXACT DUPLICATE")
        print("-" * 90)

        result = deduplication_service.retain_if_new(
            bank_id=BANK_ID,
            candidate=BASE_MEMORY,
        )

        print(result)

        assert result["retained"] is False

        assert (
            result["relationship"].relationship
            == MemoryRelationshipService.EXACT_DUPLICATE
        )

        # --------------------------------------------------
        # 3. Paraphrase
        # --------------------------------------------------

        print("\n")
        print("-" * 90)
        print("CASE 3: PARAPHRASE")
        print("-" * 90)

        result = deduplication_service.retain_if_new(
            bank_id=BANK_ID,
            candidate=PARAPHRASE,
        )

        print(result)

        # --------------------------------------------------
        # 4. Related
        # --------------------------------------------------

        print("\n")
        print("-" * 90)
        print("CASE 4: RELATED BUT NEW")
        print("-" * 90)

        result = deduplication_service.retain_if_new(
            bank_id=BANK_ID,
            candidate=RELATED,
        )

        print(result)

        # --------------------------------------------------
        # 5. Contradiction
        # --------------------------------------------------

        print("\n")
        print("-" * 90)
        print("CASE 5: CONTRADICTION")
        print("-" * 90)

        result = deduplication_service.retain_if_new(
            bank_id=BANK_ID,
            candidate=CONTRADICTION,
        )

        print(result)

        print("\n")
        print("=" * 90)
        print("B6 INTEGRATION TEST COMPLETE")
        print("=" * 90)

    finally:
        deduplication_service.close()


if __name__ == "__main__":
    main()