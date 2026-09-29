from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.integrations.groq_client import GroqClient


class NormalChatService:
    """
    Handles chat when memory_enabled is False.
    Uses ONLY current chat message history and backend Groq credentials.
    Performs NO Hindsight recall/retain, NO canonical registry operations,
    and NO C1-C6 learning logic.
    """

    def __init__(
        self,
        groq_client: Optional[Any] = None,
        model: Optional[str] = None,
    ):
        self.groq_wrapper = groq_client or GroqClient()
        self.model = model or settings.GROQ_MODEL

    def _get_client(self):
        return getattr(self.groq_wrapper, "client", self.groq_wrapper)

    def answer(
        self,
        *,
        user_message: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        evidence_descriptions: Optional[List[str]] = None,
        project_name: Optional[str] = None,
    ) -> str:
        client = self._get_client()

        system_prompt = (
            "You are a helpful, clear, and direct AI assistant. "
            "Memory mode is currently DISABLED for this conversation. "
            "You have access ONLY to the current chat context provided. "
            "Do not pretend to recall information from long-term project memory."
        )
        if project_name:
            system_prompt += f" The current workspace project is {project_name}."

        messages = [{"role": "system", "content": system_prompt}]

        # Add recent conversation history (last 10 messages)
        if chat_history:
            for msg in chat_history[-10:]:
                role = msg.get("role")
                content = msg.get("content")
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": content})

        # Append current user message with any attached evidence context
        content_parts = []
        if user_message and user_message.strip():
            content_parts.append(user_message.strip())
        if evidence_descriptions:
            content_parts.append("\n\nAttached evidence context:")
            for desc in evidence_descriptions:
                content_parts.append(f"- {desc}")

        full_user_content = "\n".join(content_parts).strip()
        if full_user_content:
            messages.append({"role": "user", "content": full_user_content})
        else:
            messages.append({"role": "user", "content": "Please respond to the attached evidence context."})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_completion_tokens=800,
        )

        reply = getattr(response.choices[0].message, "content", "")
        return str(reply or "").strip()
