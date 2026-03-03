---
phase: 06-replace-legacy-agent-terminology-code-with-skill-terminology-runtime-across-codebase
plan: "02"
subsystem: retrieval-runtime
wave: 2
tags: [retrieval, runtime, skill-terminology]
requires:
  - phase: 06-replace-legacy-agent-terminology-code-with-skill-terminology-runtime-across-codebase
    plan: "01"
    provides: Canonical skill-first interfaces
provides:
  - Skill-only route/sub-skill orchestration metrics
  - Skill-first runtime state naming and route labels
  - Markdown specs aligned to skill terminology
affects: [phase-06-03]
tech-stack:
  added: []
  patterns: [runtime contract normalization]
key-files:
  created: []
  modified:
    - src/memmachine/retrieval_agent/skills/retrieve_skill.py
    - src/memmachine/retrieval_agent/agents/tool_select_agent.py
    - src/memmachine/retrieval_agent/skills/specs/sub_skills/tool_select.md
    - tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py
    - tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py
key-decisions:
  - "Normalized selector output and top-level orchestration metrics around `selected_skill`/`selected_skill_name` only."
  - "Removed retrieval runtime dependence on legacy `selected_tool` contract keys in active paths."
patterns-established:
  - "Top-level and sub-skill contracts should emit skill labels only."
requirements-completed: [MIGR-04]
duration: 30min
completed: 2026-03-02
---

# Phase 06-02 Summary

**Retrieval runtime contracts now use skill terminology end-to-end for route selection, sub-skill runs, and orchestration metrics.**

## Accomplishments

- Completed runtime naming migration from tool/agent-style labels to skill labels in
  top-level orchestration and selector metrics.
- Updated retrieval test contracts to assert `selected_skill_name` and
  skill-labeled orchestration traces.
- Removed remaining runtime-local references to `selected_tool` in active retrieval
  strategy code.

## Verification

- `.venv/bin/ruff check src/memmachine/retrieval_agent`
- `.venv/bin/pytest tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py tests/memmachine/retrieval_agent/test_route_policy.py -q`

## Deviations from Plan

None.

## Next Phase Readiness

Wave 3 can safely remove compatibility aliases and cut over API/evaluation/test
callers to skill-first naming without runtime contract drift.
