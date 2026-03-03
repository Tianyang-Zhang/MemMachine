# Technology Stack

**Analysis Date:** 2026-02-27

## Languages

**Primary:**
- Python 3.12+ - Main server, memory engines, Python SDK (`pyproject.toml`, `src/memmachine/`).

**Secondary:**
- TypeScript 5.x - REST client package in `src/memmachine-ts/rest_client/`.
- Shell/YAML/Markdown - Docker, ops scripts, docs, and examples.

## Runtime

**Environment:**
- CPython 3.12+ (`requires-python = ">= 3.12"`).
- Node.js >=20.19.0 for the TypeScript REST client package (`src/memmachine-ts/rest_client/package.json`).

**Package Manager:**
- `uv` workspace for Python dependencies and scripts (`uv.lock`, `pyproject.toml`).
- `npm` for TypeScript REST client package workflows.

## Frameworks

**Core:**
- FastAPI + Uvicorn for HTTP API server (`src/memmachine/server/app.py`).
- FastMCP for MCP transport (`src/memmachine/server/mcp_stdio.py`, `src/memmachine/server/mcp_http.py`).
- Pydantic v2 for API/config models (`src/memmachine/common/configuration/`, `src/memmachine/common/api/spec.py`).

**Testing:**
- Pytest + pytest-asyncio for Python test suite (`tests/memmachine/`).
- Jest + ts-jest for TypeScript REST client tests (`src/memmachine-ts/rest_client/jest.config.ts`).

**Build/Dev:**
- Ruff (format + lint), ty (type checking), complexipy (complexity checks).
- tsup + TypeScript compiler for TS package builds.

## Key Dependencies

**Critical:**
- `neo4j` - Episodic/vector graph storage backend (`src/memmachine/common/vector_graph_store/neo4j_vector_graph_store.py`).
- `sqlalchemy` + `asyncpg` + `pgvector` - SQL storage and vector-enabled semantic data paths.
- `openai`, `boto3`, `cohere` - LLM/embedder/reranker provider integrations.
- `prometheus-client` - Metrics endpoint instrumentation.

**Infrastructure:**
- `docker-compose.yml` coordinates Postgres (pgvector), Neo4j, app, and docs services.

## Configuration

**Environment:**
- Runtime settings loaded from `configuration.yml` and environment variables.
- `.env` support loaded in server entrypoint (`src/memmachine/server/app.py`).

**Build:**
- Python build and tooling config in `pyproject.toml`.
- TS client build/lint/test config in `src/memmachine-ts/rest_client/` (`package.json`, `tsconfig.json`, `eslint.config.mjs`).

## Platform Requirements

**Development:**
- Python 3.12+, `uv`, and optionally Docker for integration tests.
- Node.js >=20.19.0 when modifying `src/memmachine-ts/rest_client/`.

**Production:**
- MemMachine server runs as Python process or Docker container.
- Persistent dependencies: PostgreSQL (with pgvector) and Neo4j.

---

*Stack analysis: 2026-02-27*
*Update after major dependency or runtime changes*
