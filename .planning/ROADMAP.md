# Roadmap: MemMachine Cross-Provider Retrieval Skills

## Overview

This roadmap migrates retrieval skill execution from a single-provider runtime to
a provider-selectable multi-turn architecture (OpenAI + Anthropic), while
preserving existing retrieval behavior, guardrails, and evaluation quality.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Session Adapter Foundations** - Establish provider-agnostic
      session boundaries and config-driven selection.
- [ ] **Phase 2: Anthropic Runtime Implementation** - Add Anthropic multi-turn
      session adapter compatible with retrieval tool loops.
- [ ] **Phase 3: Retrieval Integration** - Route top-level and sub-skill
      orchestration through selected provider runtime.
- [ ] **Phase 4: Guardrails and Fallback Parity** - Align error handling,
      tool-call safety, and retry behavior across providers.
- [ ] **Phase 5: Validation and Benchmarking** - Prove correctness and quality
      parity with tests and retrieval evaluations.

## Phase Details

### Phase 1: Session Adapter Foundations
**Goal**: Create provider selection/factory plumbing and normalized session
runtime contract.
**Depends on**: Nothing (first phase)
**Requirements**: SESS-01, SESS-02, SESS-03, SESS-04
**Success Criteria** (what must be TRUE):
1. Retrieval runtime selects provider via config without code changes.
2. Session adapter interface is shared and typed for both providers.
3. Guardrails and metrics contract are defined and asserted in tests.
**Plans**: 3 plans

Plans:
- [ ] 01-01: Define/refine shared skill-session adapter contract and exports
- [ ] 01-02: Implement provider selection factory and config wiring
- [ ] 01-03: Add baseline tests for contract and metric normalization hooks

### Phase 2: Anthropic Runtime Implementation
**Goal**: Implement Anthropic live-session adapter with tool-call continuation.
**Depends on**: Phase 1
**Requirements**: ANTH-01, ANTH-02, ANTH-03, ANTH-04
**Success Criteria** (what must be TRUE):
1. Anthropic adapter can run multi-turn sessions until completion.
2. Anthropic tool calls are parsed/validated into expected internal shape.
3. Anthropic errors are surfaced via typed runtime/fallback pathways.
**Plans**: 3 plans

Plans:
- [ ] 02-01: Add `skill_anthropic_session_language_model.py` core runtime
- [ ] 02-02: Implement tool-call parsing and function_call_output mapping
- [ ] 02-03: Add Anthropic-focused runtime unit tests (happy path + errors)

### Phase 3: Retrieval Integration
**Goal**: Integrate selected provider runtime into retrieval orchestrators.
**Depends on**: Phase 2
**Requirements**: ROUT-01, ROUT-02, ROUT-03, ROUT-04
**Success Criteria** (what must be TRUE):
1. `RetrieveSkill` executes through selected provider adapter.
2. Sub-skills (`split`, `coq`, `direct_memory`) use the same selected adapter.
3. Existing fallback and trace semantics remain stable.
**Plans**: 3 plans

Plans:
- [ ] 03-01: Inject session adapter into retrieval service locator path
- [ ] 03-02: Wire sub-skill runner and top-level skill to shared provider
      selection
- [ ] 03-03: Verify trace/event output parity against current format

### Phase 4: Guardrails and Fallback Parity
**Goal**: Normalize tool-call safety, fallback reasons, and retry behavior.
**Depends on**: Phase 3
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04
**Success Criteria** (what must be TRUE):
1. Unknown/malformed tool calls fail safely with explicit reasons.
2. `memmachine_search` behavior remains deterministic across providers.
3. Retry/backoff and timeout behavior are bounded and configurable.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Harden provider parsers and tool allowlist enforcement
- [ ] 04-02: Standardize fallback reason mapping and error propagation
- [ ] 04-03: Add provider-aware retry/backoff and timeout tests

### Phase 5: Validation and Benchmarking
**Goal**: Validate no regression in behavior and evaluate quality/latency impact.
**Depends on**: Phase 4
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
1. Provider multi-turn tests pass for top-level and sub-skill paths.
2. Config-based routing tests prove deterministic provider selection.
3. Retrieval evaluation metrics show parity or documented trade-offs.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Add end-to-end retrieval skill session test matrix
- [ ] 05-02: Run and compare retrieval benchmark/evaluation outputs
- [ ] 05-03: Document migration notes and operational verification checklist

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Session Adapter Foundations | 0/3 | Not started | - |
| 2. Anthropic Runtime Implementation | 0/3 | Not started | - |
| 3. Retrieval Integration | 0/3 | Not started | - |
| 4. Guardrails and Fallback Parity | 0/3 | Not started | - |
| 5. Validation and Benchmarking | 0/3 | Not started | - |
