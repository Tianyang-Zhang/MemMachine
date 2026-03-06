# Requirements: MemMachine Cross-Provider Retrieval Skills

**Defined:** 2026-03-06
**Core Value:** Retrieval skills behave consistently across OpenAI and Anthropic with one configuration switch, while preserving multi-turn tool-calling reliability.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Session Infrastructure

- [ ] **SESS-01**: System selects retrieval skill session provider from config (`openai` or `anthropic`) for each retrieval query.
- [ ] **SESS-02**: Both providers implement the shared `run_live_session` contract and return a normalized `SkillRunResult` shape.
- [ ] **SESS-03**: Session runtime enforces `max_turns` and timeout guardrails consistently across providers.
- [ ] **SESS-04**: Session runtime reports normalized metrics (`llm_input_tokens`, `llm_output_tokens`, `llm_time_seconds`, `turn_count`) for both providers.

### Anthropic Provider Support

- [ ] **ANTH-01**: Anthropic session runtime supports multi-turn continuation until no tool calls remain.
- [ ] **ANTH-02**: Anthropic runtime parses tool calls into validated tool name + argument objects compatible with retrieval tool registry.
- [ ] **ANTH-03**: Anthropic runtime returns tool outputs in provider-compatible follow-up format so the model can continue the session.
- [ ] **ANTH-04**: Anthropic runtime surfaces explicit runtime/contract errors through existing retrieval fallback pathways.

### Retrieval Orchestration Integration

- [ ] **ROUT-01**: `RetrieveSkill` uses selected provider session runtime without changing top-level policy semantics.
- [ ] **ROUT-02**: `SubSkillRunner` routes `split`, `coq`, and `direct_memory` execution through selected provider session runtime.
- [ ] **ROUT-03**: Existing fallback behavior (including direct memory fallback when no top-level tool call emitted) remains intact.
- [ ] **ROUT-04**: Retrieval session traces preserve provider-agnostic structure for events, tool calls, and sub-skill runs.

### Tool Calling and Guardrails

- [ ] **TOOL-01**: Tool name allowlisting prevents execution of unknown model-proposed tools for both providers.
- [ ] **TOOL-02**: Malformed tool-call payloads raise explicit typed errors and are mapped to fallback reasons.
- [ ] **TOOL-03**: `memmachine_search` tool call behavior and output serialization remain deterministic across providers.
- [ ] **TOOL-04**: Retry/backoff behavior for provider API requests is bounded and configurable.

### Testing and Validation

- [ ] **TEST-01**: Unit tests validate OpenAI and Anthropic multi-turn tool-call chaining behavior.
- [ ] **TEST-02**: Unit tests validate provider selection wiring from config through retrieval service locator.
- [ ] **TEST-03**: Unit/integration tests validate top-level and sub-skill parity for tool-call transcript generation.
- [ ] **TEST-04**: Regression checks confirm no decrease in retrieval correctness metrics versus OpenAI baseline.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extensibility

- **EXT-01**: Add optional MCP-backed external tool transport for cross-provider runtime portability.
- **EXT-02**: Expand provider support to Bedrock/Ollama using the same session adapter pattern.
- **EXT-03**: Add dynamic provider failover policy with explicit governance rules.

### Operations

- **OPS-01**: Build provider comparison dashboard for latency/token/quality trend analysis.
- **OPS-02**: Add per-tenant provider routing policies.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rewriting retrieval markdown skill specs from scratch | Runtime migration should preserve behavior and limit scope |
| Introducing a new custom skill DSL | Existing markdown contracts are sufficient for this milestone |
| Automatic silent provider failover | Reduces determinism and weakens debugging/evaluation quality |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SESS-01 | Phase 1 | Pending |
| SESS-02 | Phase 1 | Pending |
| SESS-03 | Phase 1 | Pending |
| SESS-04 | Phase 1 | Pending |
| ANTH-01 | Phase 2 | Pending |
| ANTH-02 | Phase 2 | Pending |
| ANTH-03 | Phase 2 | Pending |
| ANTH-04 | Phase 2 | Pending |
| ROUT-01 | Phase 3 | Pending |
| ROUT-02 | Phase 3 | Pending |
| ROUT-03 | Phase 3 | Pending |
| ROUT-04 | Phase 3 | Pending |
| TOOL-01 | Phase 4 | Pending |
| TOOL-02 | Phase 4 | Pending |
| TOOL-03 | Phase 4 | Pending |
| TOOL-04 | Phase 4 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 5 | Pending |
| TEST-03 | Phase 5 | Pending |
| TEST-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-06*
*Last updated: 2026-03-06 after initial definition*
