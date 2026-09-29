import uuid

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.services.outcome_learning_service import (
    OutcomeLearningService,
)
from app.services.memory_learning_profile import (
    MemoryLearningProfileService,
)


BANK_ID = (
    f"c1-profile-"
    f"{uuid.uuid4().hex[:8]}"
)


def main():

    canonical = CanonicalMemoryService()

    outcome = OutcomeLearningService(
        canonical_memory_service=canonical,
    )

    profile_service = MemoryLearningProfileService(
        outcome_learning_service=outcome,
    )

    try:

        print("=" * 90)
        print("C1 MEMORY LEARNING PROFILE TEST")
        print("=" * 90)

        memory = (
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        )

        # --------------------------------------------------
        # Register canonical memory
        # --------------------------------------------------

        assert canonical.register(
            bank_id=BANK_ID,
            text=memory,
        )

        canonical_memory = (
            canonical.get_canonical_memory(
                bank_id=BANK_ID,
                text=memory,
            )
        )

        memory_id = canonical_memory["id"]

        print("\nMEMORY ID:")
        print(memory_id)

        # --------------------------------------------------
        # Record outcomes
        # --------------------------------------------------

        outcome.record_for_memory(
            bank_id=BANK_ID,
            memory_text=memory,
            outcome=OutcomeLearningService.SUCCESS,
            evidence="Integration test passed.",
        )

        outcome.record_for_memory(
            bank_id=BANK_ID,
            memory_text=memory,
            outcome=OutcomeLearningService.SUCCESS,
            evidence="Regression test passed.",
        )

        outcome.record_for_memory(
            bank_id=BANK_ID,
            memory_text=memory,
            outcome=OutcomeLearningService.FAILURE,
            evidence="Stress test failed.",
        )

        # --------------------------------------------------
        # Build learning profile
        # --------------------------------------------------

        profile = (
            profile_service.get_profile(
                bank_id=BANK_ID,
                memory_id=memory_id,
            )
        )

        print("\nLEARNING PROFILE:")
        print(profile)

        # --------------------------------------------------
        # Verify profile
        # --------------------------------------------------

        assert profile.memory_id == memory_id

        assert profile.total_outcomes == 3
        assert profile.successes == 2
        assert profile.failures == 1
        assert profile.neutral == 0

        assert profile.success_rate == (
            2 / 3
        )

        assert profile.learning_signal == (
            1 / 3
        )

        assert profile.has_evidence is True
        assert profile.is_positive is True
        assert profile.is_negative is False
        assert profile.is_neutral is False

        assert profile.reliability == 0.6

        print("\nPROFILE INTERPRETATION:")
        print(
            "has_evidence:",
            profile.has_evidence,
        )
        print(
            "is_positive:",
            profile.is_positive,
        )
        print(
            "is_negative:",
            profile.is_negative,
        )
        print(
            "reliability:",
            profile.reliability,
        )

        print("\n" + "=" * 90)
        print(
            "C1 MEMORY LEARNING PROFILE TEST PASSED"
        )
        print("=" * 90)

    finally:
        outcome.close()


if __name__ == "__main__":
    main()