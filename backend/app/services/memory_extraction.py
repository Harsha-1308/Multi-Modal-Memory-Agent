import json

from app.integrations.groq_client import GroqClient


class MemoryExtractionService:

    def __init__(self):
        self.groq = GroqClient()

    def extract(self, content: str) -> list:

        system_prompt = """
You are a universal memory extraction agent for a
long-term project-aware AI assistant.

Your job is to extract DURABLE, FUTURE-USEFUL pieces of
information from the user's message.

The information may come from ANY domain.

Do not assume the domain is software, engineering, finance,
research, education, medicine, business, or any other specific
domain.

Your job is domain-independent.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
    "memories": [
        {
            "content": "durable information",
            "memory_type": "fact",
            "importance": 0.0
        }
    ]
}

"memories" must always be a JSON array.

The array may contain zero, one, or multiple memories.

============================================================
WHAT SHOULD BECOME A MEMORY
============================================================

Extract information that is likely to remain useful in future
conversations.

Examples include:

- durable facts
- important decisions
- successful approaches
- failed approaches
- problems and their causes
- experiment results
- outcomes
- reusable lessons
- important project preferences
- relationships between important components
- important constraints
- significant research findings

============================================================
MEMORY TYPES
============================================================

Use exactly one of these types:

fact
decision
experience
outcome
preference
relationship
research

Definitions:

fact:
A durable statement about something that is true or was
established.

decision:
A meaningful choice that was made.

experience:
Something that was tried, encountered, or experienced,
especially when it provides useful historical information.

outcome:
The result of an action, experiment, decision, or approach.

preference:
A durable preference or working convention.

relationship:
A meaningful relationship between entities, components,
concepts, or people.

research:
A meaningful finding, observation, or conclusion from research
or investigation.

============================================================
DO NOT EXTRACT
============================================================

Do not extract:

- greetings
- acknowledgements
- filler
- casual conversation
- temporary conversational statements
- questions by themselves
- generic technical knowledge
- generic definitions
- information that has no likely future value

For example:

"Hello"

must produce:

{
    "memories": []
}

"Okay, thanks."

must produce:

{
    "memories": []
}

"TCP is a transport-layer protocol."

should normally produce:

{
    "memories": []
}

because this is generic technical knowledge rather than
project-specific durable information.

============================================================
MULTIPLE MEMORIES
============================================================

A single message can contain multiple independent durable facts.

Extract them separately when doing so preserves useful meaning.

Example:

"We tried Redis caching, but it increased complexity.
We switched to database indexing and response time improved."

Possible extraction:

[
    {
        "content": "Redis caching was tried.",
        "memory_type": "experience"
    },
    {
        "content": "Redis caching increased system complexity.",
        "memory_type": "experience"
    },
    {
        "content": "The team switched to database indexing.",
        "memory_type": "decision"
    },
    {
        "content": "Database indexing improved response time.",
        "memory_type": "outcome"
    }
]

Do not artificially split information when the pieces only make
sense together.

============================================================
PRESERVE MEANING
============================================================

Do not invent information.

Do not add technologies, causes, implementations, people,
dates, numbers, or relationships that are not present in the
input.

The extracted memory must be supported by the user's message.

============================================================
IMPORTANCE
============================================================

importance must be a number between 0 and 1.

Use higher values for information that is especially useful for
future conversations.

Use lower values for less important durable information.

============================================================
OUTPUT RULES
============================================================

Return ONLY valid JSON.

Do not use markdown.

Do not use ```json.

Do not include explanations outside the JSON.

Every memory object must contain exactly:

content
memory_type
importance
"""

        user_prompt = f"""
Extract durable future-useful memories from the following
information.

INFORMATION:
{content}
"""

        raw_response = self.groq.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            raise ValueError(
                "Memory Extraction Agent returned invalid JSON: "
                + raw_response
            )

        if not isinstance(result, dict):
            raise ValueError(
                "Memory Extraction Agent must return a JSON object"
            )

        if "memories" not in result:
            raise ValueError(
                "Memory Extraction Agent response is missing "
                "'memories'"
            )

        if not isinstance(result["memories"], list):
            raise ValueError(
                "'memories' must be a JSON array"
            )

        allowed_types = {
            "fact",
            "decision",
            "experience",
            "outcome",
            "preference",
            "relationship",
            "research",
        }

        validated_memories = []

        for memory in result["memories"]:

            if not isinstance(memory, dict):
                raise ValueError(
                    "Each memory must be a JSON object"
                )

            required_fields = {
                "content",
                "memory_type",
                "importance",
            }

            missing_fields = required_fields - memory.keys()

            if missing_fields:
                raise ValueError(
                    "Memory is missing fields: "
                    + str(missing_fields)
                )

            if not isinstance(memory["content"], str):
                raise ValueError(
                    "Memory content must be a string"
                )

            if not memory["content"].strip():
                raise ValueError(
                    "Memory content cannot be empty"
                )

            if memory["memory_type"] not in allowed_types:
                raise ValueError(
                    "Invalid memory_type: "
                    + str(memory["memory_type"])
                )

            if not isinstance(
                memory["importance"],
                (int, float),
            ):
                raise ValueError(
                    "Memory importance must be a number"
                )

            if not 0 <= memory["importance"] <= 1:
                raise ValueError(
                    "Memory importance must be between 0 and 1"
                )

            validated_memories.append(
                {
                    "content": memory["content"].strip(),
                    "memory_type": memory["memory_type"],
                    "importance": float(memory["importance"]),
                }
            )

        return validated_memories

    def close(self):
        self.groq.client.close()