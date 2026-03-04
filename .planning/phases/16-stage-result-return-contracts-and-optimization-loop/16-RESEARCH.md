# Phase 16 Research

## Existing Runtime Facts
- CoQ/split summaries are returned as JSON strings via
  `return_sub_skill_result` and parsed opportunistically at top-level.
- Top-level currently always returns merged episodes, regardless of sufficiency.
- Top-level `return_final` schema does not yet support structured
  `stage_results` / `sub_queries` fields.

## Implementation Direction
- Update `coq.md`, `split.md`, `retrieve_skill.md` contracts so:
  - `coq`/top-level handle stage-results
  - `split` remains strict sub-query planner only.
- Add minimal runtime support in `tool_protocol.py` + `retrieve_skill.py` to
  carry top-level stage-result/sub-query payloads and emit stage-result-only
  memory when top-level sufficiency/confidence gates are met.
- Validate with targeted retrieval_skill tests, then run 100q benchmark gate.
