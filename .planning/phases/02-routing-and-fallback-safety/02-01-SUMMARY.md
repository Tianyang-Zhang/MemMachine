---
phase: 02-routing-and-fallback-safety
plan: "01"
subsystem: api
tags: [retrieval-agent, route-selection, select-skill, confidence, guardrails]
requires:
  - phase: 01.1-top-level-llm-markdown-orchestration-gap-closure
    provides: markdown-driven top-level orchestration and persistent session state
provides:
  - Deterministic select-skill route decision contract
  - Selector retry/tie-break behavior for unclassifiable and borderline routes
  - Route-selection integration coverage for retrieve-skill
affects: [phase-02-plan-02-fallback-policy, phase-03-decomposition-skills]
tech-stack:
  added: []
  patterns: [route-contract-first, selector-retry-tie-break]
key-files:
  created:
    - src/memmachine/retrieval_agent/skills/route_policy.py
    - tests/memmachine/retrieval_agent/test_route_policy.py
    - tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py
  modified:
    - src/memmachine/retrieval_agent/skills/retrieve_skill.py
    - src/memmachine/retrieval_agent/skills/specs/top_level/retrieve_skill.md
    - src/memmachine/retrieval_agent/skills/types.py
key-decisions:
  - "Route selection uses one model-driven select-skill contract with deterministic fields and confidence range validation."
  - "Selector retries once when unclassifiable or low-confidence, then resolves conflicts by choosing higher confidence."
patterns-established:
  - "Top-level route decision is resolved before orchestration tool calls and surfaced in metrics."
  - "Legacy selector labels are normalized into route-contract outputs for compatibility."
requirements-completed: [ROUT-01, SAFE-04]
duration: 4 min
completed: 2026-02-27
---

# Phase 02 Plan 01: Route Selection Policy Summary

**Retrieve-skill now performs explicit select-skill route decisioning with strict confidence/reason contracts and deterministic retry/tie-break behavior.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-27T22:31:12Z
- **Completed:** 2026-02-27T22:35:19Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Added a strict route-policy module for select-skill decision parsing and reconciliation.
- Integrated route decision selection into `RetrieveSkill` before top-level tool orchestration.
- Added route-focused tests for contract parsing, retry behavior, and confidence-based conflict resolution.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add route decision contract and parser** - `6fd12b9` (feat)
2. **Task 2: Integrate selector retry and conflict tie-break into RetrieveSkill** - `6fd12b9` (feat, same commit as Task 1)
3. **Task 3: Add route-selection integration tests** - `bd3788d` (test)

## Files Created/Modified
- `src/memmachine/retrieval_agent/skills/route_policy.py` - Route decision parser, legacy normalization, and retry tie-break logic.
- `src/memmachine/retrieval_agent/skills/retrieve_skill.py` - Selector invocation, decision metrics, and route-aware top-level prompting.
- `src/memmachine/retrieval_agent/skills/types.py` - Added strict `RouteDecisionV1` contract.
- `src/memmachine/retrieval_agent/skills/specs/top_level/retrieve_skill.md` - Updated rules to align with select-skill route decision usage.
- `tests/memmachine/retrieval_agent/test_route_policy.py` - Unit tests for route parsing and decision reconciliation.
- `tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py` - Integration tests for selector retry and conflict resolution.

## Decisions Made
- Kept route contract strict (`selected_route`, `confidence_score`, `reason_code`, optional reason note/fallback reason).
- Added compatibility parsing for legacy route labels so existing model outputs do not break routing behavior.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Route decisions are deterministic and surfaced in metrics.
- Phase 02-02 can now enforce fallback policies and hard guardrails against low confidence/timeouts/bound overflows.

---
*Phase: 02-routing-and-fallback-safety*
*Completed: 2026-02-27*
