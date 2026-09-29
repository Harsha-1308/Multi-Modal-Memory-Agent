from app.services.memory_decision import MemoryDecisionService
from app.services.memory_extraction import MemoryExtractionService
from app.services.memory_deduplication_service import (
    MemoryDeduplicationService,
)


class MemoryLearningService:

    def __init__(self):
        self.deduplication = MemoryDeduplicationService()
        self.decision = MemoryDecisionService()
        self.extraction = MemoryExtractionService()

    def process(self, bank_id: str, content: str):

        # --------------------------------------------------------
        # STEP 1 - Extract durable memories
        # --------------------------------------------------------

        extracted_memories = self.extraction.extract(content)

        result = {
            "input": content,
            "extracted_memories": extracted_memories,
            "decisions": [],
            "retained_memories": [],
            "discarded_memories": [],
        }

        # --------------------------------------------------------
        # STEP 2 - Process EACH extracted memory independently
        # --------------------------------------------------------

        for memory in extracted_memories:

            # ----------------------------------------------------
            # STEP 2A - Decide whether memory is worth retaining
            # ----------------------------------------------------

            decision = self.decision.decide(
                memory["content"]
            )

            decision_record = {
                "memory": memory,
                "decision": decision,
            }

            result["decisions"].append(
                decision_record
            )

            # ----------------------------------------------------
            # STEP 2B - Stop if the memory is not durable
            # ----------------------------------------------------

            if not decision["should_retain"]:

                discarded_record = {
                    "memory": memory,
                    "decision": decision,
                }

                result["discarded_memories"].append(
                    discarded_record
                )

                continue

            # ----------------------------------------------------
            # STEP 3 - Canonical memory / deduplication
            # ----------------------------------------------------

            memory_result = self.deduplication.retain_if_new(
                bank_id=bank_id,
                candidate=memory["content"],
            )

            # ----------------------------------------------------
            # STEP 4 - Separate retained vs discarded
            # ----------------------------------------------------

            if memory_result["retained"]:

                retained_record = {
                    "memory": memory,
                    "decision": decision,
                    "relationship": memory_result["relationship"],
                    "memory_result": memory_result,
                }

                result["retained_memories"].append(
                    retained_record
                )

            else:

                discarded_record = {
                    "memory": memory,
                    "decision": decision,
                    "relationship": memory_result["relationship"],
                    "memory_result": memory_result,
                }

                result["discarded_memories"].append(
                    discarded_record
                )

        return result

    def close(self):
        self.deduplication.close()
        self.decision.close()
        self.extraction.close()