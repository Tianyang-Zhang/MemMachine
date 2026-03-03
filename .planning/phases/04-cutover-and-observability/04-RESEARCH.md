# Phase 04 Research

## Findings

- Service locator still built and returned legacy top-level routes.
- Search API omitted retrieval-agent trace metadata even though RetrieveSkill
  already produced detailed orchestration metrics.
- Existing router tests could cover additive optional response fields without
  breaking current clients.

## Strategy

- Collapse service locator to strict `RetrieveSkill` construction.
- Promote retrieval trace to `MemMachine.SearchResponse` and API DTOs as
  optional `retrieval_trace`.
- Add compatibility metric keys from `RetrieveSkill` (`agent`, `selected_tool`)
  for benchmark consumers.
