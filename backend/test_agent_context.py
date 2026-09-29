from app.services.agent_service import AgentService


BANK_ID = "demo-project-001"


def run_test(agent, label, question, memory_enabled=True):

    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)

    print("\nQUESTION:")
    print(question)

    print("\nMEMORY ENABLED:")
    print(memory_enabled)

    result = agent.answer(
        bank_id=BANK_ID,
        question=question,
        memory_enabled=memory_enabled,
    )

    print("\nMEMORY COUNT:")
    print(result["memory_count"])

    print("\nMEMORIES USED:")
    for memory in result["memories_used"]:
        print(memory)

    print("\nANSWER:")
    print(result["answer"])


def main():

    agent = AgentService()

    # 1. Completely unrelated
    run_test(
        agent,
        "UNRELATED TCP UDP",
        "What is the difference between TCP and UDP?",
        True,
    )

    # 2. Historical incident
    run_test(
        agent,
        "PREVIOUS INCIDENT",
        "What happened previously with the concurrent wallet update failures?",
        True,
    )

    # 3. Solution
    run_test(
        agent,
        "PREVIOUS SOLUTION",
        "How was the concurrent wallet update problem solved previously?",
        True,
    )

    # 4. Current recurrence
    run_test(
        agent,
        "CURRENT RECURRENCE",
        (
            "The wallet update is failing concurrently again. "
            "What should we investigate based on what happened previously?"
        ),
        True,
    )

    # 5. Memory OFF
    run_test(
        agent,
        "MEMORY OFF",
        "What happened previously with the concurrent wallet update failures?",
        False,
    )

    agent.close()


if __name__ == "__main__":
    main()