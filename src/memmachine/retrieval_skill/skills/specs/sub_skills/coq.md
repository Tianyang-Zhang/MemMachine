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

Execute sequential multi-hop retrieval decisions for one query lifecycle.
At each step, judge evidence sufficiency for the original query. If evidence is
insufficient, generate the next best grounded rewritten query for the missing
fact. If sufficient, finalize.

## Rules

Follow this mechanism exactly.

### 1. Hard constraints

- Use only retrieved documents for sufficiency decisions.
- Do not use external knowledge or assumptions.
- Do not invent new entities.
- Keep the flow sequential: each next hop depends on current evidence state.

### 2. Input normalization

Internally treat inputs as:
- original query string
- used rewritten queries list (possibly empty)
- ordered retrieved documents list (possibly empty)

`evidence_indices` must always reference the retrieved document order
(0-based).

### 3. Decompose required information

For the original query, identify required components:
- entities
- required attributes (names, dates, locations, numbers, specs)
- required relations and dependency hops
- constraints (timeframe, location, scope, completeness)

### 4. Relevance and evidence scan

A document is relevant only if it explicitly provides a required fact or an
intermediate link in the required dependency chain.

Collect contributing evidence document indices in `evidence_indices`.
If no document contributes required facts/links, return `evidence_indices=[]`.

### 5. Strict sufficiency standard

Set `is_sufficient=true` only when all conditions hold:
- all required query components are explicitly supported
- every needed dependency hop is explicitly supported
- required exact details are explicitly present
- completeness requirements (compare/list-all/count/full scope) are satisfiable
  from available evidence

If uncertain, choose `is_sufficient=false`.

### 6. Next-best rewritten query objective

Only when `is_sufficient=false`, generate one single-line `new_query` that
maximizes retrieval of missing evidence with this priority order:
1. earliest blocking hop
2. highest specificity grounded in known entities/terms
3. minimality (ask only for missing fact/link)
4. novelty versus tried rewritten queries

Rewritten query rules:
- use only entities from original query and retrieved evidence
- avoid duplicates of tried rewritten queries after lowercasing and whitespace
  normalization
- if best candidate is duplicate, rephrase with same intent and specificity
- if no grounded better rewrite exists, set `new_query` to original query

### 7. Sufficient case behavior

When `is_sufficient=true`:
- stop rewriting
- set `new_query` to original query exactly
- return evidence indices supporting sufficiency

### 8. Confidence calibration

`confidence_score` reflects confidence in sufficiency judgment only.

Use these anchors:
- `0.90-1.00`: very clear sufficiency/insufficiency
- `0.60-0.89`: moderate clarity, still well-supported
- `0.30-0.59`: low clarity, noisy/partial evidence
- `0.00-0.29`: extremely unclear or unusable evidence

If choosing insufficient due to uncertainty, keep confidence below `0.70`.

### 9. Edge-case handling

- empty/no-relevance evidence -> insufficient, `evidence_indices=[]`, produce the
  most targeted grounded rewrite from original query
- underspecified original query not resolved by evidence -> insufficient
- unreadable evidence -> treat as no evidence

## Tools

- `memmachine_search`: retrieve evidence for the current hop query.
- `return_sub_skill_result`: return one final JSON summary payload.

## Output Contract

Return one JSON object as the `summary` value in `return_sub_skill_result`.

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

Fail-closed requirements:
- never return free-form prose in place of JSON
- never emit keys outside the documented contract
- when insufficient and uncertain, keep `is_sufficient=false`
- when sufficient, `new_query` must equal original query exactly

## Examples

### Example 1: sufficient after retrieval

Input (conceptual):
- original query: `Who wrote Dune?`
- evidence contains explicit author fact in doc index 0

Output summary JSON:
`{"is_sufficient":true,"evidence_indices":[0],"new_query":"Who wrote Dune?","confidence_score":0.97,"reason_code":"sufficient_explicit_fact","reason_note":"author is explicit"}`

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

### Example 4: insufficient due to ambiguity

Input (conceptual):
- original query ambiguous and evidence does not disambiguate

Output summary JSON:
`{"is_sufficient":false,"evidence_indices":[],"new_query":"<original query>","confidence_score":0.25,"reason_code":"underspecified_query","reason_note":"evidence cannot resolve ambiguity"}`

## Failure Modes

- Never use external world knowledge to fill missing facts.
- Never invent entities not present in original query/evidence.
- Never return `is_sufficient=true` under uncertainty.
- Never emit invalid evidence indices.
