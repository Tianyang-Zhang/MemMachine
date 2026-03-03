# Phase 2: Routing and Fallback Safety - Research

**Researched:** 2026-02-27
**Domain:** Route decision policy, fallback safety, and bounded orchestration controls
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Route selection is model-driven and returns a single selected route.
- Borderline confidence should bias toward decomposition routes for recall.
- If selector cannot classify, retry selector once before fallback.
- If first and retry route conflict, choose the higher-confidence route.
- Enforce all bounds in this phase: `max_steps`, `max_hops`, `max_branches`,
  global timeout, and per-sub-skill timeout.
- On bound hit: allow one controlled retry; if still bounded, fallback.
- Preserve partially merged evidence when fallback occurs after partial progress.
- Route decision output always includes: `selected_route`, `confidence_score`,
  `reason_code`, optional `fallback_trigger_reason`.
- `confidence_score` is float in `[0.0, 1.0]`.
- Reason reporting includes stable enum-like code plus short human-readable note.
- Response metrics expose full per-step/per-tool trace by default.

### Claude's Discretion
- Exact confidence threshold values and tie-break expressions.
- Exact reason/fallback enum symbol naming.
- Internal trace payload structure as long as full step/tool detail is retained.

### Deferred Ideas (OUT OF SCOPE)
- None.
</user_constraints>

<research_summary>
## Summary

Phase 2 should layer deterministic route-policy and fallback-control modules onto
Phase 1.1 orchestration without breaking markdown-owned decision flow.

The safest path is two-step:
1. add route decision contract + selector retry/tie-break integration;
2. add fallback policy engine for low-confidence, exception, timeout, and bound
   paths with full trace metrics.

This keeps orchestration policy LLM-driven while making reliability behavior
explicit, testable, and requirement-mapped.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Existing `LanguageModel` abstraction | existing | selector + orchestration calls | Already used by retrieval agents |
| Pydantic models in `skills/types.py` | existing | deterministic route/fallback payloads | Project contract baseline |
| Existing `RetrieveSkill` session state | existing | persistent top-level trace/state | Already integrated in phase 1.1 |
| pytest + pytest-asyncio | existing | route/fallback behavior tests | Existing test stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `time` / monotonic clock | stdlib | global/per-sub timeout enforcement | fallback policy checks |
| stdlib `enum`/literal fields | stdlib | reason code domains | strict route/fallback code sets |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-process fallback policy module | inline logic in `RetrieveSkill` | Faster coding, but less testability and higher drift |
| Deterministic route-output contract | free-form LLM route text | Simpler prompting, but brittle parsing and weaker guarantees |

**Installation:**
```bash
# No additional dependency required for Phase 2.
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Route decision contract module
**What:** Parse/validate selector outputs into fixed fields:
`selected_route`, `confidence_score`, `reason_code`, `reason_note`.
**When to use:** every selector response before orchestration branching.

### Pattern 2: Fallback policy engine
**What:** Centralized policy that maps runtime conditions
(low confidence, downstream exception, timeout, bound exceeded) to
`fallback_trigger_reason` and retry/fallback actions.
**When to use:** top-level orchestration runtime before/after each step.

### Pattern 3: Bound-aware orchestrator accounting
**What:** Track step/hop/branch counts and global/per-sub timers in top-level
session state so guardrails are deterministic.
**When to use:** each top-level tool call and sub-skill spawn.

### Anti-patterns to avoid
- Route decisions encoded as ad-hoc strings without strict parsing.
- Separate fallback handling branches with inconsistent reason semantics.
- Hidden fallback transitions without trace visibility in response metrics.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Route output parsing | string contains checks | strict contract parser/model | deterministic behavior + stable tests |
| Fallback behavior | scattered `except`/`if` fallback calls | centralized fallback policy mapper | requirement coverage + consistency |
| Timeout semantics | provider-specific hardcoding | monotonic budget checks + policy mapping | predictable cross-model behavior |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Confidence ambiguity
**What goes wrong:** selector emits inconsistent scales or missing confidence.
**How to avoid:** normalize to float `[0.0, 1.0]`, reject invalid payloads, and
fallback with explicit reason.

### Pitfall 2: Retry loops causing hidden unbounded behavior
**What goes wrong:** retries bypass step/hop limits and increase latency.
**How to avoid:** include retries in bounded counters and policy accounting.

### Pitfall 3: Timeout fallback dropping useful partial evidence
**What goes wrong:** response quality drops despite valid collected evidence.
**How to avoid:** preserve merged evidence in session, then run direct fallback
search and return both with explicit reason metadata.
</common_pitfalls>

<code_examples>
## Code Examples

### Current top-level orchestration integration point
```python
# Source: src/memmachine/retrieval_agent/skills/retrieve_skill.py
output_text, raw_function_calls = await model.generate_response(...)
```

### Existing session-state trace model
```python
# Source: src/memmachine/retrieval_agent/skills/session_state.py
class TopLevelSkillSessionState(BaseModel):
    events: list[SkillSessionEvent]
    tool_calls: list[SkillToolCallRecord]
    sub_skill_runs: list[SubSkillRunRecord]
```

### Existing fallback reason surface
```python
# Source: src/memmachine/retrieval_agent/skills/retrieve_skill.py
metrics["fallback_trigger_reason"] = reason
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Prompt-only route text + best effort fallback | Structured route outputs + explicit fallback policy reasons | Better diagnosability and deterministic reliability |
| Single timeout handling | Layered global + scoped timeout budgets | Better control over long-running multi-step orchestration |

**Deferred beyond Phase 2:**
- Learned confidence calibration from telemetry.
- Adaptive fallback policies per route type.
</sota_updates>

<open_questions>
## Open Questions

1. Should low-confidence threshold be static or route-specific in Phase 2?
   Recommendation: static phase-level threshold now; route-specific tuning later.

2. How verbose should full per-step trace be in API metrics payload size-wise?
   Recommendation: include required trace by default in phase 2; optimize size in
   phase 4 observability work.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/phases/02-routing-and-fallback-safety/02-CONTEXT.md`
- `src/memmachine/retrieval_agent/skills/retrieve_skill.py`
- `src/memmachine/retrieval_agent/skills/session_state.py`
- `src/memmachine/retrieval_agent/skills/tool_protocol.py`
- `tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py`
- `src/memmachine/retrieval_agent/agents/tool_select_agent.py`

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

### Tertiary (LOW confidence)
- None.
</sources>

<metadata>
## Metadata

**Research scope:**
- Route decision contracts and retry/tie-break policy
- Fallback trigger mapping for SAFE requirements
- Bounded orchestration controls and trace semantics

**Confidence breakdown:**
- Route policy architecture: HIGH
- Fallback policy design: HIGH
- Timeout/bounds handling: HIGH
- Test strategy: HIGH

**Research date:** 2026-02-27
**Valid until:** 2026-03-29
</metadata>

---

*Phase: 02-routing-and-fallback-safety*
*Research completed: 2026-02-27*
*Ready for planning: yes*
