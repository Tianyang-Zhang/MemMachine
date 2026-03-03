# Phase 3: Decomposition Skills - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement decomposition sub-skills (`coq`, `split`) under the existing
top-level retrieve-skill orchestration runtime, while preserving the single
top-level session model and explicit fallback safety behavior.

This phase adds decomposition behavior and aggregation contracts, not legacy
agent cutover/removal.

</domain>

<decisions>
## Implementation Decisions

### Top-level entry policy and pass-through
- Top-level orchestration starts with `tool_select` sub-skill for route/skill
  intent classification.
- Add explicit `pass-through` behavior: if query is simple/non-multi-hop,
  top-level may skip deeper decomposition and directly run MemMachine search.
- If selector output is malformed/unparseable, retry selector once; if still
  malformed, force direct-memory fallback.
- If selector confidence is low, force direct-memory fallback.
- Top-level can re-route multiple times as needed, but remains bounded by
  existing guardrails (`max_steps`, hop/branch limits, global/sub-skill
  timeout).

### Prompt parity with legacy retrieval agents
- Translate and preserve behavior from legacy prompts into markdown skill files:
  - `TOOL_SELECT_PROMPT` -> `tool_select.md`
  - `COMBINED_SUFFICIENCY_AND_REWRITE_PROMPT` -> `coq.md`
  - `SPLIT_QUERY_PROMPT` -> `split.md`
- Skill markdown should be the primary place for workflow/policy evolution in
  future iterations.

### `coq` sub-skill behavior
- `coq` execution is always sequential.
- Query rewrite/sufficiency logic must follow the combined prompt behavior.
- `coq` may call MemMachine search each hop and should return structured summary
  plus collected evidence to top-level.

### `split` sub-skill behavior
- `split` generates branch queries using split prompt behavior.
- Split branches execute in parallel with dynamic branch count and hard cap of
  `5`.
- Each split branch may execute direct memory retrieval or route through `coq`
  if branch query is multi-hop.
- Branch retry policy: one retry on failure, then fail branch.
- Completion threshold: all branches must succeed; otherwise top-level applies
  fallback behavior.

### Aggregation and ranking contract
- Top-level LLM returns complete outputs from all spawned sub-skills.
- Python runtime performs final rerank against the original user query after
  top-level aggregation.
- Dedup uses episode UID only.
- Conflict-resolution policy for contradictory evidence is deferred.

### Trace and state expectations
- Top-level skill remains active for entire lifecycle and owns full state across
  all sub-skills/sub-agents.
- Persist full sub-skill transcript metadata: tool calls, arguments, outputs,
  retries, and status.
- Persist per-branch retry counts and reason codes.
- Final metrics should include branch counts (total/success/failure/retry) and
  `rerank_applied`.

### Claude's Discretion
- Exact output schema naming for selector/sub-skill summary payloads as long as
  they remain strict and machine-parseable.
- Exact branch scheduling strategy under cap=5.
- Trace payload field layout, provided all required telemetry is present.

</decisions>

<specifics>
## Specific Ideas

- Keep top-level runtime as the control plane: it decides which sub-skill to
  spawn next and when to terminate.
- Keep decomposition policy in markdown specs so behavior can be tuned without
  Python control-flow rewrites.
- Ensure final rerank is done once at top-level aggregation to align output with
  the original query intent.

</specifics>

<deferred>
## Deferred Ideas

- Conflict-resolution logic for contradictory branch evidence.
- Advanced rank fusion beyond one top-level rerank pass.

</deferred>

---

*Phase: 03-decomposition-skills*
*Context gathered: 2026-02-28*
