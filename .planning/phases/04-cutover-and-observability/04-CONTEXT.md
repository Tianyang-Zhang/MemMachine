# Phase 04: Cutover and Observability - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning/execution

## Phase Boundary

Finalize migration cutover by removing legacy top-level route wiring and expose
retrieval orchestration traces in API responses while preserving compatibility.

## Locked Decisions

- `create_retrieval_agent(...)` must always return `RetrieveSkill` entrypoint.
- Legacy top-level selector text aliases are no longer accepted in route parser.
- API search response can add optional trace field (non-breaking) gated by
  `response_model_exclude_none=True`.
