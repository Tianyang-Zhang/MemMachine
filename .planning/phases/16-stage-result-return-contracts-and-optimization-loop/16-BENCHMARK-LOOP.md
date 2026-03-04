# Phase 16 Benchmark Loop Log

## Gate Policy

- Initial baseline: `overall llm_score = 0.93`
- For each round:
  - if score `< baseline`: discard round, do not commit, replan
  - if score `>= baseline`: commit round, update baseline to this score, replan
- Stop condition: baseline reaches `0.96` or higher.

## Iterations

| Round | Change Summary | Benchmark Tag | llm_score | Decision | New Baseline |
|------:|----------------|---------------|----------:|----------|-------------:|
| 0 | Baseline from existing artifact | optv2 (historical) | 0.93 | baseline set | 0.93 |
| 1 | Stage-result v1 (`coq` + top-level; initial threshold 0.8) | optv6_stage_result_r1 | 0.92 | discard (below baseline) | 0.93 |
| 2 | Split planner-only + coq/top-level stage-result gating (`threshold=0.9`) | optv6_stage_result_r2 | 0.95 | keep + commit | 0.95 |
