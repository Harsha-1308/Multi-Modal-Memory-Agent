import os
import uuid

from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.services.hindsight_canonical_resolver import (
    HindsightCanonicalResolver,
)
from app.services.retrieval_quality_gate import (
    RetrievalQualityGate,
)
from app.services.adaptive_memory_selector import (
    AdaptiveMemorySelector,
)
from app.services.closed_learning_loop_service import (
    ClosedLearningLoopService,
)
from app.services.memory_learning_state_service import (
    MemoryLearningStateService,
)
from app.repositories.sqlite.learning_repository import (
    SQLiteLearningRepository,
)
from app.services.learning_agent_service import (
    LearningAgentService,
)


BANK_ID = (
    f"agent-orchestrator-{uuid.uuid4().hex[:8]}"
)

LEARNING_DB = (
    f"test_agent_learning_{uuid.uuid4().hex[:8]}.db"
)

CANONICAL_DB = (
    f"test_agent_canonical_{uuid.uuid4().hex[:8]}.db"
)

MEMORY_A_TEXT = (
    "Pessimistic database locking resolved "
    "the wallet concurrency problem."
)

MEMORY_B_TEXT = (
    "Optimistic concurrency control resolved "
    "the wallet concurrency problem."
)

QUERY = (
    "What approach should I use for the "
    "wallet concurrency problem?"
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def deterministic_answer(context):
    selected = context[
        "memory"
    ]

    learning = context[
        "learning"
    ][
        "state"
    ]

    decision = context[
        "decision"
    ]

    return (
        f"Memory={selected['canonical_memory_id']} | "
        f"Behavior={decision['behavior']} | "
        f"Signal={learning['learning_signal']} | "
        f"Informative={learning['informative_outcomes']}"
    )


print()
print("=" * 90)
print("LEARNING AGENT SERVICE — END-TO-END ORCHESTRATOR TEST")
print("=" * 90)

memory_service = None
canonical = None
repository = None

try:

    # --------------------------------------------------------
    # 1. SERVICES
    # --------------------------------------------------------

    print()
    print("[1] INITIALIZE SERVICES")

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

    learning_service = MemoryLearningStateService(
        repository=repository,
    )

    closed_loop = ClosedLearningLoopService(
        learning_service=learning_service,
    )

    selector = AdaptiveMemorySelector(
        learning_service=learning_service,
        closed_loop_service=closed_loop,
    )

    quality_gate = RetrievalQualityGate(
        min_similarity=0.0,
    )

    agent = LearningAgentService(
        memory_service=memory_service,
        resolver=resolver,
        selector=selector,
        closed_loop=closed_loop,
        quality_gate=quality_gate,
    )

    print("STATUS: PASS")

    # --------------------------------------------------------
    # 2. CANONICAL MEMORIES
    # --------------------------------------------------------

    print()
    print("[2] CREATE CANONICAL MEMORIES")

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
        "Expected exactly two canonical memories.",
    )

    memory_ids = {
        item["id"]
        for item in memories
    }

    print(
        "CANONICAL IDS:",
        sorted(memory_ids),
    )
    for memory_id in memory_ids:
        learning_service.learn(memory_id)

    print("STATUS: PASS")

    # --------------------------------------------------------
    # 3. REAL HINDSIGHT
    # --------------------------------------------------------

    print()
    print("[3] STORE IN REAL HINDSIGHT")

    retained_a = memory_service.retain(
        bank_id=BANK_ID,
        content=MEMORY_A_TEXT,
    )

    retained_b = memory_service.retain(
        bank_id=BANK_ID,
        content=MEMORY_B_TEXT,
    )

    require(
        retained_a is not None,
        "Hindsight retain A failed.",
    )

    require(
        retained_b is not None,
        "Hindsight retain B failed.",
    )

    print("STATUS: PASS")

    # --------------------------------------------------------
    # 4. ORCHESTRATOR RETRIEVAL
    # --------------------------------------------------------

    print()
    print("[4] ORCHESTRATOR RETRIEVAL")

    retrieval = agent.retrieve_candidates(
        bank_id=BANK_ID,
        query=QUERY,
    )

    print(
        "RAW RESULTS:",
        retrieval["raw_result_count"],
    )

    print(
        "RESOLVED:",
        retrieval["resolved_count"]
        if "resolved_count" in retrieval
        else len(
            retrieval[
                "resolved_candidates"
            ]
        ),
    )

    print(
        "ACCEPTED:",
        retrieval["accepted_count"],
    )

    print(
        "REJECTED:",
        retrieval["rejected_count"],
    )

    require(
        retrieval[
            "raw_result_count"
        ] >= 2,
        "Expected at least two Hindsight results.",
    )

    require(
        len(
            retrieval[
                "candidates"
            ]
        ) >= 2,
        "Expected both canonical memories.",
    )

    for candidate in retrieval[
        "candidates"
    ]:
        require(
            set(
                candidate.keys()
            )
            == {
                "canonical_memory_id",
                "text",
                "retrieval_similarity",
            },
            "Invalid C6 candidate schema.",
        )

        require(
            candidate[
                "canonical_memory_id"
            ] in memory_ids,
            "Invalid canonical memory ID.",
        )

        require(
            0.0
            <= candidate[
                "retrieval_similarity"
            ]
            <= 1.0,
            "Invalid retrieval similarity.",
        )

    print()
    print(
    "RETRIEVED CANDIDATES:",
    len(retrieval["candidates"]),
)

    require(
    len(retrieval["candidates"]) >= 2,
    "The retrieval stage did not produce enough candidates.",
)

    print("STATUS: PASS")

    # --------------------------------------------------------
    # 5. FULL ANSWER PIPELINE
    # --------------------------------------------------------

    print()
    print("[5] FULL ANSWER PIPELINE")

    selection = agent.select_memory(
    retrieval["candidates"]
)

    context = agent.build_context(
    query=QUERY,
    selection=selection,
)

    answer = agent.generate_answer(
    context=context,
    answer_generator=deterministic_answer,
)

    result = {
    "answer": answer,
    "selected_memory": selection["selected"],
    "selection": selection,
    "behavior": context["decision"]["behavior"],
    "learning": context["learning"]["state"],
    "provenance": context["learning"]["provenance"],
    "retrieval": {
        "raw_result_count": retrieval["raw_result_count"],
        "resolved_count": len(
            retrieval["resolved_candidates"]
        ),
        "accepted_count": retrieval["accepted_count"],
        "rejected_count": retrieval["rejected_count"],
        "rejected": retrieval["rejected"],
    },
}

    print()
    print("ANSWER:")
    print(result["answer"])

    print()
    print("SELECTED MEMORY:")
    print(
        result[
            "selected_memory"
        ]
    )

    print()
    print("BEHAVIOR:")
    print(
        result[
            "behavior"
        ]
    )

    print()
    print("LEARNING:")
    print(
        result[
            "learning"
        ]
    )

    print()
    print("PROVENANCE:")
    print(
        result[
            "provenance"
        ]
    )

    require(
        result[
            "selected_memory"
        ]["canonical_memory_id"]
        in memory_ids,
        "Selected memory is invalid.",
    )

    require(
        result[
            "behavior"
        ]
        == "insufficient",
        (
            "No outcomes exist yet, so behavior "
            "should be insufficient."
        ),
    )

    require(
        result[
            "learning"
        ]["informative_outcomes"]
        == 0,
        "Initial informative outcomes must be zero.",
    )

    require(
        result[
            "provenance"
        ]["memory_id"]
        == result[
            "selected_memory"
        ]["canonical_memory_id"],
        "Provenance memory ID mismatch.",
    )

    require(
        result[
            "retrieval"
        ]["accepted_count"]
        >= 2,
        "Expected at least two accepted candidates.",
    )

    print()
    print("STATUS: PASS")

    # --------------------------------------------------------
    # 6. NO-LEARNING SELECTION PROOF
    # --------------------------------------------------------

    print()
    print("[6] C6 IS ACTUALLY INSIDE THE ORCHESTRATOR")

    selected = result[
        "selected_memory"
    ]

    ranked = result[
        "selection"
    ][
        "ranked_candidates"
    ]

    print(
        "SELECTED:",
        selected[
            "canonical_memory_id"
        ],
    )

    print(
        "RANKED CANDIDATES:"
    )

    for item in ranked:
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

    for item in ranked:
        require(
            item[
                "learning_multiplier"
            ]
            == 1.0,
            "No-learning multiplier must be 1.0.",
        )

    print("STATUS: PASS")

    # --------------------------------------------------------
    # 7. FAILURE SAFETY
    # --------------------------------------------------------

    print()
    print("[7] BASIC INPUT SAFETY")

    try:
        agent.answer(
            bank_id=BANK_ID,
            query="",
            answer_generator=deterministic_answer,
        )
        raise AssertionError(
            "Empty query should have failed."
        )
    except ValueError:
        pass

    try:
        agent.answer(
            bank_id="",
            query=QUERY,
            answer_generator=deterministic_answer,
        )
        raise AssertionError(
            "Empty bank_id should have failed."
        )
    except ValueError:
        pass

    print("EMPTY QUERY: PASS")
    print("EMPTY BANK ID: PASS")

    print()
    print("==========================================")
    print("LEARNING AGENT ORCHESTRATOR: PASSED")
    print("==========================================")

finally:

    if memory_service is not None:
        close_method = getattr(
            memory_service,
            "close",
            None,
        )

        if close_method is not None:
            close_method()

    if canonical is not None:
        canonical.close()

    if repository is not None:
        repository.close()

    for path in (
        LEARNING_DB,
        CANONICAL_DB,
    ):
        try:
            if os.path.exists(path):
                os.remove(path)
                print(
                    "REMOVED TEMP DB:",
                    path,
                )
        except OSError:
            pass