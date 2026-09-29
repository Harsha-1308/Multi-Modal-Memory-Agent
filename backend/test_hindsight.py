import os

from dotenv import load_dotenv
from hindsight_client import Hindsight


load_dotenv()


def main():
    api_key = os.getenv("HINDSIGHT_API_KEY")
    base_url = os.getenv(
        "HINDSIGHT_BASE_URL",
        "https://api.hindsight.vectorize.io"
    )

    if not api_key:
        raise RuntimeError("HINDSIGHT_API_KEY is missing")

    client = Hindsight(
        base_url=base_url,
        api_key=api_key,
    )

    bank_id = "demo-project-001"

    try:
        print("Creating memory bank...")

        bank = client.create_bank(
            bank_id=bank_id,
            name="Demo Project 001",
            background=(
                "A generic project workspace used to test "
                "project-specific AI memory."
            ),
        )

        print("Bank created:")
        print(bank)

        print("\nRetaining project experience...")

        client.retain(
            bank_id=bank_id,
            content="""
            Project incident:

            The payment service experienced concurrent wallet
            update failures.

            The team first attempted application-level retries.
            That approach did not resolve the concurrency problem.

            The final solution was pessimistic database locking.
            After applying the locking strategy, the integration
            tests passed successfully.

            This was a successful project-level resolution.
            """
        )

        print("Memory retained.")

        print("\nRecalling memory...")

        result = client.recall(
            bank_id=bank_id,
            query=(
                "What happened previously with concurrent "
                "wallet update failures?"
            ),
        )

        print("\nRECALLED MEMORIES:")

        for memory in result.results:
            print("--------------------------------")
            print(memory.text)

        print("\nReflecting...")

        response = client.reflect(
            bank_id=bank_id,
            query=(
                "We are seeing another concurrent wallet "
                "update problem. Based on previous project "
                "experience, what should we investigate?"
            ),
        )

        print("\nREFLECTION:")
        print(response.text)

    finally:
        client.close()


if __name__ == "__main__":
    main()