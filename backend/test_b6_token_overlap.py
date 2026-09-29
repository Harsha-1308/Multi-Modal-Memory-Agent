from app.services.memory_relationship_service import (
    MemoryRelationshipService,
)

service = MemoryRelationshipService()

BASE = (
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

cases = [
    ("PARAPHRASE", PARAPHRASE, 0.8195942640304565),
    ("RELATED", RELATED, 0.7866465556603575),
    ("CONTRADICTION", CONTRADICTION, 0.8382218826347062),
]

for name, candidate, similarity in cases:

    overlap = service.calculate_token_overlap(
        candidate,
        BASE,
    )

    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    print("Semantic similarity:", similarity)
    print("Token overlap:", overlap)

    print(
        "Candidate tokens:",
        service.remove_stop_words(
            service.token_set(candidate)
        ),
    )

    print(
        "Base tokens:",
        service.remove_stop_words(
            service.token_set(BASE)
        ),
    )