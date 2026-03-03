---
phase: 02-routing-and-fallback-safety
plan: "02"
subsystem: api
tags: [retrieval-agent, fallback-policy, timeout, bounded-execution, traces]
requires:
  - phase: 02-routing-and-fallback-safety
    provides: select-skill route decision contract and selector retry/tie-break behavior
provides:
  - Unified fallback policy engine for reliability triggers
  - Global/per-sub timeout and max-step/hop/branch bounded controls
  - SAFE requirement regression tests and full trace metrics exposure
affects: [phase-03-decomposition-skills, phase-04-cutover-and-observability]
tech-stack:
  added: []
  patterns: [centralized-fallback-policy, guardrail-retry-then-fallback, trace-first-metrics]
key-files:
  created:
    - src/memmachine/retrieval_agent/skills/fallback_policy.py
    - tests/memmachine/retrieval_agent/test_retrieve_skill_fallback_policy.py
  modified:
    - src/memmachine/retrieval_agent/skills/retrieve_skill.py
    - src/memmachine/retrieval_agent/skills/session_state.py
    - tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py
    - tests/memmachine/retrieval_agent/test_retrieve_skill_bootstrap.py
    - tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py
key-decisions:
  - "Low-confidence route decisions trigger direct-memory fallback through centralized fallback policy reasons."
  - "Retryable guardrail triggers (timeouts and bound exceedances) perform one controlled retry before forced fallback."
patterns-established:
  - "Fallback behavior is determined by policy trigger + retry budget, not ad-hoc branches."
  - "Response metrics include full per-step/per-tool trace snapshots by default."
requirements-completed: [SAFE-01, SAFE-02, SAFE-03, SAFE-04]
duration: 7 min
completed: 2026-02-27
---

# Phase 02 Plan 02: Fallback and Guardrail Summary

**Retrieve-skill now enforces centralized fallback policy and bounded orchestration controls, with explicit fallback reasons and full trace payloads in metrics.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-27T22:35:20Z
- **Completed:** 2026-02-27T22:42:21Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Added fallback policy engine that maps low-confidence, timeout, exception, and bound triggers to deterministic retry/fallback actions.
- Added global timeout, per-sub-skill timeout, and max-step/hop/branch enforcement with one controlled retry before fallback.
- Added SAFE-focused tests validating low-confidence, timeout, and bound-trigger fallback behavior with trace assertions and partial-evidence preservation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add unified fallback policy engine** - `be2f25d` (feat) + `4fa6a8b` (refactor)
2. **Task 2: Enforce bounded execution and trace-rich fallback handling** - `be2f25d` (feat)
3. **Task 3: Add reliability regression tests for SAFE requirements** - `435401c` (test)

## Files Created/Modified
- `src/memmachine/retrieval_agent/skills/fallback_policy.py` - Trigger/action policy for retry-vs-fallback behavior and reason normalization.
- `src/memmachine/retrieval_agent/skills/retrieve_skill.py` - Guardrail loop, timeout/bound checks, low-confidence fallback, and trace-rich metrics.
- `src/memmachine/retrieval_agent/skills/session_state.py` - Added full trace snapshot helper for metrics surfaces.
- `tests/memmachine/retrieval_agent/test_retrieve_skill_fallback_policy.py` - SAFE regression suite for fallback triggers and retries.
- `tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py` - Updated selector behavior support for compatibility.
- `tests/memmachine/retrieval_agent/test_retrieve_skill_bootstrap.py` - Selector-aware bootstrap failure test adaptation.
- `tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py` - Selector-aware session-state test adaptation.

## Decisions Made
- Count retries against guardrail budget and preserve accumulated episodes across retry/fallback transitions.
- Surface full event/tool/sub-skill trace payload in metrics to match phase requirement for detailed trace visibility.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fallback policy artifact did not meet minimum line threshold**
- **Found during:** `gsd-tools verify artifacts` for `02-02-PLAN.md`
- **Issue:** `fallback_policy.py` was below required minimum line count in plan must-haves.
- **Fix:** Expanded fallback policy module with explicit helper surface (`is_retryable_trigger`, retry-budget helper, reason helper) and reused them in policy decision path.
- **Files modified:** `src/memmachine/retrieval_agent/skills/fallback_policy.py`
- **Verification:** `gsd-tools verify artifacts .planning/phases/02-routing-and-fallback-safety/02-02-PLAN.md` passed.
- **Committed in:** `4fa6a8b`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** No scope expansion; improved policy clarity and satisfied plan artifact gate.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SAFE fallback guarantees and bounded controls are now enforced in top-level orchestration.
- Phase 3 can focus on decomposition skill breadth while relying on stable route/fallback guardrails.

---
*Phase: 02-routing-and-fallback-safety*
*Completed: 2026-02-27*
