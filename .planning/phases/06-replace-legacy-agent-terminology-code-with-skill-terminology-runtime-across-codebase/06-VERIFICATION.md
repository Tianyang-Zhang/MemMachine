---
phase: 06-replace-legacy-agent-terminology-code-with-skill-terminology-runtime-across-codebase
verified: 2026-03-02T08:25:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 06 Verification Report

## Goal Achievement

1. Retrieval runtime and strategy contracts are skill-first (`skill`,
   `skill_name`, `selected_skill_name`) in active execution paths.
2. Top-level caller wiring (runtime/API/evaluation/tests) uses
   `create_retrieval_skill` and skill-mode/skill-trace terminology.
3. Legacy retrieval alias contracts (`create_retrieval_agent`, `AgentToolBase*`,
   `agent_name`) were removed from active retrieval runtime and tests.

## Verification Evidence

- Lint:
  - `.venv/bin/ruff check src/memmachine/retrieval_agent src/memmachine/main/memmachine.py src/memmachine/common/api/doc.py src/memmachine/common/api/spec.py src/memmachine/server/api_v2/service.py src/memmachine/server/api_v2/mcp.py src/memmachine/rest_client/memory.py evaluation/utils/agent_utils.py evaluation/retrieval_agent/wikimultihop_search.py evaluation/retrieval_agent/hotpotQA_test.py evaluation/retrieval_agent/longmemeval_test.py evaluation/retrieval_agent/locomo_search.py evaluation/retrieval_agent/tool/wikimultihop_skill_search.py evaluation/retrieval_agent/generate_scores.py tests/memmachine/retrieval_agent tests/memmachine/main/test_memmachine_mock.py tests/memmachine/server/api_v2/test_router.py tests/memmachine/server/api_v2/test_mcp.py tests/memmachine/rest_client/test_memory.py`
- Tests:
  - `.venv/bin/pytest tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py tests/memmachine/retrieval_agent/test_route_policy.py -q`
  - `.venv/bin/pytest tests/memmachine/main/test_memmachine_mock.py tests/memmachine/server/api_v2/test_router.py tests/memmachine/retrieval_agent/test_retrieval_agent.py -q`
  - `.venv/bin/pytest tests/memmachine/retrieval_agent/test_retrieve_skill_orchestration_loop.py tests/memmachine/retrieval_agent/test_retrieve_skill_session_state.py tests/memmachine/retrieval_agent/test_route_policy.py tests/memmachine/retrieval_agent/test_retrieve_skill_route_selection.py tests/memmachine/retrieval_agent/test_retrieve_skill_bootstrap.py tests/memmachine/retrieval_agent/test_retrieve_skill_fallback_policy.py tests/memmachine/retrieval_agent/test_retrieval_agent.py tests/memmachine/retrieval_agent/test_skill_interface_contract.py tests/memmachine/main/test_memmachine_mock.py tests/memmachine/server/api_v2/test_router.py tests/memmachine/server/api_v2/test_mcp.py tests/memmachine/rest_client/test_memory.py -q`
- Guard check:
  - `! rg -n "agent_name|MemMachineAgent|SplitQueryAgent|ChainOfQueryAgent|ToolSelectAgent" src/memmachine/retrieval_agent tests/memmachine/retrieval_agent --glob '*.py'`
