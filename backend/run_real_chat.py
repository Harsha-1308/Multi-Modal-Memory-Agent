
"""
run_real_chat.py

Interactive, persistent, evidence-aware Hindsight chat runner.

Design:
    USER INPUT
        -> intent router
             QUERY about project -> Hindsight + canonical resolution
                                    -> query-aware C6 selection
                                    -> C5 learning context
                                    -> real Groq technical answer
                                    -> source-evidence bundle
             MEMORY UPDATE       -> existing B6 dedup ingestion
             GENERAL QUESTION    -> real Groq general answer
             CHAT                -> natural conversational reply
        -> persistent conversation storage

Important:
    - B6 ingestion remains the existing MemoryDeduplicationService.
    - C2/C3/C4/C5 learning semantics are not reimplemented.
    - Original Hindsight retrieval similarity is preserved.
    - Query-aware selection adds a small relevance layer on top of C6.
    - "Source evidence" and "learning/outcome evidence" are kept separate.
"""

from __future__ import annotations

import json
import mimetypes
import os
from difflib import SequenceMatcher
import re
import sqlite3
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.repositories.sqlite.learning_repository import SQLiteLearningRepository
from app.services.memory_service import MemoryService
from app.services.canonical_memory_service import CanonicalMemoryService
from app.services.hindsight_canonical_resolver import HindsightCanonicalResolver
from app.services.retrieval_quality_gate import RetrievalQualityGate
from app.services.memory_learning_state_service import MemoryLearningStateService
from app.services.adaptive_memory_selector import AdaptiveMemorySelector
from app.services.closed_learning_loop_service import ClosedLearningLoopService
from app.services.experience_service import ExperienceService
from app.services.outcome_capture_service import OutcomeCaptureService
from app.services.outcome_classification_service import OutcomeClassificationService
from app.services.evidence_service import EvidenceService
from app.services.learning_feedback_service import LearningFeedbackService
from app.services.learning_aware_groq_agent import LearningAwareGroqAgent
from app.services.learning_agent_service import LearningAgentService
from app.services.learning_interaction_service import LearningInteractionService
from app.services.memory_deduplication_service import MemoryDeduplicationService


PROJECT_NAME = os.getenv("PROJECT_NAME", "Wallet Service")
PROJECT_DESCRIPTION = os.getenv(
    "PROJECT_DESCRIPTION",
    (
        "A production backend service managing digital wallet balances and "
        "money transfers. The project is investigating a concurrency bug in "
        "POST /wallet/transfer."
    ),
)

DEFAULT_SEED_MEMORIES = [
    (
        "problem",
        "The wallet transfer service has a concurrency problem: two transactions "
        "can read the same wallet balance before either transaction writes the "
        "updated balance, causing a lost update.",
    ),
    (
        "retry_failed",
        "Application-level retries were attempted to resolve the wallet concurrency "
        "problem, but the approach failed to reliably prevent incorrect balances "
        "under concurrent transactions.",
    ),
    (
        "locking_worked",
        "Pessimistic database locking was implemented for the wallet balance update, "
        "and the concurrent transaction tests passed with the correct final balance.",
    ),
]


def load_seed_memories() -> List[Tuple[str, str]]:
    """Load optional project seed fixtures without changing runtime routing logic."""
    raw = os.getenv("SEED_MEMORIES_JSON", "").strip()
    if not raw:
        return list(DEFAULT_SEED_MEMORIES)
    try:
        parsed = json.loads(raw)
        result: List[Tuple[str, str]] = []
        for item in parsed:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                key, value = str(item[0]).strip(), str(item[1]).strip()
                if key and value:
                    result.append((key, value))
        return result or list(DEFAULT_SEED_MEMORIES)
    except Exception:
        return list(DEFAULT_SEED_MEMORIES)


SEED_MEMORIES = load_seed_memories()

RECENT_UPDATE_LIMIT = 8
GENERAL_MEMORY_MATCH_THRESHOLD = 0.20

# ---------------------------------------------------------------------------
# Domain-neutral intent routing
# ---------------------------------------------------------------------------
# IMPORTANT:
# The active project may be Wallet, React, Python, ML, DevOps, etc.  Therefore
# topic words MUST NOT decide whether something is a memory update.  The runtime
# semantic router below receives the active project's name/description and uses
# meaning + conversation context instead.

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

THANKS_PATTERNS = (
    r"^(thanks|thank you|thx)\b",
    r"^(thanks|thank you).*(help|support|answer|everything)?$",
)

ACK_PATTERNS = (
    r"^(ok|okay|got it|understood|cool|great|nice|perfect|awesome|sounds good)\b",
)

# Generic language cues used ONLY as a fallback if semantic routing is
# unavailable.  There are deliberately no Wallet/React/Python/etc words here.
MEMORY_UPDATE_PATTERNS = (
    r"\b(?:we|i)\s+(?:found|discovered|implemented|integrated|tried|tested|fixed|resolved|decided|deployed|changed|updated|configured|removed|added|switched|chose|selected)\b",
    r"\b(?:we|i)\s+(?:will|should|plan\s+to|are\s+going\s+to|am\s+going\s+to)\s+(?:use|implement|change|add|remove|deploy|switch|try)\b",
    r"\b(?:this|that|the)\b(?:\s+[a-z0-9_.-]+){1,6}\s+(?:is|was|isn't|isnt|is\s+not|wasn't|wasnt|was\s+not|fails?|failed|crashes?|crashed|crashing|broke|broken|doesn't|doesnt|does\s+not|returns?|throws?|stopped|passed|passes|succeeded|successful|not\s+working|not\s+work)\b",
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

GENERIC_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on",
    "at", "by", "with", "from", "about", "into", "as", "is", "are", "was",
    "were", "be", "been", "being", "do", "does", "did", "what", "why", "how",
    "when", "where", "who", "which", "can", "could", "should", "would", "will",
    "have", "has", "had", "we", "i", "you", "our", "your", "me", "it", "this",
    "that", "there", "then", "they", "them", "said", "say", "tell", "please",
    "now", "just", "already", "used", "use", "u", "ur",
}

# Generic morphological normalization.  No project vocabulary is embedded.
MORPHOLOGY_SUFFIXES = (
    ("ies", "y"),
    ("ing", ""),
    ("ed", ""),
    ("es", ""),
    ("s", ""),
)


# Backward-compatible name used by existing helper code.
STOP_WORDS = GENERIC_STOP_WORDS


def normalize_token(token: str) -> str:
    t = (token or "").lower().strip()
    if not t:
        return ""

    # Do not stem common endings that would damage ordinary words such as
    # ``this``, ``status``, ``class`` or ``analysis``.
    if t in STOP_WORDS:
        return t

    for suffix, replacement in MORPHOLOGY_SUFFIXES:
        if suffix == "s" and t.endswith(("us", "ss", "is")):
            continue
        if suffix == "es" and t.endswith("sses"):
            # ``classes`` -> ``class`` rather than ``class``-like damage.
            candidate = t[:-2]
            if candidate.endswith("ss"):
                return candidate
        if t.endswith(suffix) and len(t) > len(suffix) + 2:
            candidate = t[: -len(suffix)] + replacement
            if len(candidate) >= 3:
                return candidate
    return t


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def pretty(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


def short_text(value: Any, limit: int = 420) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."



def content_tokens(text: str) -> List[str]:
    tokens = []
    for token in re.findall(r"[a-z0-9]+", (text or "").lower()):
        normalized = normalize_token(token)
        if token in STOP_WORDS or normalized in STOP_WORDS:
            continue
        if normalized:
            tokens.append(normalized)
    return tokens


def lexical_relevance(query: str, text: str) -> float:
    q_tokens = content_tokens(query)
    t_tokens = content_tokens(text)
    if not q_tokens or not t_tokens:
        return 0.0

    q_set = set(q_tokens)
    t_set = set(t_tokens)
    overlap = len(q_set & t_set) / max(1, len(q_set))

    # Small sequence signal for direct phrases.
    q_text = " ".join(q_tokens)
    t_text = " ".join(t_tokens)
    sequence = 1.0 if q_text and q_text in t_text else 0.0

    # Contiguous two-token matches.
    bigram_hits = 0
    if len(q_tokens) >= 2:
        t_set_bigrams = {
            (t_tokens[i], t_tokens[i + 1])
            for i in range(len(t_tokens) - 1)
        }
        for i in range(len(q_tokens) - 1):
            if (q_tokens[i], q_tokens[i + 1]) in t_set_bigrams:
                bigram_hits += 1
    bigram_score = (
        bigram_hits / max(1, len(q_tokens) - 1)
        if len(q_tokens) >= 2
        else 0.0
    )

    # A small fuzzy token signal helps conversational variants without encoding
    # domain-specific synonym lists (e.g. locks -> lock, implementations -> implement).
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
    """Domain-neutral project reference detection for the fallback router."""
    return matches_any(PROJECT_REFERENCE_PATTERNS, text)


def matches_any(patterns: Sequence[str], text: str) -> bool:
    return any(re.search(pattern, text.strip().lower()) for pattern in patterns)


def _collapse_repeated_letters(value: str) -> str:
    # Keep normal words intact while treating common chat typos such as
    # ``hellooo`` / ``hiiii`` / ``heyyy`` as their intended short forms.
    return re.sub(r"(.)\1{1,}", r"\1\1", value)


def fuzzy_match_word(word: str, targets: Sequence[str], threshold: float = 0.80) -> bool:
    candidate = (word or "").strip().lower()
    candidate = _collapse_repeated_letters(candidate)
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
    """Normalize lightweight texting shorthand for intent detection only."""
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
    if matches_any(IDENTITY_CHAT_PATTERNS, lowered):
        return True
    if matches_any(GREETING_PATTERNS, lowered):
        return True
    if matches_any(ACK_PATTERNS, lowered):
        return True
    first = re.match(r"^([a-z]+)", lowered)
    if first and fuzzy_match_word(first.group(1), ("thanks", "thank"), threshold=0.80):
        return True
    return False


def is_project_summary_query(text: str) -> bool:
    return matches_any(
        PROJECT_SUMMARY_PATTERNS,
        " ".join((text or "").strip().split()).lower(),
    )


def classify_user_input(text: str) -> str:
    """
    Domain-neutral deterministic fallback classifier.

    The normal runtime uses SemanticIntentRouter.  This function is intentionally
    conservative and contains no project/topic vocabulary.
    """
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

    if matches_any(IDENTITY_CHAT_PATTERNS, routing_text):
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

    if not followup_question and matches_any(GREETING_PATTERNS, routing_text):
        return "CHAT"

    # History/status language is project-oriented even when the user does not
    # explicitly say "project". This keeps vague follow-up questions connected
    # to the active project's prior work when the semantic router is unavailable.
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

    # Ambiguous free-form text is kept out of memory rather than being silently
    # stored as project knowledge.
    return "CHAT"



class SemanticIntentRouter:
    """Semantic, project-agnostic runtime intent classifier.

    The current project name/description and recent project conversation are
    supplied at runtime. The classifier therefore learns *what counts as this
    project's context* from configuration and conversation instead of a list of
    hardcoded topic words.

    The deterministic path is only a safety net. It never contains project
    vocabulary, and it becomes more project-aware from the shape of the user's
    language and the recent project conversation.
    """

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

        # First accept a clean JSON response.
        try:
            data = json.loads(value)
            intent = str(data.get("intent", "")).strip().upper()
            if intent in cls.VALID_INTENTS:
                return intent
        except Exception:
            pass

        # Accept JSON that was wrapped in Markdown/code fences or extra text.
        explicit = re.search(
            r'"?intent"?\s*:\s*"?(CHAT|MEMORY_UPDATE|PROJECT_QUERY|GENERAL_QUERY)\b',
            value,
            re.I,
        )
        if explicit:
            return explicit.group(1).upper()

        # Last-resort plain-label parsing for a tiny model response such as
        # "PROJECT_QUERY". This remains intentionally conservative.
        compact = value.strip().upper()
        if compact in cls.VALID_INTENTS:
            return compact

        return None

    @staticmethod
    def recent_context(store: "ConversationStore", project_id: str) -> str:
        rows = store.list_messages(project_id=project_id)

        # Do not feed ordinary GENERAL_QUERY history back into the project
        # intent classifier. That can cross-contaminate a later project query
        # with unrelated conceptual topics.
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
    def _contextual_fallback(
        cleaned: str,
        base_fallback: str,
        recent: str,
    ) -> str:
        """Use generic language + recent project context as the last fallback."""
        if base_fallback != "GENERAL_QUERY":
            return base_fallback

        normalized = normalize_routing_text(cleaned)

        if is_project_summary_query(normalized):
            return "PROJECT_QUERY"

        # Vague anaphoric project questions such as "why did that fail?" or
        # "what are we using here?" need recent project context to resolve.
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
        conversation_store: "ConversationStore",
        project_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        cleaned = " ".join((text or "").strip().split())
        fallback = classify_user_input(cleaned)
        recent = self.recent_context(conversation_store, project_id)

        # Social messages are deterministic and should not consume an LLM call.
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

        model = getattr(self.groq_agent, "model", "openai/gpt-oss-120b")

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
                message = response.choices[0].message
                content = getattr(message, "content", None)
            except Exception:
                content = None
            return str(content or "").strip()

        try:
            # The previous 120-token budget was too tight for some reasoning
            # models: the model could consume its budget before emitting JSON,
            # producing an empty `message.content`. Give the routing task enough
            # room while keeping it much cheaper than the answer call.
            raw = invoke(300)
            parsed = self.parse_intent(raw)

            # One bounded retry handles an occasionally incomplete router
            # response without changing the normal one-call path.
            if parsed is None and not raw:
                raw = invoke(450)
                parsed = self.parse_intent(raw)

            if parsed:
    # Do not allow the semantic router to classify a real question
    # as ordinary CHAT unless the message is actually social.
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


class ConversationStore:
    """Persistent conversation records, filtered by project/bank."""

    def __init__(self, db_path: str = "real_chat_history.db") -> None:
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                chat_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT NOT NULL,
                canonical_memory_id INTEGER,
                ingestion_status TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES conversations(chat_id)
            );
            """
        )
        self.connection.commit()

    def create_chat(self, chat_id: str, project_id: str, bank_id: str) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO conversations(
                chat_id, project_id, bank_id, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (chat_id, project_id, bank_id, now_iso()),
        )
        self.connection.commit()

    def add_message(
        self,
        *,
        chat_id: str,
        role: str,
        content: str,
        message_type: str,
        canonical_memory_id: Optional[int] = None,
        ingestion_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO messages(
                chat_id, role, content, message_type,
                canonical_memory_id, ingestion_status,
                metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                role,
                content,
                message_type,
                canonical_memory_id,
                ingestion_status,
                json.dumps(metadata or {}, default=str),
                now_iso(),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_messages(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if project_id is None:
            rows = self.connection.execute(
                "SELECT * FROM messages ORDER BY message_id ASC"
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT m.*
                FROM messages m
                JOIN conversations c ON c.chat_id = m.chat_id
                WHERE c.project_id = ?
                ORDER BY m.message_id ASC
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_update_records(
        self,
        *,
        bank_id: str,
        limit: int = RECENT_UPDATE_LIMIT,
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                m.message_id,
                m.chat_id,
                m.content,
                m.canonical_memory_id,
                m.created_at
            FROM messages m
            JOIN conversations c ON c.chat_id = m.chat_id
            WHERE c.bank_id = ?
              AND m.role = 'user'
              AND m.message_type = 'MEMORY_UPDATE'
            ORDER BY m.message_id DESC
            LIMIT ?
            """,
            (bank_id, int(limit)),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def find_memory_source(
        self,
        *,
        project_id: str,
        canonical_memory_id: int,
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                m.message_id,
                m.chat_id,
                m.content,
                m.created_at
            FROM messages m
            JOIN conversations c ON c.chat_id = m.chat_id
            WHERE c.project_id = ?
              AND m.role = 'user'
              AND m.message_type = 'MEMORY_UPDATE'
              AND m.canonical_memory_id = ?
            ORDER BY m.message_id ASC
            """,
            (project_id, int(canonical_memory_id)),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()


def canonical_text(memory: Any) -> Optional[str]:
    if isinstance(memory, dict):
        return memory.get("original_text") or memory.get("text")
    return getattr(memory, "original_text", None) or getattr(memory, "text", None)


def canonical_id(memory: Any) -> Optional[int]:
    if isinstance(memory, int):
        return memory

    if isinstance(memory, dict):
        value = memory.get("id")
        if value is None:
            value = memory.get("canonical_memory_id")
        if value is None:
            value = memory.get("memory_id")
    else:
        value = getattr(memory, "id", None)
        if value is None:
            value = getattr(memory, "canonical_memory_id", None)
        if value is None:
            value = getattr(memory, "memory_id", None)

    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def find_canonical_id_by_text(
    memories: List[Dict[str, Any]],
    text: str,
) -> Optional[int]:
    for memory in memories:
        if canonical_text(memory) == text:
            return canonical_id(memory)
    return None


class RuntimeMemoryIngestionService:
    """
    Runtime write boundary over the existing B6 ingestion mechanism.

    This service does not reimplement B6. It verifies the local canonical
    write after B6 returns and exposes a frontend-friendly receipt.
    """

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

        memory_id = exact_id or (
            new_ids[0] if len(new_ids) == 1 else None
        )

        # Every verified canonical memory should have a learning-state row,
        # even before its first outcome. This keeps C6 and the frontend from
        # seeing a "memory exists but learning state is missing" split-brain.
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
    """
    Adds a query-specific relevance layer on top of the existing C6 scorer.

    Existing C6 values are preserved:
        adjusted_score
        learning_signal
        learning_confidence
        learning_multiplier

    We add:
        query_relevance
        recent_update_relevance
        final_selection_score

    IMPORTANT:
        Hindsight retrieval may use an expanded query containing recent project
        updates. That expanded text is useful for recall, but it must NOT be used
        as the query-relevance signal. Otherwise every recent update effectively
        becomes part of the current question and can pull an unrelated memory
        upward in C6 selection.
    """

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

        # Always score the candidate against the user's actual message, not the
        # Hindsight-expanded retrieval query.
        query_rel = lexical_relevance(
            self.query,
            scored.get("text") or "",
        )

        update_rel = 0.0
        for update in self.recent_updates:
            update_query_rel = lexical_relevance(self.query, update)
            if update_query_rel < self.RECENT_UPDATE_GATE:
                # An unrelated recent update must not boost this candidate.
                continue

            candidate_update_rel = lexical_relevance(
                update,
                scored.get("text") or "",
            )
            update_rel = max(
                update_rel,
                min(update_query_rel, candidate_update_rel),
            )

        # Keep C6 as the main signal, then apply a bounded relevance factor.
        factor = max(
            0.75,
            min(
                1.10,
                0.75 + (0.25 * query_rel) + (0.10 * update_rel),
            ),
        )
        final_score = float(scored["adjusted_score"]) * factor

        scored["query_relevance"] = query_rel
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


class RealChatLab:
    def __init__(self) -> None:
        self.project_id = f"project-{uuid.uuid4().hex[:10]}"
        self.bank_id = f"real-chat-{uuid.uuid4().hex[:10]}"
        self.chat_id = f"chat-{uuid.uuid4().hex[:10]}"

        self.repository: Optional[SQLiteLearningRepository] = None
        self.memory_service: Optional[MemoryService] = None
        self.canonical_memory_service: Optional[CanonicalMemoryService] = None
        self.learning_service: Optional[MemoryLearningStateService] = None
        self.resolver: Optional[HindsightCanonicalResolver] = None
        self.quality_gate: Optional[RetrievalQualityGate] = None
        self.closed_loop: Optional[ClosedLearningLoopService] = None
        self.selector: Optional[AdaptiveMemorySelector] = None

        self.experience_service: Optional[ExperienceService] = None
        self.outcome_service: Optional[OutcomeCaptureService] = None
        self.classification_service: Optional[OutcomeClassificationService] = None
        self.evidence_service: Optional[EvidenceService] = None
        self.feedback_service: Optional[LearningFeedbackService] = None

        self.groq_agent: Optional[LearningAwareGroqAgent] = None
        self.learning_agent: Optional[LearningAgentService] = None
        self.interaction_service: Optional[LearningInteractionService] = None
        self.ingestion_service: Optional[RuntimeMemoryIngestionService] = None
        self.intent_router: Optional[SemanticIntentRouter] = None

        self.conversation_store = ConversationStore("real_chat_history.db")

        self.canonical_ids: Dict[str, int] = {}
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_ingestion: Optional[Dict[str, Any]] = None
        self.last_evidence: Optional[Dict[str, Any]] = None
        self.last_memory_awareness: Optional[Dict[str, Any]] = None
        self.last_project_query_input: Optional[str] = None
        self.last_user_input: Optional[str] = None

    def initialize(self) -> None:
        section("INITIALIZE REAL CHAT + MEMORY + EVIDENCE LAB")

        self.repository = SQLiteLearningRepository(
            db_path=f"real_chat_learning_{self.project_id}.db"
        )
        self.memory_service = MemoryService()
        self.canonical_memory_service = CanonicalMemoryService()

        self.learning_service = MemoryLearningStateService(
            repository=self.repository
        )
        self.resolver = HindsightCanonicalResolver(
            canonical_memory_service=self.canonical_memory_service
        )
        self.quality_gate = RetrievalQualityGate()
        self.closed_loop = ClosedLearningLoopService(
            learning_service=self.learning_service
        )
        self.selector = AdaptiveMemorySelector(
            learning_service=self.learning_service,
            closed_loop_service=self.closed_loop,
        )

        self.experience_service = ExperienceService(
            repository=self.repository,
            canonical_memory_service=self.canonical_memory_service,
        )
        self.outcome_service = OutcomeCaptureService(
            repository=self.repository
        )
        self.classification_service = OutcomeClassificationService(
            repository=self.repository
        )
        self.evidence_service = EvidenceService(
            repository=self.repository
        )
        self.feedback_service = LearningFeedbackService(
            experience_service=self.experience_service,
            outcome_service=self.outcome_service,
            classification_service=self.classification_service,
            learning_service=self.learning_service,
            evidence_service=self.evidence_service,
            closed_loop_service=self.closed_loop,
        )

        self.groq_agent = LearningAwareGroqAgent()
        self.intent_router = SemanticIntentRouter(
            groq_agent=self.groq_agent,
            project_name=PROJECT_NAME,
            project_description=PROJECT_DESCRIPTION,
        )

        self.learning_agent = LearningAgentService(
            memory_service=self.memory_service,
            resolver=self.resolver,
            selector=self.selector,
            closed_loop=self.closed_loop,
            quality_gate=self.quality_gate,
            answer_generator=self.groq_agent,
        )

        self.interaction_service = LearningInteractionService(
            learning_agent=self.learning_agent,
            feedback_service=self.feedback_service,
            answer_generator=self.groq_agent,
        )

        self.ingestion_service = RuntimeMemoryIngestionService(
            memory_service=self.memory_service,
            canonical_memory_service=self.canonical_memory_service,
            learning_service=self.learning_service,
        )

        self.conversation_store.create_chat(
            chat_id=self.chat_id,
            project_id=self.project_id,
            bank_id=self.bank_id,
        )

        print(f"PROJECT ID : {self.project_id}")
        print(f"BANK ID    : {self.bank_id}")
        print(f"CHAT ID    : {self.chat_id}")
        print("SERVICES   : READY")

    def create_bank(self) -> None:
        assert self.memory_service is not None

        section("CREATE HINDSIGHT PROJECT BUCKET")
        self.memory_service.create_project_bank(
            bank_id=self.bank_id,
            project_name=PROJECT_NAME,
            project_description=PROJECT_DESCRIPTION,
        )
        print("HINDSIGHT BANK: PASS")

    def seed_memories(self) -> None:
        assert self.canonical_memory_service is not None
        assert self.memory_service is not None
        assert self.learning_service is not None

        section("SEED BASE PROJECT KNOWLEDGE")

        for key, text_value in SEED_MEMORIES:
            registered = self.canonical_memory_service.register(
                self.bank_id,
                text_value,
            )
            if registered is not True:
                raise RuntimeError(
                    f"Canonical registration failed for {key}: {registered!r}"
                )

            self.memory_service.retain(
                bank_id=self.bank_id,
                content=text_value,
            )

        memories = self.canonical_memory_service.list_memories(
            bank_id=self.bank_id
        )

        for key, text_value in SEED_MEMORIES:
            memory_id = find_canonical_id_by_text(memories, text_value)
            if memory_id is None:
                raise RuntimeError(
                    f"Canonical memory was not verifiably persisted: {key}"
                )

            self.canonical_ids[key] = memory_id
            self.learning_service.refresh(memory_id)

            print(f"MEMORY {memory_id:>4} [{key}] STORED + VERIFIED")
            print(f"        {text_value}")

        print("BASE MEMORY COUNT:", len(memories))
        print("BASE MEMORY SEED: PASS")

    def show_help(self) -> None:
        section("COMMANDS")

        commands = [
            ("/help", "Show commands."),
            ("/project", "Show project/bank/chat context."),
            ("/memories", "Show canonical memories + learning state."),
            ("/history", "Show persisted conversation history."),
            ("/evidence", "Show source evidence + learning evidence from the last answer."),
            ("/state", "Show the last complete result and memory-awareness state."),
            ("/remember <fact>", "Force a fact through B6 ingestion."),
            ("/recall <query>", "Run a project retrieval diagnostic."),
            ("/newchat", "Start a new chat with the same project memory."),
            ("/feedback success", "Record a real successful outcome + evidence."),
            ("/feedback failure", "Record a real failed outcome + evidence."),
            ("/selftest", "Run offline intent and relevance checks."),
            ("/quit", "Exit."),
        ]

        for command, description in commands:
            print(f"{command:28} {description}")

        print()
        print("Normal text is automatically classified as:")
        print("  CHAT | MEMORY_UPDATE | PROJECT_QUERY | GENERAL_QUERY")

    def show_project(self) -> None:
        section("PROJECT CONTEXT")
        print("Project :", PROJECT_NAME)
        print("Project ID:", self.project_id)
        print("Bank ID   :", self.bank_id)
        print("Chat ID   :", self.chat_id)

    def show_memories(self) -> None:
        assert self.canonical_memory_service is not None
        assert self.learning_service is not None
        assert self.closed_loop is not None

        section("CANONICAL MEMORY STORE")

        memories = self.canonical_memory_service.list_memories(
            bank_id=self.bank_id
        )
        print("CANONICAL COUNT:", len(memories))

        for index, memory in enumerate(memories, start=1):
            memory_id = canonical_id(memory)
            text_value = canonical_text(memory)

            state = (
                self.learning_service.get_state(memory_id)
                if memory_id is not None
                else None
            )
            decision = (
                self.closed_loop.decide_behavior(state)
                if state
                else {"behavior": "insufficient"}
            )

            print()
            print(f"[{index}] MEMORY {memory_id}")
            print("    ", short_text(text_value, 700))

            sources = (
                self.conversation_store.find_memory_source(
                    project_id=self.project_id,
                    canonical_memory_id=memory_id,
                )
                if memory_id is not None
                else []
            )
            if sources:
                print("    user-originated update: YES")
                print("    source message ids:", [s["message_id"] for s in sources])
            else:
                print("    user-originated update: NO (seeded/project memory)")

            if state:
                print(
                    "    outcomes=", state.get("total_outcomes"),
                    "successes=", state.get("successes"),
                    "failures=", state.get("failures"),
                    "signal=", state.get("learning_signal"),
                    "evidence_coverage=", state.get("evidence_coverage"),
                )
                print("    C5=", decision.get("behavior"))
            else:
                print("    learning state: none")

    def _recent_updates(self) -> List[Dict[str, Any]]:
        return self.conversation_store.recent_update_records(
            bank_id=self.bank_id,
            limit=RECENT_UPDATE_LIMIT,
        )

    def _retrieval_query(self, user_text: str) -> str:
        updates = self._recent_updates()
        normalized = " ".join((user_text or "").strip().split())

        # For broad history/problem questions, give Hindsight a domain-neutral
        # retrieval hint so it can return multiple project issues instead of
        # over-focusing on the most recently mentioned one.
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

        lines = "\n".join(
            f"- {item['content']}"
            for item in updates
        )
        return (
            f"{base_query}\n\n"
            "Recent user-provided project updates. "
            "Use them only when they are relevant:\n"
            f"{lines}"
        )

    def _find_relevant_recent_update(
        self,
        query: str,
    ) -> Optional[Dict[str, Any]]:
        best = None
        best_score = 0.0

        for update in self._recent_updates():
            score = lexical_relevance(query, update["content"])
            if score > best_score:
                best_score = score
                best = dict(update)
                best["query_relevance"] = score

        return best if best_score >= 0.30 else None

    def _relevant_recent_updates_for_query(
        self,
        query: str,
        supporting_memories: Optional[List[Dict[str, Any]]] = None,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Return only recent project updates that can actually support this query."""
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
                # For history questions, an update is useful when it is tied to
                # the retrieved project history even when the broad query itself
                # contains few content words.
                relevance = max(query_score, 0.60 * support_score)
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
                int(pair[1].get("message_id") or 0),
            ),
            reverse=True,
        )
        return [item for _, item in scored[:limit]]


    def _build_answer_evidence(
        self,
        *,
        result: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        assert self.canonical_memory_service is not None

        selected = result.get("selected_memory") or {}
        selection = result.get("selection") or {}
        ranked = selection.get("ranked_candidates") or []
        retrieval = result.get("retrieval") or {}

        evidence_items: List[Dict[str, Any]] = []

        for rank, candidate in enumerate(ranked[:4], start=1):
            memory_id = candidate.get("canonical_memory_id")
            if memory_id is None:
                continue

            source_messages = self.conversation_store.find_memory_source(
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
                    "query_relevance": lexical_relevance(
                        query,
                        item["content"],
                    ),
                    "created_at": item["created_at"],
                }
            )

        raw_result_summary = []
        # Raw results are not part of result; the resolved candidates retain
        # identity details. This source list is still useful for the frontend.
        for item in (result.get("retrieval", {}).get("rejected") or []):
            raw_result_summary.append(dict(item))

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

        return {
            "query": query,
            "answer_memory_id": canonical_id(selected),
            "source_evidence": evidence_items,
            "recent_user_updates": recent_updates,
            "learning_evidence": learning_evidence,
            "retrieval": retrieval,
            "note": (
                "Source evidence explains where the answer came from. "
                "Learning/outcome evidence is separate and is populated only "
                "when outcomes and evidence are recorded through the feedback path."
            ),
            "raw_rejections": raw_result_summary,
        }

    def _project_supporting_memories(
        self,
        query: str,
        selection: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Keep supporting canonical memories without changing the C6 primary choice."""
        ranked = list(selection.get("ranked_candidates") or [])
        if not ranked:
            return []

        summary_mode = is_project_summary_query(query)

        if summary_mode:
            # Broad history questions ask for a reconstruction of the project's
            # recorded history, not just the memory that happens to share the
            # most words with "what problems did I have?". Preserve distinct
            # Hindsight/C6 candidates so the Groq synthesizer can connect
            # problem -> attempt -> outcome -> resolution.
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
        """Generate the answer from the selected memory plus relevant supporting facts."""
        assert self.groq_agent is not None

        client = getattr(self.groq_agent, "client", None)
        model = getattr(self.groq_agent, "model", "openai/gpt-oss-120b")
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

        # Hindsight can normalize/paraphrase retained memories. The exact
        # user-originated source message is therefore supplied alongside the
        # canonical memory so the final answer can explain what happened rather
        # than merely repeat a normalized evidence sentence.
        source_records: List[Dict[str, Any]] = []
        seen_source_memory_ids = set()

        for item in [primary, *supporting_memories]:
            item_id = canonical_id(item)
            if item_id is None or item_id in seen_source_memory_ids:
                continue
            seen_source_memory_ids.add(item_id)

            source_messages = self.conversation_store.find_memory_source(
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
            f"{pretty(provenance)}\n\n"
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
        """Safe fallback that never collapses a multi-step history into one memory."""
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
                        self.conversation_store.find_memory_source(
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


    def _interactive_lead(
        self,
        query: str,
        evidence: Dict[str, Any],
    ) -> str:
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

    def _get_learning_agent_for_query(
        self,
        *,
        query: str,
        include_recent_updates: bool = True,
    ) -> LearningAgentService:
        assert self.memory_service is not None
        assert self.resolver is not None
        assert self.selector is not None
        assert self.closed_loop is not None
        assert self.quality_gate is not None
        assert self.groq_agent is not None

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

    def _probe_project_memory(self, user_text: str) -> Dict[str, Any]:
        """
        Check whether the active project memory contains a relevant concept
        without turning the probe itself into the final answer.

        This is the missing bridge for GENERAL_QUERY:
            memory exists -> use it as project context + answer generally
            memory does not exist -> explicitly say so + answer generally

        The probe deliberately excludes recent-update boosting. Otherwise a
        recent project update could make an unrelated general question look
        project-specific.
        """
        query = " ".join((user_text or "").strip().split())

        try:
            query_agent = self._get_learning_agent_for_query(
                query=query,
                include_recent_updates=False,
            )

            # LearningAgentService still executes the complete retrieval ->
            # resolver -> C6/C5 path, but we do not need Groq just to test
            # whether a project-memory match exists.
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

        # For a general question, require direct lexical/concept relevance.
        # This prevents an unrelated Hindsight result from being mistaken for
        # project memory merely because the fallback semantic score is nonzero.
        matched = [
            item
            for item in ranked
            if float(item.get("query_relevance", 0.0) or 0.0)
            >= GENERAL_MEMORY_MATCH_THRESHOLD
        ]

        # The newest user update is a valid project source too, but only when
        # the user's actual wording is sufficiently related to it.
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
            "status": (
                "related_memory_found"
                if selected is not None
                else "no_related_memory"
            ),
            "reason": (
                "A candidate crossed the conservative general-query memory "
                "relevance threshold."
                if selected is not None
                else "No canonical project memory reached the conservative "
                "general-query relevance threshold."
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

            source_messages = self.conversation_store.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(candidate_id),
            )

            state = (
                self.learning_service.get_state(candidate_id)
                if self.learning_service is not None
                else None
            )
            provenance = (
                self.learning_service.get_provenance(candidate_id)
                if self.learning_service is not None
                else None
            )

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
            "note": (
                "General queries are always answered generally. Project memory is "
                "used only as optional context when a conservative relevance check "
                "finds a related canonical memory."
            ),
        }

    def _general_groq_answer(
        self,
        user_text: str,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        General-answer path.

        When memory_context is present, the answer remains a general explanation
        but may use project-specific memory as clearly identified context.
        """
        assert self.groq_agent is not None

        client = getattr(self.groq_agent, "client", None)
        model = getattr(
            self.groq_agent,
            "model",
            "openai/gpt-oss-120b",
        )

        if client is None:
            return (
                "I can handle that as a general question, but the real Groq "
                "client is not available right now."
            )

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

        if re.search(
            r"^what(?:'s|\s+is)\s+your\s+name\??$|^who\s+are\s+you\??$",
            normalized,
        ):
            return (
                "I’m ChatGPT. I’m here to help with both general questions and "
                "the project memory we’re building."
            )

        # Fuzzy greeting handling deliberately allows common texting typos such as
        # helloo/hellooo/heyyy/hiiii to behave like normal greetings.
        first_match = re.match(r"^([a-z]+)", normalized)
        first_word = first_match.group(1) if first_match else ""
        if fuzzy_match_word(first_word, ("hi", "hello", "hey"), threshold=0.70):
            remainder = normalized[first_match.end():].strip() if first_match else ""
            if not remainder or is_social_message(remainder):
                return (
                    f"Hi! I’m here with you. We’re working on the {PROJECT_NAME} "
                    "project, and I’m keeping normal conversation separate from "
                    "project memory. What should we work on next?"
                )

        if re.search(r"^(hi|hello|hey)\b", normalized):
            return (
                f"Hi! I’m here with you. We’re working on the {PROJECT_NAME} "
                "project, and I’m keeping normal conversation separate from "
                "project memory. What should we work on next?"
            )

        if re.search(r"^how are you\b|^how is it going\b|^what is up\b", normalized):
            return (
                "I’m doing well and ready to continue. Send me the next project "
                "update, question, or log result and we’ll keep the project context connected."
            )

        if fuzzy_match_word(first_word, ("thanks", "thank"), threshold=0.75):
            return (
                "You’re welcome. I’ve kept the project context, memory updates, "
                "conversation history, and learning evidence separate, so we can "
                "continue from the same point."
            )

        return (
            "Got it. We can keep chatting normally, or you can give me a project "
            "update, log/result, or a project question and I’ll connect it to the right memory path."
        )


    @staticmethod
    def _empty_learning_evidence(memory_id: Optional[int] = None) -> Dict[str, Any]:
        return {
            "memory_id": memory_id,
            "success": {"outcome_ids": [], "evidence_ids": []},
            "failure": {"outcome_ids": [], "evidence_ids": []},
            "partial": {"outcome_ids": [], "evidence_ids": []},
            "unknown": {"outcome_ids": [], "evidence_ids": []},
        }

    def _retrieve_related_memories_for_update(
        self,
        user_text: str,
    ) -> Dict[str, Any]:
        """
        Retrieve the project state *before* the current update is ingested.

        This is the missing bridge between "a user reported an update" and
        "the agent understood how that update relates to what was already known."

        Hindsight remains responsible for semantic recall. Canonical memory/C6/C5
        remain responsible for local identity and learning context. No hardcoded
        topic vocabulary is used here.
        """
        assert self.memory_service is not None
        assert self.resolver is not None
        assert self.selector is not None
        assert self.closed_loop is not None
        assert self.quality_gate is not None
        assert self.groq_agent is not None

        query = " ".join((user_text or "").strip().split())
        try:
            # IMPORTANT: the current update has already been written to the
            # conversation table, but it has NOT yet been retained into Hindsight.
            # We explicitly disable recent-update boosting so the pre-update
            # retrieval set represents prior project knowledge only.
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
                    "retrieval": {
                        "raw_result_count": retrieval.get("raw_result_count", 0),
                        "resolved_count": len(
                            retrieval.get("resolved_candidates") or []
                        ),
                        "accepted_count": retrieval.get("accepted_count", 0),
                        "rejected_count": retrieval.get("rejected_count", 0),
                        "rejected": retrieval.get("rejected", []),
                    },
                }

            selection = query_agent.select_memory(candidates)
            ranked = selection.get("ranked_candidates") or []

            # Keep several retrieved memories. The relationship classifier below
            # is semantic and is explicitly told not to assume that retrieval
            # implies relationship.
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

            if not prior_candidates:
                return {
                    "status": "no_previous_context",
                    "query": query,
                    "selected": None,
                    "candidates": [],
                    "retrieval": {
                        "raw_result_count": retrieval.get("raw_result_count", 0),
                        "resolved_count": len(
                            retrieval.get("resolved_candidates") or []
                        ),
                        "accepted_count": retrieval.get("accepted_count", 0),
                        "rejected_count": retrieval.get("rejected_count", 0),
                        "rejected": retrieval.get("rejected", []),
                    },
                }

            return {
                "status": "previous_context_found",
                "query": query,
                "selected": selection.get("selected"),
                "candidates": prior_candidates,
                "retrieval": {
                    "raw_result_count": retrieval.get("raw_result_count", 0),
                    "resolved_count": len(
                        retrieval.get("resolved_candidates") or []
                    ),
                    "accepted_count": retrieval.get("accepted_count", 0),
                    "rejected_count": retrieval.get("rejected_count", 0),
                    "rejected": retrieval.get("rejected", []),
                },
                "selection": selection,
            }
        except LookupError:
            return {
                "status": "no_previous_context",
                "query": query,
                "selected": None,
                "candidates": [],
                "retrieval": {
                    "raw_result_count": 0,
                    "resolved_count": 0,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "rejected": [],
                },
            }
        except Exception as exc:
            return {
                "status": "update_context_unavailable",
                "query": query,
                "selected": None,
                "candidates": [],
                "retrieval": {
                    "raw_result_count": 0,
                    "resolved_count": 0,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "rejected": [],
                },
                "error": str(exc),
            }

    def _analyze_update_relation(
        self,
        *,
        user_text: str,
        prior_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ask the real agent to understand the new update in relation to prior
        project records.

        This does NOT rewrite the stored memory. The user's original update is
        kept as the exact source record. The result is a separate interpretation
        used for the conversational reply and frontend observability.
        """
        assert self.groq_agent is not None

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
                "understanding": (
                    "This is a new project update, and no earlier project memory "
                    "was confidently available to connect it to."
                ),
                "reply": (
                    "I understand this as a new project issue/update. I don't have "
                    "a previously recorded project issue that I can confidently "
                    "connect it to yet, so I’ll treat this as the starting record "
                    "for the issue."
                ),
                "missing_information": (
                    "No prior related project record was available."
                ),
                "source": "no_prior_context",
            }

        candidate_lines = []
        for item in prior_candidates:
            memory_id = canonical_id(item)
            if memory_id is None:
                continue
            text_value = short_text(item.get("text"), 850)

            source_messages = self.conversation_store.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(memory_id),
            )
            source_text = (
                " | Original user update(s): "
                + " || ".join(
                    short_text(message.get("content"), 700)
                    for message in source_messages
                    if message.get("content")
                )
                if source_messages
                else ""
            )
            candidate_lines.append(
                f"- MEMORY {memory_id}: {text_value}{source_text}"
            )

        if not candidate_lines:
            return {
                "relation": "NO_PRIOR_CONTEXT",
                "related_memory_ids": [],
                "understanding": (
                    "No prior canonical memory could be supplied to the relation "
                    "analyzer."
                ),
                "reply": (
                    "I understand this as a new project update. I don't have a "
                    "previously recorded issue available to connect it to yet."
                ),
                "missing_information": "No prior canonical memory was available.",
                "source": "no_candidate_details",
            }

        client = getattr(self.groq_agent, "client", None)
        model = getattr(
            self.groq_agent,
            "model",
            "openai/gpt-oss-120b",
        )

        if client is None:
            top = prior_candidates[0]
            top_id = canonical_id(top)
            return {
                "relation": "UNCONFIRMED_PRIOR_CONTEXT",
                "related_memory_ids": [],
                "understanding": (
                    "Hindsight retrieved earlier project records, but the semantic "
                    "relationship could not be confirmed safely."
                ),
                "reply": (
                    "I found earlier project records that may be relevant, but I "
                    "could not safely confirm a relationship for this update. I’ll "
                    "store the new information separately rather than guessing how "
                    "the records are connected."
                ),
                "missing_information": (
                    "A semantic relationship could not be confirmed because the "
                    "Groq relation analyzer was unavailable."
                ),
                "source": "fallback_no_groq",
            }

        system = (
            "You are the update-understanding layer of a project-memory assistant. "
            "A user has just supplied a new project/work update. Earlier canonical "
            "memories were retrieved from Hindsight before the new update was stored. "
            "Determine whether the new update is actually related to any earlier "
            "memory and explain the relationship in plain language.\\n\\n"
            "Do not assume two records are related merely because Hindsight retrieved "
            "them. Use semantic meaning and project context. A topic can appear in "
            "different issues, so do not force a relationship.\\n\\n"
            "Choose one relation: RELATED_REFINEMENT (adds detail or narrows an "
            "existing issue), RELATED_PROGRESSION (new step/state in the same issue), "
            "RELATED_RESOLUTION (fix/result for an earlier issue), "
            "RELATED_CONTRADICTION (new information changes/conflicts with an earlier "
            "record), DUPLICATE (same information already recorded), "
            "UNRELATED_NEW_ISSUE (a different issue in the same project), or "
            "NO_PRIOR_CONTEXT (no earlier record is actually related).\\n\\n"
            "The response must be useful to the user. State what the new update means "
            "in relation to the prior record, what is known, and what is still missing "
            "when applicable. Never invent a root cause, fix, test result, or current "
            "state that is not in the supplied records.\\n\\n"
            'Return ONLY JSON: {"relation":"...", "related_memory_ids":[1], '
            '"understanding":"...", "reply":"...", "missing_information":"..."}'
        )

        user = (
            "CURRENT NEW USER UPDATE:\\n"
            f"{user_text}\\n\\n"
            "EARLIER PROJECT MEMORIES RETRIEVED BEFORE THIS UPDATE WAS STORED:\\n"
            + "\\n".join(candidate_lines)
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
            raw = str(
                getattr(response.choices[0].message, "content", None) or ""
            ).strip()

            data: Optional[Dict[str, Any]] = None
            try:
                data = json.loads(raw)
            except Exception:
                match = re.search(r"\{.*\}", raw, re.S)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except Exception:
                        data = None

            relation = str(
                (data or {}).get("relation", "")
            ).strip().upper()

            related_ids = []
            for value in (data or {}).get("related_memory_ids", []):
                try:
                    related_ids.append(int(value))
                except (TypeError, ValueError):
                    continue

            # Only allow IDs that were actually supplied as retrieved prior
            # memories. This prevents the model from inventing memory IDs.
            allowed_ids = {
                int(canonical_id(item))
                for item in prior_candidates
                if canonical_id(item) is not None
            }
            related_ids = [
                value for value in related_ids
                if value in allowed_ids
            ]

            if (
                relation not in valid_relations
                or not str((data or {}).get("understanding", "")).strip()
                or not str((data or {}).get("reply", "")).strip()
            ):
                raise ValueError("Unusable update relation response.")

            if relation in {
                "NO_PRIOR_CONTEXT",
                "UNRELATED_NEW_ISSUE",
            }:
                related_ids = []

            return {
                "relation": relation,
                "related_memory_ids": related_ids,
                "understanding": str(data.get("understanding", "")).strip(),
                "reply": str(data.get("reply", "")).strip(),
                "missing_information": str(
                    data.get("missing_information", "")
                ).strip(),
                "source": "semantic_groq",
                "raw": raw,
            }
        except Exception as exc:
            top = prior_candidates[0]
            top_id = canonical_id(top)
            return {
                "relation": "UNCONFIRMED_PRIOR_CONTEXT",
                "related_memory_ids": [],
                "understanding": (
                    "Hindsight retrieved earlier project information, but the semantic "
                    "relationship response could not be parsed safely."
                ),
                "reply": (
                    "I found earlier project information that may be relevant, but I "
                    "could not safely confirm how it relates to this update. I’ll keep "
                    "the new update separate rather than guessing the relationship."
                ),
                "missing_information": (
                    f"Semantic relation analysis was unavailable: {exc}"
                ),
                "source": "fallback_relation_error",
                "error": str(exc),
            }

    def _build_update_evidence(
        self,
        *,
        query: str,
        user_message_id: int,
        ingestion: Dict[str, Any],
        prior_context: Dict[str, Any],
        relation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the same frontend-friendly evidence contract for updates."""
        source_evidence: List[Dict[str, Any]] = []

        current_memory_id = ingestion.get("canonical_memory_id")
        if current_memory_id is not None:
            current_row = self.conversation_store.connection.execute(
                "SELECT created_at FROM messages WHERE message_id = ?",
                (int(user_message_id),),
            ).fetchone()
            current_created_at = (
                current_row["created_at"]
                if current_row is not None
                else now_iso()
            )

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
                            "created_at": current_created_at,
                        }
                    ],
                }
            )

        for rank, candidate in enumerate(
            prior_context.get("candidates") or [],
            start=2,
        ):
            memory_id = canonical_id(candidate)
            if memory_id is None:
                continue

            source_messages = self.conversation_store.find_memory_source(
                project_id=self.project_id,
                canonical_memory_id=int(memory_id),
            )
            source_evidence.append(
                {
                    "rank": rank,
                    "source_type": "canonical_memory",
                    "source_kind": (
                        "user_provided_project_update"
                        if source_messages
                        else "seeded_project_memory"
                    ),
                    "canonical_memory_id": memory_id,
                    "text": candidate.get("text"),
                    "retrieval_similarity": candidate.get("retrieval_similarity"),
                    "query_relevance": candidate.get("query_relevance"),
                    "learning_signal": candidate.get("learning_signal"),
                    "learning_confidence": candidate.get("learning_confidence"),
                    "learning_multiplier": candidate.get("learning_multiplier"),
                    "source_messages": source_messages,
                    "related_to_current_update": (
                        int(memory_id)
                        in set(relation.get("related_memory_ids") or [])
                    ),
                }
            )

            if len(source_evidence) >= 7:
                break

        related_learning = {}
        for memory_id in relation.get("related_memory_ids") or []:
            if self.learning_service is None:
                continue
            state = self.learning_service.get_state(int(memory_id))
            provenance = self.learning_service.get_provenance(int(memory_id))
            related_learning[str(memory_id)] = {
                "state": state,
                "provenance": provenance,
            }

        return {
            "query": query,
            "answer_mode": "memory_update",
            "current_update": {
                "message_id": user_message_id,
                "canonical_memory_id": current_memory_id,
                "text": query,
            },
            "update_understanding": relation,
            "prior_context": {
                "status": prior_context.get("status"),
                "retrieval": prior_context.get("retrieval"),
                "selected_memory": prior_context.get("selected"),
                "candidate_count": len(prior_context.get("candidates") or []),
            },
            "source_evidence": source_evidence,
            "learning_evidence": self._empty_learning_evidence(current_memory_id),
            "related_learning_context": related_learning,
            "ingestion": ingestion,
            "note": (
                "For an update, source evidence records the current user update and "
                "the earlier project records used to understand its relationship. "
                "Learning/outcome evidence remains separate and appears only after "
                "feedback/outcomes are recorded."
            ),
        }

    def print_update_understanding(
        self,
        relation: Dict[str, Any],
        prior_context: Dict[str, Any],
    ) -> None:
        section("UPDATE UNDERSTANDING — WHAT THE AGENT CONNECTED")

        print("RELATION :", relation.get("relation"))
        print(
            "RELATED MEMORY IDS :",
            relation.get("related_memory_ids") or [],
        )
        print("UNDERSTANDING:")
        print(relation.get("understanding") or "")
        print()
        print("MISSING / NOT YET KNOWN:")
        print(relation.get("missing_information") or "None recorded.")
        print()
        print("PRIOR CONTEXT STATUS:", prior_context.get("status"))
        retrieval = prior_context.get("retrieval") or {}
        print("HINDSIGHT RAW RESULTS :", retrieval.get("raw_result_count", 0))
        print("RESOLVED CANDIDATES   :", retrieval.get("resolved_count", 0))
        print("ACCEPTED CANDIDATES   :", retrieval.get("accepted_count", 0))

    def handle_user(
        self,
        user_text: str,
        forced_type: Optional[str] = None,
    ) -> None:
        assert self.ingestion_service is not None

        if forced_type:
            input_type = forced_type
            intent_meta = {"source": "forced"}
        else:
            assert self.intent_router is not None
            input_type, intent_meta = self.intent_router.classify(
                text=user_text,
                conversation_store=self.conversation_store,
                project_id=self.project_id,
            )
        self.last_user_input = user_text
        if input_type == "PROJECT_QUERY":
            self.last_project_query_input = user_text
        else:
            self.last_project_query_input = None

        user_message_id = self.conversation_store.add_message(
            chat_id=self.chat_id,
            role="user",
            content=user_text,
            message_type=input_type,
            metadata={"intent_router": intent_meta},
        )

        section(f"{self.chat_id} — USER → AGENT")
        print("USER:")
        print(user_text)
        print()
        print("INPUT TYPE:", input_type)
        print("INTENT ROUTER:", pretty(intent_meta))

        if input_type == "MEMORY_UPDATE":
            # IMPORTANT:
            #   1) Retrieve what Hindsight already knows BEFORE storing this update.
            #   2) Ask the semantic layer how the update relates to those memories.
            #   3) Keep the user's update as the exact source record.
            #   4) Run the existing B6 ingestion unchanged.
            #   5) Respond with the understood relationship + storage result.
            prior_context = self._retrieve_related_memories_for_update(user_text)
            relation = self._analyze_update_relation(
                user_text=user_text,
                prior_context=prior_context,
            )

            try:
                ingestion = self.ingestion_service.ingest(
                    bank_id=self.bank_id,
                    text=user_text,
                )
            except Exception as exc:
                ingestion = {
                    "input": user_text,
                    "retained": False,
                    "relationship": None,
                    "relationship_similarity": None,
                    "canonical_memory_id": None,
                    "canonical_registry_verified": False,
                    "hindsight_action": "error",
                    "hindsight_error": str(exc),
                }

            self.last_ingestion = ingestion
            memory_id = ingestion.get("canonical_memory_id")

            # Attach source message to the canonical memory when possible.
            if memory_id is not None:
                self.conversation_store.connection.execute(
                    """
                    UPDATE messages
                    SET canonical_memory_id = ?,
                        ingestion_status = ?
                    WHERE message_id = ?
                    """,
                    (
                        int(memory_id),
                        (
                            "stored"
                            if ingestion.get("canonical_registry_verified")
                            else "not_verified"
                        ),
                        int(user_message_id),
                    ),
                )
                self.conversation_store.connection.commit()

            # Combine semantic understanding with B6's storage relationship.
            # B6 remains authoritative for duplicate/dedup write behavior;
            # semantic relation is explanatory context for the user.
            storage_relationship = ingestion.get("relationship")

            if ingestion.get("retained"):
                storage_line = (
                    f"I stored this as project memory {memory_id}."
                    if memory_id is not None
                    else
                    "I sent this through the memory-ingestion path, but I could "
                    "not verify a canonical memory ID."
                )
            elif storage_relationship in {
                "exact_duplicate",
                "semantic_duplicate",
            }:
                storage_line = (
                    f"I recognized it as already represented by project memory "
                    f"{memory_id} and did not create a duplicate."
                )
            else:
                storage_line = (
                    "The memory write was not fully verified, so I am not claiming "
                    "that the new record was safely stored."
                )

            if relation.get("reply"):
                answer = (
                    f"{relation['reply'].strip()}\n\n"
                    f"{storage_line}"
                )
            else:
                answer = storage_line

            # Make the persistent message metadata carry the relationship that
            # the agent actually understood, not just the low-level B6 result.
            self.conversation_store.connection.execute(
                """
                UPDATE messages
                SET metadata_json = ?
                WHERE message_id = ?
                """,
                (
                    json.dumps(
                        {
                            "intent_router": intent_meta,
                            "update_relation": relation,
                            "prior_context": prior_context,
                            "ingestion": ingestion,
                        },
                        default=str,
                    ),
                    int(user_message_id),
                ),
            )
            self.conversation_store.connection.commit()

            evidence = self._build_update_evidence(
                query=user_text,
                user_message_id=user_message_id,
                ingestion=ingestion,
                prior_context=prior_context,
                relation=relation,
            )
            self.last_evidence = evidence

            self.conversation_store.add_message(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="MEMORY_ACK",
                canonical_memory_id=memory_id,
                ingestion_status=(
                    "stored"
                    if ingestion.get("canonical_registry_verified")
                    else "not_verified"
                ),
                metadata={
                    "source_message_id": user_message_id,
                    "update_relation": relation,
                    "prior_context": prior_context,
                    "ingestion": ingestion,
                    "evidence": evidence,
                },
            )

            print("AGENT:")
            print(answer)
            self.print_update_understanding(
                relation=relation,
                prior_context=prior_context,
            )
            self.print_ingestion(ingestion)
            self.print_evidence(evidence)
            return

        if input_type == "CHAT":
            answer = self._chat_reply(user_text)
            self.conversation_store.add_message(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="CHAT_REPLY",
            )
            print("AGENT:")
            print(answer)
            return

        if input_type == "GENERAL_QUERY":
            # GENERAL_QUERY is still memory-aware. The memory check answers one
            # question first: "Does this active project actually know anything
            # related to what the user asked?" It never changes the fact that the
            # final response is a general answer.
            awareness = self._probe_project_memory(user_text)
            self.last_memory_awareness = awareness

            if awareness.get("memory_match"):
                selected = awareness.get("selected_memory") or {}
                lead = (
                    "I found related knowledge in this project's memory: "
                    f"Memory {selected.get('canonical_memory_id')} — "
                    f"“{short_text(selected.get('text'), 360)}”. "
                    "I’ll use it as project context, then answer your question generally."
                )
            elif awareness.get("status") == "memory_check_unavailable":
                lead = (
                    "I couldn’t complete the project-memory check, so I won’t "
                    "pretend there is a project-specific match. I’ll answer this "
                    "as a general question."
                )
            else:
                lead = (
                    "I checked this project’s memory and found no related "
                    "project-specific knowledge for this question. I’ll answer "
                    "it generally."
                )

            try:
                answer_body = self._general_groq_answer(
                    user_text,
                    memory_context=(awareness if awareness.get("memory_match") else None),
                )
            except Exception as exc:
                answer_body = (
                    "I can answer that as a general question, but the Groq "
                    f"request failed: {exc}"
                )

            answer = f"{lead}\n\n{answer_body}"
            evidence = self._build_general_answer_evidence(
                query=user_text,
                awareness=awareness,
            )
            self.last_evidence = evidence

            self.conversation_store.add_message(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="GENERAL_QUERY_REPLY",
                canonical_memory_id=evidence.get("answer_memory_id"),
                metadata={
                    "source": (
                        "general_groq_with_project_memory"
                        if awareness.get("memory_match")
                        else "general_groq_no_project_memory"
                    ),
                    "memory_awareness": awareness,
                    "evidence": evidence,
                },
            )
            print("AGENT:")
            print(answer)
            self.print_general_memory_awareness(awareness)
            self.print_evidence(evidence)
            return

        # PROJECT_QUERY
        retrieval_query = self._retrieval_query(user_text)

        try:
            # Hindsight may still receive the expanded retrieval query for recall,
            # but C6/query relevance must score the user's actual question so a
            # recent unrelated update cannot contaminate memory selection.
            query_agent = self._get_learning_agent_for_query(
                query=user_text,
            )

            # Preserve the existing LearningAgentService pipeline while giving the
            # final answer generator the relevant supporting memories as well as the
            # primary C6 selection. This matters for questions such as "what happened"
            # where one memory is only an intermediate step in the full history.
            retrieval = query_agent.retrieve_candidates(
                bank_id=self.bank_id,
                query=retrieval_query,
            )
            candidates = retrieval.get("candidates") or []
            if not candidates:
                raise LookupError(
                    "No usable memories were found for the supplied query."
                )

            selection = query_agent.select_memory(candidates)
            context = query_agent.build_context(
                query=user_text,
                selection=selection,
            )
            supporting_memories = self._project_supporting_memories(
                user_text,
                selection,
            )
            recent_updates = self._relevant_recent_updates_for_query(
                user_text,
                supporting_memories=supporting_memories,
            )

            try:
                answer_body = self._project_groq_answer(
                    query=user_text,
                    context=context,
                    supporting_memories=supporting_memories,
                    recent_updates=recent_updates,
                )
            except Exception:
                # Never fall back to the old single-memory generator for a
                # multi-step project question. It can hide supporting facts.
                answer_body = self._deterministic_project_fallback(
                    query=user_text,
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
                "retrieval": {
                    "raw_result_count": retrieval.get("raw_result_count", 0),
                    "resolved_count": len(retrieval.get("resolved_candidates") or []),
                    "accepted_count": retrieval.get("accepted_count", 0),
                    "rejected_count": retrieval.get("rejected_count", 0),
                    "rejected": retrieval.get("rejected", []),
                },
                "answer_context": {
                    "answer_mode": (
                        "project_summary"
                        if is_project_summary_query(user_text)
                        else "project_focused"
                    ),
                    "supporting_memories": supporting_memories,
                    "recent_user_updates": recent_updates,
                },
            }
        except LookupError as exc:
            # Fallback to recent user-provided project updates if Hindsight
            # has not yet surfaced the new memory.
            update = self._find_relevant_recent_update(user_text)
            if update is not None:
                evidence = {
                    "query": user_text,
                    "answer_memory_id": update.get("canonical_memory_id"),
                    "source_evidence": [
                        {
                            "rank": 1,
                            "source_type": "user_memory_update",
                            "source_kind": "recent_project_update",
                            "canonical_memory_id": update.get("canonical_memory_id"),
                            "text": update.get("content"),
                            "retrieval_similarity": None,
                            "identity_score": None,
                            "identity_margin": None,
                            "query_relevance": update.get("query_relevance"),
                            "source_messages": [
                                {
                                    "message_id": update.get("message_id"),
                                    "chat_id": update.get("chat_id"),
                                    "text": update.get("content"),
                                    "created_at": update.get("created_at"),
                                }
                            ],
                        }
                    ],
                    "recent_user_updates": self._recent_updates(),
                    "learning_evidence": {
                        "memory_id": update.get("canonical_memory_id"),
                        "success": {"outcome_ids": [], "evidence_ids": []},
                        "failure": {"outcome_ids": [], "evidence_ids": []},
                        "partial": {"outcome_ids": [], "evidence_ids": []},
                        "unknown": {"outcome_ids": [], "evidence_ids": []},
                    },
                    "retrieval": {
                        "raw_result_count": 0,
                        "resolved_count": 0,
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "rejected": [],
                    },
                    "note": "Fallback used because Hindsight had no usable candidate.",
                }
                answer = (
                    "I found the project update you gave me that matches this: "
                    f"“{update['content']}”\n\n"
                    "I can use that as current project knowledge, but it is "
                    "not outcome evidence until a test/result is recorded."
                )
                self.last_result = {
                    "answer": answer,
                    "selected_memory": {
                        "canonical_memory_id": update.get("canonical_memory_id"),
                        "text": update.get("content"),
                        "retrieval_similarity": None,
                    },
                    "selection": {
                        "selected": {
                            "canonical_memory_id": update.get("canonical_memory_id"),
                            "text": update.get("content"),
                            "retrieval_similarity": 0.0,
                            "learning_signal": 0.0,
                            "informative_outcomes": 0,
                            "evidence_coverage": 0.0,
                            "behavior": "insufficient",
                            "learning_confidence": 0.0,
                            "learning_multiplier": 1.0,
                            "adjusted_score": 0.0,
                            "query_relevance": update.get("query_relevance"),
                            "final_selection_score": update.get("query_relevance"),
                        },
                        "ranked_candidates": [],
                    },
                    "behavior": "insufficient",
                    "learning": None,
                    "provenance": evidence["learning_evidence"],
                    "retrieval": evidence["retrieval"],
                }
                self.last_evidence = evidence

                self.conversation_store.add_message(
                    chat_id=self.chat_id,
                    role="assistant",
                    content=answer,
                    message_type="QUERY_REPLY",
                    canonical_memory_id=update.get("canonical_memory_id"),
                    metadata={
                        "retrieval_query": retrieval_query,
                        "evidence": evidence,
                        "fallback_reason": str(exc),
                    },
                )

                print("AGENT:")
                print(answer)
                self.print_evidence(evidence)
                return

            answer = (
                "I could not safely connect this project question to a usable "
                "canonical memory yet, so I’m not going to invent a project-specific "
                f"answer. Retrieval status: {exc}"
            )
            self.last_result = None
            self.last_evidence = None

            self.conversation_store.add_message(
                chat_id=self.chat_id,
                role="assistant",
                content=answer,
                message_type="QUERY_REPLY",
                metadata={
                    "retrieval_query": retrieval_query,
                    "error": str(exc),
                },
            )

            print("AGENT:")
            print(answer)
            return

        self.last_result = result
        evidence = self._build_answer_evidence(
            result=result,
            query=user_text,
        )
        answer_context = result.get("answer_context") or {}
        evidence["answer_mode"] = answer_context.get("answer_mode")
        evidence["supporting_memories"] = answer_context.get(
            "supporting_memories",
            [],
        )
        self.last_evidence = evidence

        technical_answer = result.get("answer") or ""
        lead = self._interactive_lead(
            query=user_text,
            evidence=evidence,
        )
        answer = f"{lead}\n\n{technical_answer}"

        selected = result.get("selected_memory") or {}
        selected_id = canonical_id(selected)

        self.conversation_store.add_message(
            chat_id=self.chat_id,
            role="assistant",
            content=answer,
            message_type="QUERY_REPLY",
            canonical_memory_id=selected_id,
            metadata={
                "source_user_message_id": user_message_id,
                "retrieval_query": retrieval_query,
                "evidence": evidence,
                "result": result,
            },
        )

        print("AGENT:")
        print(answer)
        self.print_agent_observability(result, retrieval_query)
        self.print_evidence(evidence)

    @staticmethod
    def self_test() -> List[Tuple[str, str, bool]]:
        lock_memory = (
            "Pessimistic database locking was implemented for the wallet balance update, "
            "and the concurrent transaction tests passed with the correct final balance."
        )
        normalization_memory = "Pessimistic database locking was implemented."
        cases = [
            ("generic code report", "MEMORY_UPDATE", classify_user_input("this code is not working") == "MEMORY_UPDATE"),
            ("generic React report", "MEMORY_UPDATE", classify_user_input("the React component is crashing") == "MEMORY_UPDATE"),
            ("generic deployment report", "MEMORY_UPDATE", classify_user_input("the deployment failed after the change") == "MEMORY_UPDATE"),
            ("generic API report", "MEMORY_UPDATE", classify_user_input("the endpoint is returning an exception") == "MEMORY_UPDATE"),
            ("generic test report", "MEMORY_UPDATE", classify_user_input("the integration tests passed") == "MEMORY_UPDATE"),
            ("generic implementation", "MEMORY_UPDATE", classify_user_input("we implemented the login flow") == "MEMORY_UPDATE"),
            ("generic project history question", "PROJECT_QUERY", classify_user_input("what did we change?") == "PROJECT_QUERY"),
            ("generic current status question", "PROJECT_QUERY", classify_user_input("what is the current status?") == "PROJECT_QUERY"),
            ("general knowledge question", "GENERAL_QUERY", classify_user_input("what is normalization?") == "GENERAL_QUERY"),
            ("general Python question", "GENERAL_QUERY", classify_user_input("what is Python?") == "GENERAL_QUERY"),
            ("helloo", "CHAT", classify_user_input("helloo") == "CHAT"),
            ("hiiii", "CHAT", classify_user_input("hiiii") == "CHAT"),
            ("thanksks", "CHAT", classify_user_input("thanksks") == "CHAT"),
            ("what is your name", "CHAT", classify_user_input("what is your name") == "CHAT"),
            ("how r u", "CHAT", classify_user_input("how r u") == "CHAT"),
            ("whats up", "CHAT", classify_user_input("whats up") == "CHAT"),
            ("what is Python?", "GENERAL_QUERY", classify_user_input("what is Python?") == "GENERAL_QUERY"),
            ("do u knwo about normalization", "GENERAL_QUERY", classify_user_input("do u knwo about normalization") == "GENERAL_QUERY"),
            ("what is normalization?", "GENERAL_QUERY", classify_user_input("what is normalization?") == "GENERAL_QUERY"),
            ("what are locks?", "GENERAL_QUERY", classify_user_input("what are locks?") == "GENERAL_QUERY"),
            ("thanks, now explain normalization", "GENERAL_QUERY", classify_user_input("thanks, now explain normalization") == "GENERAL_QUERY"),
            ("thanks, now explain wallet concurrency", "PROJECT_QUERY", classify_user_input("thanks, now explain wallet concurrency") == "PROJECT_QUERY"),
            ("What happened with wallet concurrency?", "PROJECT_QUERY", classify_user_input("What happened with wallet concurrency?") == "PROJECT_QUERY"),
            ("helloo, what happened with wallet concurrency?", "PROJECT_QUERY", classify_user_input("helloo, what happened with wallet concurrency?") == "PROJECT_QUERY"),
            ("We discovered that pessimistic locking is the wallet solution.", "MEMORY_UPDATE", classify_user_input("We discovered that pessimistic locking is the wallet solution.") == "MEMORY_UPDATE"),
            ("okay, we implemented a lock", "MEMORY_UPDATE", classify_user_input("okay, we implemented a lock") == "MEMORY_UPDATE"),
            ("what are locks? → lock memory", "LOCK_RELEVANT", lexical_relevance("what are locks?", lock_memory) >= GENERAL_MEMORY_MATCH_THRESHOLD),
            ("normalization → no lock memory", "NO_LOCK_RELEVANCE", lexical_relevance("what is normalization?", lock_memory) < GENERAL_MEMORY_MATCH_THRESHOLD),
            ("normalization → no lock memory", "NO_LOCK_RELEVANCE", lexical_relevance("what is normalization?", normalization_memory) < GENERAL_MEMORY_MATCH_THRESHOLD),
        ]
        # Router parsing itself is domain-neutral.
        cases.extend([
            ("router JSON PROJECT_QUERY", "PROJECT_QUERY", SemanticIntentRouter.parse_intent('{"intent":"PROJECT_QUERY","reason":"history"}') == "PROJECT_QUERY"),
            ("router JSON MEMORY_UPDATE", "MEMORY_UPDATE", SemanticIntentRouter.parse_intent('{"intent":"MEMORY_UPDATE","reason":"new work state"}') == "MEMORY_UPDATE"),
            ("router JSON GENERAL_QUERY", "GENERAL_QUERY", SemanticIntentRouter.parse_intent('{"intent":"GENERAL_QUERY","reason":"conceptual question"}') == "GENERAL_QUERY"),
            ("router plain CHAT", "CHAT", SemanticIntentRouter.parse_intent("CHAT") == "CHAT"),
        ])
        return cases

    def remember(self, text: str) -> None:
        if not text.strip():
            print("Usage: /remember <fact>")
            return
        self.handle_user(text.strip(), forced_type="MEMORY_UPDATE")

    def recall_only(self, query: str) -> None:
        if not query.strip():
            print("Usage: /recall <query>")
            return

        section("RECALL-ONLY DIAGNOSTIC")
        retrieval_query = self._retrieval_query(query.strip())

        try:
            query_agent = self._get_learning_agent_for_query(
                query=retrieval_query,
            )
            result = query_agent.answer(
                bank_id=self.bank_id,
                query=retrieval_query,
                answer_generator=self.groq_agent,
            )
        except Exception as exc:
            print("RECALL ERROR:", repr(exc))
            return

        evidence = self._build_answer_evidence(
            result=result,
            query=query.strip(),
        )
        print("QUERY:", query.strip())
        print("EFFECTIVE RETRIEVAL QUERY:")
        print(retrieval_query)
        self.print_agent_observability(
            result,
            retrieval_query,
        )
        self.print_evidence(evidence)

    def print_ingestion(self, ingestion: Dict[str, Any]) -> None:
        section("MEMORY INGESTION RECEIPT")
        print("INPUT                  :", ingestion.get("input"))
        print("RELATIONSHIP           :", ingestion.get("relationship"))
        print("RETAINED AS NEW        :", ingestion.get("retained"))
        print("CANONICAL MEMORY ID    :", ingestion.get("canonical_memory_id"))
        print(
            "CANONICAL WRITE VERIFIED:",
            ingestion.get("canonical_registry_verified"),
        )
        print("HINDSIGHT ACTION       :", ingestion.get("hindsight_action"))
        print(
            "HINDSIGHT RESULT TYPE  :",
            ingestion.get("hindsight_result_type"),
        )

        if ingestion.get("hindsight_error"):
            print("HINDSIGHT ERROR        :", ingestion.get("hindsight_error"))
        if ingestion.get("learning_state_error"):
            print("LEARNING STATE ERROR   :", ingestion.get("learning_state_error"))

        status_ok = bool(
            ingestion.get("hindsight_action") == "skipped_duplicate"
            or (
                ingestion.get("canonical_registry_verified")
                and ingestion.get("hindsight_action") == "retained"
                and not ingestion.get("learning_state_error")
            )
        )
        print("STATUS                 :", "PASS" if status_ok else "NOT VERIFIED")

    def print_agent_observability(
        self,
        result: Dict[str, Any],
        retrieval_query: str,
    ) -> None:
        section("WHAT THE AGENT ACTUALLY USED")

        selected = result.get("selected_memory") or {}
        selection = result.get("selection") or {}
        selected_from_c6 = selection.get("selected") or {}
        ranked = selection.get("ranked_candidates") or []
        retrieval = result.get("retrieval") or {}

        print("ORIGINAL USER QUERY:")
        print(self.last_user_input or "")
        print()
        print("EFFECTIVE RETRIEVAL QUERY:")
        print(retrieval_query)
        print()

        print("1. SELECTED MEMORY")
        print("   ID   :", canonical_id(selected))
        print("   TEXT :", short_text(selected.get("text"), 700))
        print()

        print("2. RETRIEVAL")
        print("   raw Hindsight results:", retrieval.get("raw_result_count"))
        print("   resolved candidates  :", retrieval.get("resolved_count"))
        print("   accepted candidates :", retrieval.get("accepted_count"))
        print("   rejected candidates :", retrieval.get("rejected_count"))
        print()

        print("3. C6 + QUERY RELEVANCE")
        for rank, candidate in enumerate(ranked, start=1):
            print(
                f"   #{rank} memory={candidate.get('canonical_memory_id')} "
                f"hindsight={candidate.get('retrieval_similarity', 0.0):.4f} "
                f"query_rel={candidate.get('query_relevance', 0.0):.4f} "
                f"learning_signal={candidate.get('learning_signal', 0.0):.4f} "
                f"confidence={candidate.get('learning_confidence', 0.0):.4f} "
                f"multiplier={candidate.get('learning_multiplier', 1.0):.4f} "
                f"C6_adjusted={candidate.get('adjusted_score', 0.0):.4f} "
                f"final={candidate.get('final_selection_score', 0.0):.4f} "
                f"behavior={candidate.get('behavior')}"
            )
        print()

        print("4. C5")
        print("   behavior:", result.get("behavior"))
        print()

        print("5. LEARNING")
        print(pretty(result.get("learning")))
        print()

        print("6. PROVENANCE / LEARNING EVIDENCE")
        print(pretty(result.get("provenance")))
        print()

        print("7. SELECTED C6 OBJECT")
        print(pretty(selected_from_c6))
        print()

        print("8. REJECTIONS")
        print(pretty(retrieval.get("rejected")))

    def print_evidence(self, evidence: Dict[str, Any]) -> None:
        section("ANSWER EVIDENCE — WHAT SUPPORTS THIS RESPONSE")

        source_evidence = evidence.get("source_evidence") or []
        if not source_evidence:
            print("No source memory evidence available.")
        else:
            for item in source_evidence[:4]:
                print()
                print(
                    f"[SOURCE {item.get('rank')}] "
                    f"{item.get('source_type')} / {item.get('source_kind')}"
                )
                print("    canonical_memory_id :", item.get("canonical_memory_id"))
                print("    text                 :", short_text(item.get("text"), 700))
                print("    query_relevance      :", item.get("query_relevance"))
                print("    Hindsight similarity :", item.get("retrieval_similarity"))
                print("    identity_score       :", item.get("identity_score"))
                print("    identity_margin      :", item.get("identity_margin"))

                messages = item.get("source_messages") or []
                if messages:
                    print("    ORIGINAL USER UPDATE:")
                    for message in messages:
                        message_id = message.get("message_id", "?")
                        message_text = (
                            message.get("text")
                            or message.get("content")
                            or ""
                        )
                        print(
                            f"      message {message_id}: "
                            f"{short_text(message_text, 700)}"
                        )
                else:
                    print("    ORIGINAL USER UPDATE: none (seeded project memory)")

        print()
        print("LEARNING / OUTCOME EVIDENCE")
        print(
            "This is different from source memory. It appears only when an "
            "experience/outcome/evidence record has been created."
        )
        print(pretty(evidence.get("learning_evidence")))

        print()
        print("FRONTEND-FRIENDLY EVIDENCE OBJECT")
        print(pretty(evidence))

    def print_general_memory_awareness(self, awareness: Dict[str, Any]) -> None:
        section("GENERAL QUERY — MEMORY AWARENESS CHECK")
        print("QUERY:", awareness.get("query"))
        print("MEMORY STATUS:", awareness.get("status"))
        print("MEMORY MATCH:", awareness.get("memory_match"))
        print("THRESHOLD:", GENERAL_MEMORY_MATCH_THRESHOLD)
        print("REASON:", awareness.get("reason"))

        selected = awareness.get("selected_memory")
        if selected:
            print()
            print("SELECTED RELATED MEMORY")
            print("    ID   :", selected.get("canonical_memory_id"))
            print("    TEXT :", selected.get("text"))
            print("    query_relevance:", selected.get("query_relevance"))
            print("    retrieval_similarity:", selected.get("retrieval_similarity"))
        else:
            print("    No related canonical memory selected.")

        print()
        print("MATCHED CANDIDATES:", len(awareness.get("matched_candidates") or []))
        for rank, item in enumerate(awareness.get("matched_candidates") or [], start=1):
            print(
                f"    #{rank} memory={item.get('canonical_memory_id')} "
                f"query_rel={item.get('query_relevance')} "
                f"retrieval={item.get('retrieval_similarity')}"
            )


    def show_evidence(self) -> None:
        section("LAST ANSWER EVIDENCE")
        if self.last_evidence is None:
            print("No answer evidence has been generated yet.")
            return
        print(pretty(self.last_evidence))

    def show_state(self) -> None:
        section("LAST STATE")

        if self.last_ingestion:
            print("LAST INGESTION")
            print(pretty(self.last_ingestion))
            print()

        if self.last_result:
            print("LAST AGENT RESULT")
            print(pretty(self.last_result))
            print()

        if self.last_memory_awareness:
            print("LAST MEMORY AWARENESS")
            print(pretty(self.last_memory_awareness))
            print()

        if self.last_evidence:
            print("LAST EVIDENCE")
            print(pretty(self.last_evidence))
            print()

        if (
            not self.last_ingestion
            and not self.last_result
            and not self.last_evidence
        ):
            print("Nothing has been processed yet.")

    def show_history(self) -> None:
        section("PERSISTED CONVERSATION HISTORY")

        rows = self.conversation_store.list_messages(
            project_id=self.project_id
        )
        if not rows:
            print("No messages stored.")
            return

        current_chat = None

        for row in rows:
            if row["chat_id"] != current_chat:
                current_chat = row["chat_id"]
                print()
                print("--- CHAT", current_chat, "---")

            print()
            print(
                f"[{row['message_id']}] "
                f"{row['role'].upper()} ({row['message_type']})"
            )
            print(row["content"])

            if row.get("canonical_memory_id") is not None:
                print("canonical_memory_id:", row["canonical_memory_id"])

            if row.get("ingestion_status"):
                print("ingestion_status:", row["ingestion_status"])

    def new_chat(self) -> None:
        self.chat_id = f"chat-{uuid.uuid4().hex[:10]}"
        self.conversation_store.create_chat(
            chat_id=self.chat_id,
            project_id=self.project_id,
            bank_id=self.bank_id,
        )

        self.last_result = None
        self.last_ingestion = None
        self.last_evidence = None
        self.last_memory_awareness = None
        self.last_project_query_input = None
        self.last_user_input = None

        section("NEW CHAT")
        print("New chat:", self.chat_id)
        print("Same project:", PROJECT_NAME)
        print("Same Hindsight bucket:", self.bank_id)
        print("Stored project memory remains available.")
        print("Previous conversation remains persisted.")

    def record_feedback(self, outcome_type: str) -> None:
        assert self.feedback_service is not None
        assert self.learning_service is not None
        assert self.closed_loop is not None

        if outcome_type not in {"success", "failure"}:
            print("C2 currently accepts only: success | failure")
            return

        if not self.last_result or self.last_project_query_input != self.last_user_input:
            print("Run a project query immediately before recording feedback so the outcome is attached to the intended memory.")
            return

        selected = self.last_result.get("selected_memory") or {}
        memory_id = canonical_id(selected)

        if memory_id is None:
            print("No canonical memory is attached to the last result.")
            return

        section("RECORD OUTCOME + EVIDENCE")

        summary = input("Outcome summary: ").strip()
        evidence_text = input("Evidence text: ").strip()

        if not summary:
            summary = (
                "The selected historical approach successfully helped resolve the issue."
                if outcome_type == "success"
                else "The selected historical approach failed to resolve the issue."
            )

        if not evidence_text:
            evidence_text = (
                "Implementation test passed with expected result."
                if outcome_type == "success"
                else "Implementation test failed and expected result was not produced."
            )

        evidence_items: List[Dict[str, Any]] = [
            {
                "type": "text",
                "content": evidence_text,
                "source_type": "interactive_chat",
                "source_id": self.chat_id,
            }
        ]

        evidence_file = input(
            "Optional evidence file path [press Enter to skip]: "
        ).strip()

        if evidence_file:
            path = Path(evidence_file)
            if not path.exists() or not path.is_file():
                print("Evidence file not found. Continuing with text evidence only.")
            else:
                file_bytes = path.read_bytes()
                mime_type = (
                    mimetypes.guess_type(path.name)[0]
                    or "application/octet-stream"
                )
                evidence_items.append(
                    {
                        "type": "file",
                        "file_name": path.name,
                        "mime_type": mime_type,
                        "file_bytes": file_bytes,
                        "source_type": "interactive_chat_file",
                        "source_id": self.chat_id,
                    }
                )

        result = self.feedback_service.record_feedback(
            bank_id=self.bank_id,
            canonical_memory_id=memory_id,
            task=self.last_user_input or "interactive wallet task",
            action="Use selected historical memory to answer the user query.",
            context=selected.get("text") or "",
            outcome_type=outcome_type,
            outcome_summary=summary,
            outcome_details=None,
            evidence=evidence_items,
        )

        print("FEEDBACK RESULT")
        print(pretty(result))

        self.conversation_store.add_message(
            chat_id=self.chat_id,
            role="system",
            content=f"Recorded {outcome_type} outcome for memory {memory_id}.",
            message_type="FEEDBACK",
            canonical_memory_id=memory_id,
            metadata=result,
        )

        state = self.learning_service.get_state(memory_id)
        print()
        print("UPDATED LEARNING STATE")
        print(pretty(state))
        print()
        print("UPDATED C5")
        print(pretty(self.closed_loop.decide_behavior(state)))

    def close(self) -> None:
        section("CLEANUP")

        for name, obj in [
            ("MemoryService", self.memory_service),
            ("CanonicalMemoryService", self.canonical_memory_service),
            ("MemoryLearningStateService", self.learning_service),
            ("LearningAwareGroqAgent", self.groq_agent),
            ("LearningRepository", self.repository),
        ]:
            if obj is None:
                continue

            close_method = getattr(obj, "close", None)
            if callable(close_method):
                try:
                    close_method()
                    print(name, "CLOSED")
                except Exception as exc:
                    print(name, "CLOSE ERROR:", exc)

        try:
            self.conversation_store.close()
            print("ConversationStore CLOSED")
        except Exception as exc:
            print("ConversationStore CLOSE ERROR:", exc)


def main() -> None:
    lab = RealChatLab()

    try:
        lab.initialize()
        lab.create_bank()
        lab.seed_memories()

        section("REAL MEMORY-AWARE CHAT READY")

        print("Project:", PROJECT_NAME)
        print("Bank   :", lab.bank_id)
        print("Chat   :", lab.chat_id)
        print()
        print("Try this sequence:")
        print('  1) hello')
        print('  2) What happened with wallet concurrency?')
        print('  3) We discovered that pessimistic locking is the wallet solution.')
        print('  4) What solution did we say was used for the wallet issue?')
        print('  5) thanks')
        print('  6) /evidence')
        print('  7) /newchat')
        print('  8) What solution did we say was used for the wallet issue?')
        print('  9) /memories')
        print(' 10) /history')
        print('')
        print('Memory-aware general tests:')
        print('  ask: do you know about normalization')
        print('  expected: no related wallet memory -> general answer')
        print('  ask: what are locks?')
        print('  expected: related wallet lock memory -> general answer + project context')
        print()
        print("Type /help for all commands. /selftest runs offline routing checks.")

        while True:
            try:
                user_input = input("\nUSER > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            lower = user_input.lower()

            if lower == "/quit":
                break
            if lower == "/selftest":
                section("OFFLINE ROUTING SELF-TEST")
                tests = lab.self_test()
                passed = 0
                for sample, expected, ok in tests:
                    print(
                        f"{sample!r:55} expected={expected:15} "
                        f"{'PASS' if ok else 'FAIL'}"
                    )
                    passed += int(ok)
                print(f"SELF-TEST: {passed}/{len(tests)} PASS")
                continue

            if lower == "/help":
                lab.show_help()
                continue
            if lower == "/project":
                lab.show_project()
                continue
            if lower == "/memories":
                lab.show_memories()
                continue
            if lower == "/history":
                lab.show_history()
                continue
            if lower == "/evidence":
                lab.show_evidence()
                continue
            if lower == "/state":
                lab.show_state()
                continue
            if lower == "/newchat":
                lab.new_chat()
                continue
            if lower.startswith("/remember"):
                parts = user_input.split(maxsplit=1)
                lab.remember(parts[1] if len(parts) == 2 else "")
                continue
            if lower.startswith("/recall"):
                parts = user_input.split(maxsplit=1)
                lab.recall_only(parts[1] if len(parts) == 2 else "")
                continue
            if lower.startswith("/feedback"):
                parts = lower.split(maxsplit=1)
                lab.record_feedback(parts[1] if len(parts) == 2 else "")
                continue

            try:
                lab.handle_user(user_input)
            except Exception as exc:
                print()
                print("REQUEST ERROR:", repr(exc))
                traceback.print_exc()

    finally:
        lab.close()


if __name__ == "__main__":
    main()
