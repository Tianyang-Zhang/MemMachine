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
3. Treat selector summary as strict contract:
   - `selected_skill`: `direct_memory` | `coq` | `split`
   - `selected_route`: `direct_memory` | `decompose`
   - `confidence_score`, `reason_code`, optional `reason_note`
4. Pass-through behavior:
   - For straightforward/non-multi-hop queries, direct memory search is valid
     and preferred.
5. Safety behavior:
   - If selector output is malformed, runtime retries selector once.
   - If selector stays malformed after retry, runtime falls back to direct
     memory.
   - If selector confidence is low, runtime falls back to direct memory.
6. Decomposition behavior:
   - Use `coq` for sequential multi-hop decomposition.
   - Use `split` for branch decomposition.
   - `split` branches may require `coq` at branch level.
7. Avoid repeated identical actions unless previous attempt clearly failed.
8. Finalize only when evidence is sufficient or fallback guardrails require safe
   termination.

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
2. One or more sub-skill runs provide sufficient merged evidence, or
3. Runtime guardrails trigger explicit fallback completion.

Top-level must remain the final decision authority.
