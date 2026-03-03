# Architecture Research — Skill-style Retrieval Agent

**Date:** 2026-02-27
**Scope:** Integrate skill-based retrieval execution into existing MemMachine architecture.

## Current Integration Surface

- Existing orchestration entry:
  - `src/memmachine/retrieval_agent/service_locator.py`
- Existing concrete tools:
  - `src/memmachine/retrieval_agent/agents/tool_select_agent.py`
  - `src/memmachine/retrieval_agent/agents/coq_agent.py`
  - `src/memmachine/retrieval_agent/agents/split_query_agent.py`
  - `src/memmachine/retrieval_agent/agents/memmachine_retriever.py`
- Upstream caller:
  - `src/memmachine/main/memmachine.py` retrieval mode in search path.

## Proposed New Components

- `src/memmachine/retrieval_agent/skills/`
  - `engine/` execution runtime and shared interfaces
  - `specs/` skill markdown definitions and loaders
  - `retrieve_skill.py` top-level orchestration
  - `select_skill.py`, `coq_skill.py`, `split_skill.py`, `fallback_skill.py`
- `src/memmachine/retrieval_agent/skills/types.py`
  - typed contracts for skill request/result/failure

## Data Flow (Target)

1. Query enters retrieval mode.
2. `retrieve-skill` initializes execution context and budget.
3. `select-skill` chooses direct / coq / split.
4. Chosen skill(s) execute and return normalized fragments.
5. Aggregator merges evidence and scores.
6. On any low-confidence/failure/timeout signal, run `fallback-skill` direct search.
7. Return canonical retrieval response structure.

## Build Order (recommended)

1. Define typed skill contracts and execution context.
2. Implement fallback path first (safety baseline).
3. Implement `select-skill` and direct route.
4. Add `coq-skill` parity path.
5. Add `split-skill` and branch aggregation.
6. Wire service locator + remove legacy execution path.
7. Add benchmark runner integration and docs.

## Compatibility Strategy

- Keep old behavior parity tests before hard cutover.
- Remove legacy agent path only after parity + benchmark gate passes.
- Maintain existing API-level response schema.

## Testing Architecture Guidance

- Unit tests for each skill contract and edge handling.
- Integration tests for route sequences and fallback triggers.
- Dataset regression tests for first 100 WikiMultiHop entries.

---
*Architecture focus: new-vs-modified components and safe migration path*
