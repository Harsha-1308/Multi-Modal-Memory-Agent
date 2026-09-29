from app.services.memory_decision import MemoryDecisionService


def run_test(service, label, content):

    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)

    print("\nINPUT:")
    print(content)

    result = service.decide(content)

    print("\nDECISION:")
    print(result)

    print("\nSHOULD RETAIN:")
    print(result["should_retain"])

    print("\nMEMORY TYPE:")
    print(result["memory_type"])

    print("\nIMPORTANCE:")
    print(result["importance"])

    print("\nREASON:")
    print(result["reason"])


def main():

    service = MemoryDecisionService()

    # ============================================================
    # SHOULD NOT RETAIN
    # ============================================================

    run_test(
        service,
        "GREETING",
        "Hello",
    )

    run_test(
        service,
        "ACKNOWLEDGEMENT",
        "Okay, thanks.",
    )

    run_test(
        service,
        "GENERIC KNOWLEDGE",
        "TCP is a transport-layer protocol.",
    )

    # ============================================================
    # SHOULD RETAIN
    # ============================================================

    run_test(
        service,
        "PROJECT FACT",
        (
            "Our payment service uses pessimistic database "
            "locking for concurrent wallet updates."
        ),
    )

    run_test(
        service,
        "FAILED APPROACH",
        (
            "We tried application-level retries for the wallet "
            "concurrency problem, but the approach failed."
        ),
    )

    run_test(
        service,
        "PROJECT OUTCOME",
        (
            "Pessimistic database locking resolved the wallet "
            "concurrency problem and the integration tests passed."
        ),
    )

    service.close()


if __name__ == "__main__":
    main()