# Requirements: Skill-Orchestrated Retrieval Agent

**Defined:** 2026-03-04
**Core Value:** Every query is handled by the right retrieval workflow, with
reliable fallback to direct memory search when confidence is low or execution is
unstable.

## v1.1 Requirements

### Sufficiency Signals

- [ ] **SUFF-01**: `coq`, `split`, and top-level each produce
  `is_sufficient` and confidence outputs for logging/debug artifacts.
- [ ] **SUFF-02**: Parent skills compute sufficiency from retrieved
  episodes/context and do not depend on child `is_sufficient` outputs for
  control.
- [ ] **SUFF-03**: For insufficient states, skills can report related evidence
  candidates and confidence markers in output contracts.

### Filtering Workflow

- [ ] **FILT-01**: Skills support LLM-led episode review before deciding next
  action.
- [ ] **FILT-02**: Insufficient-path rule: if any related episode confidence is
  `>= 0.7`, low-confidence episodes are deprioritized for next-step reasoning;
  if none reach threshold, keep all episodes.
- [ ] **FILT-03**: Sufficient-path rule: for high-confidence decisions, evidence
  selection can be emitted; if selection is empty, fallback behavior keeps all
  episodes.

### Split Live Verification

- [ ] **SPLT-01**: `split` runs one live verification pass after branch
  execution using accumulated branch context.
- [ ] **SPLT-02**: Split verification pass may rerun branches when verification
  detects missing evidence/noise.
- [ ] **CONT-01**: Upper-level skill receives lower-level return context
  (episodes + structured outputs) for verification/filter decisions.

### Metrics and Validation

- [ ] **METR-01**: Top-level sufficiency signals are exposed in perf metrics and
  trace outputs similarly to sub-skill sufficiency signals.
- [ ] **BENCH-01**: Team can execute
  `./run_test.sh wikimultihop optv2 search retrieval_skill 100` after changes
  and capture milestone benchmark results.

## v2 Requirements

### Optimization Follow-ups

- **OPT-01**: Accuracy/policy tuning campaign beyond sufficiency/filter flow.
- **OPT-02**: New-skill onboarding contract/checklist for future skill
  expansion.
- **OPT-03**: Repeatable A/B policy harness with stronger statistical reporting.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New skill families outside current retrieval set | Keep milestone focused on sufficiency/filter architecture |
| Broad reranker redesign | Not required for this verification-first milestone |
| UI/product-level changes | Milestone is retrieval runtime + metrics behavior |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SUFF-01 | Phase 12 | Pending |
| SUFF-02 | Phase 12 | Pending |
| SUFF-03 | Phase 12 | Pending |
| FILT-01 | Phase 13 | Pending |
| FILT-02 | Phase 13 | Pending |
| FILT-03 | Phase 13 | Pending |
| SPLT-01 | Phase 14 | Pending |
| SPLT-02 | Phase 14 | Pending |
| CONT-01 | Phase 14 | Pending |
| METR-01 | Phase 15 | Pending |
| BENCH-01 | Phase 15 | Pending |

**Coverage:**
- v1.1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-04 after milestone v1.1 initialization*
