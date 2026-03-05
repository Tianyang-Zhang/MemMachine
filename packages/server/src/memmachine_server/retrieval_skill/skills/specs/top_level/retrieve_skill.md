---
name: retrieve-skill
version: v1
kind: top-level
description: "Single markdown policy for decomposition-driven MemMachine retrieval."
route_name: retrieve-skill
timeout_seconds: 180
max_return_len: 10000
max_steps: 8
fallback_hook: memmachine-search
allowed_actions:
  - memmachine_search
  - return_final
allowed_tools:
  - memmachine_search
  - return_final
required_sections:
  - Intent
  - Rules
  - Actions
  - Completion
---

## Intent

Execute a full retrieval lifecycle for one user query.

You must decide:
1. whether MemMachine search is needed,
2. how to decompose complex queries into iterative hops,
3. which query to issue at each hop,
4. when evidence is sufficient to finalize.

Goal: return the best evidence episodes for answering the query, then finish with
`return_final`.

## Rules

Follow this mechanism exactly.

### 1. Hard constraints

- Use only retrieved evidence for sufficiency decisions.
- Do not use external knowledge or assumptions when deciding sufficiency.
- Do not invent new entities.
- Keep the flow sequential for dependency chains: each next hop must target the
  earliest blocking missing fact.
- Optimize for retrieval quality and evidence completeness before finalization.

### 2. Working state (persist across hops)

Maintain internally:
- `original_query`: fixed incoming query.
- `used_queries`: ordered list of issued `memmachine_search` queries.
- `all_retrieved_documents`: cumulative evidence across all hops.
- `answer_candidate`: shortest explicit answer span currently supported.
- `related_episode_indices`: evidence related to the query.
- `selected_episode_indices`: evidence judged most supportive.

Every sufficiency check must use cumulative evidence, not only the latest hop.

`related_episode_indices` and `selected_episode_indices` should reference the
cumulative evidence order (0-based) after all hops.

Maintain an internal hop table for reasoning quality:
- hop id,
- resolved entity/relation target,
- earliest blocking missing fact,
- candidate answer value (if any),
- supporting evidence indices,
- conflicting candidate values (if any).

### 3. MemMachine strengths and limits

MemMachine strengths (high precision):
- single-hop factual lookups with explicit anchors,
- memory-grounded conversational facts with clear wording,
- retrieval aligned to episode fields:
  - `content`, `created_at`, `producer_id`, `producer_role`,
    `produced_for_id`, `episode_type`, `metadata`, `filterable_metadata`.

MemMachine limitations (lower reliability):
- one-shot multi-hop relation chains in a single query,
- implicit aggregation/comparison without explicit evidence,
- ambiguous pronouns and missing entities,
- long overloaded queries with many constraints.

### 4. Iterative decomposition loop

For each iteration:
1. Analyze `original_query` with cumulative evidence.
2. Identify missing required facts/hops.
3. Generate exactly one next query for the earliest blocking hop.
4. Call `memmachine_search`.
5. Append results to cumulative evidence.
6. Re-evaluate sufficiency on all evidence.
7. Update `answer_candidate` only when evidence explicitly states the target.

Stop immediately when sufficient.

Never skip the earliest blocking hop. If final asked attribute is unresolved,
next query must target that unresolved dependency chain, not a side fact.

Step budget guardrail:
- Keep total `memmachine_search` calls <= 7.
- Reserve the final call for the unresolved final asked attribute (not side hops).
- If unresolved near budget end, spend the last call on one grounded lexical/alias
  variant for the final asked attribute before finalizing with best-supported
  answer/proxy.

Before finalizing, verify final-hop coverage:
- At least one issued query must target the final asked attribute.
- Do not finalize on identity-link evidence alone if final asked attribute is
  still missing.

Decomposition patterns by question type:
- `comparison`: resolve target attribute for entity A and entity B separately,
  then compare.
- `bridge_comparison`: resolve bridge entities first, then resolve compared
  attributes for both sides, then compare.
- `compositional`: resolve relation chain in order; final hop must target the
  asked attribute.
- `inference`: retrieve all required supporting facts before concluding.

### 5. Decompose required information

For the original query, identify:
- entities,
- required attributes (names, dates, locations, organizations, numbers),
- required relations and dependency hops,
- constraints (time, location, scope, completeness).

A document is relevant only if it supports a required fact or dependency link.

### 6. Relevance and evidence scan

Only treat a document as relevant if it explicitly provides:
- a required final target fact, or
- an intermediate dependency link required to reach that target.

Ignore documents that are topically related but do not advance the dependency
chain needed by `original_query`.

### 7. Query rewrite policy (next-best query)

- Prioritize earliest blocking hop before later hops.
- First hop must come directly from `original_query`.
- Later hops must use `original_query` + cumulative evidence.
- Never repeat a previous query after lowercasing and whitespace normalization.
- Avoid duplicate rewrites after punctuation/spacing-only changes.
- Avoid near-duplicate rewrites with the same missing-fact target.
- Prefer minimal targeted queries.
- For later hops, include both:
  - resolved entity from prior hops,
  - stable anchor from original query (for example film/work/person title).
- Include disambiguating appositives when available.
- Before declaring exhaustion, try at least one grounded lexical variant for the
  final asked attribute.
- For ambiguous names, include context appositive from original query:
  - e.g. `Arshad Khan director of Daadagiri nationality`.

Before each `memmachine_search` call, check:
1. query targets the earliest unresolved blocking fact,
2. query is novel after normalization,
3. query preserves original anchor context for later hops.

Relation-focused templates (adapt):
- birthplace: `Where was [entity] born?`
- death place: `Where did [entity] die?`
- workplace/employer: `Where does [entity] work?`
- awards: `What award did [entity] win?`
- kinship chain: `Who was [entity]'s mother/father?`

Final-target lexical variants (use at most one grounded variant when needed):
- birthplace: `place of birth`, `born in`
- death place: `place of death`, `died in`, `died at`
- nationality/country: `nationality`, `country of citizenship`
- employer/workplace: `employer`, `organization worked for`
- for names with diacritics or transliteration variance, try one normalized alias
  form in the final-target hop (for example `Greville` vs `Gréville`).

If no grounded novel query exists, finalize as insufficient.

### 8. Strict sufficiency standard

Set `is_sufficient=true` only when all hold:
- all required query components are explicitly supported,
- every needed dependency hop is explicitly supported,
- required exact details are explicitly present,
- completeness requirements (compare/list/count/full scope) are satisfied by
  retrieved evidence,
- final-hop evidence is present,
- candidate answer type matches asked target type,
- an explicit `answer_candidate` is present,
- no unresolved conflict exists for the same asked target.

When sufficient, normalize a single canonical `answer_candidate` string:
- person/place/organization/date/year questions: one explicit value,
- comparison questions: one side/entity only (not both descriptions),
- yes/no questions: exactly `yes` or `no`.

Answer-type guardrails:
- if asked for `country`, city/organization evidence is not sufficient,
- if asked for `organization`/workplace, nationality-only evidence is not
  sufficient,
- if asked for year/date, explicit temporal value is required,
- if asked for person/kinship, explicit person entity is required,
- if asked for workplace, return organization/entity name, not location only,
- if asked for "work at", prefer explicit employer/organization over role title,
- if multiple plausible same-name entities exist, issue disambiguating query
  anchored by original query context.

If uncertain, keep `is_sufficient=false`.

Controlled best-supported fallback (last resort, low confidence):
- If exact asked attribute is missing after grounded attempts, but one dominant
  proxy value is explicitly supported for the resolved entity and no competing
  proxy is equally strong, you may finalize with that proxy value.
- Mark this with lower confidence (`<=0.69`) and explicit reason note that this
  is a best-supported proxy.
- Proxy priority examples:
  - location questions (`birthplace`, `place of death`, `where`): strongest
    explicit location tied to the resolved entity in canonical bio context.
  - workplace questions: explicit organization affiliation, including
    publication/institution roles (for example wrote for, served at, president
    of, commissioner of).
  - country/nationality questions: explicit nationality/citizenship/demonym
    tied to the resolved-name entity when direct country wording is absent.

Do not use proxy fallback when multiple competing values remain unresolved.

### 9. Sufficient and insufficient behavior

When sufficient:
- stop searching immediately,
- finalize with `return_final`,
- set `final_response` to begin with the canonical `answer_candidate`,
- ensure `reason_note` explicitly contains the exact `answer_candidate` value,
- include supporting evidence indices,
- include concise reason fields.

Sufficient response constraints:
- do not ask clarifying questions,
- do not answer with "I don't know",
- avoid multi-candidate hedging unless query explicitly asks for multiple values.
- for yes/no questions, output exactly `yes` or `no` first before explanation.

When insufficient:
- continue with a novel next query until hop budget is exhausted,
- if still insufficient at end, finalize with `is_sufficient=false` and include
  best next-hop rationale in reason fields.
- do not emit speculative answer values as if final.

### 10. Confidence calibration

`confidence_score` reflects confidence in sufficiency judgment:
- `0.90-1.00`: very clear
- `0.60-0.89`: moderate clarity
- `0.30-0.59`: low clarity
- `0.00-0.29`: very unclear

If insufficient due to uncertainty, keep confidence below `0.70`.

### 11. Edge-case handling

- Empty/no-relevance evidence: keep `is_sufficient=false` and issue the most
  targeted grounded rewrite.
- Underspecified query not resolved by evidence: keep insufficient and use best
  grounded next hop.
- Conflicting values for final target: issue disambiguating query before
  sufficiency.

### 12. Finalization policy

Use `return_final` only when:
- sufficient evidence exists, or
- best-effort retrieval is exhausted by budget and no grounded novel hop exists.

## Actions

Use only these actions:
- `memmachine_search`: retrieve evidence for each iterative hop query.
- `return_final`: finish orchestration with sufficiency metadata.

### return_final Payload Guidance

Provide these fields whenever possible:
- `final_response`: one concise answer-first statement
- `is_sufficient`: boolean
- `confidence_score`: number in `[0.0, 1.0]`
- `reason_code`: short snake_case code
- `reason_note`: short explanation that includes the exact answer value when
  sufficient
- `related_episode_indices`: optional list of related evidence indices
- `selected_episode_indices`: optional list of selected evidence indices

## Completion

Complete when:
1. all required facts are explicitly supported and sufficiency is true, or
2. no grounded novel next hop exists within step/time budget and sufficiency is
   false.

At completion, call `return_final`.
