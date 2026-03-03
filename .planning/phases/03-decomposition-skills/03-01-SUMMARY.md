---
phase: 03-decomposition-skills
plan: "01"
subsystem: retrieval-agent
tags: [tool-select, coq, pass-through, selector-safety]
requires:
  - phase: 02.2-refactor-retrieval-skill-runtime-to-use-new-live-session-language-model-and-enforce-single-top-level-llm-call-per-query
    provides: single top-level live-session orchestration baseline
provides:
  - Selector contract normalization (`selected_skill` + compatible `selected_route`)
  - Selector malformed-summary retry-once then deterministic fallback
  - Low-confidence selector guardrail fallback to direct memory
  - Markdown specs for top-level retrieve policy and `coq` sub-skill policy
affects: [phase-03-plan-02]
tech-stack:
  added: []
  patterns: [contract-normalization, fail-closed-selector, markdown-policy]
key-files:
  modified:
    - src/memmachine/retrieval_agent/skills/retrieve_skill.py
    - src/memmachine/retrieval_agent/skills/types.py
    - src/memmachine/retrieval_agent/skills/route_policy.py
    - src/memmachine/retrieval_agent/skills/specs/top_level/retrieve_skill.md
    - src/memmachine/retrieval_agent/skills/specs/sub_skills/tool_select.md
    - src/memmachine/retrieval_agent/skills/specs/sub_skills/coq.md
    - tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py
requirements-completed: [ROUT-02, ORCH-02]
duration: 1 session
completed: 2026-02-28
---

# Phase 03 Plan 01 Summary

Implemented selector pass-through safety and coq decomposition foundations.

## Accomplishments
- Updated route-decision contract to support `selected_skill` (`direct_memory`,
  `coq`, `split`) while retaining `selected_route` compatibility.
- Added runtime enforcement: malformed selector summary retries once, then
  deterministic fallback; low-confidence selector decisions also trigger
  fallback.
- Added/updated markdown policies for top-level retrieve orchestration,
  `tool_select`, and new `coq` sub-skill.
- Added regression tests for selector retry and low-confidence fallback.

## Verification
- `.venv/bin/ruff check src/memmachine/retrieval_agent/skills tests/memmachine/retrieval_agent/test_route_policy.py tests/memmachine/retrieval_agent/test_skill_markdown_specs.py tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py`
- `.venv/bin/pytest tests/memmachine/retrieval_agent/test_route_policy.py tests/memmachine/retrieval_agent/test_skill_markdown_specs.py tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py`

---
*Phase: 03-decomposition-skills*
*Completed: 2026-02-28*
