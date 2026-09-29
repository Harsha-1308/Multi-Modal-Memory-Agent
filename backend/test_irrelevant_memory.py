from app.services.agent_service import AgentService


BANK_ID = "demo-project-001"


def main():
    agent = AgentService()

    question = (
        "What is the difference between TCP and UDP?"
    )

    result = agent.answer(
        bank_id=BANK_ID,
        question=question,
        memory_enabled=True,
    )

    print("=" * 70)
    print("QUESTION")
    print("=" * 70)
    print(question)

    print("\n")
    print("=" * 70)
    print("ANSWER")
    print("=" * 70)
    print(result["answer"])

    print("\n")
    print("=" * 70)
    print("MEMORY COUNT")
    print("=" * 70)
    print(result["memory_count"])

    print("\n")
    print("=" * 70)
    print("MEMORIES USED")
    print("=" * 70)

    for memory in result["memories_used"]:
        print("----------------------------------------")
        print(memory)

    agent.close()


if __name__ == "__main__":
    main()