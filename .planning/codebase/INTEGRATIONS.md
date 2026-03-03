# External Integrations

**Analysis Date:** 2026-02-27

## APIs & External Services

**LLM and Embedding Providers:**
- OpenAI provider integrations for model + embedding calls (`src/memmachine/common/language_model/openai_*.py`, `src/memmachine/common/embedder/openai_embedder.py`).
- Amazon Bedrock integrations for language model, embedder, and reranker flows (`src/memmachine/common/language_model/amazon_bedrock_language_model.py`, `src/memmachine/common/embedder/amazon_bedrock_embedder.py`, `src/memmachine/common/reranker/amazon_bedrock_reranker.py`).
- Cohere reranker integration (`src/memmachine/common/reranker/cohere_reranker.py`).
- OpenAI-compatible endpoints (including local Ollama-style endpoints) via configurable base URLs.

**Protocol Surfaces:**
- REST API v2 (`src/memmachine/server/api_v2/router.py`).
- MCP server over stdio and HTTP (`src/memmachine/server/mcp_stdio.py`, `src/memmachine/server/mcp_http.py`).

## Data Storage

**Databases:**
- Neo4j graph/vector storage for episodic memory and graph operations.
- PostgreSQL + pgvector for semantic/config/session persistence.
- SQLite path used in some local/test scenarios (`configuration.yml`).

**File/Config Storage:**
- App configuration from `configuration.yml` and env.
- Alembic migration history in `src/memmachine/semantic_memory/storage/alembic_pg/versions/`.

## Authentication & Identity

**Current State:**
- No centralized user-auth provider is embedded as a core runtime dependency.
- API-level project/session context is carried via org/project fields in request models.

## Monitoring & Observability

**Metrics:**
- Prometheus metric export endpoint in API router (`/api/v2/metrics`).

**Logging:**
- Structured Python logging configured by `logging` section of `configuration.yml` and server startup code.

## CI/CD & Deployment

**Hosting:**
- Docker Compose path includes `memmachine`, `postgres`, `neo4j`, and `docs` services (`docker-compose.yml`).

**CI Pipeline:**
- GitHub Actions workflows exist in `.github/workflows/`.

## Environment Configuration

**Development:**
- Typical setup uses local Docker services and `uv` tooling.
- Optional cloud credentials are required for integration tests that target external providers.

**Production:**
- Use environment variables and a sanitized config file; avoid committing secrets.
- Multiple workers are supported through `MEMMACHINE_WORKERS`.

## Webhooks & Callbacks

**Incoming/Outgoing Webhooks:**
- No first-class webhook subsystem identified in core server modules.
- Integrations primarily occur through API/MCP and provider SDK calls.

## Ecosystem Integrations

**Framework Adapters:**
- Integration examples under `integrations/` include `langchain`, `langgraph`, `crewai`, `llamaindex`, `n8n`, `dify`, `fastgpt`, and `aws_strands_agent_sdk`.
- Example apps are available under `examples/` and `examples/ts_rest_client_demo/`.

---

*Integration audit: 2026-02-27*
*Update when adding or removing external services*
