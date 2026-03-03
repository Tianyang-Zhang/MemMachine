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
2. Start by spawning `tool_select` unless direct memory search is already
   clearly sufficient.
3. Run `tool_select` once per top-level query unless runtime explicitly asks
   for one retry after a malformed selector summary.
4. Treat selector summary as strict contract:
   - `selected_skill`: `direct_memory` | `coq` | `split`
   - `selected_route`: `direct_memory` | `decompose`
   - `confidence_score`, `reason_code`, optional `reason_note`
5. CoQ handoff contract:
   - If selector chooses `coq`, spawn `coq` with the original top-level query
     text exactly.
   - Do not pass pre-decomposed planner text (for example, no
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
   - If selector output is malformed, runtime retries selector once.
   - If selector stays malformed after retry, runtime falls back to direct
     memory.
   - If selector confidence is low, runtime falls back to direct memory.
8. Decomposition behavior:
   - Use `coq` for sequential multi-hop decomposition.
   - Use `split` for branch decomposition.
   - After `split` emits branch queries, route each branch through
     `tool_select` before execution.
   - Branches classified as `coq` should execute with `coq`; branches classified
     as `direct_memory` should execute with direct memory.
   - If a `coq` run ends with `is_sufficient=false` and a non-empty actionable
     `new_query`, run one targeted `direct_memory_search` using that `new_query`
     before finalizing (unless an equivalent query was already attempted).
   - Prefer this targeted follow-up when CoQ already resolved intermediate
     entities but is missing final asked-attribute evidence.
9. Avoid repeated identical actions unless previous attempt clearly failed.
10. Finalize only when evidence is sufficient or fallback guardrails require safe
    termination.
11. Noise-control finalization rule:
    - Do not finalize on identity-link evidence alone.
    - Before `return_final`, ensure merged evidence includes at least one snippet
    aligned to the asked target attribute type (for example birth/death place,
    employer organization, award name, kinship target person).
12. CoQ answer handoff rule:
    - When CoQ returns `is_sufficient=true`, do not answer with uncertainty
      language (for example "I don't know") unless you also cite an explicit
      contradiction in merged evidence.
    - Prefer answering with the CoQ `answer_candidate` when present.
13. LLM-driven sufficiency decision:
    - Top-level LLM owns the final sufficiency judgment using merged episodes,
      sub-skill summaries, and tool-call traces.
    - If still insufficient, identify missing evidence, form a new sub-query
      (or retry original query), and choose another tool call to continue.
    - Python runtime should enforce contracts/limits, not semantic sufficiency.

## Actions

Use only these actions:

- `spawn_sub_skill`: run one named sub-skill with query context.
- `direct_memory_search`: run top-level MemMachine search.
- `return_final`: finish with final response rationale.

Recommended first sub-skill: `tool_select`.
Valid decomposition sub-skills: `coq`, `split`.

## Completion

Complete when:

1. Direct memory search is sufficient, or
2. One or more sub-skill runs provide sufficient merged evidence (including a
   targeted direct-memory follow-up when CoQ returns insufficient with an
   actionable `new_query`), or
3. Hop/branch budget is exhausted and runtime guardrails require safe
   completion/fallback.

Top-level must remain the final decision authority.
