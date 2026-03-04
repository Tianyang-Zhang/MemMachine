# Requirements: v1.2 Stage-Result Return Optimization Loop

**Defined:** 2026-03-04
**Core Value:** Improve retrieval answer quality by making each skill level
prefer stage-results over raw episodes when confidence/sufficiency supports it,
while preserving safe fallback behavior.

## v1.2 Requirements

### Stage-Result Contracts

- [ ] **STAGE-01**: `coq` emits stage-results for resolved hop queries and the
  final stage query when sufficient and confidence meets threshold.
- [ ] **STAGE-02**: `split` remains a pure splitter that returns only
  `sub_queries` planning output, without sufficiency or stage-result fields.
- [ ] **STAGE-03**: Sub-skill return payloads can include:
  `stage_results`/`generated_sub_queries` for `coq`, and `sub_queries` for
  `split`, with fail-closed behavior when confidence/sufficiency is not met.
- [ ] **STAGE-04**: If a stage is insufficient or confidence is below threshold,
  that stage returns episode-only behavior (no stage-result emission for the
  stage-level return).

### Top-Level Return Behavior

- [ ] **RET-01**: Top-level returns stage-results + sub-queries as retrieval
  memory when top-level sufficiency is true and confidence meets threshold.
- [ ] **RET-02**: Top-level retains current episode-return fallback behavior for
  insufficient/low-confidence outcomes.

### Optimization Loop Gate

- [ ] **LOOP-01**: Run 100-question WikiMultiHop benchmark after each
  implementation/optimization round.
- [ ] **LOOP-02**: Baseline gate: discard rounds with `overall llm_score <
  baseline`; keep and commit rounds with `overall llm_score >= baseline`, then
  update baseline.
- [ ] **LOOP-03**: Continue loop until `overall llm_score >= 0.96`.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New hard-coded Python evidence filters | v1.2 keeps semantic decisions LLM-owned |
| New skill families | Focus is return contract and benchmarked optimization |
| Non-Wiki benchmark expansion | Loop gate scope is 100q WikiMultiHop |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STAGE-01 | Phase 16 | Planned |
| STAGE-02 | Phase 16 | Planned |
| STAGE-03 | Phase 16 | Planned |
| STAGE-04 | Phase 16 | Planned |
| RET-01 | Phase 16 | Planned |
| RET-02 | Phase 16 | Planned |
| LOOP-01 | Phase 16 | Planned |
| LOOP-02 | Phase 16 | Planned |
| LOOP-03 | Phase 16 | Planned |

**Coverage:**
- v1.2 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0
