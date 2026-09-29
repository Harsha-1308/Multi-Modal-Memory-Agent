from typing import Optional

from app.services.memory_relationship_service import (
    MemoryRelationship,
    MemoryRelationshipService,
)
from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)


class MemoryDeduplicationService:
    """
    B6 canonical memory decision layer.

    Responsibilities:

    1. Check exact duplicates locally.
    2. Inspect canonical memories already accepted by the system.
    3. Compare the candidate against stable canonical text.
    4. Detect:
       - exact duplicate
       - semantic duplicate
       - related but new
       - contradiction
    5. Register only genuinely new candidates.

    Hindsight remains the external memory backend.
    CanonicalMemoryService is the source of truth for
    deduplication comparisons.
    """

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        canonical_memory_service: Optional[
            CanonicalMemoryService
        ] = None,
        relationship_service: Optional[
            MemoryRelationshipService
        ] = None,
    ):
        self.memory_service = (
            memory_service
            if memory_service is not None
            else MemoryService()
        )

        self.canonical_memory_service = (
            canonical_memory_service
            if canonical_memory_service is not None
            else CanonicalMemoryService()
        )

        self.relationship_service = (
            relationship_service
            if relationship_service is not None
            else MemoryRelationshipService()
        )

    def analyze(
        self,
        bank_id: str,
        candidate: str,
    ) -> MemoryRelationship:
        """
        Analyze a candidate against canonical memories.

        Hindsight is NOT used as the source of comparison text.
        """

        # --------------------------------------------------
        # 1. Exact duplicate
        # --------------------------------------------------

        if self.canonical_memory_service.is_exact_duplicate(
            bank_id=bank_id,
            text=candidate,
        ):
            return MemoryRelationship(
                relationship=(
                    MemoryRelationshipService.EXACT_DUPLICATE
                ),
                similarity=1.0,
                reason=(
                    "Candidate already exists in the "
                    "canonical memory registry."
                ),
            )

        # --------------------------------------------------
        # 2. Get stable canonical memories
        # --------------------------------------------------

        canonical_memories = (
            self.canonical_memory_service.list_memories(
                bank_id=bank_id,
            )
        )

        if not canonical_memories:
            return MemoryRelationship(
                relationship=(
                    MemoryRelationshipService.RELATED_NEW
                ),
                similarity=None,
                reason=(
                    "No canonical memories are available "
                    "for comparison."
                ),
            )

        # --------------------------------------------------
        # 3. Compare candidate against canonical memories
        # --------------------------------------------------

        relationships = []

        for memory in canonical_memories:

            existing_text = memory["original_text"]

            relationship = (
                self.relationship_service.classify(
                    candidate=candidate,
                    existing=existing_text,
                    semantic_similarity=None,
                )
            )

            relationships.append(
                relationship
            )

        # --------------------------------------------------
        # 4. Contradiction first
        # --------------------------------------------------

        contradictions = [
            relationship
            for relationship in relationships
            if (
                relationship.relationship
                == MemoryRelationshipService.CONTRADICTION
            )
        ]

        if contradictions:
            return max(
                contradictions,
                key=lambda relationship: (
                    relationship.similarity
                    if relationship.similarity is not None
                    else 0.0
                ),
            )

        # --------------------------------------------------
        # 5. Semantic duplicate
        # --------------------------------------------------

        semantic_duplicates = [
            relationship
            for relationship in relationships
            if (
                relationship.relationship
                == MemoryRelationshipService.SEMANTIC_DUPLICATE
            )
        ]

        if semantic_duplicates:
            return max(
                semantic_duplicates,
                key=lambda relationship: (
                    relationship.similarity
                    if relationship.similarity is not None
                    else 0.0
                ),
            )

        # --------------------------------------------------
        # 6. Otherwise related/new
        # --------------------------------------------------

        return max(
            relationships,
            key=lambda relationship: (
                relationship.similarity
                if relationship.similarity is not None
                else 0.0
            ),
        )

    def retain_if_new(
        self,
        bank_id: str,
        candidate: str,
    ):
        """
        Analyze and retain the candidate only when it is not
        an exact or semantic duplicate.

        Contradictions and related-new memories are preserved.
        """

        relationship = self.analyze(
            bank_id=bank_id,
            candidate=candidate,
        )

        if relationship.relationship in {
            MemoryRelationshipService.EXACT_DUPLICATE,
            MemoryRelationshipService.SEMANTIC_DUPLICATE,
        }:
            return {
                "retained": False,
                "relationship": relationship,
                "hindsight_result": None,
            }

        # --------------------------------------------------
        # Register canonical memory FIRST
        # --------------------------------------------------

        registered = (
            self.canonical_memory_service.register(
                bank_id=bank_id,
                text=candidate,
            )
        )

        if not registered:
            return {
                "retained": False,
                "relationship": MemoryRelationship(
                    relationship=(
                        MemoryRelationshipService.EXACT_DUPLICATE
                    ),
                    similarity=1.0,
                    reason=(
                        "Candidate was already registered "
                        "by another operation."
                    ),
                ),
                "hindsight_result": None,
            }

        # --------------------------------------------------
        # Store in Hindsight
        # --------------------------------------------------

        hindsight_result = (
            self.memory_service.retain(
                bank_id=bank_id,
                content=candidate,
            )
        )

        return {
            "retained": True,
            "relationship": relationship,
            "hindsight_result": hindsight_result,
        }

    def close(self):
        self.canonical_memory_service.close()
        self.memory_service.close()