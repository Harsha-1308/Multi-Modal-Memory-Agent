import os
from typing import Any, Dict, Optional
from app.core.config import settings
from groq import Groq


class LearningAwareGroqAgent:
    """
    C5.1 real LLM integration.

    This class deliberately does NOT calculate learning itself.

    C4 is responsible for:
        historical outcomes
        evidence
        learning signal

    C5 is responsible for:
        behavior decision

    This class is responsible for:
        passing that learning state to the real LLM
        and generating the final answer.

    Therefore the dependency direction is:

        C4
         ↓
        C5
         ↓
        Groq
    """

    DEFAULT_MODEL = "openai/gpt-oss-120b"

    def __init__(
        self,
        client: Optional[Groq] = None,
        model: Optional[str] = None,
    ):
        api_key = settings.GROQ_API_KEY

        if client is None:
            if not api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not configured."
                )

            client = Groq(
                api_key=api_key
            )

        self.client = client

        self.model = settings.GROQ_MODEL

    # ============================================================
    # PROMPT CONSTRUCTION
    # ============================================================

    @staticmethod
    def build_system_prompt() -> str:
        return """
You are the final answer generator for a project-memory AI agent.

Your job is to answer the USER QUESTION using the supplied memory,
evidence, and learning state.

GROUNDING RULES
1. Use only information supplied in the prompt.
2. Never invent facts, events, outcomes, causes, history, or details.
3. If the supplied memory contains one relevant fact, answer with that
   fact directly.
4. Do not turn a simple fact into a long explanation.
5. Do not infer information that is not explicitly supported.
6. Do not mention information merely because it is absent from memory.
7. Only discuss uncertainty when the supplied evidence itself contains
   conflicting or uncertain information.
8. If there is no relevant information, say:
   "I don't have enough information in project memory to answer that."

INTERNAL INFORMATION
The following information is INTERNAL and must NEVER be exposed to
the user unless the user explicitly asks how the memory system works:

- memory IDs
- canonical memory IDs
- retrieval scores
- similarity scores
- C4 learning state
- C5 behavior
- C5 decision reasons
- learning signals
- success/failure rates
- evidence IDs
- outcome IDs
- provenance metadata
- internal classifications
- routing information
- system implementation details

ANSWER STYLE
1. Answer the user's actual question directly.
2. Be concise.
3. Prefer 1-4 sentences for simple questions.
4. Do not create headings such as:
   "Answer", "What the evidence shows", "Implications",
   "Consequently", "Next steps", or "Missing information"
   unless the user explicitly asks for a detailed explanation.
5. Do not repeat the question.
6. Do not add generic background knowledge unless it is necessary
   to answer the question and is supported by the supplied context.
7. Do not expose the internal reasoning used to select the memory.
8. Do not mention C4, C5, C6, Hindsight, retrieval, learning,
   memory scores, or provenance in the final answer.

LEARNING
Learning state influences how confidently you use historical information,
but it is internal control information. Do not describe the learning
state to the user.

If historical evidence supports a fact, state the fact.
If historical evidence supports a conclusion, state the conclusion
with appropriate qualification.
If evidence is genuinely conflicting, briefly state the conflict.

The final response should sound like a normal helpful assistant,
not a system diagnostic report.
""".strip()

    @staticmethod
    def build_user_prompt(
    context: Dict[str, Any],
) -> str:

        query = context.get("query", "")

        memory = context.get("memory", {})
        learning = context.get("learning", {})
        decision = context.get("decision", {})

        memory_text = memory.get("text")

        state = learning.get("state", {})

        behavior = decision.get("behavior")

        return f"""
USER QUESTION
-------------
{query}

RELEVANT PROJECT MEMORY
-----------------------
{memory_text}

INTERNAL LEARNING STATE
-----------------------
Total outcomes: {state.get("total_outcomes")}
Successful outcomes: {state.get("successes")}
Failed outcomes: {state.get("failures")}
Partial outcomes: {state.get("partial")}
Unknown outcomes: {state.get("unknown")}
Informative outcomes: {state.get("informative_outcomes")}
Success rate: {state.get("success_rate")}
Failure rate: {state.get("failure_rate")}
Learning signal: {state.get("learning_signal")}
Evidence coverage: {state.get("evidence_coverage")}

INTERNAL BEHAVIOR DECISION
--------------------------
Behavior: {behavior}

TASK
----
Answer the USER QUESTION directly.

IMPORTANT:
- Use the relevant project memory when it answers the question.
- Do not invent anything.
- Do not expose the internal learning state or behavior decision.
- Do not mention memory IDs or internal metadata.
- Do not discuss what is missing unless the user asks.
- Do not create unnecessary headings.
- Keep the answer concise.
- If the memory contains a single fact that answers the question,
  simply state that fact.
TASK
----
Answer the USER QUESTION using the relevant project memory.

STRICT OUTPUT RULES:
- Return ONLY the answer to the user's question.
- Do not write an introduction.
- Do not write "Answer:".
- Do not write "Explanation:".
- Do not write "What the evidence shows".
- Do not write "Conclusion".
- Do not write "Note".
- Do not discuss what is missing from memory.
- Do not describe the memory system.
- Do not explain how the memory was retrieved.
- Do not expose internal metadata.
- Do not add implications, assumptions, or background information.
- Do not infer relationships that are not explicitly stated.
- If one sentence from the memory directly answers the question,
  return that fact in one concise sentence.
- If the question cannot be answered from the supplied memory,
  return exactly:
  "I don't have enough information to answer that."

Return plain conversational text.
""".strip()
    # ============================================================
    # GROQ CALL
    # ============================================================

    def answer(
        self,
        context: Dict[str, Any],
    ) -> str:
        memory = context.get("memory", {})
        memory_text = memory.get("text")
        if memory_text:
            return memory_text.strip()

        system_prompt = (
            self.build_system_prompt()
        )

        user_prompt = (
            self.build_user_prompt(
                context
            )
        )

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.1,
                max_completion_tokens=700,
            )
        )

        if not response.choices:
            raise RuntimeError(
                "Groq returned no choices."
            )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise RuntimeError(
                "Groq returned an empty answer."
            )

        return content.strip()
    def __call__(
    self,
    context: Dict[str, Any],
) -> str:
        return self.answer(context)

    # ============================================================
    # DEBUG / INSPECTION
    # ============================================================

    def explain_request(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "model": self.model,
            "memory_id": (
                context
                .get("memory", {})
                .get("canonical_memory_id")
            ),
            "behavior": (
                context
                .get("decision", {})
                .get("behavior")
            ),
            "learning_signal": (
                context
                .get("learning", {})
                .get("state", {})
                .get("learning_signal")
            ),
            "success_rate": (
                context
                .get("learning", {})
                .get("state", {})
                .get("success_rate")
            ),
            "failure_rate": (
                context
                .get("learning", {})
                .get("state", {})
                .get("failure_rate")
            ),
        }