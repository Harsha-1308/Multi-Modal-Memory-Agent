from app.services.memory_deduplication_service import (
    MemoryDeduplicationService,
)
from app.services.memory_relationship_service import (
    MemoryRelationshipService,
)


BANK_ID = "b6-final-regression"


def assert_relationship(result, expected):
    actual = result["relationship"].relationship

    assert actual == expected, (
        f"Expected {expected}, got {actual}"
    )


def main():

    service = MemoryDeduplicationService()

    try:

        print("=" * 90)
        print("B6 FINAL REGRESSION TEST")
        print("=" * 90)

        # --------------------------------------------------
        # 1. BASE MEMORY
        # --------------------------------------------------

        base = (
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        )

        result = service.retain_if_new(
            bank_id=BANK_ID,
            candidate=base,
        )

        assert result["retained"] is True
        assert_relationship(
            result,
            MemoryRelationshipService.RELATED_NEW,
        )

        print("1. BASE MEMORY                PASS")

        # --------------------------------------------------
        # 2. EXACT DUPLICATE
        # --------------------------------------------------

        result = service.retain_if_new(
            bank_id=BANK_ID,
            candidate=base,
        )

        assert result["retained"] is False
        assert_relationship(
            result,
            MemoryRelationshipService.EXACT_DUPLICATE,
        )

        print("2. EXACT DUPLICATE             PASS")

        # --------------------------------------------------
        # 3. SEMANTIC DUPLICATE
        # --------------------------------------------------

        paraphrase = (
            "The wallet concurrency issue was fixed "
            "successfully using pessimistic locking."
        )

        result = service.retain_if_new(
            bank_id=BANK_ID,
            candidate=paraphrase,
        )

        assert result["retained"] is False
        assert_relationship(
            result,
            MemoryRelationshipService.SEMANTIC_DUPLICATE,
        )

        print("3. SEMANTIC DUPLICATE          PASS")

        # --------------------------------------------------
        # 4. RELATED BUT NEW
        # --------------------------------------------------

        related = (
            "Pessimistic locking increased database "
            "contention during high-volume transactions."
        )

        result = service.retain_if_new(
            bank_id=BANK_ID,
            candidate=related,
        )

        assert result["retained"] is True
        assert_relationship(
            result,
            MemoryRelationshipService.RELATED_NEW,
        )

        print("4. RELATED BUT NEW             PASS")

        # --------------------------------------------------
        # 5. CONTRADICTION
        # --------------------------------------------------

        contradiction = (
            "Pessimistic database locking failed to "
            "resolve the wallet concurrency problem."
        )

        result = service.retain_if_new(
            bank_id=BANK_ID,
            candidate=contradiction,
        )

        assert result["retained"] is True
        assert_relationship(
            result,
            MemoryRelationshipService.CONTRADICTION,
        )

        print("5. CONTRADICTION               PASS")

        # --------------------------------------------------
        # 6. FINAL CANONICAL REGISTRY
        # --------------------------------------------------

        memories = (
            service.canonical_memory_service
            .list_canonical_memories(BANK_ID)
        )

        assert len(memories) == 3

        texts = {
            memory["original_text"]
            for memory in memories
        }

        assert base in texts
        assert related in texts
        assert contradiction in texts
        assert paraphrase not in texts

        print("6. CANONICAL REGISTRY          PASS")

        print()
        print("=" * 90)
        print("B6 FINAL REGRESSION TEST PASSED")
        print("=" * 90)

    finally:
        service.close()


if __name__ == "__main__":
    main()