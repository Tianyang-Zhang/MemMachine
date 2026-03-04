---
name: retrieve-skill
version: v1
kind: top-level
description: "Top-level orchestrator policy for markdown-guided retrieval skill flow."
route_name: retrieve-skill
timeout_seconds: 180
max_return_len: 10000
max_steps: 8
fallback_hook: direct-memory-search
allowed_actions:
  - spawn_sub_skill
  - direct_memory_search
  - return_final
allowed_tools:
  - spawn_sub_skill
  - direct_memory_search
  - return_final
required_sections:
  - Intent
  - Rules
  - Actions
  - Completion
---

## Intent

Act as the top-level retrieval orchestrator. Keep full state ownership for the
entire query lifecycle, including all sub-skill outputs and direct memory
searches.

## Rules

1. Maintain one global orchestrator state through completion.
2. Route-selection ownership is top-level policy:
   - choose one initial execution skill directly:
     `direct_memory`, `coq`, or `split`
   - do not spawn `tool_select` as a sub-skill
3. Route selection heuristics:
   - use `coq` when query requires dependent multi-hop resolution
   - use `split` when query has independent branches that can be answered in
     parallel
   - use `direct_memory` for straightforward single-hop lookup
4. Parent decision independence rule:
   - Child `is_sufficient` signals are useful for logging and debugging.
   - Top-level must still compute its own sufficiency from merged evidence and
     traces.
   - Do not treat child sufficiency booleans as authoritative truth.
5. CoQ handoff contract:
   - Spawn `coq` with a concrete question query (original query or a targeted
     branch follow-up).
   - Do not pass raw planner boilerplate text (for example,
     `Decompose: 1)... 2)...` payloads).
   - `coq` owns decomposition, hop planning, and sufficiency decisions.
   - Read CoQ `summary` JSON from sub-skill output and use it to drive
     follow-up retrieval actions.
   - If CoQ summary has `is_sufficient=true` and non-empty `answer_candidate`,
     treat `answer_candidate` as the primary answer unless contradicted by a
     stronger, explicitly anchored snippet in merged evidence.
6. Pass-through behavior:
   - For straightforward/non-multi-hop queries, direct memory search is valid
     and preferred.
7. Safety behavior:
   - Runtime enforces contract validity, hop/branch limits, and fallback.
   - If any sub-skill output is malformed or execution fails, runtime can fall
     back to direct memory.
8. Decomposition behavior:
   - Use `coq` for sequential multi-hop decomposition.
   - Use `split` for branch decomposition.
   - After `split` emits branch queries, top-level must choose each branch
     execution skill directly (`coq` or `direct_memory`).
   - Do not recurse `split` for split-branch execution.
   - If a `coq` run ends with `is_sufficient=false` and a non-empty actionable
     `new_query`, run one targeted `direct_memory_search` using that `new_query`
     before finalizing (unless an equivalent query was already attempted).
9. LLM-led filtering semantics:
   - When insufficient, examine all available episodes and identify those
     related to answering the original query.
   - `selected_episode_indices` is optional metadata for trace/evaluation only.
   - Keep return-all behavior: runtime returns merged evidence up to configured
     query limit after rerank; do not rely on selected indices for pruning.
10. Sufficient high-confidence evidence selection:
   - When `is_sufficient=true`, include clear supporting evidence indices when
     available (`selected_episode_indices`).
   - If selection is empty, still return a valid final payload.
11. Avoid repeated identical actions unless previous attempt clearly failed.
12. Finalize only when evidence is sufficient or fallback guardrails require
    safe termination.
13. Noise-control finalization rule:
    - Do not finalize on identity-link evidence alone.
    - Before `return_final`, ensure merged evidence includes at least one
      snippet aligned to the asked target attribute type.
14. CoQ answer handoff rule:
    - When CoQ returns `is_sufficient=true`, do not answer with uncertainty
      language (for example "I don't know") unless you also cite an explicit
      contradiction in merged evidence.
    - Prefer answering with the CoQ `answer_candidate` when present.
15. LLM-driven sufficiency decision:
    - Top-level LLM owns the final sufficiency judgment using merged episodes,
      sub-skill summaries, and tool-call traces.
    - If still insufficient, identify missing evidence, form a new sub-query
      (or retry original query), and choose another tool call to continue.
    - Python runtime should enforce contracts/limits, not semantic sufficiency.

## Actions

Use only these actions:

- `spawn_sub_skill`: run one named sub-skill with query context.
- `direct_memory_search`: run top-level MemMachine search.
- `return_final`: finish with final response rationale and sufficiency fields.

Preferred first action: choose one of `direct_memory`, `coq`, or `split`
directly from query text and current state.
Valid decomposition sub-skills: `coq`, `split`.

### return_final Payload Guidance

Provide these fields whenever possible:
- `is_sufficient`: boolean
- `confidence_score`: number in `[0.0, 1.0]`
- `reason_code`: short snake_case code
- `reason_note`: short explanation
- `related_episode_indices`: optional list of related evidence indices
- `selected_episode_indices`: optional list of selected evidence indices

## Completion

Complete when:

1. Direct memory search is sufficient, or
2. One or more sub-skill runs provide sufficient merged evidence (including a
   targeted direct-memory follow-up when CoQ returns insufficient with an
   actionable `new_query`), or
3. Hop/branch budget is exhausted and runtime guardrails require safe
   completion/fallback.

Top-level must remain the final decision authority.
