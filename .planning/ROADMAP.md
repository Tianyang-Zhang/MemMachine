# Roadmap: Skill-Orchestrated Retrieval Agent

## Milestones

- [x] **v1.0 Skill style retrieval agent** - shipped 2026-03-02.
  Archive: `.planning/milestones/v1.0-ROADMAP.md`
- [x] **v1.1 Sufficiency-Aware Skill Verification** - shipped 2026-03-04.
  Archive: `.planning/milestones/v1.1-ROADMAP.md`
- [ ] **v1.2 Stage-Result Return Optimization Loop** - active.

## Active Milestone: v1.2 Stage-Result Return Optimization Loop

**Milestone Goal:** Implement stage-result-first return semantics across
coq/top-level with markdown-first contracts, keep split as planning-only, then
execute benchmark-gated
optimization until `llm_score >= 0.96`.

## Phases

- [ ] **Phase 16: Stage-Result Return Contracts and Optimization Loop** - add
  stage-result contracts/return behavior and run iterative 100q benchmark gate.

## Phase Details

### Phase 16: Stage-Result Return Contracts and Optimization Loop

**Goal:** Implement stage-result-first retrieval return flow with minimal runtime
changes and execute benchmark-gated iterative tuning.
**Depends on:** Phase 15
**Requirements:** [STAGE-01, STAGE-02, STAGE-03, STAGE-04, RET-01, RET-02,
LOOP-01, LOOP-02, LOOP-03]
**Success Criteria** (what must be TRUE):
1. CoQ emits stage-results only for sufficient/high-confidence stage-level
   returns; split remains planner-only with `sub_queries` output.
2. Top-level uses stage-results as first evidence source and can return
   stage-results + sub-queries as retrieval memory when sufficient.
3. 100-question benchmark runs after each round and follows strict
   baseline/commit gate until the target score is reached.
**Plans**: 2 plans

Plans:
- [ ] 16-01: Implement markdown-first stage-result contracts and minimal runtime
  support for top-level stage-result memory return
- [ ] 16-02: Execute benchmark-gated optimization loop with commit/discard policy

## Next Step

`$gsd-execute-phase 16`
