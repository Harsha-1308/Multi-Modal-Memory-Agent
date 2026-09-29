import uuid

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.services.outcome_learning_service import (
    OutcomeLearningService,
)


BANK_ID = (
    f"c1-canonical-outcome-"
    f"{uuid.uuid4().hex[:8]}"
)


def main():

    canonical = CanonicalMemoryService()

    outcome = OutcomeLearningService(
        canonical_memory_service=canonical,
    )

    try:

        print("=" * 90)
        print("C1 CANONICAL MEMORY + OUTCOME INTEGRATION")
        print("=" * 90)

        # ==================================================
        # STEP 1
        # Register canonical memory
        # ==================================================

        memory = (
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        )

        registered = canonical.register(
            bank_id=BANK_ID,
            text=memory,
        )

        print("\nCANONICAL MEMORY REGISTERED:")
        print(registered)

        assert registered is True

        # ==================================================
        # STEP 2
        # Resolve canonical identity
        # ==================================================

        canonical_memory = (
            outcome.resolve_canonical_memory(
                bank_id=BANK_ID,
                memory_text=memory,
            )
        )

        print("\nCANONICAL MEMORY:")
        print(canonical_memory)

        assert canonical_memory is not None

        memory_id = canonical_memory["id"]

        assert isinstance(
            memory_id,
            int,
        )

        # ==================================================
        # STEP 3
        # Record success
        # ==================================================

        result_1 = (
            outcome.record_from_evidence(
                bank_id=BANK_ID,
                memory_text=memory,
                evidence=(
                    "Wallet integration tests passed."
                ),
            )
        )

        print("\nOUTCOME 1:")
        print(result_1)

        assert result_1["outcome"] == (
            OutcomeLearningService.SUCCESS
        )

        assert result_1["memory_id"] == memory_id

        # ==================================================
        # STEP 4
        # Record another success
        # ==================================================

        result_2 = (
            outcome.record_from_evidence(
                bank_id=BANK_ID,
                memory_text=memory,
                evidence=(
                    "Concurrency regression "
                    "test passed."
                ),
            )
        )

        print("\nOUTCOME 2:")
        print(result_2)

        assert result_2["outcome"] == (
            OutcomeLearningService.SUCCESS
        )

        assert result_2["memory_id"] == memory_id

        # ==================================================
        # STEP 5
        # Record failure
        # ==================================================

        result_3 = (
            outcome.record_from_evidence(
                bank_id=BANK_ID,
                memory_text=memory,
                evidence=(
                    "A later stress test failed "
                    "with a concurrency error."
                ),
            )
        )

        print("\nOUTCOME 3:")
        print(result_3)

        assert result_3["outcome"] == (
            OutcomeLearningService.FAILURE
        )

        assert result_3["memory_id"] == memory_id

        # ==================================================
        # STEP 6
        # Verify outcome records are linked
        # ==================================================

        outcomes = (
            outcome.get_outcomes_for_memory(
                bank_id=BANK_ID,
                memory_id=memory_id,
            )
        )

        print("\nOUTCOME RECORDS:")
        for item in outcomes:
            print(
                item["memory_id"],
                "->",
                item["outcome"],
                "->",
                item["evidence"],
            )

        assert len(outcomes) == 3

        for item in outcomes:
            assert item["memory_id"] == memory_id

        # ==================================================
        # STEP 7
        # Verify learning state
        # ==================================================

        state = (
            outcome.get_learning_state_for_memory(
                bank_id=BANK_ID,
                memory_id=memory_id,
            )
        )

        print("\nLEARNING STATE:")
        print(state)

        assert state["memory_id"] == memory_id
        assert state["total_outcomes"] == 3
        assert state["successes"] == 2
        assert state["failures"] == 1
        assert state["neutral"] == 0

        assert state["success_rate"] == (
            2 / 3
        )

        assert state["learning_signal"] == (
            1 / 3
        )

        # ==================================================
        # STEP 8
        # Verify text-based lookup resolves through
        # canonical identity
        # ==================================================

        state_by_text = (
            outcome.get_learning_state(
                bank_id=BANK_ID,
                memory_text=memory,
            )
        )

        print("\nLEARNING STATE THROUGH MEMORY TEXT:")
        print(state_by_text)

        assert state_by_text["memory_id"] == (
            memory_id
        )

        assert state_by_text["total_outcomes"] == 3

        # ==================================================
        # STEP 9
        # Verify canonical registry remains unchanged
        # ==================================================

        canonical_memories = (
            canonical.list_canonical_memories(
                BANK_ID
            )
        )

        print("\nCANONICAL REGISTRY:")
        for item in canonical_memories:
            print(
                item["id"],
                "->",
                item["original_text"],
            )

        assert len(canonical_memories) == 1
        assert canonical_memories[0]["id"] == (
            memory_id
        )

        # ==================================================
        # FINAL
        # ==================================================

        print("\n" + "=" * 90)
        print(
            "C1 CANONICAL OUTCOME INTEGRATION "
            "TEST PASSED"
        )
        print("=" * 90)

    finally:
        outcome.close()


if __name__ == "__main__":
    main()