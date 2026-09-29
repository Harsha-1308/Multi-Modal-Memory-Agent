from typing import Any, Dict, List, Optional

from app.services.memory_service import MemoryService
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


class LearningAgentService:
    """
    Main end-to-end learning agent.

    Retrieval path:

        Query
          ↓
        Hindsight
          ↓
        Canonical identity resolution
          ↓
        Quality gate + deduplication
          ↓
        C6 adaptive selection
          ↓
        C5 learning-aware context
          ↓
        Answer generator

    The service deliberately does NOT create outcomes here.
    Outcomes belong to the separate learning-feedback path.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        resolver: HindsightCanonicalResolver,
        selector: AdaptiveMemorySelector,
        closed_loop: ClosedLearningLoopService,
        quality_gate: Optional[
            RetrievalQualityGate
        ] = None,
        answer_generator=None,
    ):
        self.memory_service = memory_service
        self.resolver = resolver
        self.selector = selector
        self.closed_loop = closed_loop

        self.quality_gate = (
            quality_gate
            if quality_gate is not None
            else RetrievalQualityGate()
        )

        self.answer_generator = answer_generator

    @staticmethod
    def _extract_results(
        recall_response: Any,
    ) -> List[Any]:
        if recall_response is None:
            return []

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

        return list(results or [])
    @staticmethod
    def _extract_source_facts(
    recall_response: Any,
) -> Dict[str, Any]:
        if recall_response is None:
            return {}

        source_facts = getattr(
        recall_response,
        "source_facts",
        None,
    )

        if source_facts is None and isinstance(
        recall_response,
        dict,
    ):
            source_facts = recall_response.get(
            "source_facts"
        )

        return source_facts or {}

    @staticmethod
    def _extract_text(
        result: Any,
    ) -> Optional[str]:
        if isinstance(result, dict):
            value = result.get("text")
        else:
            value = getattr(
                result,
                "text",
                None,
            )

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    @staticmethod
    def _extract_similarity(
        result: Any,
    ) -> Optional[float]:
        if isinstance(result, dict):
            value = result.get(
                "semantic_similarity"
            )

            if value is None:
                value = result.get(
                    "retrieval_similarity"
                )

            scores = result.get(
                "scores"
            )

        else:
            value = getattr(
                result,
                "semantic_similarity",
                None,
            )

            if value is None:
                value = getattr(
                    result,
                    "retrieval_similarity",
                    None,
                )

            scores = getattr(
                result,
                "scores",
                None,
            )

        if value is not None:
            try:
                return float(value)
            except (
                TypeError,
                ValueError,
            ):
                return None

        if scores is not None:
            if isinstance(scores, dict):
                value = scores.get(
                    "semantic"
                )

            else:
                value = getattr(
                    scores,
                    "semantic",
                    None,
                )

            if value is not None:
                try:
                    return float(value)
                except (
                    TypeError,
                    ValueError,
                ):
                    return None

        return None

    def retrieve_candidates(
        self,
        bank_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """
        Execute:

            Hindsight recall
            → resolver
            → quality gate
        """

        if not isinstance(
            bank_id,
            str,
        ) or not bank_id.strip():
            raise ValueError(
                "bank_id must be a non-empty string."
            )

        if not isinstance(
            query,
            str,
        ) or not query.strip():
            raise ValueError(
                "query must be a non-empty string."
            )

        recall_response = (
            self.memory_service.recall(
                bank_id=bank_id,
                query=query.strip(),
            )
        )

        raw_results = self._extract_results(
            recall_response
        )
        print("\n========== RAW HINDSIGHT RESULTS ==========")
        print(f"RAW RESULT COUNT: {len(raw_results)}")

        for index, result in enumerate(raw_results, start=1):
            print(f"\nRAW RESULT #{index}")
            print("TYPE:", type(result).__name__)
            print("TEXT:", getattr(result, "text", None))
            print("CONTENT:", getattr(result, "content", None))
            print("SIMILARITY:", getattr(result, "similarity", None))
            print("SCORES:", getattr(result, "scores", None))

        if not raw_results:
            return {
                "raw_result_count": 0,
                "resolved_candidates": [],
                "candidates": [],
                "accepted_count": 0,
                "rejected_count": 0,
                "rejected": [],
            }

        source_facts = self._extract_source_facts(
    recall_response
)

        resolved = self.resolver.resolve_results(
    results=raw_results,
    bank_id=bank_id,
    source_facts=source_facts,
)
        print("\n========== D2 RESOLVER DEBUG ==========")
        print("RAW RESULTS:", len(raw_results))
        print("RESOLVED RESULTS:", len(resolved))

        for i, item in enumerate(resolved, 1):
            print(f"\nRESOLVED {i}:")
            print(item)

        print("========================================\n")

        # The resolver already removes candidates
        # that it cannot safely map.
        resolved_candidates = []

        for item in resolved:
            if not isinstance(
                item,
                dict,
            ):
                continue

            memory_id = item.get(
                "canonical_memory_id"
            )

            text = item.get(
                "text"
            )

            similarity = item.get(
                "retrieval_similarity"
            )

            if similarity is None:
                # Defensive recovery from the original
                # Hindsight result is intentionally NOT
                # attempted here because the resolver
                # should preserve the retrieval score.
                continue

            resolved_candidates.append(
                {
                    "canonical_memory_id": memory_id,
                    "text": text,
                    "retrieval_similarity": similarity,
                    "identity_score": item.get(
                        "identity_score"
                    ),
                    "identity_margin": item.get(
                        "identity_margin"
                    ),
                }
            )

        gated = (
            self.quality_gate
            .filter_and_deduplicate(
                resolved_candidates
            )
        )

        return {
            "raw_result_count": len(
                raw_results
            ),
            "resolved_candidates": resolved,
            "candidates": gated[
                "candidates"
            ],
            "accepted_count": gated[
                "accepted_count"
            ],
            "rejected_count": gated[
                "rejected_count"
            ],
            "rejected": gated[
                "rejected"
            ],
        }

    def select_memory(
        self,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not candidates:
            raise LookupError(
                "No valid memory candidates were "
                "available after retrieval filtering."
            )

        return self.selector.select(
            candidates
        )

    def build_context(
        self,
        query: str,
        selection: Dict[str, Any],
    ) -> Dict[str, Any]:
        selected = selection[
            "selected"
        ]

        memory_id = selected[
            "canonical_memory_id"
        ]

        learning_context = (
            self.closed_loop.build_agent_context(
                canonical_memory_id=memory_id,
                query=query,
                memory_text=selected.get(
                    "text"
                ),
            )
        )

        return {
            "query": query,
            "retrieval": {
                "selected": selected,
                "ranked_candidates": selection[
                    "ranked_candidates"
                ],
            },
            "memory": learning_context[
                "memory"
            ],
            "learning": learning_context[
                "learning"
            ],
            "decision": learning_context[
                "decision"
            ],
        }

    def generate_answer(
        self,
        context: Dict[str, Any],
        answer_generator=None,
    ):
        generator = (
            answer_generator
            if answer_generator is not None
            else self.answer_generator
        )

        if generator is None:
            raise RuntimeError(
                "No answer_generator was configured."
            )

        return generator(
            context
        )

    def answer(
        self,
        bank_id: str,
        query: str,
        answer_generator=None,
    ) -> Dict[str, Any]:
        # """
        # Complete single-pass answer workflow.

        # IMPORTANT:
        # Hindsight is queried exactly once.

        # Pipeline:

        #     Hindsight recall
        #         ↓
        #     canonical identity resolution
        #         ↓
        #     quality gate
        #         ↓
        #     C6 adaptive selection
        #         ↓
        #     C5 learning context
        #         ↓
        #     answer generation
        # """

        retrieval = self.retrieve_candidates(
            bank_id=bank_id,
            query=query,
        )

        candidates = retrieval["candidates"]

        if not candidates:
            raise LookupError(
                "No usable memories were found "
                "for the supplied query."
            )

        selection = self.select_memory(
            candidates
        )

        context = self.build_context(
            query=query,
            selection=selection,
        )

        answer = self.generate_answer(
            context=context,
            answer_generator=answer_generator,
        )

        selected = selection["selected"]

        return {
            "answer": answer,

            "selected_memory": selected,

            "selection": selection,

            "behavior": context[
                "decision"
            ]["behavior"],

            "learning": context[
                "learning"
            ]["state"],

            "provenance": context[
                "learning"
            ]["provenance"],

            "retrieval": {
                "raw_result_count": retrieval[
                    "raw_result_count"
                ],

                "resolved_count": len(
                    retrieval[
                        "resolved_candidates"
                    ]
                ),

                "accepted_count": retrieval[
                    "accepted_count"
                ],

                "rejected_count": retrieval[
                    "rejected_count"
                ],

                "rejected": retrieval[
                    "rejected"
                ],
            },
        }
    def close(self):
        """
        The orchestrator does not own the underlying
        services' lifecycle.

        The application/test that created the services
        remains responsible for closing them.
        """
        return None