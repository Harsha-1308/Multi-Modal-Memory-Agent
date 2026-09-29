class MemoryContextBuilder:

    def __init__(self, relevance_threshold: float = 0.002):
        self.relevance_threshold = relevance_threshold

    def build(self, memories):
        """
        Build project-memory context from Hindsight results.

        The threshold is applied at the QUERY level:
        if no retrieved memory has a final score above the
        threshold, we treat the query as having no relevant
        project memory.

        We do NOT filter individual memories by score.
        If the query is relevant, all retrieved memories
        are preserved so useful historical context is not lost.
        """

        if not memories:
            return {
                "has_memory": False,
                "memory_count": 0,
                "max_score": 0.0,
                "context": "No relevant project memory was found.",
                "memories": [],
            }

        formatted_memories = []

        max_score = 0.0

        for memory in memories:
            score = getattr(memory.scores, "final", 0.0) or 0.0

            if score > max_score:
                max_score = score

            formatted_memories.append(
                {
                    "text": memory.text,
                    "type": getattr(memory, "type", "unknown"),
                    "score": score,
                }
            )

        # --------------------------------------------------
        # QUERY-LEVEL RELEVANCE DECISION
        # --------------------------------------------------

        if max_score < self.relevance_threshold:
            return {
                "has_memory": False,
                "memory_count": 0,
                "max_score": max_score,
                "context": "No relevant project memory was found.",
                "memories": [],
            }

        # --------------------------------------------------
        # RELEVANT QUERY
        #
        # IMPORTANT:
        # Do not filter individual memories by score.
        # Preserve the complete retrieved context.
        # --------------------------------------------------

        context_lines = [
            "PROJECT MEMORY EVIDENCE",
            "",
            "The following information comes from historical "
            "project memory. Treat it as project evidence, not "
            "as proof of the current system state.",
            "",
        ]

        for index, memory in enumerate(formatted_memories, start=1):
            context_lines.append(
                f"{index}. [{memory['type']}] {memory['text']}"
            )

        return {
            "has_memory": True,
            "memory_count": len(formatted_memories),
            "max_score": max_score,
            "context": "\n".join(context_lines),
            "memories": formatted_memories,
        }