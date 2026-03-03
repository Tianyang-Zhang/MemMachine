# 04-01 Summary

## Completed

- `create_retrieval_agent(...)` now always returns `RetrieveSkill`; legacy
  route names are ignored with a warning.
- Route policy parser now rejects non-JSON legacy selector payloads.
- Retrieval-agent tests updated accordingly.

## Verification

- `.venv/bin/pytest tests/memmachine/retrieval_agent/test_route_policy.py tests/memmachine/retrieval_agent/test_retrieval_agent.py -q` passed.
