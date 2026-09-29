from app.integrations.groq_client import GroqClient
from app.services.memory_service import MemoryService
from app.services.memory_context import MemoryContextBuilder


class AgentService:

    def __init__(self):
        self.groq = GroqClient()
        self.memory = MemoryService()
        self.context_builder = MemoryContextBuilder(
            relevance_threshold=0.002
        )

    def answer(
        self,
        bank_id: str,
        question: str,
        memory_enabled: bool = True,
    ):

        # ============================================================
        # MEMORY DISABLED
        # ============================================================

        if not memory_enabled:
            memory_context = "No project memory was provided."
            memory_count = 0
            memories_used = []

        # ============================================================
        # MEMORY ENABLED
        # ============================================================

        else:
            recall_result = self.memory.recall(
                bank_id=bank_id,
                query=question,
            )

            context_result = self.context_builder.build(
                recall_result.results
            )

            memory_context = context_result["context"]
            memory_count = context_result["memory_count"]
            memories_used = context_result["memories"]

        # ============================================================
        # SYSTEM PROMPT
        # ============================================================

        system_prompt = """
You are a project-aware AI assistant.

Your job is to answer the user's question accurately while
strictly separating:

1. HISTORICAL PROJECT EVIDENCE
2. GENERAL TECHNICAL KNOWLEDGE
3. CURRENT PROJECT FACTS

============================================================
HISTORICAL PROJECT EVIDENCE
============================================================

PROJECT MEMORY contains information that was previously
recorded about the project.

Treat this information as historical evidence.

You may use it to explain what happened previously.

However, historical evidence does NOT automatically prove
that the same implementation still exists today.

============================================================
NO FABRICATION
============================================================

NEVER invent project-specific details.

Do NOT claim that the project uses a specific:

- SQL query
- ORM
- framework annotation
- programming language
- library
- API
- database
- transaction configuration
- isolation level
- infrastructure component
- deployment system
- retry configuration
- background job
- async mechanism
- monitoring system
- test implementation
- command
- file
- class
- function
- configuration
- architecture
- Git commit

unless that information is explicitly present in PROJECT
MEMORY or in the user's current message.

If a project-specific detail is unknown, say that it is
unknown.

============================================================
GENERAL TECHNICAL REASONING
============================================================

You MAY provide general engineering knowledge and possible
investigation steps.

But clearly label these as possibilities, recommendations,
or things to check.

Do NOT present a general possibility as a fact about this
project.

For example:

BAD:
"The project uses SELECT FOR UPDATE."

GOOD:
"The historical memory says pessimistic database locking
was used, but it does not specify the exact SQL mechanism.
One thing to investigate would be whether the current
implementation still uses an appropriate row-locking
mechanism."

============================================================
CURRENT STATE
============================================================

Do NOT assume that historical project behavior is still
true today.

If the user asks what is happening NOW, distinguish:

- what the historical memory proves
- what is currently unknown
- what should be investigated

============================================================
RECOMMENDATIONS
============================================================

When recommending investigation steps:

1. Start from the historical evidence.
2. Explain what that evidence tells us.
3. Identify what remains unknown.
4. Suggest reasonable things to investigate.
5. Clearly label those things as recommendations or
   hypotheses rather than project facts.

============================================================
RELEVANCE
============================================================

If PROJECT MEMORY is unrelated to the question, ignore it.

Do not force project history into unrelated answers.

============================================================
ACCURACY
============================================================

Never manufacture project history merely to make the answer
appear personalized.

When evidence is insufficient, explicitly say so.
"""

        # ============================================================
        # USER PROMPT
        # ============================================================

        user_prompt = f"""
USER QUESTION
=============

{question}


PROJECT MEMORY EVIDENCE
=======================

{memory_context}


TASK
====

Answer the user's question directly.

Use the project memory when it is relevant.

For statements about what happened historically:

- rely only on the provided project memory.

For statements about the current project:

- do not assume historical behavior is still present.

For technical recommendations:

- use general engineering knowledge,
- clearly identify recommendations as things to investigate,
- do not present them as known project facts.

If important project information is missing, explicitly say
that it is unknown.

Do not invent project-specific implementation details.
"""

        # ============================================================
        # GENERATE ANSWER
        # ============================================================

        answer = self.groq.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return {
            "answer": answer,
            "memory_enabled": memory_enabled,
            "memory_count": memory_count,
            "memories_used": memories_used,
        }

    def close(self):
        self.memory.close()