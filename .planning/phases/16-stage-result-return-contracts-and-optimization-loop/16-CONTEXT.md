# Phase 16 Context

## Goal
Implement stage-result-first return logic for coq/top-level (with split kept as
query-planner-only) and run a
benchmark-gated optimization loop from baseline `0.93` to target `0.96`.

## Requirement IDs
- STAGE-01
- STAGE-02
- STAGE-03
- STAGE-04
- RET-01
- RET-02
- LOOP-01
- LOOP-02
- LOOP-03

## User Constraints
- Prefer markdown-only behavior updates where possible.
- If Python changes are necessary, keep them minimal and avoid hard-filtering
  style semantic gates.
- Run 100q WikiMultiHop benchmark after each implementation round.
- Discard any round with `overall llm_score < baseline`.
- Commit any round with `overall llm_score >= baseline`, then update baseline.
