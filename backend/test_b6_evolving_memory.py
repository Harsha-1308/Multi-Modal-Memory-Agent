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
    f"b6-evolving-{uuid.uuid4().hex[:8]}"
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


def print_result(name, result):
    print("\n")
    print("-" * 90)
    print(name)
    print("-" * 90)

    print("RETAINED:")
    print(result["retained"])

    print("\nRELATIONSHIP:")
    print(
        result["relationship"].relationship
    )

    print("\nSIMILARITY:")
    print(
        result["relationship"].similarity
    )

    print("\nREASON:")
    print(
        result["relationship"].reason
    )


def main():

    print("=" * 90)
    print("B6 EVOLVING MEMORY REGRESSION TEST")
    print("=" * 90)

    print("\nBANK:")
    print(BANK_ID)

    memory_service = MemoryService()

    canonical_service = CanonicalMemoryService(
        db_path=(
            f"b6_evolving_"
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

        # --------------------------------------------------
        # CREATE BANK
        # --------------------------------------------------

        print("\nCREATING BANK...")

        memory_service.create_project_bank(
            bank_id=BANK_ID,
            project_name="B6 Evolving Memory Test",
            project_description=(
                "Regression test for memory "
                "deduplication as the bank evolves."
            ),
        )

        # --------------------------------------------------
        # CASE 1
        # --------------------------------------------------

        result = (
            deduplication_service.retain_if_new(
                bank_id=BANK_ID,
                candidate=BASE_MEMORY,
            )
        )

        print_result(
            "CASE 1: BASE MEMORY",
            result,
        )

        assert result["retained"] is True

        # --------------------------------------------------
        # CASE 2
        # --------------------------------------------------

        result = (
            deduplication_service.retain_if_new(
                bank_id=BANK_ID,
                candidate=PARAPHRASE,
            )
        )

        print_result(
            "CASE 2: PARAPHRASE",
            result,
        )

        assert (
            result["relationship"].relationship
            == MemoryRelationshipService.SEMANTIC_DUPLICATE
        )

        assert result["retained"] is False

        # --------------------------------------------------
        # CASE 3
        # --------------------------------------------------

        result = (
            deduplication_service.retain_if_new(
                bank_id=BANK_ID,
                candidate=RELATED,
            )
        )

        print_result(
            "CASE 3: RELATED BUT NEW",
            result,
        )

        assert (
            result["relationship"].relationship
            == MemoryRelationshipService.RELATED_NEW
        )

        assert result["retained"] is True

        # --------------------------------------------------
        # CASE 4
        # --------------------------------------------------

        result = (
            deduplication_service.retain_if_new(
                bank_id=BANK_ID,
                candidate=CONTRADICTION,
            )
        )

        print_result(
            "CASE 4: CONTRADICTION",
            result,
        )

        assert (
            result["relationship"].relationship
            == MemoryRelationshipService.CONTRADICTION
        )

        assert result["retained"] is True

        # --------------------------------------------------
        # FINAL REGISTRY CHECK
        # --------------------------------------------------

        print("\n")
        print("=" * 90)
        print("FINAL CANONICAL REGISTRY CHECK")
        print("=" * 90)

        memories = [
            BASE_MEMORY,
            PARAPHRASE,
            RELATED,
            CONTRADICTION,
        ]

        for index, memory in enumerate(
            memories,
            start=1,
        ):

            stored = (
                canonical_service.get_memory(
                    bank_id=BANK_ID,
                    text=memory,
                )
            )

            print(
                f"\nMEMORY {index}:"
            )

            print(
                "REGISTERED:",
                stored is not None,
            )

        print("\n")
        print("=" * 90)
        print(
            "B6 EVOLVING MEMORY TEST PASSED"
        )
        print("=" * 90)

    finally:

        deduplication_service.close()


if __name__ == "__main__":
    main()