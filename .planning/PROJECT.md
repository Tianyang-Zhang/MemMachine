# Skill-Orchestrated Retrieval Agent

## What This Is

This project replaced the legacy retrieval-agent pipeline with a skill-first,
workflow-driven retrieval system in MemMachine. Retrieval runs through a
top-level orchestrator with decomposition skills and fallback behavior.

The next milestone focuses on sufficiency-aware skill behavior, LLM-driven
episode filtering decisions, and split live verification using full child-call
context.

## Core Value

Every query is handled by the right retrieval workflow, with reliable fallback
to direct memory search when confidence is low or execution is unstable.

## Current State

- Milestone `v1.0 Skill style retrieval agent` shipped on 2026-03-02.
- v1.0 roadmap and requirements are archived under `.planning/milestones/`.
- Active retrieval runtime is skill-first across server, tests, and evaluation.

## Current Milestone: v1.1 Sufficiency-Aware Skill Verification

**Goal:** Add per-skill sufficiency logging and live split verification while
preserving LLM control of filtering decisions.

**Target features:**
- Per-skill (`coq`, `split`, top-level) sufficiency/confidence outputs for
  logging and evaluation artifacts.
- Split live verification pass after branch execution, with optional branch
  re-run during verification.
- LLM-visible episode-review/filter workflow before final return decisions.
- Top-level metrics updated to expose top-level sufficiency signals.
- 100-question WikiMultiHop benchmark rerun after implementation.

## Requirements

### Validated

- [x] ORCH-01: Top-level `retrieve-skill` orchestration entrypoint.
- [x] ORCH-02: Multi-skill retrieval flow with one normalized final result.
- [x] ORCH-03: Retrieval trace metadata exposure for route/execution decisions.
- [x] ROUT-01: `select-skill` routing with explicit confidence output.
- [x] ROUT-02: Multi-hop decomposition via `coq-skill`.
- [x] ROUT-03: Branch decomposition via `split-skill`.
- [x] ROUT-04: Split-branch escalation through `coq-skill` when needed.
- [x] SAFE-01: Low-confidence fallback to direct MemMachine search.
- [x] SAFE-02: Exception fallback to direct MemMachine search.
- [x] SAFE-03: Timeout fallback to direct MemMachine search.
- [x] SAFE-04: Bounded execution controls for hops/branches/steps.
- [x] MIGR-01: Legacy retrieval-agent execution path removed.
- [x] MIGR-02: Retrieval API response compatibility preserved.
- [x] MIGR-03: First-100 WikiMultiHop functional gate completed.
- [x] MIGR-04: Skill-first terminology canonicalized across active paths.

### Active

- [ ] SUFF-01: `coq`, `split`, and top-level each emit internal
  `is_sufficient`/confidence signals for logging, perf metrics, and evaluation
  JSON.
- [ ] SUFF-02: Parent skills produce their own sufficiency judgement from
  retrieved episodes/context, independent of child `is_sufficient` values.
- [ ] FILT-01: Skills support LLM-led review of retrieved episodes before next
  action/final return decisions.
- [ ] FILT-02: On insufficient state, workflow keeps all episodes if no
  high-confidence episode exists; otherwise keeps high-confidence related
  episodes for follow-up reasoning.
- [ ] SPLT-01: `split` adds one live verification pass after branch execution,
  with ability to rerun branches during verification when needed.
- [ ] CONT-01: Upper-level skill in call tree receives full lower-level return
  context needed for verification and filtering decisions.
- [ ] METR-01: Top-level sufficiency is recorded as first-class metric/tracing
  signal alongside sub-skill sufficiency signals.
- [ ] BENCH-01: Run `./run_test.sh wikimultihop optv2 search retrieval_skill 100`
  and store benchmark output artifact for this milestone.

### Out of Scope

- Adding new skill families beyond `tool_select/coq/split/direct_memory` in
  this milestone.
- Reworking fallback policy strategy unrelated to sufficiency/filter flow.
- Runtime auto-pruning logic that overrides LLM-selected filtering behavior.

## Context

v1.1 scope is driven by the current conversation:
- Keep parent sufficiency decisions independent from child sufficiency outputs.
- Add per-skill sufficiency output contracts for observability.
- Preserve LLM control of filtering decisions; runtime should expose context and
  capture outputs, not enforce hidden heuristics.
- Enable split post-branch live verification with branch rerun capability.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Parent sufficiency is independent of child sufficiency | Avoid chained truth assumptions across levels | — Pending (v1.1) |
| Add top-level sufficiency metric parity with sub-skills | Improve debug/evaluation observability | — Pending (v1.1) |
| Split gets one live verification pass after branch execution | Needed to verify with full branch context | — Pending (v1.1) |
| Keep benchmark gate in milestone scope | Validate behavior impact on real retrieval tasks | — Pending (v1.1) |

---
*Last updated: 2026-03-04 after v1.1 milestone initialization*
