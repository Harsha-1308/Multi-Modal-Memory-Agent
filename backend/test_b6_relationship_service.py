from app.services.memory_relationship_service import (
    MemoryRelationshipService,
)


def test_exact_duplicate():
    service = MemoryRelationshipService()

    result = service.classify(
        candidate=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        existing=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        semantic_similarity=0.9363,
    )

    print("\nTEST 1: EXACT DUPLICATE")
    print(result)

    assert (
        result.relationship
        == service.EXACT_DUPLICATE
    )


def test_paraphrase():
    service = MemoryRelationshipService(
        
    )

    result = service.classify(
        candidate=(
            "The wallet concurrency issue was fixed "
            "successfully using pessimistic locking."
        ),
        existing=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        semantic_similarity=0.9123,
    )

    print("\nTEST 2: PARAPHRASE")
    print(result)

    assert (
        result.relationship
        == service.SEMANTIC_DUPLICATE
    )


def test_related_new():
    service = MemoryRelationshipService(
        
    )

    result = service.classify(
        candidate=(
            "Pessimistic locking increased database "
            "contention during high-volume transactions."
        ),
        existing=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        semantic_similarity=0.8197,
    )

    print("\nTEST 3: RELATED BUT NEW")
    print(result)

    assert (
        result.relationship
        == service.RELATED_NEW
    )


def test_contradiction():
    service = MemoryRelationshipService(
        
    )

    result = service.classify(
        candidate=(
            "Pessimistic database locking failed to "
            "resolve the wallet concurrency problem."
        ),
        existing=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        semantic_similarity=0.9093,
    )

    print("\nTEST 4: CONTRADICTION")
    print(result)

    assert (
        result.relationship
        == service.CONTRADICTION
    )


def test_low_similarity_is_related():
    service = MemoryRelationshipService(
        
    )

    result = service.classify(
        candidate=(
            "The database monitoring dashboard was "
            "updated for production."
        ),
        existing=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        semantic_similarity=0.30,
    )

    print("\nTEST 5: LOW SIMILARITY")
    print(result)

    assert (
        result.relationship
        == service.RELATED_NEW
    )


def test_high_similarity_without_negation_is_duplicate():
    service = MemoryRelationshipService(
       
    )

    result = service.classify(
        candidate=(
            "The wallet concurrency issue was "
            "successfully fixed with pessimistic locking."
        ),
        existing=(
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        ),
        semantic_similarity=0.90,
    )

    print("\nTEST 6: HIGH SIMILARITY")
    print(result)

    assert (
        result.relationship
        == service.SEMANTIC_DUPLICATE
    )


def main():
    print("=" * 90)
    print("B6 RELATIONSHIP SERVICE TEST")
    print("=" * 90)

    test_exact_duplicate()
    test_paraphrase()
    test_related_new()
    test_contradiction()
    test_low_similarity_is_related()
    test_high_similarity_without_negation_is_duplicate()

    print("\n")
    print("=" * 90)
    print("ALL B6 RELATIONSHIP TESTS PASSED")
    print("=" * 90)


if __name__ == "__main__":
    main()