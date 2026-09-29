from app.integrations.groq_client import GroqClient


def main():
    client = GroqClient()

    answer = client.generate(
        system_prompt=(
            "You are a helpful software engineering assistant."
        ),
        user_prompt=(
            "Explain what a database race condition is "
            "in simple terms."
        ),
    )

    print("\nGROQ RESPONSE:")
    print(answer)


if __name__ == "__main__":
    main()