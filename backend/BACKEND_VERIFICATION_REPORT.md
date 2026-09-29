# Project Memory Agent — Verification Report

Date: 2026-09-29

## Verification result

The web integration was repaired without replacing the existing Hindsight/C1–C6 architecture. The working package preserves project-scoped memory, evidence provenance, learning state, and the existing runtime services.

Deterministic backend suite:

```text
25 passed
```

Backend compilation:

```text
python -m compileall -q app tests scripts
PASS
```

Frontend static TS/TSX pass in the repair environment:

```text
TypeScript no-check/no-emit parse pass
PASS
```

A full `npm run build` was not executed because the uploaded environment had an empty/incomplete `node_modules` directory and external npm registry access was unavailable. `npm ci` could not retrieve packages in that environment. The package therefore does not claim a full production React/Vite build was completed here.

## Functional regressions fixed

### Memory retrieval

Project-history queries no longer depend only on lexical overlap. For broad/anaphoric history questions, Hindsight retrieval similarity is treated as the primary relevance signal and lexical overlap remains an additional signal.

This fixes the concrete flow:

```text
my frontend got crashed
        -> stored as project memory
what was my problem before
        -> semantic retrieval finds that memory
```

### Intent routing

Added domain-neutral recognition for memory-inventory questions and stronger fallback handling for direct bug/problem statements. A semantic router result that incorrectly downgrades a real question to CHAT is guarded by deterministic question detection.

### Evidence

The original binary evidence remains stored in the file/evidence repository. Only semantic evidence text enters Hindsight. The API intentionally retains both `attachments` and `source_evidence` because they serve different contracts; the frontend merges them by evidence ID so the same uploaded artifact renders once.

Stored images use `/api/v1/evidence/{evidence_id}/content` for the actual image preview and lightbox instead of showing only the filename.

### Markdown

Assistant messages are now rendered through the local `MarkdownContent` component so common Markdown from Groq is presented as formatted text rather than raw `**...**` markers.

### Memory ON/OFF

Memory OFF uses the normal-chat path and does not retain or recall through Hindsight. The current user prompt is excluded from the persisted history passed to the normal-chat call, preventing accidental duplication of the current request.

Memory state is carried in assistant metadata and is therefore rendered consistently after refresh.

### Learning state / trace

The API response schema now preserves `learning_state`, and memory update evidence includes the current learning state when a canonical memory is available. The UI surfaces source evidence, understanding, and learning/experience information separately.

### Right sidebar

The right sidebar reads verified project memories from the project memory endpoint, clearly labels Memory ON/OFF, and refreshes after successful sends so new project memory appears without a manual reload.

## Tests covered

The deterministic suite includes project/chats, project isolation, memory toggle behavior, memory retrieval, general-query memory awareness, evidence upload/attachment/content retrieval, response-trace persistence, memory inventory, empty-input handling, and other existing C1–C6 regression coverage.

A dedicated regression file covers the exact previously failing history query, memory inventory, related general question, learning-state response contract, duplicate evidence representations at the API boundary, and empty/evidence-only requests.

## Security

Provider credentials are environment-driven in `backend/app/core/config.py`. No live Groq or Hindsight key is included in this package.
