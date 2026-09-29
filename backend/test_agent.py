from app.services.agent_service import AgentService


BANK_ID = "demo-project-001"


def main():
    agent = AgentService()

    question = (
        "The wallet update is failing concurrently again. "
        "What should we investigate first?"
    )

    # =====================================================
    # MEMORY OFF
    # =====================================================

    print("=" * 70)
    print("MEMORY OFF")
    print("=" * 70)

    result_without_memory = agent.answer(
        bank_id=BANK_ID,
        question=question,
        memory_enabled=False,
    )

    print("\nANSWER:")
    print(result_without_memory["answer"])

    print("\nMEMORY COUNT:")
    print(result_without_memory["memory_count"])

    # =====================================================
    # MEMORY ON
    # =====================================================

    print("\n")
    print("=" * 70)
    print("MEMORY ON")
    print("=" * 70)

    result_with_memory = agent.answer(
        bank_id=BANK_ID,
        question=question,
        memory_enabled=True,
    )

    print("\nANSWER:")
    print(result_with_memory["answer"])

    print("\nMEMORY COUNT:")
    print(result_with_memory["memory_count"])

    print("\nMEMORIES USED:")

    for memory in result_with_memory["memories_used"]:
        print("----------------------------------------")
        print(memory)

    agent.close()


if __name__ == "__main__":
    main()