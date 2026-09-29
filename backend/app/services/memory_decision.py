import json

from app.integrations.groq_client import GroqClient


class MemoryDecisionService:

    def __init__(self):
        self.groq = GroqClient()

    def decide(self, content: str) -> dict:

        system_prompt = """
You are a memory decision agent for a project-aware AI assistant.

Your job is to decide whether a piece of information should be
stored as LONG-TERM PROJECT MEMORY.

Return ONLY valid JSON.

The JSON must have exactly these fields:

{
    "should_retain": true or false,
    "memory_type": "fact" | "decision" | "experience" | "outcome" |
                    "preference" | "relationship" | "research" | "none",
    "importance": number between 0 and 1,
    "reason": "short explanation"
}

============================================================
RETAIN
============================================================

Retain information when it contains durable information about
the project.

Examples include:

- important project facts
- architectural decisions
- implementation decisions
- successful approaches
- failed approaches
- bugs and their causes
- solutions to project problems
- experiment results
- project outcomes
- reusable lessons
- project-specific preferences
- important relationships between project components

Examples:

"Our payment service uses pessimistic database locking."

This should be retained as a fact.

"We tried application-level retries for the wallet concurrency
problem, but the approach failed."

This should be retained as an experience.

"Pessimistic database locking resolved the concurrency problem
and the integration tests passed."

This should be retained as an outcome.

============================================================
DO NOT RETAIN
============================================================

Do NOT retain:

- greetings
- casual conversation
- acknowledgements
- filler
- temporary conversational statements
- generic technical knowledge
- generic explanations
- repeated information that adds no new value
- questions by themselves
- meaningless statements

Examples:

"Hello"

should not be retained.

"Okay, thanks."

should not be retained.

"TCP is a transport-layer protocol."

should generally not be retained unless it is specifically
important to the project.

============================================================
IMPORTANT RULE
============================================================

Be conservative.

Only retain information that is likely to be useful in future
project conversations.

The question is:

"If this information disappeared, would remembering it later
help the assistant understand or work on this project?"

If yes, retain it.

If no, do not retain it.

============================================================
OUTPUT
============================================================

Return ONLY JSON.

Do not use markdown.

Do not include ```json.

Do not include additional text.
"""

        user_prompt = f"""
Evaluate the following information.

INFORMATION:
{content}

Decide whether it should become long-term project memory.
"""

        raw_response = self.groq.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        try:
            decision = json.loads(raw_response)
        except json.JSONDecodeError:
            raise ValueError(
                "Memory Decision Agent returned invalid JSON: "
                + raw_response
            )

        required_fields = {
            "should_retain",
            "memory_type",
            "importance",
            "reason",
        }

        missing_fields = required_fields - decision.keys()

        if missing_fields:
            raise ValueError(
                "Memory Decision Agent response is missing fields: "
                + str(missing_fields)
            )

        if not isinstance(decision["should_retain"], bool):
            raise ValueError(
                "should_retain must be a boolean"
            )

        if not isinstance(decision["importance"], (int, float)):
            raise ValueError(
                "importance must be a number"
            )

        if not 0 <= decision["importance"] <= 1:
            raise ValueError(
                "importance must be between 0 and 1"
            )

        allowed_types = {
            "fact",
            "decision",
            "experience",
            "outcome",
            "preference",
            "relationship",
            "research",
            "none",
        }

        if decision["memory_type"] not in allowed_types:
            raise ValueError(
                "Invalid memory_type: "
                + str(decision["memory_type"])
            )

        if not isinstance(decision["reason"], str):
            raise ValueError(
                "reason must be a string"
            )

        return decision

    def close(self):
        self.groq.client.close()