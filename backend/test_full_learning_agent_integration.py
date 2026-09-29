import os
import shutil
import uuid

from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import CanonicalMemoryService
from app.services.hindsight_canonical_resolver import HindsightCanonicalResolver
from app.services.adaptive_memory_selector import AdaptiveMemorySelector

from app.repositories.sqlite.learning_repository import (
    SQLiteLearningRepository,
)

from app.services.experience_service import ExperienceService
from app.services.outcome_capture_service import OutcomeCaptureService
from app.services.outcome_classification_service import (
    OutcomeClassificationService,
)
from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)
from app.services.closed_learning_loop_service import (
    ClosedLearningLoopService,
)


# ============================================================
# TEST CONFIGURATION
# ============================================================

BANK_ID = f"full-integration-{uuid.uuid4().hex[:8]}"

LEARNING_DB = (
    f"test_full_learning_{uuid.uuid4().hex[:8]}.db"
)

CANONICAL_DB = (
    f"test_full_canonical_{uuid.uuid4().hex[:8]}.db"
)

QUERY = (
    "What approach should I use for the wallet concurrency problem?"
)

MEMORY_A_TEXT = (
    "Pessimistic database locking resolved the wallet concurrency problem."
)

MEMORY_B_TEXT = (
    "Optimistic concurrency control resolved the wallet concurrency problem."
)


# ============================================================
# HELPERS
# ============================================================

def section(number, title):
    print()
    print("=" * 95)
    print(f"[{number}] {title}")
    print("-" * 95)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close_service(service):
    """
    Safely close a service if it exposes close().
    """

    close_method = getattr(service, "close", None)

    if close_method is None:
        return

    result = close_method()

    # Most project services currently expose synchronous close().
    # If a future implementation returns an awaitable,
    # this test intentionally does not hide that behavior.
    if result is not None:
        return result


def create_evidenced_outcome(
    experience_service,
    outcome_service,
    classification_service,
    repository,
    memory_id,
    action,
    outcome_type,
    evidence_text,
):
    """
    Creates a complete:

        Experience
             ↓
        Outcome
             ↓
        Evidence
             ↓
        Classification

    record.

    This is deliberately using the real C1-C4 services.
    """

    experience = experience_service.create(
        bank_id=BANK_ID,
        canonical_memory_id=memory_id,
        task="Resolve the wallet concurrency problem.",
        action=action,
        context="Full integration test.",
    )

    require(
        experience is not None,
        "Experience creation returned None.",
    )

    require(
        "experience_id" in experience,
        "Experience does not contain experience_id.",
    )

    outcome = outcome_service.create(
        experience_id=experience["experience_id"],
        outcome_type=outcome_type,
        summary=evidence_text,
    )

    require(
        outcome is not None,
        "Outcome creation returned None.",
    )

    require(
        "outcome_id" in outcome,
        "Outcome does not contain outcome_id.",
    )

    evidence = repository.create_evidence(
        evidence_id=str(uuid.uuid4()),
        experience_id=experience["experience_id"],
        outcome_id=outcome["outcome_id"],
        evidence_type="test_result",
        content=evidence_text,
        file_name=None,
        mime_type=None,
        storage_key=None,
        sha256=None,
        source_type="test_result",
        source_id="full-learning-agent-integration",
    )

    require(
        evidence is not None,
        "Evidence creation returned None.",
    )

    classified = classification_service.classify(
        outcome["outcome_id"]
    )

    require(
        classified is not None,
        "Classification returned None.",
    )

    require(
        classified["classification"] == outcome_type,
        (
            "Classification mismatch. "
            f"Expected={outcome_type}, "
            f"Actual={classified['classification']}"
        ),
    )

    return {
        "experience": experience,
        "outcome": outcome,
        "evidence": evidence,
        "classification": classified,
    }


def deterministic_answer(context):
    """
    Deterministic agent used only for integration testing.

    This allows us to prove that C5 receives the correct
    selected memory, learning state and behavior before
    adding another external dependency such as Groq.
    """

    selected = context["memory"]
    learning = context["learning"]["state"]
    decision = context["decision"]

    return (
        f"Selected memory: {selected['canonical_memory_id']}. "
        f"Behavior: {decision['behavior']}. "
        f"Learning signal: {learning['learning_signal']}. "
        f"Informative outcomes: "
        f"{learning['informative_outcomes']}."
    )


# ============================================================
# START TEST
# ============================================================

print()
print("=" * 95)
print("FULL LEARNING AGENT INTEGRATION TEST")
print("=" * 95)

memory_service = None
canonical = None
repository = None

try:

    # ========================================================
    # 1. INITIALIZATION
    # ========================================================

    section(1, "INITIALIZE ALL SERVICES")

    memory_service = MemoryService()

    canonical = CanonicalMemoryService(
        db_path=CANONICAL_DB
    )

    repository = SQLiteLearningRepository(
        db_path=LEARNING_DB
    )

    resolver = HindsightCanonicalResolver(
    canonical_memory_service=canonical,
)

    experience_service = ExperienceService(
    repository=repository,
    canonical_memory_service=canonical,
)

    outcome_service = OutcomeCaptureService(
        repository=repository
    )

    classification_service = (
        OutcomeClassificationService(
            repository=repository
        )
    )

    learning_service = MemoryLearningStateService(
        repository=repository
    )

    closed_loop = ClosedLearningLoopService(
        learning_service=learning_service
    )

    selector = AdaptiveMemorySelector(
        learning_service=learning_service,
        closed_loop_service=closed_loop,
    )

    print("MemoryService: READY")
    print("CanonicalMemoryService: READY")
    print("SQLiteLearningRepository: READY")
    print("ExperienceService: READY")
    print("OutcomeCaptureService: READY")
    print("OutcomeClassificationService: READY")
    print("MemoryLearningStateService: READY")
    print("ClosedLearningLoopService: READY")
    print("AdaptiveMemorySelector: READY")
    print("HindsightCanonicalResolver: READY")
    print("BANK ID:", BANK_ID)

    print("STATUS: PASS")

    # ========================================================
    # 2. CREATE CANONICAL MEMORIES
    # ========================================================

    section(2, "CREATE CANONICAL MEMORIES")

    require(
        canonical.register(
            BANK_ID,
            MEMORY_A_TEXT,
        ),
        "Memory A registration failed.",
    )

    require(
        canonical.register(
            BANK_ID,
            MEMORY_B_TEXT,
        ),
        "Memory B registration failed.",
    )

    memories = canonical.list_memories(
        bank_id=BANK_ID
    )

    require(
        len(memories) == 2,
        f"Expected 2 canonical memories, got {len(memories)}.",
    )

    # IMPORTANT:
    # Canonical records use original_text, not text.

    memory_by_text = {}

    for memory in memories:

        original_text = memory.get(
            "original_text"
        )

        require(
            original_text is not None,
            "Canonical memory missing original_text.",
        )

        memory_by_text[original_text] = memory

    require(
        MEMORY_A_TEXT in memory_by_text,
        "Memory A missing from canonical registry.",
    )

    require(
        MEMORY_B_TEXT in memory_by_text,
        "Memory B missing from canonical registry.",
    )

    memory_a_id = memory_by_text[MEMORY_A_TEXT]["id"]
    memory_b_id = memory_by_text[MEMORY_B_TEXT]["id"]

    print("MEMORY A ID:", memory_a_id)
    print("MEMORY B ID:", memory_b_id)

    print("STATUS: PASS")

    # ========================================================
    # 3. STORE REAL MEMORIES IN HINDSIGHT
    # ========================================================

    section(3, "STORE MEMORIES IN REAL HINDSIGHT")

    hindsight_a = memory_service.retain(
        bank_id=BANK_ID,
        content=MEMORY_A_TEXT,
    )

    hindsight_b = memory_service.retain(
        bank_id=BANK_ID,
        content=MEMORY_B_TEXT,
    )

    require(
        hindsight_a is not None,
        "Hindsight retain A returned None.",
    )

    require(
        hindsight_b is not None,
        "Hindsight retain B returned None.",
    )

    print("Hindsight A: STORED")
    print("Hindsight B: STORED")
    print("STATUS: PASS")

    # ========================================================
    # 4. REAL HINDSIGHT RECALL
    # ========================================================

    section(4, "REAL HINDSIGHT RECALL")

    print("QUERY:", QUERY)

    recall_response = memory_service.recall(
        bank_id=BANK_ID,
        query=QUERY,
    )

    results = getattr(
        recall_response,
        "results",
        None,
    )

    if results is None and isinstance(
        recall_response,
        dict,
    ):
        results = recall_response.get(
            "results"
        )

    results = results or []

    require(
        len(results) >= 2,
        (
            "Expected at least two Hindsight "
            f"results, got {len(results)}."
        ),
    )

    print("HINDSIGHT RESULT COUNT:", len(results))

    for index, result in enumerate(
        results[:10],
        start=1,
    ):

        text = getattr(
            result,
            "text",
            None,
        )

        similarity = getattr(
            result,
            "semantic_similarity",
            None,
        )

        if similarity is None:

            scores = getattr(
                result,
                "scores",
                None,
            )

            if scores is not None:
                similarity = getattr(
                    scores,
                    "semantic",
                    None,
                )

        print()
        print("RESULT", index)
        print("TEXT:", text)
        print("SIMILARITY:", similarity)

    print("STATUS: PASS")

    # ========================================================
    # 5. REAL HINDSIGHT → CANONICAL IDENTITY
    # ========================================================

    section(
        5,
        "RESOLVE REAL HINDSIGHT RESULTS TO CANONICAL IDS",
    )

    resolved = resolver.resolve_results(
    results,
    BANK_ID,
)

    require(
        len(resolved) >= 2,
        (
            "Expected at least two resolved "
            f"candidates, got {len(resolved)}."
        ),
    )

    valid_ids = {
        memory_a_id,
        memory_b_id,
    }

    resolved_ids = []

    for index, candidate in enumerate(
        resolved,
        start=1,
    ):

        candidate_id = candidate.get(
            "canonical_memory_id"
        )

        resolved_ids.append(
            candidate_id
        )

        print()
        print("RESOLVED", index)
        print(
            "CANONICAL ID:",
            candidate_id,
        )
        print(
            "RETRIEVAL SIMILARITY:",
            candidate.get(
                "retrieval_similarity"
            ),
        )
        print(
            "IDENTITY SCORE:",
            candidate.get(
                "identity_score"
            ),
        )
        print(
            "IDENTITY MARGIN:",
            candidate.get(
                "identity_margin"
            ),
        )

        require(
            candidate_id in valid_ids,
            (
                "Resolver produced an invalid "
                f"canonical ID: {candidate_id}"
            ),
        )

        require(
            candidate.get(
                "retrieval_similarity"
            ) is not None,
            "Retrieval similarity was lost.",
        )

    require(
        set(resolved_ids)
        == valid_ids,
        (
            "Resolver did not recover both "
            "canonical memories."
        ),
    )

    print()
    print("VALID CANONICAL IDS:", sorted(valid_ids))
    print(
        "RESOLVED CANONICAL IDS:",
        sorted(set(resolved_ids)),
    )
    print("STATUS: PASS")

    # ========================================================
    # 6. BUILD REAL C6 CANDIDATES
    # ========================================================

    section(
        6,
        "BUILD REAL C6 CANDIDATES",
    )

    candidates = []

    seen_ids = set()

    for candidate in resolved:

        memory_id = candidate[
            "canonical_memory_id"
        ]

        # Hindsight may return multiple representations
        # of the same underlying memory.
        #
        # C6 must not receive duplicate canonical IDs.

        if memory_id in seen_ids:
            continue

        seen_ids.add(memory_id)

        candidates.append(
            {
                "canonical_memory_id": memory_id,
                "text": candidate.get(
                    "text"
                ),
                "retrieval_similarity": candidate[
                    "retrieval_similarity"
                ],
            }
        )

    require(
        len(candidates) == 2,
        (
            "Expected two unique C6 candidates, "
            f"got {len(candidates)}."
        ),
    )

    for candidate in candidates:
        print(candidate)

        require(
            set(candidate.keys())
            == {
                "canonical_memory_id",
                "text",
                "retrieval_similarity",
            },
            "C6 candidate schema is incorrect.",
        )

    print("STATUS: PASS")

    # ========================================================
    # 7. BASELINE C6
    # ========================================================

    section(
        7,
        "C6 BASELINE — NO LEARNING",
    )

    baseline = selector.select(
        candidates
    )

    baseline_selected = baseline[
        "selected"
    ]

    print(
        "SELECTED MEMORY:",
        baseline_selected[
            "canonical_memory_id"
        ],
    )

    print(
        "RANKED CANDIDATES:"
    )

    for item in baseline[
        "ranked_candidates"
    ]:
        print(
            item[
                "canonical_memory_id"
            ],
            "retrieval=",
            item[
                "retrieval_similarity"
            ],
            "signal=",
            item[
                "learning_signal"
            ],
            "multiplier=",
            item[
                "learning_multiplier"
            ],
            "adjusted=",
            item[
                "adjusted_score"
            ],
        )

    for item in baseline[
        "ranked_candidates"
    ]:
        require(
            item[
                "learning_multiplier"
            ] == 1.0,
            (
                "A memory without learning "
                "should have multiplier 1.0."
            ),
        )

    print("STATUS: PASS")

    # ========================================================
    # 8. CREATE FAILURE HISTORY FOR MEMORY A
    # ========================================================

    section(
        8,
        "LEARN FAILURE HISTORY FOR MEMORY A",
    )

    for index in range(5):

        create_evidenced_outcome(
            experience_service=experience_service,
            outcome_service=outcome_service,
            classification_service=classification_service,
            repository=repository,
            memory_id=memory_a_id,
            action=(
                "Used pessimistic database locking "
                f"attempt {index + 1}."
            ),
            outcome_type="failure",
            evidence_text=(
                "The pessimistic locking approach "
                "failed the integration test."
            ),
        )

    state_a = learning_service.refresh(
        canonical_memory_id=memory_a_id
    )

    require(
        state_a["failures"] == 5,
        "Memory A should have five failures.",
    )

    require(
        state_a["successes"] == 0,
        "Memory A should have zero successes.",
    )

    require(
        state_a["learning_signal"] == -1.0,
        "Memory A learning signal should be -1.",
    )

    require(
        state_a["evidence_coverage"] == 1.0,
        "Memory A evidence coverage should be 1.",
    )

    print(
        "MEMORY A STATE:",
        state_a,
    )

    # ========================================================
    # 9. C6 MUST CHANGE SELECTION
    # ========================================================

    section(
        9,
        "C6 ADAPTATION AFTER MEMORY A FAILURE",
    )

    after_a_failure = selector.select(
        candidates
    )

    selected_after_failure = (
        after_a_failure["selected"]
    )

    print(
        "SELECTED MEMORY:",
        selected_after_failure[
            "canonical_memory_id"
        ],
    )

    require(
        selected_after_failure[
            "canonical_memory_id"
        ]
        != memory_a_id,
        (
            "C6 did not reduce the failed "
            "memory's selection."
        ),
    )

    a_ranked = next(
        item
        for item in after_a_failure[
            "ranked_candidates"
        ]
        if item[
            "canonical_memory_id"
        ] == memory_a_id
    )

    require(
        a_ranked[
            "learning_multiplier"
        ] == 0.0,
        (
            "Five fully evidenced failures "
            "should produce multiplier 0."
        ),
    )

    print(
        "MEMORY A MULTIPLIER:",
        a_ranked[
            "learning_multiplier"
        ],
    )

    print("STATUS: PASS")

    # ========================================================
    # 10. CREATE SUCCESS HISTORY FOR MEMORY B
    # ========================================================

    section(
        10,
        "LEARN SUCCESS HISTORY FOR MEMORY B",
    )

    for index in range(5):

        create_evidenced_outcome(
            experience_service=experience_service,
            outcome_service=outcome_service,
            classification_service=classification_service,
            repository=repository,
            memory_id=memory_b_id,
            action=(
                "Used optimistic concurrency "
                f"control attempt {index + 1}."
            ),
            outcome_type="success",
            evidence_text=(
                "The optimistic concurrency control "
                "approach passed the integration test."
            ),
        )

    state_b = learning_service.refresh(
        canonical_memory_id=memory_b_id
    )

    require(
        state_b["successes"] == 5,
        "Memory B should have five successes.",
    )

    require(
        state_b["failures"] == 0,
        "Memory B should have zero failures.",
    )

    require(
        state_b["learning_signal"] == 1.0,
        "Memory B learning signal should be +1.",
    )

    require(
        state_b["evidence_coverage"] == 1.0,
        "Memory B evidence coverage should be 1.",
    )

    print(
        "MEMORY B STATE:",
        state_b,
    )

    # ========================================================
    # 11. C6 MUST PREFER MEMORY B
    # ========================================================

    section(
        11,
        "C6 SELECTION AFTER MEMORY B SUCCESS",
    )

    after_b_success = selector.select(
        candidates
    )

    selected_after_success = (
        after_b_success["selected"]
    )

    print(
        "SELECTED MEMORY:",
        selected_after_success[
            "canonical_memory_id"
        ],
    )

    require(
        selected_after_success[
            "canonical_memory_id"
        ]
        == memory_b_id,
        (
            "C6 did not prefer the successful "
            "memory."
        ),
    )

    b_ranked = next(
        item
        for item in after_b_success[
            "ranked_candidates"
        ]
        if item[
            "canonical_memory_id"
        ] == memory_b_id
    )

    require(
        b_ranked[
            "learning_multiplier"
        ] == 2.0,
        (
            "Five fully evidenced successes "
            "should produce multiplier 2."
        ),
    )

    print(
        "MEMORY B MULTIPLIER:",
        b_ranked[
            "learning_multiplier"
        ],
    )

    print("STATUS: PASS")

    # ========================================================
    # 12. BUILD C5 LEARNING CONTEXT
    # ========================================================

    section(
        12,
        "C5 CLOSED LEARNING LOOP",
    )

    selected = after_b_success[
        "selected"
    ]

    c5_context = (
        closed_loop.build_agent_context(
            canonical_memory_id=selected[
                "canonical_memory_id"
            ],
            query=QUERY,
            memory_text=selected[
                "text"
            ],
        )
    )

    require(
        c5_context["query"] == QUERY,
        "C5 query was not preserved.",
    )

    require(
        c5_context["memory"][
            "canonical_memory_id"
        ] == memory_b_id,
        "C5 received wrong selected memory.",
    )

    require(
        c5_context["learning"]["state"][
            "successes"
        ] == 5,
        "C5 did not receive Memory B learning state.",
    )

    require(
        c5_context["learning"]["state"][
            "learning_signal"
        ] == 1.0,
        "C5 did not receive learning signal.",
    )

    require(
        c5_context["decision"]["behavior"]
        == "prefer",
        "C5 should decide PREFER for Memory B.",
    )

    print("C5 BEHAVIOR:")
    print(
        c5_context["decision"][
            "behavior"
        ]
    )

    print("C5 LEARNING:")
    print(
        c5_context["learning"][
            "state"
        ]
    )

    print("C5 PROVENANCE:")
    print(
        c5_context["learning"][
            "provenance"
        ]
    )

    print("STATUS: PASS")

    # ========================================================
    # 13. DETERMINISTIC AGENT ANSWER
    # ========================================================

    section(
        13,
        "AGENT ANSWER USING REAL LEARNING CONTEXT",
    )

    answer_result = closed_loop.answer(
        query=QUERY,
        canonical_memory_id=selected[
            "canonical_memory_id"
        ],
        answer_generator=deterministic_answer,
        memory_text=selected[
            "text"
        ],
    )

    require(
        answer_result is not None,
        "Closed-loop answer returned None.",
    )

    require(
        answer_result["memory_id"]
        == memory_b_id,
        "Answer used the wrong memory ID.",
    )

    require(
        answer_result["behavior"]
        == "prefer",
        "Answer did not preserve C5 behavior.",
    )

    require(
        "Learning signal" in answer_result[
            "answer"
        ],
        "Answer generator did not receive learning context.",
    )

    print("FINAL ANSWER:")
    print(answer_result["answer"])

    print("STATUS: PASS")

    # ========================================================
    # 14. CHANGE HISTORY AND VERIFY ADAPTATION
    # ========================================================

    section(
        14,
        "CHANGE HISTORY — MEMORY B BECOMES BALANCED",
    )

    new_failure_outcome_ids = []

    for index in range(5):

        result = create_evidenced_outcome(
        experience_service=experience_service,
        outcome_service=outcome_service,
        classification_service=classification_service,
        repository=repository,
        memory_id=memory_b_id,
        action=(
            "Used optimistic concurrency "
            f"control after regression {index + 1}."
        ),
        outcome_type="failure",
        evidence_text=(
            "The optimistic concurrency control "
            "approach failed the regression test."
        ),
    )

        require(
        result is not None,
        f"Failure outcome {index + 1} was not created.",
    )

        require(
        "outcome" in result,
        f"Failure outcome {index + 1} result has no outcome.",
    )

        require(
        "outcome_id" in result["outcome"],
        f"Failure outcome {index + 1} has no outcome_id.",
    )
 
        new_failure_outcome_ids.append(
        result["outcome"]["outcome_id"]
    )


    state_b_balanced = learning_service.refresh(
    canonical_memory_id=memory_b_id
)


    require(
    state_b_balanced["successes"] == 5,
    "Memory B success count changed unexpectedly.",
)

    require(
    state_b_balanced["failures"] == 5,
    "Memory B failure count should be 5.",
)

    require(
    state_b_balanced["learning_signal"] == 0.0,
    "Balanced history should have zero signal.",
)


    require(
    state_b_balanced["last_outcome_id"] in new_failure_outcome_ids,
    (
        "last_outcome_id does not belong to the five newly-created "
        f"failure outcomes. "
        f"last_outcome_id={state_b_balanced['last_outcome_id']}, "
        f"new_failure_outcome_ids={new_failure_outcome_ids}"
    ),
)

    require(
    state_b_balanced["last_classification"] == "failure",
    (
        "last_classification should be failure after the five "
        f"new failure outcomes, got "
        f"{state_b_balanced['last_classification']!r}"
    ),
)

    print(
    "NEW FAILURE OUTCOME IDS:",
    new_failure_outcome_ids,
)

    print(
    "MEMORY B BALANCED STATE:",
    state_b_balanced,
)

    print("STATUS: PASS")

    # ========================================================
    # 15. RESTART / PERSISTENCE
    # ========================================================

    section(
        15,
        "RESTART AND PERSISTENCE",
    )

    close_service(repository)
    repository = None

    repository = SQLiteLearningRepository(
        db_path=LEARNING_DB
    )

    learning_service_restarted = (
        MemoryLearningStateService(
            repository=repository
        )
    )

    closed_loop_restarted = (
        ClosedLearningLoopService(
            learning_service=
            learning_service_restarted
        )
    )

    selector_restarted = AdaptiveMemorySelector(
        learning_service=
        learning_service_restarted,
        closed_loop_service=
        closed_loop_restarted,
    )

    persisted_a = (
        learning_service_restarted.get_state(
            canonical_memory_id=memory_a_id
        )
    )

    persisted_b = (
        learning_service_restarted.get_state(
            canonical_memory_id=memory_b_id
        )
    )

    require(
        persisted_a is not None,
        "Memory A learning state was lost.",
    )

    require(
        persisted_b is not None,
        "Memory B learning state was lost.",
    )

    require(
        persisted_a["failures"] == 5,
        "Memory A failures did not persist.",
    )

    require(
        persisted_b["successes"] == 5,
        "Memory B successes did not persist.",
    )

    require(
        persisted_b["failures"] == 5,
        "Memory B failures did not persist.",
    )

    print(
        "PERSISTED A:",
        persisted_a,
    )

    print(
        "PERSISTED B:",
        persisted_b,
    )

    # ========================================================
    # 16. RE-RUN C6 AFTER RESTART
    # ========================================================

    section(
        16,
        "C6 AFTER RESTART",
    )

    restarted_selection = (
        selector_restarted.select(
            candidates
        )
    )

    restarted_selected = (
        restarted_selection["selected"]
    )

    print(
        "SELECTED AFTER RESTART:",
        restarted_selected[
            "canonical_memory_id"
        ],
    )

    require(
        restarted_selected[
            "canonical_memory_id"
        ] == memory_b_id,
        (
            "C6 behavior was not preserved "
            "after restart."
        ),
    )

    print("STATUS: PASS")

    # ========================================================
    # 17. BANK ISOLATION
    # ========================================================

    section(
        17,
        "BANK / PROJECT ISOLATION",
    )

    second_bank = (
        f"isolated-{uuid.uuid4().hex[:8]}"
    )

    isolated_text = (
        "A completely unrelated memory belonging "
        "to another project."
    )

    require(
        canonical.register(
            second_bank,
            isolated_text,
        ),
        "Second-bank registration failed.",
    )

    second_bank_memories = (
        canonical.list_memories(
            bank_id=second_bank
        )
    )

    require(
        len(second_bank_memories) == 1,
        "Second bank should contain exactly one memory.",
    )

    first_bank_memories = (
        canonical.list_memories(
            bank_id=BANK_ID
        )
    )

    require(
        len(first_bank_memories) == 2,
        (
            "First bank was contaminated by "
            "second-bank memory."
        ),
    )

    first_bank_texts = {
        item["original_text"]
        for item in first_bank_memories
    }

    require(
        isolated_text not in first_bank_texts,
        (
            "Cross-bank memory contamination detected."
        ),
    )

    print("BANK A MEMORY COUNT:", len(first_bank_memories))
    print(
        "BANK B MEMORY COUNT:",
        len(second_bank_memories),
    )

    print("STATUS: PASS")

    # ========================================================
    # FINAL
    # ========================================================

    section(
        18,
        "FULL INTERNAL LEARNING PIPELINE PASSED",
    )

    print()
    print("PROVEN:")
    print("1. Canonical memories are persisted.")
    print("2. Real Hindsight retain works.")
    print("3. Real Hindsight recall works.")
    print("4. Real retrieval similarity is preserved.")
    print("5. Hindsight results map to canonical IDs.")
    print("6. Invalid canonical IDs are rejected.")
    print("7. Duplicate canonical candidates are removed.")
    print("8. C6 consumes real Hindsight candidates.")
    print("9. Failure history changes future selection.")
    print("10. Success history changes future selection.")
    print("11. C5 receives the selected memory.")
    print("12. C5 receives learning state.")
    print("13. C5 receives provenance.")
    print("14. C5 behavior reaches the answer generator.")
    print("15. Learning survives restart.")
    print("16. C6 behavior survives restart.")
    print("17. Separate banks remain isolated.")

    print()
    print(
        "FULL INTERNAL LEARNING PIPELINE: PASSED"
    )

finally:

    print()
    print("=" * 95)
    print("CLEANUP")
    print("=" * 95)

    try:
        if memory_service is not None:
            close_service(memory_service)
            print("MemoryService: CLOSED")
    except Exception as exc:
        print(
            "MemoryService close warning:",
            repr(exc),
        )

    try:
        if canonical is not None:
            close_service(canonical)
            print("CanonicalMemoryService: CLOSED")
    except Exception as exc:
        print(
            "CanonicalMemoryService close warning:",
            repr(exc),
        )

    try:
        if repository is not None:
            close_service(repository)
            print("SQLiteLearningRepository: CLOSED")
    except Exception as exc:
        print(
            "Repository close warning:",
            repr(exc),
        )

    # Remove only the temporary databases created by THIS test.
    for path in (
        LEARNING_DB,
        CANONICAL_DB,
    ):

        try:
            if os.path.exists(path):
                os.remove(path)
                print(
                    "Removed temporary DB:",
                    path,
                )
        except Exception as exc:
            print(
                "Could not remove temporary DB:",
                path,
                repr(exc),
            )

    print("CLEANUP COMPLETE")