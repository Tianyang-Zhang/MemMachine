# Coding Conventions

**Analysis Date:** 2026-02-27

## Naming Patterns

**Files:**
- Python modules use `snake_case.py`.
- Python tests use `test_*.py`.
- TypeScript client tests use `*.spec.ts` under `src/memmachine-ts/rest_client/tests/`.

**Functions and Variables:**
- Python: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- TypeScript client: `camelCase` for values/functions, `PascalCase` for classes/types.

**Types:**
- Python favors explicit annotations (`list[str]`, `dict[str, int]`, typed Pydantic models).
- TypeScript uses strict compiler settings and explicit types over `any`.

## Code Style

**Formatting:**
- Python formatting is Ruff-driven (`uv run ruff format`).
- TS client formatting uses Prettier (`npm run format`).

**Linting:**
- Python linting uses Ruff (`uv run ruff check`) with project-wide config in `pyproject.toml`.
- TS linting uses ESLint (`npm run lint`) with import ordering rules.

## Import Organization

**Order:**
1. Python stdlib imports.
2. Third-party imports.
3. Local package imports.

**Grouping:**
- Keep imports explicit; avoid wildcard imports.
- In TS client, ESLint enforces grouped import ordering.

## Error Handling

**Patterns:**
- Raise explicit exceptions with context in core modules.
- At API boundary, map domain errors to `RestError` responses.
- Preserve exception causes via `raise ... from err` where appropriate.

**Async/Error Boundaries:**
- Async interfaces are used consistently in server/storage/model paths.
- Avoid blocking calls in async contexts.

## Logging

**Framework:**
- Python `logging` with configured format/level/path.

**Patterns:**
- Log lifecycle transitions and resource failures in startup paths.
- Keep log responsibility near subsystem boundaries.

## Comments

**When to Comment:**
- Explain design intent and non-obvious behavior.
- Avoid redundant comments that restate code.

**Docstrings:**
- Public methods and important modules commonly include docstrings.

## Function Design

**Size and Scope:**
- Favor small, testable units with clear boundaries.
- Keep API layer thin; delegate to service/orchestration layers.

**Parameters and Returns:**
- Prefer typed objects for structured inputs.
- Normalize outputs through spec models at transport boundaries.

## Module Design

**Exports:**
- Python modules expose explicit classes/functions; avoid broad side effects.
- TS client uses index exports per submodule (`src/*/index.ts`).

**Layering:**
- Keep provider implementations in `common/` and domain orchestration in memory subpackages.

---

*Convention analysis: 2026-02-27*
*Update when lint/type rules or coding norms change*
