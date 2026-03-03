---
name: coq
version: v1
kind: sub-skill
description: "Sequential chain-of-query policy for sufficiency checks and next-hop rewriting."
route_name: coq
timeout_seconds: 120
max_return_len: 10000
max_steps: 8
fallback_hook: direct-memory-search
allowed_actions: []
allowed_tools:
  - memmachine_search
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

Execute a full sequential multi-hop retrieval lifecycle for the incoming query.
The incoming `query` is the original user question. CoQ must decompose it
internally, iterate hop-by-hop with `memmachine_search`, and decide sufficiency
using all evidence collected across hops.

## Rules

Follow this mechanism exactly.

### 1. Hard constraints

- Use only retrieved documents for sufficiency decisions.
- Do not use external knowledge or assumptions.
- Do not invent new entities.
- Keep the flow sequential: each next hop depends on current cumulative evidence
  state.

### 2. Working state (must persist across hops)

Maintain:
- `original_query`: incoming `query` string (fixed for full run)
- `used_queries`: ordered list of issued `memmachine_search` queries
- `all_retrieved_documents`: ordered list of all retrieved docs from every hop

Every sufficiency check must use `all_retrieved_documents`, not only the latest
hop.

`evidence_indices` must always reference `all_retrieved_documents` order
(0-based).

### 3. Iterative CoQ loop

For each iteration:
1. Analyze `original_query` and current cumulative evidence.
2. Identify still-missing required facts/hops.
3. Generate exactly one next `sub_query` for the earliest blocking missing hop.
4. Call `memmachine_search` with that `sub_query`.
5. Append returned docs to `all_retrieved_documents`.
6. Re-evaluate sufficiency on the full cumulative evidence.

Stop immediately when sufficient.

### 4. Decompose required information

For `original_query`, identify required components:
- entities
- required attributes (names, dates, locations, numbers, specs)
- required relations and dependency hops
- constraints (timeframe, location, scope, completeness)

### 5. Relevance and evidence scan

A document is relevant only if it explicitly provides a required fact or an
intermediate link in the required dependency chain.

Collect contributing evidence document indices in `evidence_indices`.
If no document contributes required facts/links, return `evidence_indices=[]`.

### 6. Next-best rewritten query objective

Query-generation policy:
- prioritize the earliest blocking hop before later hops.
- First hop query must be derived from `original_query`.
- Later hop queries must be derived from both `original_query` and
  `used_queries`/retrieved evidence.
- Never repeat a previous query after lowercasing and whitespace normalization.
- avoid duplicates of tried rewritten queries after normalization.
- Avoid near-duplicate rewrites with the same intent and missing-fact target.
- Prefer minimal targeted queries for the earliest missing dependency hop.

If no grounded novel query exists, stop and return insufficient with
`reason_code=query_exhausted_no_novel_hop`.

### 7. Strict sufficiency standard

Set `is_sufficient=true` only when all hold:
- all required query components are explicitly supported
- every needed dependency hop is explicitly supported
- required exact details are explicitly present
- completeness requirements (compare/list-all/count/full scope) are satisfiable
  from available evidence

If uncertain, choose `is_sufficient=false`.

### 8. Sufficient case behavior

When `is_sufficient=true`:
- stop searching immediately
- return the final answer directly in assistant text (preferred), or return
  structured success via `return_sub_skill_result`
- if using structured success, set `new_query` to `original_query` exactly and
  return supporting `evidence_indices`

Never issue another `memmachine_search` after sufficiency is reached.

### 9. Insufficient case behavior

When still insufficient:
- continue the loop with a novel next query until step budget is exhausted
- if finishing insufficient, return structured summary via
  `return_sub_skill_result` with the best next query candidate in `new_query`

### 10. Confidence calibration

`confidence_score` reflects confidence in sufficiency judgment only.

Use these anchors:
- `0.90-1.00`: very clear sufficiency/insufficiency
- `0.60-0.89`: moderate clarity, still well-supported
- `0.30-0.59`: low clarity, noisy/partial evidence
- `0.00-0.29`: extremely unclear or unusable evidence

If choosing insufficient due to uncertainty, keep confidence below `0.70`.

### 11. Edge-case handling

- empty/no-relevance evidence -> insufficient, `evidence_indices=[]`, produce the
  most targeted grounded rewrite from original query
- underspecified original query not resolved by evidence -> insufficient
- unreadable evidence -> treat as no evidence

## Tools

- `memmachine_search`: retrieve evidence for each iterative hop query.
- `return_sub_skill_result`: optional structured completion payload, required
  when ending insufficient.

## Output Contract

Preferred sufficient completion:
- return direct final answer text in assistant response (no extra tool call
  required).

Structured completion (for insufficient, or if explicit structured success is
needed):
- return one JSON object as the `summary` value in `return_sub_skill_result`.

`v1` required fields:
- `is_sufficient`: boolean
- `evidence_indices`: array of integer indices (0-based, no negatives)
- `new_query`: single-line string
- `confidence_score`: number in `[0.0, 1.0]`
- `reason_code`: short snake_case code
- `reason_note`: short human-readable note (empty string allowed)

`v1` optional fields:
- `final_query`: string
- `evidence_summary`: short string
- `steps`: integer >= 1
- `used_queries`: array of strings

Fail-closed requirements:
- never return free-form prose in place of JSON
- never emit keys outside the documented contract
- when insufficient and uncertain, keep `is_sufficient=false`
- when sufficient, `new_query` must equal original query exactly
- when sufficient in structured mode, `new_query` must equal `original_query`
  exactly

## Examples

### Example 1: sufficient after cumulative retrieval

Input (conceptual):
- original query: `What prize did the discoverer of penicillin receive?`
- cumulative evidence includes:
  - doc 0: penicillin was discovered by Alexander Fleming
  - doc 3: Alexander Fleming received the Nobel Prize in Physiology or Medicine

Output summary JSON:
`{"is_sufficient":true,"evidence_indices":[0,3],"new_query":"What prize did the discoverer of penicillin receive?","confidence_score":0.95,"reason_code":"sufficient_cumulative_evidence","reason_note":"discoverer identity and prize evidence both present"}`

### Example 2: insufficient missing first dependency hop

Input (conceptual):
- original query: `Who is the spouse of the author of Dune?`
- evidence has no author fact

Output summary JSON:
`{"is_sufficient":false,"evidence_indices":[],"new_query":"Who is the author of Dune?","confidence_score":0.58,"reason_code":"missing_blocking_hop","reason_note":"need author identity before spouse lookup"}`

### Example 3: duplicate rewrite avoided

Input (conceptual):
- tried rewrites include `who is the author of dune?`
- best candidate duplicates that rewrite after normalization

Output summary JSON:
`{"is_sufficient":false,"evidence_indices":[],"new_query":"Identify Dune's author.","confidence_score":0.52,"reason_code":"rewrite_rephrased_for_novelty","reason_note":"avoided duplicate tried query"}`

### Example 4: no novel grounded next hop

Input (conceptual):
- no grounded query remains beyond previously used rewrites

Output summary JSON:
`{"is_sufficient":false,"evidence_indices":[1],"new_query":"<original query>","confidence_score":0.34,"reason_code":"query_exhausted_no_novel_hop","reason_note":"all grounded rewrites already tried"}`

## Failure Modes

- Never use external world knowledge to fill missing facts.
- Never invent entities not present in original query/evidence.
- Never return `is_sufficient=true` under uncertainty.
- Never emit invalid evidence indices.
- Never reset sufficiency judgment to only the latest hop's evidence.
- Never issue duplicate `memmachine_search` queries in the same CoQ run.
