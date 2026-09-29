from app.services.agent_service import AgentService


BANK_ID = "demo-project-001"


def main():

    agent = AgentService()

    question = (
        "The wallet update is failing concurrently again. "
        "What should we investigate based on what happened previously?"
    )

    print("\n" + "=" * 80)
    print("GROUNDING TEST")
    print("=" * 80)

    print("\nQUESTION:")
    print(question)

    result = agent.answer(
        bank_id=BANK_ID,
        question=question,
        memory_enabled=True,
    )

    print("\nMEMORY COUNT:")
    print(result["memory_count"])

    print("\nMEMORIES USED:")

    for memory in result["memories_used"]:
        print(memory)

    print("\nANSWER:")
    print(result["answer"])

    agent.close()


if __name__ == "__main__":
    main()