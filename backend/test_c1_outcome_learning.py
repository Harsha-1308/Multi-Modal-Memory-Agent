from app.services.outcome_learning_service import (
    OutcomeLearningService,
)


BANK_ID = "c1-outcome-test"


def main():

    service = OutcomeLearningService()

    try:

        print("=" * 90)
        print("C1 OUTCOME LEARNING TEST")
        print("=" * 90)

        memory = (
            "Pessimistic database locking resolved "
            "the wallet concurrency problem."
        )

        # -----------------------------------------------
        # Outcome 1
        # -----------------------------------------------

        outcome_id = service.record_outcome(
            bank_id=BANK_ID,
            memory_text=memory,
            outcome=OutcomeLearningService.SUCCESS,
            evidence="Wallet integration tests passed.",
        )

        print("\nOUTCOME 1 ID:")
        print(outcome_id)

        # -----------------------------------------------
        # Outcome 2
        # -----------------------------------------------

        outcome_id = service.record_outcome(
            bank_id=BANK_ID,
            memory_text=memory,
            outcome=OutcomeLearningService.SUCCESS,
            evidence="Concurrency regression test passed.",
        )

        print("\nOUTCOME 2 ID:")
        print(outcome_id)

        # -----------------------------------------------
        # Outcome 3
        # -----------------------------------------------

        outcome_id = service.record_outcome(
            bank_id=BANK_ID,
            memory_text=memory,
            outcome=OutcomeLearningService.FAILURE,
            evidence="A later stress test exposed another concurrency issue.",
        )

        print("\nOUTCOME 3 ID:")
        print(outcome_id)

        # -----------------------------------------------
        # Get raw outcomes
        # -----------------------------------------------

        outcomes = service.get_outcomes(
            bank_id=BANK_ID,
            memory_text=memory,
        )

        print("\nRECORDED OUTCOMES:")
        for outcome in outcomes:
            print(
                outcome["outcome"],
                "->",
                outcome["evidence"],
            )

        # -----------------------------------------------
        # Get aggregate learning state
        # -----------------------------------------------

        state = service.get_learning_state(
            bank_id=BANK_ID,
            memory_text=memory,
        )

        print("\nLEARNING STATE:")
        print(state)

        # -----------------------------------------------
        # Assertions
        # -----------------------------------------------

        assert len(outcomes) == 3

        assert state["total_outcomes"] == 3
        assert state["successes"] == 2
        assert state["failures"] == 1
        assert state["neutral"] == 0

        assert state["success_rate"] == 2 / 3

        print("\n" + "=" * 90)
        print("C1 OUTCOME LEARNING TEST PASSED")
        print("=" * 90)

    finally:
        service.close()


if __name__ == "__main__":
    main()