# Codebase Structure

**Analysis Date:** 2026-02-27

## Directory Layout

```text
MemMachine/
├── src/                     # Primary source code
│   ├── memmachine/          # Python server/SDK/memory implementation
│   └── memmachine-ts/       # TypeScript REST client package
├── tests/                   # Python test suite + test data
├── docs/                    # Documentation site content
├── integrations/            # Framework/platform adapters
├── examples/                # End-to-end usage examples
├── evaluation/              # Evaluation and benchmark tooling
├── tools/                   # Utility scripts/migrations
├── .planning/               # GSD planning artifacts and codebase map
├── pyproject.toml           # Python workspace/build/test/lint config
├── docker-compose.yml       # Local stack orchestration
└── configuration.yml        # Runtime configuration template/example
```

## Directory Purposes

**`src/memmachine/`:**
- Purpose: Core Python package.
- Contains: API server, memory engines, resource/config abstractions, Python client modules.
- Key files: `main/memmachine.py`, `server/app.py`, `common/resource_manager/resource_manager.py`.

**`src/memmachine-ts/rest_client/`:**
- Purpose: TypeScript REST client library.
- Contains: client/memory/project modules, tests, lint/build/test config.
- Key files: `src/client/memmachine-client.ts`, `package.json`, `tests/*.spec.ts`.

**`tests/memmachine/`:**
- Purpose: Python tests mirroring runtime package layout.
- Contains: subsystem-focused tests and shared fixtures.
- Key files: `tests/memmachine/conftest.py`, `tests/memmachine/server/api_v2/test_router.py`.

**`integrations/` and `examples/`:**
- Purpose: external framework adapters and reference implementations.

**`evaluation/`:**
- Purpose: benchmark-style evaluation scripts and datasets.

## Key File Locations

**Entry Points:**
- `src/memmachine/server/app.py`: main HTTP server bootstrap.
- `src/memmachine/server/mcp_stdio.py`: MCP stdio CLI.
- `src/memmachine/server/mcp_http.py`: MCP HTTP CLI.

**Configuration:**
- `pyproject.toml`: Python deps, scripts, Ruff/pytest/coverage configuration.
- `configuration.yml`: runtime provider and memory settings.
- `src/memmachine-ts/rest_client/tsconfig.json`: TS compiler configuration.

**Core Logic:**
- `src/memmachine/main/memmachine.py`: orchestration facade.
- `src/memmachine/common/resource_manager/`: provider/resource factories.
- `src/memmachine/episodic_memory/` and `src/memmachine/semantic_memory/`: memory subsystems.

**Testing:**
- `tests/memmachine/`: Python tests.
- `src/memmachine-ts/rest_client/tests/`: TypeScript client tests.

**Documentation:**
- `README.md`, `USAGE.md`, `docs/`.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`.
- Python tests use `test_*.py`.
- TS tests use `*.spec.ts`.

**Directories:**
- Domain-first package directories (`common`, `server`, `episodic_memory`, `semantic_memory`, `retrieval_agent`).

**Special Patterns:**
- `packages/` is a symlink mirror of `src/`; search/edit in `src/` to avoid duplicate hits.

## Where to Add New Code

**New API Feature:**
- Router/spec boundary: `src/memmachine/server/api_v2/`.
- Domain implementation: relevant package under `src/memmachine/`.
- Tests: mirrored path under `tests/memmachine/`.

**New Provider Integration:**
- Provider implementation under `src/memmachine/common/{language_model|embedder|reranker|vector_store}/`.
- Provider registration/config models under `src/memmachine/common/configuration/`.
- Integration tests under matching `tests/memmachine/common/` subtree.

**TS REST Client Change:**
- Source in `src/memmachine-ts/rest_client/src/`.
- Tests in `src/memmachine-ts/rest_client/tests/`.

## Special Directories

**`.planning/`:**
- Purpose: GSD planning docs and generated codebase map.
- Committed: yes, if not gitignored by local policy.

**`evaluation/`:**
- Purpose: heavier benchmark flows and datasets; not part of typical unit-test cycle.

---

*Structure analysis: 2026-02-27*
*Update when directory layout changes materially*
