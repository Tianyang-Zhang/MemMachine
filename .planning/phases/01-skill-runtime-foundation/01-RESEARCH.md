# Phase 1: Skill Runtime Foundation - Research

**Researched:** 2026-02-27
**Domain:** Retrieval-agent skill runtime foundation (contracts + orchestration entry)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Invalid skill output: attempt one normalization pass, then fail if still
  invalid.
- Required fields are strict from day one.
- Unknown fields are rejected in Phase 1.
- Phase 1 uses a single v1 contract (no mixed variants).
- Use a strict, minimal schema template for skill specs.
- Include explicit examples for common patterns in skill authoring guidance.
- Apply opinionated defaults (timeouts/limits/fallback hooks) to reduce
  boilerplate.
- Block execution when a spec is incomplete.
- Errors are developer-first and technical.
- Error format must include: what failed, why, how to fix, and where.
- Use stable typed error codes from day one (e.g., `SKILL_CONTRACT_*`).
- Fallback paths must explicitly state the trigger reason each time.
- Internal trace metadata remains internal by default in Phase 1.
- Low parity with legacy behavior is acceptable in this phase.
- If compatibility and authoring convenience conflict, prioritize authoring
  convenience in Phase 1.
- Target compatibility where practical, but convenience-first is the tie-breaker.

### Claude's Discretion
- Exact wording and formatting of error/help text while preserving required
  structure.
- Structure and placement of authoring examples within docs/spec guidance.
- Default-value specifics (exact timeout/limit numbers) if not explicitly
  constrained elsewhere.

### Deferred Ideas (OUT OF SCOPE)
- None.
</user_constraints>

<research_summary>
## Summary

Phase 1 should establish a strict skill runtime contract layer that downstream
skill implementations can rely on without ambiguity. The existing retrieval
stack already has strong typed interfaces (`QueryParam`, `QueryPolicy`,
`AgentToolBase`) and service-locator wiring, so the least-risk approach is to
add a new `skills/` package that mirrors existing typing discipline and starts
with one narrow entry path.

The safest baseline is a two-step implementation sequence:
1. introduce contract types + validation/runtime primitives with stable error
   codes;
2. wire a `retrieve-skill` bootstrap path in service locator with compatibility
   tests.

**Primary recommendation:** build strict typed contracts first, then wire
`retrieve-skill` entry path with integration tests that protect current response
shape behavior.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python typing + dataclasses/Pydantic | Existing project stack | Contracts and validation | Matches established codebase conventions |
| Existing retrieval abstractions (`AgentToolBase`) | Existing | Tool/runtime compatibility | Preserves integration with current retrieval flow |
| pytest + pytest-asyncio | Existing | Unit/integration verification | Already used in retrieval-agent tests |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` | stdlib | Runtime diagnostics | Emit developer-first structured error context |
| `typing.Protocol` / typed models | stdlib / existing | Stable interfaces | Ensure downstream skill implementations are explicit |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Strict in-process contract objects | Generic dict-only schemas | Faster to start, but high ambiguity and weaker static guarantees |
| Single v1 schema | Multi-version parser now | More flexibility later, but unnecessary complexity in Phase 1 |

**Installation:**
```bash
# No new package required for Phase 1 baseline.
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```text
src/memmachine/retrieval_agent/skills/
├── __init__.py              # Public exports for runtime contracts
├── types.py                 # Skill request/response/error contracts
├── runtime.py               # Validation + normalization + guardrail helpers
├── spec_loader.py           # Strict skill spec loading/parsing
└── retrieve_skill.py        # Entry orchestration bootstrap
```

### Pattern 1: Contract-first runtime
**What:** Define typed request/result/error models before orchestration logic.
**When to use:** Always in Phase 1 to prevent downstream drift.
**Example:**
```python
@dataclass
class SkillResult:
    response: list[Episode]
    confidence: float
    route_trace: list[str]
```

### Pattern 2: Compatibility wrapper in service locator
**What:** Add retrieve-skill bootstrap through `create_retrieval_agent` without
rewriting entire stack at once.
**When to use:** Phase 1 migration baseline.
**Example:**
```python
if agent_name == "RetrieveSkillAgent":
    return RetrieveSkillAgent(shared_param)
```

### Anti-Patterns to Avoid
- Defining runtime behavior in ad-hoc dicts with no typed contract.
- Mixing phase-2/phase-3 capabilities (routing logic, decomposition engines)
  into Phase 1 foundation work.
- Hiding fallback trigger details in generic exceptions.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Generic schema validation logic from scratch | Custom brittle validators | Existing typed model validation approach used in codebase | Reduces parsing bugs and inconsistency |
| New end-to-end retrieval stack in one step | Big-bang migration | Service-locator compatibility wrapper + phased migration | Limits regression blast radius |
| Informal error strings | Free-form exceptions | Stable typed error codes (`SKILL_CONTRACT_*`) | Supports deterministic handling and testability |

**Key insight:** strict contracts and deterministic error semantics are the
foundation; orchestration sophistication can layer on later phases.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Contract leakage through dicts
**What goes wrong:** runtime accepts inconsistent shapes and downstream logic
branches on ad-hoc keys.
**Why it happens:** rushing entry wiring before finalizing typed contracts.
**How to avoid:** all skill boundaries use explicit typed structures and strict
required fields.
**Warning signs:** repeated `if "field" in data` checks across files.

### Pitfall 2: Over-scoping Phase 1
**What goes wrong:** routing/decomposition logic creeps into foundation phase.
**Why it happens:** trying to prove too much in first milestone step.
**How to avoid:** enforce roadmap boundary: contracts + entry path only.
**Warning signs:** split/coq behavior changes appear in Phase 1 PRs.

### Pitfall 3: Silent fallback reasons
**What goes wrong:** fallback occurs but developers cannot diagnose why.
**Why it happens:** generic exceptions and missing reason propagation.
**How to avoid:** include explicit fallback trigger reason in every failure path.
**Warning signs:** logs show "fallback used" without trigger metadata.
</common_pitfalls>

<code_examples>
## Code Examples

### Service locator baseline (current repo)
```python
# Source: src/memmachine/retrieval_agent/service_locator.py
memory_agent = MemMachineAgent(...)
shared_param = AgentToolBaseParam(model=model, children_tools=[memory_agent], ...)
```

### Existing retrieval contracts baseline
```python
# Source: src/memmachine/retrieval_agent/common/agent_api.py
class QueryParam(BaseModel):
    query: str
    limit: int = 0
```

### Existing retrieval behavior tests
```python
# Source: tests/memmachine/retrieval_agent/test_retrieval_agent.py
results, metrics = await tool_select_agent.do_query(...)
assert metrics["selected_tool"] == "ChainOfQueryAgent"
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt-only routing with weak contracts | Typed orchestration boundaries + strict validation | Ongoing trend | Better reliability and debuggability |
| Large monolithic agent entry points | Smaller composable tool/skill modules | Ongoing trend | Easier phased migration and testing |

**New patterns to consider later (not Phase 1):**
- Structured route traces surfaced to observability pipelines.
- Policy-based fallback tuning once baseline migration is stable.

**Deferred from Phase 1:**
- Prompt optimization for score improvements.
- Expanded skill catalog beyond foundation set.
</sota_updates>

<open_questions>
## Open Questions

1. **How strict should spec parser be for optional metadata keys?**
   - What we know: required fields must be strict.
   - What's unclear: whether optional fields should be rejected or ignored.
   - Recommendation: reject unknown fields in Phase 1 per user decision.

2. **How much trace data should be emitted internally in Phase 1?**
   - What we know: metadata should remain internal by default.
   - What's unclear: minimum trace fields for debugging.
   - Recommendation: emit route/fallback reason + error code + stage name.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- Local codebase: `src/memmachine/retrieval_agent/service_locator.py`
- Local codebase: `src/memmachine/retrieval_agent/common/agent_api.py`
- Local tests: `tests/memmachine/retrieval_agent/test_retrieval_agent.py`
- User decisions: `.planning/phases/01-skill-runtime-foundation/01-CONTEXT.md`

### Secondary (MEDIUM confidence)
- Existing project conventions in `.planning/codebase/CONVENTIONS.md`
- Existing phase templates under `/memverge/home/tomz/.codex/get-shit-done/templates/`

### Tertiary (LOW confidence)
- None.
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: retrieval-agent skill runtime contracts
- Ecosystem: current MemMachine retrieval modules and tests
- Patterns: contract-first + service-locator compatibility wrapper
- Pitfalls: over-scoping, contract drift, opaque fallback reasons

**Confidence breakdown:**
- Standard stack: HIGH - relies on existing project stack
- Architecture: HIGH - aligns with existing retrieval layering
- Pitfalls: HIGH - derived from migration constraints and user decisions
- Code examples: HIGH - from local repository files

**Research date:** 2026-02-27
**Valid until:** 2026-03-29
</metadata>

---

*Phase: 01-skill-runtime-foundation*
*Research completed: 2026-02-27*
*Ready for planning: yes*
