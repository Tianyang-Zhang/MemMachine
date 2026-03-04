# Roadmap: Skill-Orchestrated Retrieval Agent

## Milestones

- [x] **v1.0 Skill style retrieval agent** - shipped 2026-03-02.
  Archive: `.planning/milestones/v1.0-ROADMAP.md`
- [ ] **v1.1 Sufficiency-Aware Skill Verification** - initialized 2026-03-04.

## v1.1 Goal

Add per-skill sufficiency observability, enable live split verification with
full branch context, and align filtering workflow behavior with LLM-driven
verification rules.

## Phases

- [ ] **Phase 12: Sufficiency Contract and Signal Baseline**
  Standardize sufficiency outputs (`is_sufficient`, confidence, evidence hints)
  across `coq`, `split`, and top-level paths; preserve parent independence from
  child sufficiency outputs.

- [ ] **Phase 13: LLM-Led Filtering Workflow Integration**
  Implement insufficient/sufficient filtering workflow semantics in skill runtime
  interactions so LLM can review episode context before next action/finalization.

- [ ] **Phase 14: Split Live Verification Pass**
  Add one post-branch verification pass for `split` with full child-context
  visibility and optional branch rerun from verification.

- [ ] **Phase 15: Top-Level Metrics Parity and Benchmark Gate**
  Expose top-level sufficiency metrics/traces and execute
  `./run_test.sh wikimultihop optv2 search retrieval_skill 100`.

## Phase Details

### Phase 12: Sufficiency Contract and Signal Baseline

**Goal:** Introduce consistent sufficiency signal contracts for all key skills
without coupling parent decisions to child sufficiency booleans.

**Requirements:** [SUFF-01, SUFF-02, SUFF-03]
**Depends on:** v1.0 baseline
**Plans:** 2 plans

Plans:
- [ ] 12-01: Extend skill/tool contracts and markdown specs for standardized
      sufficiency output payloads.
- [ ] 12-02: Wire runtime parsing/logging paths to record sufficiency outputs
      without using child sufficiency for control flow.

**Success criteria:**
1. `coq`, `split`, and top-level emit sufficiency/confidence payloads.
2. Parent control decisions derive from retrieved context, not child
   `is_sufficient`.
3. Sufficiency payloads are visible in trace/debug outputs.

### Phase 13: LLM-Led Filtering Workflow Integration

**Goal:** Let LLM evaluate related/high-confidence evidence for next-step and
finalization decisions while preserving fallback defaults.

**Requirements:** [FILT-01, FILT-02, FILT-03]
**Depends on:** Phase 12
**Plans:** 2 plans

Plans:
- [ ] 13-01: Implement insufficient-path related-evidence and confidence
      threshold workflow (`>=0.7` rule, fallback-to-all behavior).
- [ ] 13-02: Implement sufficient-path evidence-selection workflow with
      empty-selection fallback-to-all semantics.

**Success criteria:**
1. Insufficient-path behavior follows confidence-threshold rules.
2. Sufficient-path behavior supports explicit evidence selection plus fallback.
3. Runtime behavior remains deterministic when selection output is missing.

### Phase 14: Split Live Verification Pass

**Goal:** Upgrade split execution to include one live verification pass after
branch runs, with optional branch rerun during verification.

**Requirements:** [SPLT-01, SPLT-02, CONT-01]
**Depends on:** Phase 13
**Plans:** 2 plans

Plans:
- [ ] 14-01: Refactor split runtime into plan -> execute -> verify pipeline with
      full child-context handoff.
- [ ] 14-02: Add optional verification-triggered branch rerun and regression
      tests for split live behavior.

**Success criteria:**
1. Split verification receives branch outputs/episodes/structured results.
2. Verification step can trigger controlled reruns when needed.
3. Final split output includes verification decisions and context trace.

### Phase 15: Top-Level Metrics Parity and Benchmark Gate

**Goal:** Add first-class top-level sufficiency metrics and validate milestone
behavior with a new 100-question benchmark run.

**Requirements:** [METR-01, BENCH-01]
**Depends on:** Phase 14
**Plans:** 2 plans

Plans:
- [ ] 15-01: Add top-level sufficiency metric/tracing parity and test coverage.
- [ ] 15-02: Execute benchmark command, capture artifacts, and document gate
      results.

**Success criteria:**
1. Perf metrics/evaluation JSON include top-level sufficiency outputs.
2. Benchmark command completes and artifact is committed.
3. Any regressions are documented with follow-up action items.

## Progress

| Milestone | Phase | Plans | Status |
|-----------|-------|-------|--------|
| v1.0 Skill style retrieval agent | 1-11 | 22/22 | Complete |
| v1.1 Sufficiency-Aware Skill Verification | 12-15 | 0/8 | Not started |

## Next Step

Start milestone execution with:

`$gsd-plan-phase 12`
