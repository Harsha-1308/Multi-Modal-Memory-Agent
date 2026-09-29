from app.services.outcome_learning_service import (
    OutcomeLearningService,
)


import uuid

BANK_ID = f"c1-classification-test-{uuid.uuid4().hex[:8]}"

def main():

    service = OutcomeLearningService()

    try:

        print("=" * 90)
        print("C1 OUTCOME CLASSIFICATION + LEARNING TEST")
        print("=" * 90)

        # ==================================================
        # MEMORY 1
        # ==================================================

        memory_success = (
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        )

        evidence_success = (
            "Wallet integration tests passed successfully."
        )

        result = service.record_from_evidence(
            bank_id=BANK_ID,
            memory_text=memory_success,
            evidence=evidence_success,
        )

        print("\nCASE 1: SUCCESS")
        print(result)

        assert result["outcome"] == (
            OutcomeLearningService.SUCCESS
        )

        # ==================================================
        # MEMORY 1 - SECOND SUCCESS
        # ==================================================

        evidence_success_2 = (
            "The concurrency regression test passed."
        )

        result = service.record_from_evidence(
            bank_id=BANK_ID,
            memory_text=memory_success,
            evidence=evidence_success_2,
        )

        print("\nCASE 2: SECOND SUCCESS")
        print(result)

        assert result["outcome"] == (
            OutcomeLearningService.SUCCESS
        )

        # ==================================================
        # MEMORY 1 - FAILURE
        # ==================================================

        evidence_failure = (
            "A later stress test failed with a "
            "concurrency error."
        )

        result = service.record_from_evidence(
            bank_id=BANK_ID,
            memory_text=memory_success,
            evidence=evidence_failure,
        )

        print("\nCASE 3: FAILURE")
        print(result)

        assert result["outcome"] == (
            OutcomeLearningService.FAILURE
        )

        # ==================================================
        # MEMORY 2 - NEUTRAL
        # ==================================================

        memory_neutral = (
            "The database configuration was changed."
        )

        evidence_neutral = (
            "The configuration file was updated."
        )

        result = service.record_from_evidence(
            bank_id=BANK_ID,
            memory_text=memory_neutral,
            evidence=evidence_neutral,
        )

        print("\nCASE 4: NEUTRAL")
        print(result)

        assert result["outcome"] == (
            OutcomeLearningService.NEUTRAL
        )

        # ==================================================
        # LEARNING STATE
        # ==================================================

        state = service.get_learning_state(
            bank_id=BANK_ID,
            memory_text=memory_success,
        )

        print("\nLEARNING STATE:")
        print(state)

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
        # NEUTRAL STATE
        # ==================================================

        neutral_state = service.get_learning_state(
            bank_id=BANK_ID,
            memory_text=memory_neutral,
        )

        print("\nNEUTRAL LEARNING STATE:")
        print(neutral_state)

        assert neutral_state["total_outcomes"] == 1
        assert neutral_state["successes"] == 0
        assert neutral_state["failures"] == 0
        assert neutral_state["neutral"] == 1

        assert neutral_state["learning_signal"] == 0.0

        # ==================================================
        # FINAL
        # ==================================================

        print("\n" + "=" * 90)
        print(
            "C1 OUTCOME CLASSIFICATION + "
            "LEARNING TEST PASSED"
        )
        print("=" * 90)

    finally:
        service.close()


if __name__ == "__main__":
    main()