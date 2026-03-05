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
| 3 | Comparative/routing tightening (spec-focused) | optv6_stage_result_r3 | 0.93 | discard (below baseline) | 0.95 |
| 4 | Death-place proxy-heavy attempt | optv6_stage_result_r4 | 0.92 | discard (below baseline) | 0.95 |
| 5 | Test-only stabilization check | optv6_stage_result_r5 | 0.94 | discard (below baseline) | 0.95 |
| 6 | Selector/routing strengthening retry | optv6_stage_result_r6 | 0.92 | discard (below baseline) | 0.95 |
| 7 | Runtime retryability tweak retry | optv6_stage_result_r7 | 0.92 | discard (below baseline) | 0.95 |
| 8 | Baseline reproducibility check (no net code delta from kept commit) | optv6_stage_result_r8_baseline_check | 0.94 | reproducibility drop observed | 0.95* |
| 8.1 | User decision: reset active gate baseline to reproducible score | n/a | 0.94 | baseline reset | 0.94 |
| 9 | CoQ/top-level prompt refinements + split planner-only aggregation test | optv6_stage_result_r9 | 0.95 | keep + commit | 0.95 |

\* Historical kept baseline remained 0.95, but active optimization gate was reset to 0.94 after reproducibility check per user instruction.
