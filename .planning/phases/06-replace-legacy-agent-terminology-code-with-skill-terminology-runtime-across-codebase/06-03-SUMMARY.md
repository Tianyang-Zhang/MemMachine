---
phase: 06-replace-legacy-agent-terminology-code-with-skill-terminology-runtime-across-codebase
plan: "03"
subsystem: caller-cutover
wave: 3
tags: [retrieval, api, evaluation, tests, cleanup]
requires:
  - phase: 06-replace-legacy-agent-terminology-code-with-skill-terminology-runtime-across-codebase
    plan: "02"
    provides: Skill-first runtime metrics and contracts
provides:
  - Skill-first retrieval constructor and interface usage across callers
  - API request/trace terminology aligned to skill mode
  - Evaluation and benchmark helpers emitting skill labels
  - Legacy retrieval alias removal in active runtime paths
affects: []
tech-stack:
  added: []
  patterns: [caller cutover, contract hardening]
key-files:
  created: []
  modified:
    - src/memmachine/retrieval_agent/service_locator.py
    - src/memmachine/retrieval_agent/__init__.py
    - src/memmachine/retrieval_agent/common/skill_api.py
    - src/memmachine/main/memmachine.py
    - src/memmachine/common/api/doc.py
    - src/memmachine/common/api/spec.py
    - src/memmachine/server/api_v2/service.py
    - src/memmachine/server/api_v2/mcp.py
    - evaluation/utils/agent_utils.py
    - evaluation/retrieval_agent/wikimultihop_search.py
    - evaluation/retrieval_agent/hotpotQA_test.py
    - evaluation/retrieval_agent/longmemeval_test.py
    - evaluation/retrieval_agent/locomo_search.py
    - evaluation/retrieval_agent/generate_scores.py
    - evaluation/retrieval_agent/tool/wikimultihop_skill_search.py
    - tests/memmachine/main/test_memmachine_mock.py
    - tests/memmachine/server/api_v2/test_router.py
    - tests/memmachine/server/api_v2/test_mcp.py
    - tests/memmachine/rest_client/test_memory.py
    - tests/memmachine/retrieval_agent/test_retrieval_agent.py
    - tests/memmachine/retrieval_agent/test_skill_interface_contract.py
  deleted:
    - src/memmachine/retrieval_agent/common/agent_api.py
key-decisions:
  - "`create_retrieval_skill` is now the only retrieval constructor; legacy wrapper removed."
  - "`skill_mode` is the canonical API request flag; `retrieval_trace.skill` is the canonical top-level trace label."
  - "Removed retrieval runtime compatibility aliases (`agent_name`, `AgentToolBase*`) from active code paths."
patterns-established:
  - "Skill-first naming is mandatory across runtime, API, tests, and evaluation outputs."
requirements-completed: [MIGR-04]
duration: 95min
completed: 2026-03-02
---

# Phase 06-03 Summary

**All active retrieval callers now use skill-first naming, and legacy retrieval-agent aliases were removed from runtime paths.**

## Accomplishments

- Removed `create_retrieval_agent` and switched all runtime/test callsites to
  `create_retrieval_skill`.
- Deleted `agent_api.py` compatibility shim and migrated callsites to
  `skill_api.py` directly.
- Updated MemMachine retrieval orchestration internals to `skill_mode`,
  `retrieval_skill`, and `retrieval_trace.skill` naming.
- Updated API/mcp/service layers and tests to use skill terminology in request
  and trace contracts.
- Migrated evaluation/benchmark helpers to skill-centric labels and output keys.

## Verification

- `.venv/bin/ruff check` on all changed retrieval/API/evaluation/test files
- `.venv/bin/pytest tests/memmachine/main/test_memmachine_mock.py tests/memmachine/server/api_v2/test_router.py tests/memmachine/retrieval_agent/test_retrieval_agent.py -q`
- `.venv/bin/pytest tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py tests/memmachine/retrieval_agent/test_route_policy.py -q`
- `.venv/bin/pytest tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py tests/memmachine/retrieval_agent/test_route_policy.py tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py tests/memmachine/retrieval_agent/test_retrieve_skill_bootstrap.py tests/memmachine/retrieval_agent/test_retrieve_skill_fallback_policy.py tests/memmachine/retrieval_agent/test_retrieval_agent.py tests/memmachine/retrieval_agent/test_skill_interface_contract.py tests/memmachine/main/test_memmachine_mock.py tests/memmachine/server/api_v2/test_router.py tests/memmachine/server/api_v2/test_mcp.py tests/memmachine/rest_client/test_memory.py -q`
- `! rg -n "agent_name|MemMachineAgent|SplitQueryAgent|ChainOfQueryAgent|ToolSelectAgent" src/memmachine/retrieval_agent tests/memmachine/retrieval_agent --glob '*.py'`

## Deviations from Plan

- Kept compatibility aliases for `agent_mode` only at API/model boundaries to
  avoid abrupt external breakage while making `skill_mode` canonical.

## Next Phase Readiness

Phase 06 requirement (`MIGR-04`) is now satisfied for active retrieval runtime,
caller, and test paths.
