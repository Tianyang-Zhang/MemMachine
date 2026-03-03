---
phase: 06-replace-legacy-agent-terminology-code-with-skill-terminology-runtime-across-codebase
plan: "01"
subsystem: retrieval-runtime
tags: [retrieval, skill-api, compatibility]
requires:
  - phase: 05-functional-benchmark-gate
    provides: Skill-based runtime baseline and benchmark wiring
provides:
  - Canonical retrieval skill interface module
  - Compatibility shim for legacy agent interface imports
  - Skill-first service locator entrypoint
affects: [phase-06-02, phase-06-03]
tech-stack:
  added: []
  patterns: [interface-first migration, compatibility shim]
key-files:
  created:
    - src/memmachine/retrieval_agent/common/skill_api.py
    - tests/memmachine/retrieval_agent/test_skill_interface_contract.py
  modified:
    - src/memmachine/retrieval_agent/common/agent_api.py
    - src/memmachine/retrieval_agent/service_locator.py
    - src/memmachine/retrieval_agent/skills/retrieve_skill.py
key-decisions:
  - "Introduced `skill_api.py` as canonical contract and kept `agent_api.py` as transition shim."
  - "Added `create_retrieval_skill(...)` entrypoint while retaining `create_retrieval_agent(...)` wrapper for compatibility."
patterns-established:
  - "Retrieval runtime should consume `skill_name`/`skill_description` instead of agent naming."
requirements-completed: [MIGR-04]
duration: 45min
completed: 2026-03-02
---

# Phase 06-01 Summary

**Canonical retrieval skill interfaces were introduced with compatibility shims so runtime wiring can migrate from agent naming to skill naming without behavioral regressions.**

## Performance

- **Duration:** 45 min
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Added `skill_api.py` with canonical `SkillToolBase` / `SkillToolBaseParam`
  and compatibility aliases for legacy `agent_*` accessors.
- Reduced `agent_api.py` to a compatibility shim so existing imports continue
  to function while new code can use skill-first contracts.
- Introduced `create_retrieval_skill(...)` as canonical constructor and updated
  retrieval runtime modules to consume skill-base interfaces.
- Added targeted interface tests to prevent accidental reversal of the
  compatibility direction.

## Verification

- `ruff check` passed for changed retrieval runtime/interface files.
- `pytest` passed:
  - `tests/memmachine/retrieval_agent/test_skill_interface_contract.py`
  - `tests/memmachine/retrieval_agent/test_retrieve_skill_bootstrap.py`
  - `tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py`
  - `tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py`
  - `tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py`

## Deviations from Plan

None.

## Next Phase Readiness

Wave 2 can now migrate runtime labels/metrics/specs to canonical skill naming
without blocking import-level compatibility issues.
