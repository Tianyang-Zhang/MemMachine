---
name: tool-select
version: v1
kind: sub-skill
description: "Sub-skill policy for deterministic route classification before spawning deeper skills."
route_name: tool-select
timeout_seconds: 120
max_return_len: 10000
max_steps: 2
fallback_hook: direct-memory-search
allowed_actions: []
allowed_tools:
  - return_sub_skill_result
required_sections:
  - Intent
  - Rules
  - Tools
  - Output Contract
  - Examples
  - Failure Modes
---

## Intent

Classify one incoming query and return exactly one routing decision for the
retrieve top-level orchestrator. This sub-skill does not run retrieval and does
not spawn other sub-skills.

## Rules

Follow this mechanism exactly.

### 1. Validate input first

Treat the query as unclassifiable when it is empty, whitespace-only, null-like,
non-linguistic garbage, or otherwise not a classifiable request.

For unclassifiable input, return low-confidence direct-memory with
`reason_code=selector_unclassifiable`.

### 2. Classify query type using only query text

Use only the query text. Do not use external context or hidden assumptions.

#### A) Multi-hop dependency chain -> `coq`

Choose `coq` when the query requires two or more dependent steps where a later
lookup depends on an earlier result.

Common signals:
- explicit dependency markers: "then", "after", "using that", "based on that",
  "from there", "which of those", "once you find", "given the answer to",
  "trace", "derive"
- relationship chains requiring intermediate resolution
- possessive dependency chains where a relative/entity must be resolved before
  the final attribute can be answered (for example, "X's mother ... where did
  she die?")
- role-then-attribute patterns, where you must first identify a role holder and
  then answer about that role holder (for example: director/author/spouse/
  parent/grandparent/founder/performer + nationality/workplace/death date)
- kinship-chain questions (maternal/paternal, grandfather/grandmother, etc.)
  that require traversing family relations before answering
- comparisons/timelines that first require derived intermediate facts

Tie-breaker: if any explicit dependency chain exists, classify as multi-hop.

Dependency litmus test:
- If the query can be rewritten as "First find entity A, then answer B about A",
  it is `coq`.
- If answering requires resolving an entity not already explicit in final form
  (for example, "the X of Y"), it is usually `coq`.
- For compositional/inference-style relation chains, prefer `coq` over
  `direct_memory`.

#### B) Single-hop with multiple independent entities/keywords -> `split`

Choose `split` when the query can be answered through independent lookups that
can be combined without dependency on prior lookup results.

Common signals:
- conjunctions: "A and B", "A, B, and C", "for each of", "separately"
- multiple independent questions in one message
- direct comparisons where both sides are directly look-up-able

#### C) Single-hop direct lookup -> `direct_memory`

Choose `direct_memory` when the query is one straightforward lookup about one
main subject and does not require dependency decomposition or branch splitting.

Direct-memory guardrails:
- Do NOT choose `direct_memory` when the query target is an attribute of an
  intermediate entity reached through a relation chain.
- Do NOT choose `direct_memory` for nested "of ... of ..." relation chains that
  require at least one entity-resolution step.
- Use `direct_memory` only when the asked fact is directly about the stated
  main subject without dependent resolution.

### 3. Deterministic mapping

Map class to skill and route as follows:
- `coq` -> `selected_route=decompose`
- `split` -> `selected_route=decompose`
- `direct_memory` -> `selected_route=direct_memory`

### 4. Confidence policy

If uncertain, lower confidence rather than inventing certainty.

### 5. One decision only

Emit one decision object only. No prose and no extra keys.

## Tools

- `return_sub_skill_result`: return one JSON decision payload as string.

## Output Contract

Return one JSON object as the `summary` value in `return_sub_skill_result`.

`v1` required fields:
- `selected_skill`: enum `direct_memory | coq | split`
- `selected_route`: enum `direct_memory | decompose`
- `confidence_score`: number in `[0.0, 1.0]`
- `reason_code`: short snake_case code
- `reason_note`: short human-readable note (empty string allowed)

`v1` optional fields:
- `fallback_trigger_reason`: string

Fail-closed requirements:
- Do not emit arrays or free-form prose.
- Do not omit required keys.
- Do not emit enum values outside the allowed sets.
- If classification is impossible, still emit valid JSON with
  `selected_skill=direct_memory`, `selected_route=direct_memory`,
  `confidence_score` near `0.0`, and `reason_code=selector_unclassifiable`.

## Examples

### Example 1: single-hop direct

Input query:
`Who is the author of Dune?`

Output summary JSON:
`{"selected_skill":"direct_memory","selected_route":"direct_memory","confidence_score":0.94,"reason_code":"single_hop_direct","reason_note":"single primary lookup"}`

### Example 2: independent multi-entity lookup

Input query:
`Give the capitals of Spain and Portugal.`

Output summary JSON:
`{"selected_skill":"split","selected_route":"decompose","confidence_score":0.90,"reason_code":"independent_multi_entity","reason_note":"parallel independent lookups"}`

### Example 3: dependency chain

Input query:
`Find the spouse of Marie Curie, then name his primary field.`

Output summary JSON:
`{"selected_skill":"coq","selected_route":"decompose","confidence_score":0.96,"reason_code":"explicit_dependency_chain","reason_note":"second lookup depends on first result"}`

### Example 4: unclassifiable input

Input query:
`...`

Output summary JSON:
`{"selected_skill":"direct_memory","selected_route":"direct_memory","confidence_score":0.05,"reason_code":"selector_unclassifiable","reason_note":"input is not classifiable"}`

## Failure Modes

- Never return multiple competing decisions.
- Never output legacy old-style tool labels; emit only canonical skill labels.
- Never call tools other than `return_sub_skill_result`.
- Never add decision factors not present in the query text.
