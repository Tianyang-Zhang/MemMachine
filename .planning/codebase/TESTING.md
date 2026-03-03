# Testing Patterns

**Analysis Date:** 2026-02-27

## Test Framework

**Runner:**
- Python: `pytest` with `pytest-asyncio` and marker config in `pyproject.toml`.
- TypeScript REST client: `jest` with `ts-jest` (`src/memmachine-ts/rest_client/jest.config.ts`).

**Run Commands:**
```bash
uv run pytest                                      # Run Python tests (excluding integration by default)
uv run pytest -m integration                       # Integration-marked tests
uv run pytest tests/memmachine/server/api_v2/test_router.py
cd src/memmachine-ts/rest_client && npm run test   # Run TS client tests
```

## Test File Organization

**Location:**
- Python tests under `tests/memmachine/`, generally mirroring `src/memmachine/` package layout.
- TS tests under `src/memmachine-ts/rest_client/tests/`.

**Naming:**
- Python: `test_*.py`.
- TS: `*.spec.ts`.

## Test Structure

**Patterns:**
- Arrange/act/assert style is common in both Python and TS tests.
- Async tests are widespread in server/storage/retrieval paths.
- Domain-specific fixtures in `tests/memmachine/conftest.py` support integration environments.

## Mocking

**Framework:**
- Python uses `unittest.mock` and pytest fixtures.
- TS uses `jest.spyOn` and mock-resolved/rejected responses.

**What gets mocked:**
- External provider clients and network/database edges.
- Expensive dependencies in unit-level tests.

## Fixtures and Factories

**Shared fixtures:**
- `tests/memmachine/conftest.py` provides reusable mock providers, optional cloud fixtures, and container-backed integration fixtures.

**Environment-aware behavior:**
- Integration fixtures skip when required credentials or Docker runtime are unavailable.

## Coverage

**Configuration:**
- Coverage source target is `src/memmachine` (`[tool.coverage.run]` in `pyproject.toml`).
- `pytest-cov` is included in dev dependency group.

**Policy:**
- No hard minimum is enforced in `pyproject.toml`; coverage is used as quality feedback.

## Test Types

**Unit Tests:**
- Validate focused modules and transformation logic in isolation.

**Integration Tests:**
- Exercise DB/provider interactions (Neo4j, Postgres, cloud model providers) with optional runtime skips.

**Client Tests:**
- TS package tests verify request construction and API error handling.

## Common Patterns

**Async Assertions:**
- Python uses `await` with pytest async support.
- TS uses `await expect(...).rejects.toThrow(...)` for failure paths.

**Regression Risk Areas to Prioritize:**
- API v2 router/service behavior.
- Retrieval-agent routing behavior.
- Resource manager initialization and fallback logic.

---

*Testing analysis: 2026-02-27*
*Update when frameworks, markers, or execution flow changes*
