from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.config import settings
from app.repositories.message_repository import MessageRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.sqlite.learning_repository import SQLiteLearningRepository
from app.services.adaptive_memory_selector import AdaptiveMemorySelector
from app.services.canonical_memory_service import CanonicalMemoryService
from app.services.closed_learning_loop_service import ClosedLearningLoopService
from app.services.evidence_service import EvidenceService
from app.services.experience_service import ExperienceService
from app.services.hindsight_canonical_resolver import HindsightCanonicalResolver
from app.services.learning_agent_service import LearningAgentService
from app.services.learning_aware_groq_agent import LearningAwareGroqAgent
from app.services.learning_feedback_service import LearningFeedbackService
from app.services.learning_interaction_service import LearningInteractionService
from app.services.memory_deduplication_service import MemoryDeduplicationService
from app.services.memory_learning_state_service import MemoryLearningStateService
from app.services.memory_service import MemoryService
from app.services.outcome_capture_service import OutcomeCaptureService
from app.services.outcome_classification_service import OutcomeClassificationService
from app.services.retrieval_quality_gate import RetrievalQualityGate

logger = logging.getLogger(__name__)

RECENT_UPDATE_LIMIT = 8
GENERAL_MEMORY_MATCH_THRESHOLD = 0.20

PROJECT_REFERENCE_PATTERNS = (
    r"\bthis\s+project\b",
    r"\bour\s+project\b",
    r"\bthe\s+project\b",
    r"\bproject\s+(?:memory|context|knowledge|history|update|record)\b",
    r"\bfrom\s+(?:my|our|your)\s+memory\b",
    r"\bwhat\s+did\s+(?:we|i|you)\s+say\b",
    r"\bwhat\s+do\s+you\s+remember\b",
    r"\bwhat\s+was\s+recorded\b",
    r"\bwhat\s+did\s+we\s+(?:change|implement|fix|decide|deploy|try|test)\b",
    r"\bwhat\s+was\s+(?:implemented|changed|fixed|deployed|tested)\b",
    r"\bearlier\s+(?:we|i|you)\b",
)

QUESTION_STARTERS = {
    "what", "why", "how", "when", "where", "who", "which", "can", "could",
    "should", "would", "do", "does", "did", "is", "are", "was", "were",
    "will", "have", "has", "had", "tell", "explain", "show", "give",
}

GREETING_PATTERNS = (
    r"^(hi|hello|hey|hey there|good morning|good afternoon|good evening)\b",
    r"^how are you\b",
    r"^how is it going\b",
    r"^what(?:'s|\s+is)\s+up\b",
)

IDENTITY_CHAT_PATTERNS = (
    r"^what(?:'s|\s+is)\s+your\s+name\??$",
    r"^who\s+are\s+you\??$",
)

ACK_PATTERNS = (
    r"^(ok|okay|got it|understood|cool|great|nice|perfect|awesome|sounds good)\b",
)

MEMORY_UPDATE_PATTERNS = (
    r"\b(?:we|i)\s+(?:found|discovered|implemented|integrated|tried|tested|fixed|resolved|decided|deployed|changed|updated|configured|removed|added|switched|chose|selected)\b",
    r"\b(?:we|i)\s+(?:will|should|plan\s+to|are\s+going\s+to|am\s+going\s+to)\s+(?:use|implement|change|add|remove|deploy|switch|try)\b",
    r"\b(?:this|that|the)\b(?:\s+[a-z0-9_.-]+){1,6}\s+(?:is|was|isn't|isnt|is\s+not|wasn't|wasnt|was\s+not|fails?|failed|crashes?|crashed|crashing|broke|broken|doesn't|doesnt|does\s+not|returns?|throws?|stopped|passed|passes|succeeded|successful|not\s+working|not\s+work)\b",
    r"\b(?:the|this|that|my|our)\s+[a-z0-9_./:-]+(?:\s+[a-z0-9_./:-]+){0,6}\s+(?:passed|failed|crashed|broke|is\s+broken|is\s+failing|is\s+working|isn't\s+working|doesn't\s+work|didn't\s+work)\b",
    r"\b(?:there\s+(?:is|was)|we\s+have|i\s+have)\b.*\b(?:error|exception|bug|issue|problem|failure|crash|crashed|broken|not\s+working)\b",
    r"\b(?:error|exception|traceback|stack\s+trace|compiler error|build error|bug|issue|problem)\b.*\b(?:occurred|happened|appeared|failed|failing|broken|crashed|throws?|returned|returns?)\b",
    r"\b(?:fails?|failed|crashes?|crashed|returns?|returned|throws?|threw|raises?|raised)\b.*\b(?:error|exception|bug|issue|problem|traceback)\b",
    r"\b(?:the|this|that)\s+[a-z0-9_./:-]+(?:\s+[a-z0-9_./:-]+){0,5}\s+(?:passed|failed|crashed|broke|is\s+broken|is\s+failing|is\s+working|isn't\s+working)\b",
    r"\b(?:implemented|deployed|tested|fixed|resolved|changed|updated|configured|integrated|removed|added|switched)\b.*\b(?:success|successful|passed|failed|failure|working|works|broken|error)\b",
)

PROJECT_SUMMARY_PATTERNS = (
    r"\bwhat\s+happen(?:ed|d)\b",
    r"\bwhat\s+happen(?:ed|d)\s+(?:with|to)\b",
    r"\bwhat\s+did\s+(?:we|i|the\s+team)\s+(?:try|do)\b",
    r"\bwhat\s+was\s+tried\b",
    r"\bwhat\s+was\s+the\s+history\b",
    r"\bwhere\s+are\s+we\s+with\b",
    r"\bwhat(?:'s|\s+is)\s+the\s+(?:current\s+)?status\b",
    r"\bwhat\s+are\s+we\s+(?:using|doing)\s+(?:here|now)\b",
    r"\bwhy\s+did\s+(?:this|that|it)\s+(?:fail|break|stop|change)\b",
    r"\bwhat\s+(?:was|is)\s+happening\s+(?:with|to)\b",
    r"\bwhat\s+(?:was|is)\s+going\s+on\s+(?:with|to)\b",
    r"\bwhat\s+(?:problem|problems|issue|issues)\b.*\b(?:facing|faced|had|have|mentioned|recorded|before|previously)\b",
    r"\b(?:which|what)\s+(?:problem|problems|issue|issues)\b.*\b(?:before|previously|so\s+far|until\s+now)\b",
    r"\bwhat\s+(?:problems|issues|bugs|incidents|challenges|blockers)\s+(?:have|has)\b",
    r"\bwhat\s+have\s+we\s+(?:faced|seen|encountered)\b",
    r"\blist\s+(?:the\s+)?(?:problems|issues|bugs|incidents|challenges|blockers)\b",
)

MEMORY_INVENTORY_PATTERNS = (
    r"\bwhat\s+(?:do|did)\s+you\s+(?:have|keep|remember)\s+in\s+(?:your|this)\s+(?:project\s+)?memory\b",
    r"\bwhat\s+(?:is|are)\s+(?:in|inside)\s+(?:your|this)\s+(?:project\s+)?memory\b",
    r"\bshow\s+(?:me\s+)?(?:your|the|this)\s+(?:project\s+)?memory\b",
    r"\bwhat\s+(?:have|has)\s+(?:you|we)\s+remembered\b",
    r"\bshow\s+(?:me\s+)?(?:all\s+)?(?:project\s+)?memories\b",
)

GENERIC_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on",
    "at", "by", "with", "from", "about", "into", "as", "is", "are", "was",
    "were", "be", "been", "being", "do", "does", "did", "what", "why", "how",
    "when", "where", "who", "which", "can", "could", "should", "would", "will",
    "have", "has", "had", "we", "i", "you", "our", "your", "me", "it", "this",
    "that", "there", "then", "they", "them", "said", "say", "tell", "please",
    "now", "just", "already", "used", "use", "u", "ur",
}

MORPHOLOGY_SUFFIXES = (
    ("ies", "y"),
    ("ing", ""),
    ("ed", ""),
    ("es", ""),
    ("s", ""),
)

STOP_WORDS = GENERIC_STOP_WORDS


def normalize_token(token: str) -> str:
    t = (token or "").lower().strip()
    if not t or t in STOP_WORDS:
        return t or ""
    for suffix, replacement in MORPHOLOGY_SUFFIXES:
        if suffix == "s" and t.endswith(("us", "ss", "is")):
            continue
        if suffix == "es" and t.endswith("sses"):
            candidate = t[:-2]
            if candidate.endswith("ss"):
                return candidate
        if t.endswith(suffix) and len(t) > len(suffix) + 2:
            candidate = t[: -len(suffix)] + replacement
            if len(candidate) >= 3:
                return candidate
    return t


def content_tokens(text: str) -> List[str]:
    tokens = []
    for token in re.findall(r"[a-z0-9]+", (text or "").lower()):
        norm = normalize_token(token)
        if token in STOP_WORDS or norm in STOP_WORDS:
            continue
        if norm:
            tokens.append(norm)
    return tokens


def lexical_relevance(query: str, text: str) -> float:
    q_tokens = content_tokens(query)
    t_tokens = content_tokens(text)
    if not q_tokens or not t_tokens:
        return 0.0

    q_set = set(q_tokens)
    t_set = set(t_tokens)
    overlap = len(q_set & t_set) / max(1, len(q_set))

    q_text = " ".join(q_tokens)
    t_text = " ".join(t_tokens)
    sequence = 1.0 if q_text and q_text in t_text else 0.0

    bigram_hits = 0
    if len(q_tokens) >= 2:
        t_set_bigrams = {
            (t_tokens[i], t_tokens[i + 1]) for i in range(len(t_tokens) - 1)
        }
        for i in range(len(q_tokens) - 1):
            if (q_tokens[i], q_tokens[i + 1]) in t_set_bigrams:
                bigram_hits += 1
    bigram_score = (
        bigram_hits / max(1, len(q_tokens) - 1) if len(q_tokens) >= 2 else 0.0
    )

    fuzzy_hits = 0
    for q_token in q_set:
        if any(
            SequenceMatcher(None, q_token, t_token).ratio() >= 0.86
            for t_token in t_set
        ):
            fuzzy_hits += 1
    fuzzy_score = fuzzy_hits / max(1, len(q_set))

    return max(
        0.0,
        min(
            1.0,
            (0.55 * overlap)
            + (0.15 * bigram_score)
            + (0.10 * sequence)
            + (0.20 * fuzzy_score),
        ),
    )


def has_project_signal(text: str) -> bool:
    return any(re.search(p, text.strip().lower()) for p in PROJECT_REFERENCE_PATTERNS)


def _collapse_repeated_letters(value: str) -> str:
    return re.sub(r"(.)\1{1,}", r"\1\1", value)


def fuzzy_match_word(word: str, targets: Sequence[str], threshold: float = 0.80) -> bool:
    candidate = _collapse_repeated_letters((word or "").strip().lower())
    if not candidate:
        return False
    for target in targets:
        target_norm = _collapse_repeated_letters(target.lower())
        if candidate == target_norm:
            return True
        if len(candidate) < 2 or abs(len(candidate) - len(target_norm)) > 2:
            continue
        if SequenceMatcher(None, candidate, target_norm).ratio() >= threshold:
            return True
    return False


def normalize_routing_text(text: str) -> str:
    value = " ".join((text or "").strip().split()).lower()
    replacements = (
        (r"\bwhat\s*'s\b", "what is"),
        (r"\bwhats\b", "what is"),
        (r"\bwho\s*'s\b", "who is"),
        (r"\bwhos\b", "who is"),
        (r"\bhow\s*'s\b", "how is"),
        (r"\bhow\s+r\b", "how are"),
        (r"\bwho\s+r\b", "who are"),
        (r"\bdo\s+u\b", "do you"),
        (r"\bcan\s+u\b", "can you"),
        (r"\bcould\s+u\b", "could you"),
        (r"\bwould\s+u\b", "would you"),
        (r"\btell\s+me\s+u\b", "tell me you"),
        (r"\bu\b", "you"),
        (r"\bur\b", "your"),
    )
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value)
    return value


def extract_fuzzy_greeting_remainder(text: str) -> Optional[str]:
    lowered = normalize_routing_text(text)
    match = re.match(r"^([a-z]+)(?:[\s,!?;:.]+|$)", lowered)
    if not match:
        return None
    if not fuzzy_match_word(match.group(1), ("hi", "hello", "hey")):
        return None
    return lowered[match.end():].strip()


def is_social_message(text: str) -> bool:
    lowered = normalize_routing_text(text)
    if not lowered:
        return True
    if any(re.search(p, lowered) for p in IDENTITY_CHAT_PATTERNS):
        return True
    if any(re.search(p, lowered) for p in GREETING_PATTERNS):
        return True
    if any(re.search(p, lowered) for p in ACK_PATTERNS):
        return True
    first = re.match(r"^([a-z]+)", lowered)
    if first and fuzzy_match_word(first.group(1), ("thanks", "thank"), threshold=0.80):
        return True
    return False


def is_project_summary_query(text: str) -> bool:
    normalized = " ".join((text or "").strip().split()).lower()
    return is_memory_inventory_query(normalized) or any(
        re.search(pattern, normalized)
        for pattern in PROJECT_SUMMARY_PATTERNS
    )


def is_memory_inventory_query(text: str) -> bool:
    normalized = " ".join((text or "").strip().split()).lower()
    return any(re.search(pattern, normalized) for pattern in MEMORY_INVENTORY_PATTERNS)


def classify_user_input(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return "CHAT"

    normalized = normalize_routing_text(cleaned.lower())
    greeting_remainder = extract_fuzzy_greeting_remainder(normalized)
    routing_text = greeting_remainder if greeting_remainder else normalized

    if greeting_remainder is not None and (
        not greeting_remainder or is_social_message(greeting_remainder)
    ):
        return "CHAT"

    if any(re.search(p, routing_text) for p in IDENTITY_CHAT_PATTERNS):
        return "CHAT"

    followup_question = bool(
        re.match(
            r"^(thanks|thank you|thx)[,!\.\s]+(?:now\s+)?"
            r"(?:explain|tell me|show me|describe|why|how|what|which|when|where)\b",
            routing_text,
        )
    )

    words = re.findall(r"[a-z0-9]+", routing_text)
    first_word = words[0] if words else ""
    question_start = (
        first_word in QUESTION_STARTERS
        or re.match(
            r"^(tell me|explain|show me|describe|do you know|can you|could you|"
            r"would you|please explain|please tell me)\b",
            routing_text,
        )
    )
    is_question = "?" in routing_text or bool(question_start) or followup_question

    if not followup_question and any(re.search(p, routing_text) for p in GREETING_PATTERNS):
        return "CHAT"

    if is_project_summary_query(routing_text):
        return "PROJECT_QUERY"

    if is_question:
        return "PROJECT_QUERY" if has_project_signal(routing_text) else "GENERAL_QUERY"

    if any(re.search(pattern, routing_text) for pattern in MEMORY_UPDATE_PATTERNS):
        return "MEMORY_UPDATE"

    if ("```" in cleaned or re.search(
        r"\b(?:traceback|stack trace|compiler error|build error)\b",
        routing_text,
        re.I,
    )) and not is_question:
        return "MEMORY_UPDATE"

    if not is_question and is_social_message(routing_text):
        return "CHAT"

    return "CHAT"


def short_text(value: Any, limit: int = 420) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def canonical_text(memory: Any) -> Optional[str]:
    if isinstance(memory, dict):
        return memory.get("original_text") or memory.get("text")
    return getattr(memory, "original_text", None) or getattr(memory, "text", None)


def canonical_id(memory: Any) -> Optional[int]:
    if isinstance(memory, int):
        return memory
    if isinstance(memory, dict):
        val = memory.get("id") or memory.get("canonical_memory_id") or memory.get("memory_id")
    else:
        val = getattr(memory, "id", None) or getattr(memory, "canonical_memory_id", None) or getattr(memory, "memory_id", None)
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def find_canonical_id_by_text(memories: List[Dict[str, Any]], text: str) -> Optional[int]:
    for memory in memories:
        if canonical_text(memory) == text:
            return canonical_id(memory)
    return None


class SemanticIntentRouter:
    VALID_INTENTS = {"CHAT", "MEMORY_UPDATE", "PROJECT_QUERY", "GENERAL_QUERY"}

    def __init__(self, *, groq_agent: Any, project_name: str, project_description: str) -> None:
        self.groq_agent = groq_agent
        self.project_name = project_name
        self.project_description = project_description

    @classmethod
    def parse_intent(cls, raw: str) -> Optional[str]:
        value = (raw or "").strip()
        if not value:
            return None
        try:
            data = json.loads(value)
            intent = str(data.get("intent", "")).strip().upper()
            if intent in cls.VALID_INTENTS:
                return intent
        except Exception:
            pass

        explicit = re.search(
            r'"?intent"?\s*:\s*"?(CHAT|MEMORY_UPDATE|PROJECT_QUERY|GENERAL_QUERY)\b',
            value,
            re.I,
        )
        if explicit:
            return explicit.group(1).upper()

        compact = value.strip().upper()
        if compact in cls.VALID_INTENTS:
            return compact

        return None

    @staticmethod
    def recent_context(message_repo: MessageRepository, project_id: str) -> str:
        rows = message_repo.list_for_project(project_id)
        useful = [
            row for row in rows
            if row.get("role") == "user"
            and row.get("message_type") in {"MEMORY_UPDATE", "PROJECT_QUERY"}
        ]
        lines = [
            f"- [{row.get('message_type')}] {short_text(row.get('content'), 320)}"
            for row in useful[-8:]
        ]
        return "\n".join(lines) if lines else "- none"

    @staticmethod
    def _contextual_fallback(cleaned: str, base_fallback: str, recent: str) -> str:
        if base_fallback != "GENERAL_QUERY":
            return base_fallback

        normalized = normalize_routing_text(cleaned)
        if is_project_summary_query(normalized):
            return "PROJECT_QUERY"

        has_recent_project_context = recent.strip() not in {"", "- none"}
        vague_reference = bool(
            re.search(
                r"\b(?:this|that|it|here|there|previously|earlier|before|last\s+time|so\s+far|until\s+now)\b",
                normalized,
            )
        )
        question_like = (
            "?" in normalized
            or bool(
                re.match(
                    r"^(?:what|why|how|when|where|which|can|could|should|would|"
                    r"do|does|did|is|are|was|were|will|have|has|had|tell|explain|"
                    r"show|describe)\b",
                    normalized,
                )
            )
        )

        if has_recent_project_context and vague_reference and question_like:
            return "PROJECT_QUERY"

        return base_fallback

    def classify(
        self,
        *,
        text: str,
        message_repo: MessageRepository,
        project_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        cleaned = " ".join((text or "").strip().split())
        fallback = classify_user_input(cleaned)
        recent = self.recent_context(message_repo, project_id)

        if fallback == "CHAT" and is_social_message(cleaned):
            return "CHAT", {
                "source": "deterministic_social",
                "fallback": fallback,
            }

        client = getattr(self.groq_agent, "client", None)
        if client is None:
            contextual = self._contextual_fallback(cleaned, fallback, recent)
            return contextual, {
                "source": "deterministic_contextual_fallback",
                "fallback": fallback,
                "recent_project_context": bool(recent.strip() not in {"", "- none"}),
            }

        system = (
            "You are the semantic intent router for a project-aware assistant. "
            "Choose exactly one of CHAT, MEMORY_UPDATE, PROJECT_QUERY, GENERAL_QUERY.\n\n"
            "CHAT = greeting, thanks, acknowledgement, identity, ordinary social conversation.\n"
            "MEMORY_UPDATE = the user is contributing new project/work information. This includes "
            "implementation changes, code/configuration changes, bug or error reports, test results, "
            "deployments, experiments, discoveries, decisions, or a statement like 'this code is not "
            "working'. It does not require a project keyword.\n"
            "PROJECT_QUERY = the user asks about the active project's implementation, history, prior "
            "decisions, bugs, results, or what was done before. It can use vague references such as "
            "'what did we change?', 'why did that fail?', 'what happened to it before?', or "
            "'what are we using here?'.\n"
            "GENERAL_QUERY = a normal knowledge/explanation question. For example, 'what are locks?', "
            "'what is normalization?', or 'what is Python?'. A general question remains a general "
            "question even when the same topic exists in project memory; a later memory-awareness step "
            "may add optional project context.\n\n"
            "Recent project work is provided only to resolve conversational context. "
            "Do not classify solely from nouns or topic overlap. Infer the user's intent. "
            'Return ONLY JSON in the form {"intent":"...","reason":"..."}.'
        )
        user = (
            f"Active project: {self.project_name}\n"
            f"Project description: {self.project_description}\n\n"
            f"Recent project work/conversation:\n{recent}\n\n"
            f"Current user message:\n{cleaned}"
        )

        model = getattr(self.groq_agent, "model", settings.GROQ_MODEL)

        def invoke(max_tokens: int) -> str:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                max_completion_tokens=max_tokens,
            )
            try:
                content = response.choices[0].message.content
            except Exception:
                content = None
            return str(content or "").strip()

        try:
            raw = invoke(300)
            parsed = self.parse_intent(raw)
            if parsed is None and not raw:
                raw = invoke(450)
                parsed = self.parse_intent(raw)

            if parsed:
    # Never allow the semantic router to downgrade a real
    # project/general question into ordinary CHAT.
                normalized = normalize_routing_text(cleaned)

                question_like = (
        "?" in normalized
        or bool(
            re.match(
                r"^(?:what|why|how|when|where|which|can|could|should|would|"
                r"do|does|did|is|are|was|were|will|have|has|had|tell|explain|"
                r"show|describe)\b",
                normalized,
            )
        )
    )

                print("ROUTER DEBUG:", {
    "cleaned": cleaned,
    "fallback": fallback,
    "parsed_before_guard": parsed,
    "question_like": question_like,
    "social": is_social_message(cleaned),
})
                if parsed == "CHAT" and question_like and not is_social_message(cleaned):
                    parsed = fallback

                return parsed, {
        "source": "semantic_groq",
        "fallback": fallback,
        "raw": raw,
    }

            contextual = self._contextual_fallback(cleaned, fallback, recent)
            return contextual, {
                "source": "deterministic_contextual_fallback_after_unparseable_router",
                "fallback": fallback,
                "raw": raw,
            }
        except Exception as exc:
            contextual = self._contextual_fallback(cleaned, fallback, recent)
            return contextual, {
                "source": "deterministic_contextual_fallback_after_router_error",
                "fallback": fallback,
                "error": str(exc),
            }


class RuntimeMemoryIngestionService:
    def __init__(
        self,
        *,
        memory_service: MemoryService,
        canonical_memory_service: CanonicalMemoryService,
        learning_service: Optional[MemoryLearningStateService] = None,
    ) -> None:
        self.memory_service = memory_service
        self.canonical_memory_service = canonical_memory_service
        self.learning_service = learning_service
        self.deduplicator = MemoryDeduplicationService(
            memory_service=memory_service,
            canonical_memory_service=canonical_memory_service,
        )

    def ingest(self, bank_id: str, text: str) -> Dict[str, Any]:
        candidate = " ".join((text or "").strip().split())
        if not candidate:
            raise ValueError("Cannot ingest empty memory text.")

        before = self.canonical_memory_service.list_memories(bank_id=bank_id)
        before_ids = {
            canonical_id(item)
            for item in before
            if canonical_id(item) is not None
        }

        try:
            result = self.deduplicator.retain_if_new(
                bank_id=bank_id,
                candidate=candidate,
            )
        except Exception as exc:
            return {
                "input": candidate,
                "retained": False,
                "relationship": None,
                "relationship_similarity": None,
                "canonical_memory_id": None,
                "canonical_registry_verified": False,
                "hindsight_action": "error",
                "hindsight_result_type": None,
                "hindsight_error": str(exc),
                "learning_state_error": None,
                "raw_result": None,
            }

        relationship = result.get("relationship")
        relationship_name = getattr(relationship, "relationship", None)
        relationship_similarity = getattr(relationship, "similarity", None)

        after = self.canonical_memory_service.list_memories(bank_id=bank_id)
        exact_id = find_canonical_id_by_text(after, candidate)
        new_ids = [
            canonical_id(item)
            for item in after
            if canonical_id(item) is not None
            and canonical_id(item) not in before_ids
        ]

        if result.get("retained"):
            hindsight_action = "retained"
        elif relationship_name in {"exact_duplicate", "semantic_duplicate"}:
            hindsight_action = "skipped_duplicate"
        else:
            hindsight_action = "not_verified"

        memory_id = exact_id or (new_ids[0] if len(new_ids) == 1 else None)

        if memory_id is not None and self.learning_service is not None:
            try:
                self.learning_service.refresh(int(memory_id))
            except Exception as exc:
                return {
                    "input": candidate,
                    "retained": bool(result.get("retained")),
                    "relationship": relationship_name,
                    "relationship_similarity": relationship_similarity,
                    "canonical_memory_id": memory_id,
                    "canonical_registry_verified": True,
                    "hindsight_action": hindsight_action,
                    "hindsight_result_type": (
                        type(result.get("hindsight_result")).__name__
                        if result.get("hindsight_result") is not None
                        else None
                    ),
                    "hindsight_error": None,
                    "learning_state_error": str(exc),
                    "raw_result": result,
                }

        hindsight_result = result.get("hindsight_result")
        return {
            "input": candidate,
            "retained": bool(result.get("retained")),
            "relationship": relationship_name,
            "relationship_similarity": relationship_similarity,
            "canonical_memory_id": memory_id,
            "canonical_registry_verified": bool(memory_id is not None),
            "hindsight_action": hindsight_action,
            "hindsight_result_type": (
                type(hindsight_result).__name__
                if hindsight_result is not None
                else None
            ),
            "hindsight_error": None,
            "learning_state_error": None,
            "raw_result": result,
        }


class QueryAwareSelector:
    RECENT_UPDATE_GATE = GENERAL_MEMORY_MATCH_THRESHOLD

    def __init__(
        self,
        base_selector: AdaptiveMemorySelector,
        query: str,
        recent_updates: Optional[List[str]] = None,
    ) -> None:
        self.base_selector = base_selector
        self.query = query
        self.recent_updates = recent_updates or []

    def score_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        scored = self.base_selector.score_candidate(candidate)
        lexical_rel = lexical_relevance(self.query, scored.get("text") or "")
        semantic_rel = float(scored.get("retrieval_similarity") or 0.0)

        # Project-history questions use broad/anaphoric wording (for example,
        # "what was my problem before?"). Hindsight's semantic retrieval is the
        # authoritative relevance signal for these queries; lexical overlap is
        # retained as an additional signal rather than a veto.
        query_rel = (
            max(lexical_rel, semantic_rel)
            if is_project_summary_query(self.query)
            else lexical_rel
        )

        update_rel = 0.0
        for update in self.recent_updates:
            update_query_rel = lexical_relevance(self.query, update)
            if is_project_summary_query(self.query):
                update_query_rel = max(update_query_rel, 0.10)
            elif update_query_rel < self.RECENT_UPDATE_GATE:
                continue

            candidate_update_rel = lexical_relevance(
                update,
                scored.get("text") or "",
            )
            update_rel = max(update_rel, min(update_query_rel, candidate_update_rel))

        factor = max(
            0.75,
            min(1.10, 0.75 + (0.25 * query_rel) + (0.10 * update_rel)),
        )
        final_score = float(scored["adjusted_score"]) * factor

        scored["query_relevance"] = query_rel
        scored["lexical_relevance"] = lexical_rel
        scored["semantic_relevance"] = semantic_rel
        scored["recent_update_relevance"] = update_rel
        scored["selection_factor"] = factor
        scored["final_selection_score"] = final_score
        return scored

    def select(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not candidates:
            raise ValueError("No memory candidates were supplied.")

        ranked = [self.score_candidate(candidate) for candidate in candidates]
        ranked.sort(
            key=lambda item: (
                item["final_selection_score"],
                item["adjusted_score"],
                item["retrieval_similarity"],
                -item["canonical_memory_id"],
            ),
            reverse=True,
        )
        return {
            "selected": ranked[0],
            "ranked_candidates": ranked,
        }


class ProjectMemoryRuntime:
    """
    Extracted, reusable memory agent runtime from run_real_chat.py.
    Accepts external project_id, bank_id, chat_id, project_name, project_description.
    Does NOT create a new project/bank for every request.
    Enforces project-level isolation.
    """

    def __init__(
        self,
        *,
        project_id: str,
        bank_id: str,
        chat_id: str,
        project_name: str,
        project_description: str,
        message_repo: Optional[MessageRepository] = None,
        evidence_repo: Optional[EvidenceRepository] = None,
        db_dir: Optional[str] = None,
        memory_service: Optional[MemoryService] = None,
        canonical_memory_service: Optional[CanonicalMemoryService] = None,
        learning_service: Optional[MemoryLearningStateService] = None,
        learning_repository: Optional[SQLiteLearningRepository] = None,
        groq_agent: Optional[Any] = None,
    ) -> None:
        self.project_id = project_id
        self.bank_id = bank_id
        self.chat_id = chat_id
        self.project_name = project_name
        self.project_description = project_description
        self.message_repo = message_repo or MessageRepository()
        self.evidence_repo = evidence_repo or EvidenceRepository()

        # Database paths
        base_dir = Path(db_dir or (Path(__file__).resolve().parent.parent.parent / "data"))
        base_dir.mkdir(parents=True, exist_ok=True)

        learning_db_path = str(base_dir / f"learning_{self.project_id}.db")
        canonical_db_path = str(base_dir / "memory_registry.db")

        # Initialize existing working services. Optional injections keep the
        # production runtime unchanged while making the complete HTTP path
        # independently testable without external API calls.
        self.repository = learning_repository or SQLiteLearningRepository(db_path=learning_db_path)
        self.memory_service = memory_service or MemoryService()
        self.canonical_memory_service = (
            canonical_memory_service
            or CanonicalMemoryService(db_path=canonical_db_path)
        )
        self.learning_service = (
            learning_service
            or MemoryLearningStateService(repository=self.repository)
        )
        self.resolver = HindsightCanonicalResolver(canonical_memory_service=self.canonical_memory_service)
        self.quality_gate = RetrievalQualityGate()
        self.closed_loop = ClosedLearningLoopService(learning_service=self.learning_service)
        self.selector = AdaptiveMemorySelector(
            learning_service=self.learning_service,
            closed_loop_service=self.closed_loop,
        )

        self.groq_agent = groq_agent or LearningAwareGroqAgent()
        self.intent_router = SemanticIntentRouter(
            groq_agent=self.groq_agent,
            project_name=self.project_name,
            project_description=self.project_description,
        )
        self.ingestion_service = RuntimeMemoryIngestionService(
            memory_service=self.memory_service,
            canonical_memory_service=self.canonical_memory_service,
            learning_service=self.learning_service,
        )

    def _recent_updates(self) -> List[Dict[str, Any]]:
        return self.message_repo.recent_update_records(
            project_id=self.project_id,
            limit=RECENT_UPDATE_LIMIT,
        )

    def _build_uploaded_evidence_sources(
        self,
        evidence_objects: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        for rank, evidence in enumerate(evidence_objects or [], start=1):
            sources.append(
                {
                    "rank": rank,
                    "source_type": "uploaded_evidence",
                    "source_kind": evidence.get("kind") or "file",
                    "evidence_id": evidence.get("evidence_id"),
                    "canonical_memory_id": evidence.get("canonical_memory_id"),
                    "original_filename": evidence.get("original_filename"),
                    "mime_type": evidence.get("mime_type"),
                    "user_description": evidence.get("user_description"),
                    "semantic_description": evidence.get("semantic_description"),
                    "combined_understanding": evidence.get("combined_understanding"),
                    "hindsight_memory": evidence.get("memory_ingestion"),
                    "storage_key": evidence.get("storage_key"),
                    "sha256": evidence.get("sha256"),
                    "size_bytes": evidence.get("size_bytes"),
                }
            )
        return sources

    def _retain_evidence_memories(
        self,
        evidence_objects: Optional[List[Dict[str, Any]]],
    ) -> None:
        """
        Persist semantic evidence to the same project-scoped Hindsight bank.

        The original binary file never goes to Hindsight. Only normalized
        semantic text is retained, while evidence provenance remains in SQLite.
        """
        for evidence in evidence_objects or []:
            evidence_id = evidence.get("evidence_id")
            filename = evidence.get("original_filename") or "uploaded evidence"
            semantic_text = (
                evidence.get("combined_understanding")
                or evidence.get("semantic_description")
                or evidence.get("user_description")
                or ""
            ).strip()

            if not semantic_text:
                continue

            memory_text = (
                f"Evidence {evidence_id or ''} from file '{filename}':\n"
                f"{semantic_text}"
            ).strip()

            try:
                ingestion = self.ingestion_service.ingest(
                    bank_id=self.bank_id,
                    text=memory_text,
                )
                evidence["memory_ingestion"] = {
                    "canonical_memory_id": ingestion.get("canonical_memory_id"),
                    "retained": ingestion.get("retained", False),
                    "relationship": ingestion.get("relationship"),
                    "relationship_similarity": ingestion.get("relationship_similarity"),
                    "hindsight_action": ingestion.get("hindsight_action"),
                    "canonical_registry_verified": ingestion.get(
                        "canonical_registry_verified", False
                    ),
                    "error": ingestion.get("hindsight_error")
                    or ingestion.get("learning_state_error"),
                }

                canonical_id_value = ingestion.get("canonical_memory_id")
                if canonical_id_value is not None:
                    evidence["canonical_memory_id"] = int(canonical_id_value)
                if evidence_id and canonical_id_value is not None:
                    try:
                        self.evidence_repo.update_understanding(
                            evidence_id=evidence_id,
                            canonical_memory_id=int(canonical_id_value),
                        )
                    except Exception:
                        logger.exception(
                            "Failed to link evidence %s to canonical memory %s",
                            evidence_id,
                            canonical_id_value,
                        )
            except Exception as exc:
                evidence["memory_ingestion"] = {
                    "canonical_memory_id": None,
                    "retained": False,
                    "relationship": None,
                    "relationship_similarity": None,
                    "hindsight_action": "error",
                    "canonical_registry_verified": False,
                    "error": str(exc),
                }

    def retain_evidence(self, evidence_objects: Optional[List[Dict[str, Any]]]) -> None:
        """Persist uploaded evidence semantics into this project's memory bank."""
        self._retain_evidence_memories(evidence_objects)

    def _attach_evidence_to_user_message(
        self,
        *,
        user_message_id: str,
        evidence_objects: Optional[List[Dict[str, Any]]],
    ) -> None:
        for evidence in evidence_objects or []:
            evidence_id = evidence.get("evidence_id")
            if not evidence_id:
                continue
            try:
                updated = self.evidence_repo.attach_to_message(
                    evidence_id=evidence_id,
                    message_id=user_message_id,
                )
                if updated:
                    evidence.update(updated)
            except Exception:
                logger.exception(
                    "Failed to link evidence %s to user message %s",
                    evidence_id,
                    user_message_id,
                )

    def _retrieval_query(self, user_text: str) -> str:
        updates = self._recent_updates()
        normalized = " ".join((user_text or "").strip().split())

        base_query = normalized
        if is_project_summary_query(normalized):
            base_query = (
                f"{normalized}\n\n"
                "Retrieve the project's relevant problems, issues, incidents, "
                "bugs, blockers, failed attempts, resolutions, and current state. "
                "Include multiple distinct project issues when the records support them."
            )

        if not updates:
            return base_query

        lines = "\n".join(f"- {item['content']}" for item in updates)
        return (
            f"{base_query}\n\n"
            "Recent user-provided project updates. "
            "Use them only when they are relevant:\n"
            f"{lines}"
        )

    def _find_relevant_recent_update(self, query: str) -> Optional[Dict[str, Any]]:
        updates = self._recent_updates()
        if not updates:
            return None

        summary_mode = is_project_summary_query(query)
        best = None
        best_score = 0.0
        for update in updates:
            score = lexical_relevance(query, update["content"])
            if score > best_score:
                best_score = score
                best = dict(update)
                best["query_relevance"] = score

        if summary_mode:
            # A history question is allowed to fall back to the newest local
            # project update when semantic retrieval has no usable candidate.
            return (
                best
                if best is not None and best_score >= 0.30
                else {**updates[-1], "query_relevance": best_score}
            )

        return best if best_score >= 0.30 else None

    def _relevant_recent_updates_for_query(
        self,
        query: str,
        supporting_memories: Optional[List[Dict[str, Any]]] = None,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        updates = self._recent_updates()
        if not updates:
            return []

        support_texts = [
            str(item.get("text") or "")
            for item in (supporting_memories or [])
            if item.get("text")
        ]
        summary_mode = is_project_summary_query(query)
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for update in updates:
            content = str(update.get("content") or "")
            if not content:
                continue

            query_score = lexical_relevance(query, content)
            support_score = max(
                (lexical_relevance(content, text) for text in support_texts),
                default=0.0,
            )

            if summary_mode:
                relevance = max(query_score, 0.60 * support_score, 0.10)
                minimum = 0.08
            else:
                relevance = query_score
                minimum = 0.20

            if relevance >= minimum:
                item = dict(update)
                item["query_relevance"] = query_score
                item["support_relevance"] = support_score
                scored.append((relevance, item))

        scored.sort(
            key=lambda pair: (
                pair[0],
                pair[1].get("created_at") or "",
                str(pair[1].get("message_id") or ""),
            ),
            reverse=True,
        )
        return [item for _, item in scored[:limit]]

    def _get_learning_agent_for_query(
        self,
        *,
        query: str,
        include_recent_updates: bool = True,
    ) -> LearningAgentService:
        recent_update_texts = (
            [item["content"] for item in self._recent_updates()]
            if include_recent_updates
            else []
        )

        query_selector = QueryAwareSelector(
            base_selector=self.selector,
            query=query,
            recent_updates=recent_update_texts,
        )

        return LearningAgentService(
            memory_service=self.memory_service,
            resolver=self.resolver,
            selector=query_selector,  # type: ignore[arg-type]
            closed_loop=self.closed_loop,
            quality_gate=self.quality_gate,
            answer_generator=self.groq_agent,
        )

    def _build_answer_evidence(
        self,
        *,
        result: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        selected = result.get("selected_memory") or {}
        selection = result.get("selection") or {}
        ranked = selection.get("ranked_candidates") or []
        retrieval = result.get("retrieval") or {}

        evidence_items: List[Dict[str, Any]] = []

        for rank, candidate in enumerate(ranked[:4], start=1):
            memory_id = candidate.get("canonical_memory_id")
            if memory_id is None:
                continue

            source_messages = self.message_repo.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(memory_id),
            )

            source_kind = (
                "user_provided_project_update"
                if source_messages
                else "seeded_project_memory"
            )

            evidence_items.append(
                {
                    "rank": rank,
                    "source_type": "canonical_memory",
                    "source_kind": source_kind,
                    "canonical_memory_id": memory_id,
                    "text": candidate.get("text"),
                    "retrieval_similarity": candidate.get("retrieval_similarity"),
                    "identity_score": candidate.get("identity_score"),
                    "identity_margin": candidate.get("identity_margin"),
                    "query_relevance": candidate.get("query_relevance"),
                    "learning_signal": candidate.get("learning_signal"),
                    "learning_confidence": candidate.get("learning_confidence"),
                    "learning_multiplier": candidate.get("learning_multiplier"),
                    "c6_adjusted_score": candidate.get("adjusted_score"),
                    "final_selection_score": candidate.get("final_selection_score"),
                    "source_messages": [
                        {
                            "message_id": item["message_id"],
                            "chat_id": item["chat_id"],
                            "text": item["content"],
                            "created_at": item["created_at"],
                        }
                        for item in source_messages
                    ],
                }
            )

        recent_updates = []
        for item in self._recent_updates():
            recent_updates.append(
                {
                    "message_id": item["message_id"],
                    "chat_id": item["chat_id"],
                    "text": item["content"],
                    "query_relevance": lexical_relevance(query, item["content"]),
                    "created_at": item["created_at"],
                }
            )

        learning_evidence = (
            result.get("provenance")
            or {
                "memory_id": canonical_id(selected),
                "success": {"outcome_ids": [], "evidence_ids": []},
                "failure": {"outcome_ids": [], "evidence_ids": []},
                "partial": {"outcome_ids": [], "evidence_ids": []},
                "unknown": {"outcome_ids": [], "evidence_ids": []},
            }
        )

        selected_id = canonical_id(selected)
        learning_state = (
            self.learning_service.get_state(selected_id)
            if selected_id is not None and self.learning_service is not None
            else None
        )
        return {
            "query": query,
            "answer_memory_id": selected_id,
            "source_evidence": evidence_items,
            "recent_user_updates": recent_updates,
            "learning_evidence": learning_evidence,
            "learning_state": learning_state,
            "retrieval": retrieval,
            "note": "Source evidence explains where the answer came from; learning/outcome evidence is kept separate.",
        }

    def _project_supporting_memories(
        self,
        query: str,
        selection: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        ranked = list(selection.get("ranked_candidates") or [])
        if not ranked:
            return []

        summary_mode = is_project_summary_query(query)
        if summary_mode:
            selected_items = []
            seen_ids = set()
            for item in ranked:
                item_id = canonical_id(item)
                if item_id is None or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                selected_items.append(item)
                if len(selected_items) >= 8:
                    break
            return selected_items

        top_relevance = max(
            (float(item.get("query_relevance", 0.0) or 0.0) for item in ranked),
            default=0.0,
        )
        threshold = max(0.12, top_relevance * 0.45)

        selected_items = [
            item
            for item in ranked
            if float(item.get("query_relevance", 0.0) or 0.0) >= threshold
        ]

        primary = selection.get("selected") or {}
        primary_id = canonical_id(primary)
        if primary_id is not None and all(
            canonical_id(item) != primary_id for item in selected_items
        ):
            selected_items.insert(0, primary)

        return selected_items[:5]

    def _project_groq_answer(
        self,
        *,
        query: str,
        context: Dict[str, Any],
        supporting_memories: List[Dict[str, Any]],
        recent_updates: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        client = getattr(self.groq_agent, "client", None)
        model = getattr(self.groq_agent, "model", settings.GROQ_MODEL)
        if client is None:
            raise RuntimeError("The real Groq client is not available.")

        primary = context.get("memory") or {}
        learning = context.get("learning") or {}
        state = learning.get("state") or {}
        decision = context.get("decision") or {}
        provenance = learning.get("provenance") or {}

        support_lines = []
        for item in supporting_memories:
            item_id = canonical_id(item)
            if item_id is not None:
                support_lines.append(
                    f"- Memory {item_id}: {short_text(item.get('text'), 700)}"
                )

        update_lines = []
        for update in recent_updates or []:
            if update.get("content"):
                update_lines.append(
                    f"- User update: {short_text(update.get('content'), 500)}"
                )

        summary_mode = is_project_summary_query(query)

        source_records: List[Dict[str, Any]] = []
        seen_source_memory_ids = set()

        for item in [primary, *supporting_memories]:
            item_id = canonical_id(item)
            if item_id is None or item_id in seen_source_memory_ids:
                continue
            seen_source_memory_ids.add(item_id)

            source_messages = self.message_repo.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(item_id),
            )
            for message in source_messages:
                source_records.append(
                    {
                        "memory_id": item_id,
                        "message_id": message.get("message_id"),
                        "content": short_text(message.get("content"), 700),
                        "created_at": message.get("created_at"),
                    }
                )

        source_lines = [
            f"- Memory {record['memory_id']} | user message {record['message_id']} | "
            f"{record['content']}"
            for record in source_records
        ]

        system_content = (
            "You are a grounded project-memory assistant. Answer the user's actual question "
            "using the supplied project records. Your job is not to repeat the evidence verbatim; "
            "you must synthesize what the evidence means for the user.\n\n"
            "For questions about what happened previously, first identify the concrete event or "
            "problem that the records establish. Then explain what that means in practical terms. "
            "Then include any recorded cause, attempted approach, resolution, or test result when "
            "such information is actually present. If the records do not contain the root cause, "
            "error message, stack trace, or resolution, explicitly say that it is not recorded "
            "instead of inventing one.\n\n"
            "Use past tense for previous/history questions. Do not turn a past incident into a "
            "claim about the current state. Do not simply quote a memory and stop. Give the user "
            "a useful conclusion derived from the evidence.\n\n"
            "Source memory and learning feedback are different: source memory contains recorded "
            "project facts, including explicit implementation or test-result statements; C4 learning "
            "contains later feedback outcomes. An empty C4 state does not erase or invalidate a "
            "source-memory fact. Do not describe an implementation as merely proposed when the "
            "source explicitly says it was implemented. Do not claim stronger certainty than the "
            "records support."
        )

        mode_instruction = (
            "This is a history/previous-state question. Produce a compact reconstruction of what "
            "happened. Prefer this structure naturally in prose: what happened/problem -> what was "
            "known or observed -> what was tried/resolved/tested if recorded -> what remains unknown "
            "from memory. For a single incident, do not fabricate a longer timeline."
            if summary_mode
            else
            "This is a focused project question. Give the direct answer first, then explain the "
            "evidence behind it in plain language. Do not stop at a quotation of the selected memory."
        )

        user_content = (
            f"User question:\n{query}\n\n"
            f"Primary C6-selected memory {primary.get('canonical_memory_id')}:\n"
            f"{primary.get('text')}\n\n"
            "Supporting canonical project memories:\n"
            f"{chr(10).join(support_lines) if support_lines else '- None'}\n\n"
            "Exact source user messages attached to those canonical memories:\n"
            f"{chr(10).join(source_lines) if source_lines else '- No direct user-source message found'}\n\n"
            "Recent user-provided project updates:\n"
            f"{chr(10).join(update_lines) if update_lines else '- None'}\n\n"
            "C5 decision for the primary memory:\n"
            f"behavior={decision.get('behavior')}; reason={decision.get('reason')}\n"
            "C4 learning state for the primary memory:\n"
            f"successes={state.get('successes')}; failures={state.get('failures')}; "
            f"partial={state.get('partial')}; unknown={state.get('unknown')}; "
            f"informative_outcomes={state.get('informative_outcomes')}; "
            f"learning_signal={state.get('learning_signal')}; "
            f"evidence_coverage={state.get('evidence_coverage')}\n\n"
            "Learning provenance for the primary memory:\n"
            f"{json.dumps(provenance, default=str, indent=2)}\n\n"
            f"{mode_instruction}\n"
            "Before writing, reconcile the canonical memory with the exact source user message "
            "when both are present. Treat the source message as what the user originally reported "
            "and the canonical memory as a normalized representation. The final response must "
            "answer the user's question, not merely list or quote evidence. Do not expose internal "
            "routing, scoring, or implementation details of the agent."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_completion_tokens=700,
        )
        return str(response.choices[0].message.content or "").strip()

    def _deterministic_project_fallback(
        self,
        *,
        query: str,
        context: Dict[str, Any],
        supporting_memories: List[Dict[str, Any]],
    ) -> str:
        primary = context.get("memory") or {}
        summary_mode = is_project_summary_query(query)

        ordered: List[Dict[str, Any]] = []
        seen = set()
        for item in [primary, *supporting_memories]:
            memory_id = canonical_id(item)
            if memory_id is None or memory_id in seen:
                continue
            seen.add(memory_id)
            ordered.append(item)

        if summary_mode:
            facts = [
                short_text(item.get("text"), 500)
                for item in ordered
                if item.get("text")
            ]
            if facts:
                if len(facts) == 1:
                    primary_id = canonical_id(primary)
                    source_messages = (
                        self.message_repo.find_memory_source(
                            project_id=self.project_id,
                            canonical_memory_id=int(primary_id),
                        )
                        if primary_id is not None
                        else []
                    )
                    original = (
                        short_text(source_messages[0].get("content"), 500)
                        if source_messages
                        else None
                    )
                    original_part = (
                        f" The original project update was: “{original}”."
                        if original and original != facts[0]
                        else ""
                    )
                    return (
                        f"Previously, the recorded project issue was: {facts[0].rstrip('.')}. "
                        f"{original_part} The available memory does not record the root cause "
                        "or a further resolution."
                    ).replace("  ", " ")

                return (
                    "Based on the recorded project history, the relevant sequence was:\n\n"
                    + "\n".join(f"- {fact}" for fact in facts)
                )

        if primary.get("text"):
            return (
                "The recorded project fact is: "
                f"{str(primary['text']).strip()} "
                "The available memory does not contain enough additional detail to infer more."
            )
        return "I found project memory, but I could not safely generate a fuller answer from it."

    def _interactive_lead(self, query: str, evidence: Dict[str, Any]) -> str:
        update = self._find_relevant_recent_update(query)
        if update is not None and not is_project_summary_query(query):
            return (
                "I found the project record relevant to this question and used it "
                "to reconstruct the answer below."
            )

        source_items = evidence.get("source_evidence") or []
        if source_items:
            if is_project_summary_query(query):
                return (
                    "I found the earlier project record and reconstructed what happened "
                    "from the stored evidence."
                )
            return (
                "I found the project record that most directly matches your question "
                "and used it as the basis for the answer below."
            )

        return "I’m answering this from the general conversation context."

    def _canonical_project_candidates(self) -> List[Dict[str, Any]]:
        """Return locally verified canonical memories scoped to this project bank."""
        memories = self.canonical_memory_service.list_memories(self.bank_id)
        candidates: List[Dict[str, Any]] = []
        for memory in memories:
            memory_id = canonical_id(memory)
            text_value = canonical_text(memory)
            if memory_id is None or not text_value:
                continue
            state = self.learning_service.get_state(memory_id) if self.learning_service else None
            candidates.append({
                "canonical_memory_id": memory_id,
                "text": text_value,
                "retrieval_similarity": 0.0,
                "query_relevance": 0.0,
                "identity_score": 1.0,
                "identity_margin": 1.0,
                "adjusted_score": 0.0,
                "learning_signal": (state or {}).get("learning_signal", 0.0),
                "learning_confidence": (state or {}).get("learning_confidence", 0.0),
                "learning_multiplier": 1.0,
                "evidence_coverage": (state or {}).get("evidence_coverage", 0.0),
                "source_messages": self.message_repo.find_memory_source(
                    project_id=self.project_id,
                    canonical_memory_id=int(memory_id),
                ),
            })
        return candidates

    def _inventory_response(self) -> Dict[str, Any]:
        memories = self._canonical_project_candidates()
        source_evidence: List[Dict[str, Any]] = []
        lines: List[str] = []
        learning_records: List[Dict[str, Any]] = []

        for rank, item in enumerate(memories, start=1):
            memory_id = item["canonical_memory_id"]
            lines.append(f"{rank}. **Memory {memory_id}** — {item['text']}")
            state = self.learning_service.get_state(memory_id) if self.learning_service else None
            provenance = self.learning_service.get_provenance(memory_id) if self.learning_service else {}
            learning_records.append({"memory_id": memory_id, "state": state, "provenance": provenance})
            source_evidence.append({
                "rank": rank,
                "source_type": "canonical_memory",
                "source_kind": "user_provided_project_update" if item.get("source_messages") else "seeded_project_memory",
                "canonical_memory_id": memory_id,
                "text": item["text"],
                "retrieval_similarity": None,
                "query_relevance": None,
                "source_messages": item.get("source_messages") or [],
                "learning_evidence": provenance,
            })

        if lines:
            answer = (
                f"I currently have **{len(lines)}** project memories in this project's memory bank.\n\n"
                + "\n".join(lines)
                + "\n\nOutcome and learning evidence are tracked separately and shown when available."
            )
        else:
            answer = "This project memory bank is currently empty. There are no verified canonical memories to show."

        evidence = {
            "query": "memory inventory",
            "answer_mode": "memory_inventory",
            "memory_match": bool(memories),
            "answer_memory_id": memories[0]["canonical_memory_id"] if memories else None,
            "source_evidence": source_evidence,
            "learning_evidence": {"memory_count": len(memories), "memories": learning_records},
            "learning_state": None,
            "understanding": {"intent": "PROJECT_QUERY", "mode": "MEMORY_INVENTORY", "status": "memories_listed"},
            "metrics": {"memory_count": len(memories)},
            "note": "Inventory is read from the locally verified canonical project store.",
        }
        return {"answer": answer, "evidence": evidence}

    def _probe_project_memory(self, user_text: str) -> Dict[str, Any]:
        query = " ".join((user_text or "").strip().split())
        try:
            query_agent = self._get_learning_agent_for_query(
                query=query,
                include_recent_updates=False,
            )
            result = query_agent.answer(
                bank_id=self.bank_id,
                query=query,
                answer_generator=lambda _context: "",
            )
        except LookupError as exc:
            return {
                "memory_match": False,
                "status": "no_related_memory",
                "reason": str(exc),
                "query": query,
                "selected_memory": None,
                "matched_candidates": [],
                "probe_result": None,
            }
        except Exception as exc:
            return {
                "memory_match": False,
                "status": "memory_check_unavailable",
                "reason": str(exc),
                "query": query,
                "selected_memory": None,
                "matched_candidates": [],
                "probe_result": None,
            }

        selection = result.get("selection") or {}
        ranked = selection.get("ranked_candidates") or []

        matched = [
            item
            for item in ranked
            if float(item.get("query_relevance", 0.0) or 0.0)
            >= GENERAL_MEMORY_MATCH_THRESHOLD
        ]

        if not matched:
            for item in self._canonical_project_candidates():
                score = lexical_relevance(query, item.get("text") or "")
                if score >= GENERAL_MEMORY_MATCH_THRESHOLD:
                    item = dict(item)
                    item["query_relevance"] = score
                    matched.append(item)

        recent_update = self._find_relevant_recent_update(query)
        if recent_update is not None and recent_update.get("canonical_memory_id") is not None:
            update_as_candidate = {
                "canonical_memory_id": recent_update.get("canonical_memory_id"),
                "text": recent_update.get("content"),
                "retrieval_similarity": None,
                "query_relevance": recent_update.get("query_relevance", 0.0),
                "source_messages": [
                    {
                        "message_id": recent_update.get("message_id"),
                        "chat_id": recent_update.get("chat_id"),
                        "text": recent_update.get("content"),
                        "created_at": recent_update.get("created_at"),
                    }
                ],
            }
            if all(
                item.get("canonical_memory_id")
                != update_as_candidate.get("canonical_memory_id")
                for item in matched
            ):
                matched.append(update_as_candidate)

        matched.sort(
            key=lambda item: (
                float(item.get("query_relevance", 0.0) or 0.0),
                float(item.get("retrieval_similarity", 0.0) or 0.0),
                -(int(item.get("canonical_memory_id") or 0)),
            ),
            reverse=True,
        )

        selected = matched[0] if matched else None
        return {
            "memory_match": selected is not None,
            "status": "related_memory_found" if selected is not None else "no_related_memory",
            "reason": (
                "A candidate crossed the conservative general-query memory relevance threshold."
                if selected is not None
                else "No canonical project memory reached the conservative general-query relevance threshold."
            ),
            "query": query,
            "selected_memory": selected,
            "matched_candidates": matched[:4],
            "probe_result": result,
        }

    def _build_general_answer_evidence(
        self,
        *,
        query: str,
        awareness: Dict[str, Any],
    ) -> Dict[str, Any]:
        selected = awareness.get("selected_memory") or {}
        memory_id = canonical_id(selected)

        source_evidence: List[Dict[str, Any]] = []
        for rank, candidate in enumerate(
            awareness.get("matched_candidates") or [],
            start=1,
        ):
            candidate_id = canonical_id(candidate)
            if candidate_id is None:
                continue

            source_messages = self.message_repo.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(candidate_id),
            )
            state = self.learning_service.get_state(candidate_id) if self.learning_service else None
            provenance = self.learning_service.get_provenance(candidate_id) if self.learning_service else None

            source_evidence.append(
                {
                    "rank": rank,
                    "source_type": "canonical_memory",
                    "source_kind": (
                        "user_provided_project_update"
                        if source_messages
                        else "seeded_project_memory"
                    ),
                    "canonical_memory_id": candidate_id,
                    "text": candidate.get("text"),
                    "retrieval_similarity": candidate.get("retrieval_similarity"),
                    "query_relevance": candidate.get("query_relevance"),
                    "learning_signal": (state or {}).get("learning_signal", 0.0),
                    "learning_confidence": candidate.get("learning_confidence", 0.0),
                    "learning_multiplier": candidate.get("learning_multiplier", 1.0),
                    "c6_adjusted_score": candidate.get("adjusted_score"),
                    "final_selection_score": candidate.get("final_selection_score"),
                    "source_messages": source_messages,
                    "learning_evidence": provenance or {
                        "memory_id": candidate_id,
                        "success": {"outcome_ids": [], "evidence_ids": []},
                        "failure": {"outcome_ids": [], "evidence_ids": []},
                        "partial": {"outcome_ids": [], "evidence_ids": []},
                        "unknown": {"outcome_ids": [], "evidence_ids": []},
                    },
                }
            )

        learning_evidence = (
            self.learning_service.get_provenance(memory_id)
            if memory_id is not None and self.learning_service is not None
            else {
                "memory_id": memory_id,
                "success": {"outcome_ids": [], "evidence_ids": []},
                "failure": {"outcome_ids": [], "evidence_ids": []},
                "partial": {"outcome_ids": [], "evidence_ids": []},
                "unknown": {"outcome_ids": [], "evidence_ids": []},
            }
        )

        return {
            "query": query,
            "answer_mode": "general",
            "memory_mode": "on",
            "memory_status": awareness.get("status"),
            "memory_match": bool(awareness.get("memory_match")),
            "answer_memory_id": memory_id,
            "source_evidence": source_evidence,
            "learning_evidence": learning_evidence,
            "memory_check": {
                "threshold": GENERAL_MEMORY_MATCH_THRESHOLD,
                "reason": awareness.get("reason"),
                "matched_count": len(awareness.get("matched_candidates") or []),
            },
            "retrieval": (
                (awareness.get("probe_result") or {}).get("retrieval")
                or {
                    "raw_result_count": 0,
                    "resolved_count": 0,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "rejected": [],
                }
            ),
            "note": "General queries answered generally with optional project context.",
        }

    def _general_groq_answer(
        self,
        user_text: str,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        client = getattr(self.groq_agent, "client", None)
        model = getattr(self.groq_agent, "model", settings.GROQ_MODEL)
        if client is None:
            return "I can handle that as a general question, but Groq client is not available."

        system_content = (
            "You are a friendly, concise assistant. Answer the user's question "
            "directly and generally. Project memory is optional context, not the whole "
            "answer. If project memory is supplied and relevant, clearly distinguish "
            "project-specific facts from general knowledge. Do not invent project details. "
            "When source memory explicitly states that something was implemented or that "
            "tests passed, report that as a recorded project fact. Do not confuse an empty "
            "C4 learning state with absence of source evidence: zero C4 outcomes means "
            "there is no feedback/outcome history, not that the recorded source fact is "
            "unknown or false. Do not make claims stronger than the supplied records."
        )

        user_content = user_text
        if memory_context is not None:
            selected = memory_context.get("selected_memory") or {}
            user_content = (
                f"User question:\n{user_text}\n\n"
                "Related project memory found by the memory check:\n"
                f"Memory {selected.get('canonical_memory_id')}: "
                f"{selected.get('text')}\n\n"
                "Project-specific learning context, when available:\n"
                f"behavior={selected.get('behavior')}; "
                f"learning_signal={selected.get('learning_signal')}; "
                f"informative_outcomes={selected.get('informative_outcomes')}; "
                f"evidence_coverage={selected.get('evidence_coverage')}\n\n"
                "Answer the user's question generally. Use the project memory where it "
                "adds relevant context. Treat explicit source-memory statements about "
                "implementation or test results as recorded project facts. If the learning "
                "state has zero outcomes, say there are no C4 feedback/outcome records "
                "rather than claiming that the project has no evidence. Clearly distinguish "
                "project-specific facts from general knowledge."
            )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_completion_tokens=500,
        )
        return str(response.choices[0].message.content or "").strip()

    def _chat_reply(self, user_text: str) -> str:
        normalized = normalize_routing_text(user_text.strip().lower())
        if re.search(r"^what(?:'s|\s+is)\s+your\s+name\??$|^who\s+are\s+you\??$", normalized):
            return f"I’m {settings.APP_NAME}. I’m here to help with both general questions and the project memory we’re building."

        first_match = re.match(r"^([a-z]+)", normalized)
        first_word = first_match.group(1) if first_match else ""
        if fuzzy_match_word(first_word, ("hi", "hello", "hey"), threshold=0.70):
            return f"Hi! I’m here with you. We’re working on the {self.project_name} project. What should we work on next?"

        if any(re.search(p, normalized) for p in GREETING_PATTERNS):
            return f"Hi! I’m here with you. We’re working on the {self.project_name} project. What should we work on next?"

        if fuzzy_match_word(first_word, ("thanks", "thank"), threshold=0.75):
            return "You’re welcome. Project context and memory remain safely saved so we can continue whenever you're ready."

        return "Got it. We can keep chatting normally, or you can give me a project update or question and I’ll connect it to the right memory path."

    def _retrieve_related_memories_for_update(self, user_text: str) -> Dict[str, Any]:
        query = " ".join((user_text or "").strip().split())
        try:
            query_agent = self._get_learning_agent_for_query(
                query=query,
                include_recent_updates=False,
            )
            retrieval = query_agent.retrieve_candidates(
                bank_id=self.bank_id,
                query=query,
            )
            candidates = retrieval.get("candidates") or []
            if not candidates:
                return {
                    "status": "no_previous_context",
                    "query": query,
                    "selected": None,
                    "candidates": [],
                    "retrieval": retrieval,
                }

            selection = query_agent.select_memory(candidates)
            ranked = selection.get("ranked_candidates") or []

            prior_candidates: List[Dict[str, Any]] = []
            seen_ids = set()
            for candidate in ranked:
                memory_id = canonical_id(candidate)
                if memory_id is None or memory_id in seen_ids:
                    continue
                seen_ids.add(memory_id)
                prior_candidates.append(dict(candidate))
                if len(prior_candidates) >= 6:
                    break

            return {
                "status": "previous_context_found",
                "query": query,
                "selected": selection.get("selected"),
                "candidates": prior_candidates,
                "retrieval": retrieval,
                "selection": selection,
            }
        except Exception as exc:
            return {
                "status": "no_previous_context",
                "query": query,
                "selected": None,
                "candidates": [],
                "retrieval": {"raw_result_count": 0, "resolved_count": 0, "accepted_count": 0, "rejected_count": 0, "rejected": []},
                "error": str(exc),
            }

    def _analyze_update_relation(
        self,
        *,
        user_text: str,
        prior_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        valid_relations = {
            "RELATED_REFINEMENT",
            "RELATED_PROGRESSION",
            "RELATED_RESOLUTION",
            "RELATED_CONTRADICTION",
            "DUPLICATE",
            "UNRELATED_NEW_ISSUE",
            "NO_PRIOR_CONTEXT",
            "UNCONFIRMED_PRIOR_CONTEXT",
        }

        prior_candidates = prior_context.get("candidates") or []
        if prior_context.get("status") == "no_previous_context" or not prior_candidates:
            return {
                "relation": "NO_PRIOR_CONTEXT",
                "related_memory_ids": [],
                "understanding": "This is a new project update, and no earlier project memory was available to connect it to.",
                "reply": "I understand this as a new project issue/update. I don't have a previously recorded project issue that I can connect it to yet, so I’ll treat this as the starting record.",
                "missing_information": "No prior related project record was available.",
                "source": "no_prior_context",
            }

        candidate_lines = []
        for item in prior_candidates:
            memory_id = canonical_id(item)
            if memory_id is None:
                continue
            text_value = short_text(item.get("text"), 850)
            candidate_lines.append(f"- MEMORY {memory_id}: {text_value}")

        client = getattr(self.groq_agent, "client", None)
        model = getattr(self.groq_agent, "model", settings.GROQ_MODEL)
        if client is None:
            return {
                "relation": "UNCONFIRMED_PRIOR_CONTEXT",
                "related_memory_ids": [],
                "understanding": "Earlier records retrieved, but relationship could not be confirmed.",
                "reply": "I found earlier project records, but couldn't confirm relation. Storing separately.",
                "missing_information": "Groq client unavailable.",
                "source": "fallback_no_groq",
            }

        system = (
            "You are the update-understanding layer of a project-memory assistant. "
            "A user has just supplied a new project/work update. Earlier canonical "
            "memories were retrieved from Hindsight before the new update was stored. "
            "Determine whether the new update is actually related to any earlier "
            "memory and explain the relationship in plain language.\n\n"
            "Do not assume two records are related merely because Hindsight retrieved them. "
            "Choose one relation: RELATED_REFINEMENT, RELATED_PROGRESSION, RELATED_RESOLUTION, "
            "RELATED_CONTRADICTION, DUPLICATE, UNRELATED_NEW_ISSUE, or NO_PRIOR_CONTEXT.\n\n"
            'Return ONLY JSON: {"relation":"...", "related_memory_ids":[1], '
            '"understanding":"...", "reply":"...", "missing_information":"..."}'
        )
        user = (
            f"CURRENT NEW USER UPDATE:\n{user_text}\n\n"
            f"EARLIER PROJECT MEMORIES RETRIEVED BEFORE THIS UPDATE WAS STORED:\n"
            + "\n".join(candidate_lines)
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                max_completion_tokens=500,
            )
            raw = str(response.choices[0].message.content or "").strip()
            data = None
            try:
                data = json.loads(raw)
            except Exception:
                match = re.search(r"\{.*\}", raw, re.S)
                if match:
                    data = json.loads(match.group(0))

            relation = str((data or {}).get("relation", "")).strip().upper()
            related_ids = [int(v) for v in (data or {}).get("related_memory_ids", []) if str(v).isdigit()]
            allowed_ids = {int(canonical_id(item)) for item in prior_candidates if canonical_id(item) is not None}
            related_ids = [v for v in related_ids if v in allowed_ids]

            if relation not in valid_relations:
                relation = "UNRELATED_NEW_ISSUE"

            if relation in {"NO_PRIOR_CONTEXT", "UNRELATED_NEW_ISSUE"}:
                related_ids = []

            return {
                "relation": relation,
                "related_memory_ids": related_ids,
                "understanding": str(data.get("understanding", "")).strip() if data else "",
                "reply": str(data.get("reply", "")).strip() if data else "",
                "missing_information": str(data.get("missing_information", "")).strip() if data else "",
                "source": "semantic_groq",
            }
        except Exception as exc:
            return {
                "relation": "UNRELATED_NEW_ISSUE",
                "related_memory_ids": [],
                "understanding": "Recorded as an independent update.",
                "reply": "I've recorded this project update.",
                "missing_information": str(exc),
                "source": "fallback_error",
            }

    def _build_update_evidence(
        self,
        *,
        query: str,
        user_message_id: str,
        ingestion: Dict[str, Any],
        prior_context: Dict[str, Any],
        relation: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_evidence: List[Dict[str, Any]] = []
        current_memory_id = ingestion.get("canonical_memory_id")

        if current_memory_id is not None:
            source_evidence.append(
                {
                    "rank": 1,
                    "source_type": "canonical_memory",
                    "source_kind": "user_provided_project_update",
                    "canonical_memory_id": current_memory_id,
                    "text": ingestion.get("input"),
                    "relation_to_prior": "CURRENT_UPDATE",
                    "source_messages": [
                        {
                            "message_id": user_message_id,
                            "chat_id": self.chat_id,
                            "text": query,
                        }
                    ],
                }
            )

        for rank, candidate in enumerate(prior_context.get("candidates") or [], start=2):
            memory_id = canonical_id(candidate)
            if memory_id is None:
                continue
            source_messages = self.message_repo.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(memory_id),
            )
            source_evidence.append(
                {
                    "rank": rank,
                    "source_type": "canonical_memory",
                    "source_kind": "user_provided_project_update" if source_messages else "seeded_project_memory",
                    "canonical_memory_id": memory_id,
                    "text": candidate.get("text"),
                    "retrieval_similarity": candidate.get("retrieval_similarity"),
                    "query_relevance": candidate.get("query_relevance"),
                    "source_messages": source_messages,
                    "related_to_current_update": int(memory_id) in set(relation.get("related_memory_ids") or []),
                }
            )

        current_learning_state = None
        if current_memory_id is not None and self.learning_service is not None:
            try:
                current_learning_state = self.learning_service.get_state(int(current_memory_id))
            except Exception:
                current_learning_state = None

        return {
            "query": query,
            "answer_mode": "memory_update",
            "current_update": {
                "message_id": user_message_id,
                "canonical_memory_id": current_memory_id,
                "text": query,
            },
            "update_understanding": relation,
            "source_evidence": source_evidence,
            "learning_evidence": {
                "memory_id": current_memory_id,
                "success": {"outcome_ids": [], "evidence_ids": []},
                "failure": {"outcome_ids": [], "evidence_ids": []},
                "partial": {"outcome_ids": [], "evidence_ids": []},
                "unknown": {"outcome_ids": [], "evidence_ids": []},
            },
            "learning_state": current_learning_state,
            "ingestion": ingestion,
            "note": "Update processed and related to prior records where supported.",
        }

    def handle_message(
        self,
        *,
        content: str,
        evidence_descriptions: Optional[List[str]] = None,
        evidence_objects: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the Memory ON workflow for a message.
        """
        user_text = content.strip()

        # If user attached evidence descriptions, incorporate into message text for ingestion/context
        effective_text = user_text
        if evidence_descriptions:
            added_info = " ".join(evidence_descriptions)
            if not effective_text:
                effective_text = added_info
            else:
                effective_text = f"{effective_text}. {added_info}"

        input_type, intent_meta = self.intent_router.classify(
            text=effective_text,
            message_repo=self.message_repo,
            project_id=self.project_id,
        )
        print(
    "RUNTIME ROUTING DEBUG:",
    {
        "effective_text": effective_text,
        "input_type": input_type,
        "intent_meta": intent_meta,
    },
    flush=True,
)

        user_msg = self.message_repo.create(
            chat_id=self.chat_id,
            role="user",
            content=user_text or (evidence_descriptions[0] if evidence_descriptions else ""),
            message_type=input_type,
            metadata={"intent_router": intent_meta, "attachments_count": len(evidence_objects or [])},
        )
        user_message_id = user_msg["message_id"]
        self._attach_evidence_to_user_message(
            user_message_id=user_message_id,
            evidence_objects=evidence_objects,
        )

        # 0. MEMORY INVENTORY QUERY
        if input_type == "PROJECT_QUERY" and is_memory_inventory_query(user_text):
            inventory = self._inventory_response()
            evidence = inventory["evidence"]
            assistant_msg = self.message_repo.create(
                chat_id=self.chat_id,
                role="assistant",
                content=inventory["answer"],
                message_type="QUERY_REPLY",
                canonical_memory_id=evidence.get("answer_memory_id"),
                metadata={
                    "memory_enabled": True,
                    "source_user_message_id": user_message_id,
                    "evidence": evidence,
                },
            )
            return {
                "message": {
                    "message_id": assistant_msg["message_id"],
                    "role": "assistant",
                    "content": inventory["answer"],
                    "created_at": assistant_msg["created_at"],
                },
                "memory": {"enabled": True, "mode": "memory", "status": "active"},
                "evidence": evidence,
                "attachments": evidence_objects or [],
                "user_message_id": user_message_id,
            }

        # 1. MEMORY UPDATE PATH
        if input_type == "MEMORY_UPDATE":
            update_text = user_text or (evidence_descriptions[0] if evidence_descriptions else "").strip()
            prior_context = self._retrieve_related_memories_for_update(update_text or effective_text)
            relation = self._analyze_update_relation(
                user_text=update_text or effective_text,
                prior_context=prior_context,
            )
            self._retain_evidence_memories(evidence_objects)

            if update_text:
                try:
                    # Keep user updates and uploaded evidence as separate memory
                    # records so the same semantic evidence is never stored twice.
                    ingestion = self.ingestion_service.ingest(
                        bank_id=self.bank_id,
                        text=update_text,
                    )
                except Exception as exc:
                    ingestion = {
                        "input": update_text,
                        "retained": False,
                        "relationship": None,
                        "canonical_memory_id": None,
                        "canonical_registry_verified": False,
                        "hindsight_action": "error",
                        "hindsight_error": str(exc),
                    }
            else:
                evidence_memory_ids = [
                    int(e["canonical_memory_id"])
                    for e in (evidence_objects or [])
                    if e.get("canonical_memory_id") is not None
                ]
                ingestion = {
                    "input": "",
                    "retained": bool(evidence_memory_ids),
                    "relationship": None,
                    "canonical_memory_id": evidence_memory_ids[0] if len(evidence_memory_ids) == 1 else None,
                    "canonical_memory_ids": evidence_memory_ids,
                    "canonical_registry_verified": bool(evidence_memory_ids),
                    "hindsight_action": "evidence_only" if evidence_memory_ids else "not_verified",
                    "hindsight_error": None,
                    "learning_state_error": None,
                }

            memory_id = ingestion.get("canonical_memory_id")
            if memory_id is not None:
                self.message_repo.update_metadata(
                    user_message_id,
                    metadata={
                        "intent_router": intent_meta,
                        "update_relation": relation,
                        "prior_context": prior_context,
                        "ingestion": ingestion,
                    },
                    canonical_memory_id=int(memory_id),
                )

            storage_relationship = ingestion.get("relationship")
            if ingestion.get("retained"):
                storage_line = f"I stored this as project memory {memory_id}." if memory_id else "Memory sent to ingestion path."
            elif storage_relationship in {"exact_duplicate", "semantic_duplicate"}:
                storage_line = f"I recognized this as already represented by project memory {memory_id}."
            else:
                storage_line = "The memory was recorded in this session."

            answer = f"{relation['reply'].strip()}\n\n{storage_line}" if relation.get("reply") else storage_line

            evidence = self._build_update_evidence(
                query=update_text or effective_text,
                user_message_id=user_message_id,
                ingestion=ingestion,
                prior_context=prior_context,
                relation=relation,
            )
            uploaded_sources = self._build_uploaded_evidence_sources(evidence_objects)
            evidence["source_evidence"] = uploaded_sources + evidence.get(
                "source_evidence", []
            )

            assistant_msg = self.message_repo.create(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="MEMORY_ACK",
                canonical_memory_id=memory_id,
                metadata={
                    "memory_enabled": True,
                    "source_message_id": user_message_id,
                    "update_relation": relation,
                    "prior_context": prior_context,
                    "ingestion": ingestion,
                    "evidence": evidence,
                },
            )

            # Return stable API format
            return {
                "message": {
                    "message_id": assistant_msg["message_id"],
                    "role": "assistant",
                    "content": answer,
                    "created_at": assistant_msg["created_at"],
                },
                "memory": {
                    "enabled": True,
                    "mode": "memory",
                    "status": "active",
                },
                "evidence": {
                    "source_evidence": evidence.get("source_evidence", []),
                    "learning_evidence": evidence.get("learning_evidence", {}),
                    "learning_state": evidence.get("learning_state"),
                    "understanding": relation,
                    "metrics": {
                        "canonical_memory_id": memory_id,
                        "retained": ingestion.get("retained", False),
                        "relationship": ingestion.get("relationship"),
                    },
                },
                "attachments": evidence_objects or [],
                "user_message_id": user_message_id,
            }

        # Evidence attached to a non-update message is still long-term
        # project knowledge when Memory is ON.
        self._retain_evidence_memories(evidence_objects)

        # 2. CHAT PATH
        if input_type == "CHAT":
            answer = self._chat_reply(effective_text)
            evidence = {
                "query": effective_text,
                "answer_mode": "chat",
                "source_evidence": self._build_uploaded_evidence_sources(
                    evidence_objects
                ),
                "learning_evidence": {},
                "understanding": {"intent": "CHAT"},
                "metrics": {},
            }
            assistant_msg = self.message_repo.create(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="CHAT_REPLY",
                metadata={"memory_enabled": True, "evidence": evidence},
            )
            return {
                "message": {
                    "message_id": assistant_msg["message_id"],
                    "role": "assistant",
                    "content": answer,
                    "created_at": assistant_msg["created_at"],
                },
                "memory": {
                    "enabled": True,
                    "mode": "chat",
                    "status": "active",
                },
                "evidence": {
                    "source_evidence": self._build_uploaded_evidence_sources(
                        evidence_objects
                    ),
                    "learning_evidence": {},
                    "understanding": {"intent": "CHAT"},
                    "metrics": {},
                },
                "attachments": evidence_objects or [],
                "user_message_id": user_message_id,
            }

        # 3. GENERAL QUERY PATH
        if input_type == "GENERAL_QUERY":
            awareness = self._probe_project_memory(effective_text)
            if awareness.get("memory_match"):
                selected = awareness.get("selected_memory") or {}
                lead = (
                    f"I found related knowledge in this project's memory: Memory {selected.get('canonical_memory_id')} — "
                    f"“{short_text(selected.get('text'), 360)}”. I’ll use it as context, then answer generally."
                )
            elif awareness.get("status") == "memory_check_unavailable":
                lead = "I couldn’t complete the project-memory check, so I won’t pretend there is a project-specific match. I’ll answer it generally."
            else:
                lead = "I checked this project’s memory and found no related project-specific knowledge for this question. I’ll answer it generally."

            try:
                answer_body = self._general_groq_answer(
                    effective_text,
                    memory_context=(awareness if awareness.get("memory_match") else None),
                )
            except Exception as exc:
                answer_body = f"I can answer that as a general question, but Groq request had an issue: {exc}"

            answer = f"{lead}\n\n{answer_body}"
            evidence = self._build_general_answer_evidence(query=effective_text, awareness=awareness)
            uploaded_sources = self._build_uploaded_evidence_sources(evidence_objects)
            evidence["source_evidence"] = uploaded_sources + evidence.get(
                "source_evidence", []
            )

            assistant_msg = self.message_repo.create(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="GENERAL_QUERY_REPLY",
                canonical_memory_id=evidence.get("answer_memory_id"),
                metadata={
                    "memory_enabled": True,
                    "memory_awareness": awareness,
                    "evidence": evidence,
                },
            )

            metrics = {}
            if awareness.get("memory_match"):
                sel = awareness.get("selected_memory") or {}
                if sel.get("query_relevance") is not None:
                    metrics["query_relevance"] = sel.get("query_relevance")
                if sel.get("retrieval_similarity") is not None:
                    metrics["retrieval_similarity"] = sel.get("retrieval_similarity")

            return {
                "message": {
                    "message_id": assistant_msg["message_id"],
                    "role": "assistant",
                    "content": answer,
                    "created_at": assistant_msg["created_at"],
                },
                "memory": {
                    "enabled": True,
                    "mode": "general",
                    "status": "active",
                },
                "evidence": {
                    "source_evidence": evidence.get("source_evidence", []),
                    "learning_evidence": evidence.get("learning_evidence", {}),
                    "understanding": {
                        "intent": "GENERAL_QUERY",
                        "memory_match": awareness.get("memory_match", False),
                        "status": awareness.get("status"),
                    },
                    "metrics": metrics,
                },
                "attachments": evidence_objects or [],
                "user_message_id": user_message_id,
            }

        # 4. PROJECT QUERY PATH
        retrieval_query = self._retrieval_query(effective_text)
        try:
            query_agent = self._get_learning_agent_for_query(query=effective_text)
            retrieval = query_agent.retrieve_candidates(bank_id=self.bank_id, query=retrieval_query)
            candidates = retrieval.get("candidates") or []
            if not candidates:
                raise LookupError("No usable memories found for query.")

            selection = query_agent.select_memory(candidates)
            context = query_agent.build_context(query=effective_text, selection=selection)
            supporting_memories = self._project_supporting_memories(effective_text, selection)
            recent_updates = self._relevant_recent_updates_for_query(effective_text, supporting_memories=supporting_memories)

            try:
                answer_body = self._project_groq_answer(
                    query=effective_text,
                    context=context,
                    supporting_memories=supporting_memories,
                    recent_updates=recent_updates,
                )
            except Exception:
                answer_body = self._deterministic_project_fallback(
                    query=effective_text,
                    context=context,
                    supporting_memories=supporting_memories,
                )

            result = {
                "answer": answer_body,
                "selected_memory": selection["selected"],
                "selection": selection,
                "behavior": context["decision"]["behavior"],
                "learning": context["learning"]["state"],
                "provenance": context["learning"]["provenance"],
                "retrieval": retrieval,
            }
        except LookupError:
            update = self._find_relevant_recent_update(effective_text)
            if update is None and is_project_summary_query(effective_text):
                local_memories = self._canonical_project_candidates()
                if local_memories:
                    update = {
                        "canonical_memory_id": local_memories[-1]["canonical_memory_id"],
                        "content": local_memories[-1]["text"],
                        "query_relevance": 0.0,
                    }
            if update is not None:
                answer = f"I found the project update you gave me that matches this: “{update['content']}”"
                evidence = {
                    "query": effective_text,
                    "answer_memory_id": update.get("canonical_memory_id"),
                    "source_evidence": self._build_uploaded_evidence_sources(
                        evidence_objects
                    ) + [
                        {
                            "rank": 1,
                            "source_type": "user_memory_update",
                            "source_kind": "recent_project_update",
                            "canonical_memory_id": update.get("canonical_memory_id"),
                            "text": update.get("content"),
                            "query_relevance": update.get("query_relevance"),
                        }
                    ],
                    "learning_evidence": {},
                }
                assistant_msg = self.message_repo.create(
                    chat_id=self.chat_id,
                    role="assistant",
                    content=answer,
                    message_type="QUERY_REPLY",
                    canonical_memory_id=update.get("canonical_memory_id"),
                    metadata={"memory_enabled": True, "evidence": evidence},
                )
                return {
                    "message": {
                        "message_id": assistant_msg["message_id"],
                        "role": "assistant",
                        "content": answer,
                        "created_at": assistant_msg["created_at"],
                    },
                    "memory": {"enabled": True, "mode": "memory", "status": "active"},
                    "evidence": {
                        "source_evidence": evidence.get("source_evidence", []),
                        "learning_evidence": {},
                        "understanding": {"intent": "PROJECT_QUERY", "note": "Reconstructed from recent update"},
                        "metrics": {"query_relevance": update.get("query_relevance")},
                    },
                    "attachments": evidence_objects or [],
                    "user_message_id": user_message_id,
                }

            answer = "I couldn’t find a sufficiently supported project-memory record for that question, so I won’t invent one."
            assistant_msg = self.message_repo.create(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="QUERY_REPLY",
                metadata={"memory_enabled": True, "evidence": {
                    "source_evidence": [],
                    "learning_evidence": {},
                    "understanding": {"intent": "PROJECT_QUERY", "status": "no_memories_found"},
                    "metrics": {},
                }},
            )
            return {
                "message": {
                    "message_id": assistant_msg["message_id"],
                    "role": "assistant",
                    "content": answer,
                    "created_at": assistant_msg["created_at"],
                },
                "memory": {"enabled": True, "mode": "memory", "status": "active"},
                "evidence": {
                    "source_evidence": [],
                    "learning_evidence": {},
                    "understanding": {"intent": "PROJECT_QUERY", "status": "no_memories_found"},
                    "metrics": {},
                },
                "attachments": evidence_objects or [],
                "user_message_id": user_message_id,
            }

        evidence = self._build_answer_evidence(result=result, query=effective_text)
        uploaded_sources = self._build_uploaded_evidence_sources(evidence_objects)
        evidence["source_evidence"] = uploaded_sources + evidence.get(
            "source_evidence", []
        )
        technical_answer = result.get("answer") or ""
        lead = self._interactive_lead(query=effective_text, evidence=evidence)
        final_answer = f"{lead}\n\n{technical_answer}"
        selected = result.get("selected_memory") or {}
        selected_id = canonical_id(selected)

        assistant_msg = self.message_repo.create(
            chat_id=self.chat_id,
            role="assistant",
            content=final_answer,
            message_type="QUERY_REPLY",
            canonical_memory_id=selected_id,
            metadata={
                "memory_enabled": True,
                "source_user_message_id": user_message_id,
                "evidence": evidence,
                "result": result,
            },
        )

        metrics = {}
        if selected.get("retrieval_similarity") is not None:
            metrics["retrieval_similarity"] = selected.get("retrieval_similarity")
        if selected.get("query_relevance") is not None:
            metrics["query_relevance"] = selected.get("query_relevance")
        if selected.get("learning_signal") is not None:
            metrics["learning_signal"] = selected.get("learning_signal")
        if selected.get("learning_confidence") is not None:
            metrics["learning_confidence"] = selected.get("learning_confidence")
        if selected.get("learning_multiplier") is not None:
            metrics["c6_multiplier"] = selected.get("learning_multiplier")
        if selected.get("evidence_coverage") is not None:
            metrics["evidence_coverage"] = selected.get("evidence_coverage")
        if selected.get("final_selection_score") is not None:
            metrics["final_selection_score"] = selected.get("final_selection_score")

        return {
            "message": {
                "message_id": assistant_msg["message_id"],
                "role": "assistant",
                "content": final_answer,
                "created_at": assistant_msg["created_at"],
            },
            "memory": {
                "enabled": True,
                "mode": "memory",
                "status": "active",
            },
            "evidence": {
                "source_evidence": evidence.get("source_evidence", []),
                "learning_evidence": evidence.get("learning_evidence", {}),
                "understanding": {
                    "intent": "PROJECT_QUERY",
                    "behavior": result.get("behavior"),
                    "primary_memory_id": selected_id,
                },
                "metrics": metrics,
            },
            "attachments": evidence_objects or [],
            "user_message_id": user_message_id,
        }
