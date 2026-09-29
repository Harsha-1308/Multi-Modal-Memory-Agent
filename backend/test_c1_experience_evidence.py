import os
import uuid

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.services.experience_service import (
    ExperienceService,
)
from app.services.evidence_service import (
    EvidenceService,
)
from app.services.experience_evidence_service import (
    ExperienceEvidenceService,
)
from app.repositories.sqlite.learning_repository import (
    SQLiteLearningRepository,
)


print("=" * 90)
print("C1 EXPERIENCE + EVIDENCE FOUNDATION TEST")
print("=" * 90)


# ---------------------------------------------------------
# UNIQUE TEST DATABASE
# ---------------------------------------------------------

db_path = (
    f"test_c1_experience_"
    f"{uuid.uuid4().hex[:8]}.db"
)

bank_id = (
    f"c1-experience-{uuid.uuid4().hex[:8]}"
)

canonical = None
repository = None
experience_service = None
evidence_service = None
chain_service = None


try:

    # -----------------------------------------------------
    # 1. CREATE CANONICAL MEMORY
    # -----------------------------------------------------

    canonical = CanonicalMemoryService(
        db_path=db_path
    )

    memory_text = (
        "Pessimistic database locking resolved "
        "the wallet concurrency problem."
    )

    registered = canonical.register(
        bank_id=bank_id,
        text=memory_text,
    )

    assert registered is True

    canonical_memory = canonical.get_memory(
        bank_id=bank_id,
        text=memory_text,
    )

    assert canonical_memory is not None

    memory_id = canonical_memory["id"]

    print()
    print("[1] CANONICAL MEMORY")
    print("-" * 90)
    print("BANK ID:", bank_id)
    print("MEMORY ID:", memory_id)
    print("TEXT:", canonical_memory["original_text"])
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 2. CREATE REPOSITORY
    # -----------------------------------------------------

    repository = SQLiteLearningRepository(
        db_path=db_path
    )

    experience_service = ExperienceService(
        repository=repository,
        canonical_memory_service=canonical,
    )

    print()
    print("[2] STORAGE ADAPTER")
    print("-" * 90)
    print("BACKEND: SQLite")
    print("DATABASE:", db_path)
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 3. CREATE EXPERIENCE
    # -----------------------------------------------------

    experience = experience_service.create(
        bank_id=bank_id,
        canonical_memory_id=memory_id,
        task=(
            "Resolve wallet concurrency during "
            "integration testing."
        ),
        action=(
            "Use pessimistic database locking."
        ),
        context=(
            "The wallet service previously had "
            "concurrency failures."
        ),
    )

    assert experience is not None
    assert experience["experience_id"]
    assert experience["canonical_memory_id"] == memory_id
    assert experience["bank_id"] == bank_id

    experience_id = experience["experience_id"]

    print()
    print("[3] EXPERIENCE CREATED")
    print("-" * 90)
    print("EXPERIENCE ID:", experience_id)
    print("MEMORY ID:", experience["canonical_memory_id"])
    print("TASK:", experience["task"])
    print("ACTION:", experience["action"])
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 4. CREATE TEXT EVIDENCE
    # -----------------------------------------------------

    evidence_service = EvidenceService(
        repository=repository
    )

    text_evidence = (
        evidence_service.create_text_evidence(
            experience_id=experience_id,
            content=(
                "Integration tests passed for the "
                "wallet concurrency fix."
            ),
            source_type="test_result",
            source_id="integration-test-run-001",
        )
    )

    assert text_evidence is not None
    assert text_evidence["evidence_type"] == "text"
    assert (
        text_evidence["experience_id"]
        == experience_id
    )

    print()
    print("[4] TEXT EVIDENCE")
    print("-" * 90)
    print("EVIDENCE ID:", text_evidence["evidence_id"])
    print("TYPE:", text_evidence["evidence_type"])
    print("SOURCE:", text_evidence["source_type"])
    print("SOURCE ID:", text_evidence["source_id"])
    print("CONTENT:", text_evidence["content"])
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 5. CREATE IMAGE EVIDENCE
    # -----------------------------------------------------

    image_bytes = (
        b"fake-image-bytes-for-controlled-test"
    )

    image_evidence = (
        evidence_service.create_file_evidence(
            experience_id=experience_id,
            file_name="wallet_test_pass.png",
            mime_type="image/png",
            storage_key=(
                f"evidence/"
                f"{experience_id}/"
                f"wallet_test_pass.png"
            ),
            file_bytes=image_bytes,
            evidence_type="image",
            source_type="test_result",
            source_id="integration-test-run-001",
        )
    )

    assert image_evidence is not None
    assert image_evidence["evidence_type"] == "image"
    assert (
        image_evidence["file_name"]
        == "wallet_test_pass.png"
    )
    assert image_evidence["mime_type"] == "image/png"
    assert image_evidence["storage_key"]
    assert image_evidence["sha256"]

    print()
    print("[5] IMAGE EVIDENCE")
    print("-" * 90)
    print("EVIDENCE ID:", image_evidence["evidence_id"])
    print("TYPE:", image_evidence["evidence_type"])
    print("FILE:", image_evidence["file_name"])
    print("MIME:", image_evidence["mime_type"])
    print("STORAGE KEY:", image_evidence["storage_key"])
    print("SHA256:", image_evidence["sha256"])
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 6. CREATE TEST RESULT EVIDENCE
    # -----------------------------------------------------

    test_evidence = (
        evidence_service.create_test_result(
            experience_id=experience_id,
            result=(
                "12 tests passed, "
                "0 tests failed."
            ),
            source_id="pytest-run-001",
        )
    )

    assert test_evidence is not None
    assert (
        test_evidence["evidence_type"]
        == "test_result"
    )

    print()
    print("[6] TEST RESULT EVIDENCE")
    print("-" * 90)
    print("EVIDENCE ID:", test_evidence["evidence_id"])
    print("TYPE:", test_evidence["evidence_type"])
    print("CONTENT:", test_evidence["content"])
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 7. RETRIEVE EXPERIENCE
    # -----------------------------------------------------

    retrieved_experience = (
        experience_service.get(
            experience_id
        )
    )

    assert retrieved_experience is not None
    assert (
        retrieved_experience["experience_id"]
        == experience_id
    )
    assert (
        retrieved_experience["canonical_memory_id"]
        == memory_id
    )

    print()
    print("[7] EXPERIENCE RETRIEVAL")
    print("-" * 90)
    print(
        "RETRIEVED EXPERIENCE ID:",
        retrieved_experience["experience_id"],
    )
    print(
        "LINKED MEMORY ID:",
        retrieved_experience["canonical_memory_id"],
    )
    print("STATUS: PASS")


    # -----------------------------------------------------
    # 8. RETRIEVE EVIDENCE
    # -----------------------------------------------------

    retrieved_evidence = (
        evidence_service.list_for_experience(
            experience_id
        )
    )

    assert len(retrieved_evidence) == 3

    evidence_ids = {
        item["evidence_id"]
        for item in retrieved_evidence
    }

    assert (
        text_evidence["evidence_id"]
        in evidence_ids
    )

    assert (
        image_evidence["evidence_id"]
        in evidence_ids
    )

    assert (
        test_evidence["evidence_id"]
        in evidence_ids
    )

    print()
    print("[8] EVIDENCE RETRIEVAL")
    print("-" * 90)
    print("EVIDENCE COUNT:", len(retrieved_evidence))

    for item in retrieved_evidence:
        print(
            f"- {item['evidence_id']} | "
            f"{item['evidence_type']} | "
            f"{item['file_name'] or item['content']}"
        )

    print("STATUS: PASS")


    # -----------------------------------------------------
    # 9. COMPLETE FRONTEND-READY CHAIN
    # -----------------------------------------------------

    chain_service = (
        ExperienceEvidenceService(
            experience_service=experience_service,
            evidence_service=evidence_service,
        )
    )

    complete = (
        chain_service.get_complete_experience(
            experience_id
        )
    )

    assert complete["experience"] is not None
    assert len(complete["evidence"]) == 3

    assert (
        complete["experience"]["canonical_memory_id"]
        == memory_id
    )

    print()
    print("[9] COMPLETE EVIDENCE CHAIN")
    print("-" * 90)

    print(
        "CANONICAL MEMORY ID:",
        complete["experience"][
            "canonical_memory_id"
        ],
    )

    print(
        "EXPERIENCE ID:",
        complete["experience"][
            "experience_id"
        ],
    )

    print(
        "EVIDENCE COUNT:",
        len(complete["evidence"]),
    )

    print()

    for evidence in complete["evidence"]:
        print(
            "EVIDENCE:",
            evidence["evidence_id"]
        )
        print(
            "  TYPE:",
            evidence["evidence_type"]
        )
        print(
            "  SOURCE:",
            evidence["source_type"]
        )
        print(
            "  FILE:",
            evidence["file_name"]
        )
        print(
            "  STORAGE KEY:",
            evidence["storage_key"]
        )
        print(
            "  CONTENT:",
            evidence["content"]
        )
        print()

    print("STATUS: PASS")


    # -----------------------------------------------------
    # 10. PROVE DATABASE PERSISTENCE
    # -----------------------------------------------------

    experience_service.close()

    experience_service = None
    evidence_service = None
    chain_service = None

    repository = SQLiteLearningRepository(
        db_path=db_path
    )

    experience_service = ExperienceService(
        repository=repository,
        canonical_memory_service=canonical,
    )

    evidence_service = EvidenceService(
        repository=repository
    )

    persisted_experience = (
        experience_service.get(
            experience_id
        )
    )

    persisted_evidence = (
        evidence_service.list_for_experience(
            experience_id
        )
    )

    assert persisted_experience is not None
    assert len(persisted_evidence) == 3

    print()
    print("[10] RESTART / PERSISTENCE TEST")
    print("-" * 90)
    print(
        "EXPERIENCE SURVIVED REOPEN:",
        persisted_experience[
            "experience_id"
        ],
    )
    print(
        "EVIDENCE SURVIVED REOPEN:",
        len(persisted_evidence),
    )
    print("STATUS: PASS")


    # -----------------------------------------------------
    # FINAL EVIDENCE
    # -----------------------------------------------------

    print()
    print("=" * 90)
    print("C1 EXPERIENCE + EVIDENCE FOUNDATION PASSED")
    print("=" * 90)

    print()
    print("FINAL VERIFIED CHAIN")
    print("-" * 90)
    print(
        f"MEMORY      : {memory_id}"
    )
    print(
        f"EXPERIENCE  : {experience_id}"
    )
    print(
        f"EVIDENCE    : {len(persisted_evidence)} items"
    )
    print(
        "PERSISTENCE : VERIFIED"
    )
    print(
        "LINKAGE     : VERIFIED"
    )
    print(
        "IMAGE META  : VERIFIED"
    )
    print(
        "SHA256      : VERIFIED"
    )
    print(
        "FRONTEND CHAIN: VERIFIED"
    )

finally:

    try:
        if experience_service is not None:
            experience_service.close()
    except Exception:
        pass

    try:
        if canonical is not None:
            canonical.close()
    except Exception:
        pass

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass