# Architecture

**Analysis Date:** 2026-02-27

## Pattern Overview

**Overall:** Modular Python service with layered API transports and pluggable memory resources.

**Key Characteristics:**
- Async-first server/runtime paths.
- Multiple transport entrypoints (REST and MCP).
- Memory subsystems split into episodic, semantic, and retrieval-agent orchestration.
- Resource-manager pattern for lazy provider construction and validation.

## Layers

**Transport Layer:**
- Purpose: Expose APIs and protocol adapters.
- Contains: FastAPI app, API v2 routers/services, MCP entrypoints.
- Depends on: Core orchestration (`MemMachine`) and request/response models.
- Used by: External clients, framework integrations, and tools.

**Orchestration Layer:**
- Purpose: Coordinate memory operations and lifecycle.
- Contains: `MemMachine` in `src/memmachine/main/memmachine.py`.
- Depends on: Resource manager, episodic/semantic managers, retrieval-agent factory.
- Used by: API service layer and MCP resources.

**Resource Layer:**
- Purpose: Construct and cache DB/model/embedder/reranker resources.
- Contains: `src/memmachine/common/resource_manager/` modules.
- Depends on: Config models + provider implementations.
- Used by: Memory services and orchestration layer.

**Memory Domain Layer:**
- Purpose: Implement storage/query behavior for different memory types.
- Contains: `episodic_memory/`, `semantic_memory/`, `retrieval_agent/` packages.
- Depends on: Resource layer abstractions.
- Used by: `MemMachine` core flows.

## Data Flow

**REST Request Flow:**
1. Client calls endpoint in `src/memmachine/server/api_v2/router.py`.
2. Router validates request via Pydantic spec models.
3. Service layer maps request to `_SessionData` and delegates to `MemMachine`.
4. `MemMachine` resolves target memory systems and resources.
5. Domain memory modules perform DB/model operations.
6. Service maps domain models back to API response models.

**MCP Tool Flow:**
1. MCP client starts stdio or HTTP entrypoint.
2. Global lifespan initializes `MemMachine` resources.
3. MCP tools call shared service logic for memory actions.
4. Results are returned over MCP transport.

**State Management:**
- Session state is keyed by `org_id/project_id`.
- Long-lived data is in Neo4j + SQL stores; runtime is otherwise mostly stateless per request.

## Key Abstractions

**`MemMachine`:**
- Purpose: High-level coordinator for lifecycle and memory operations.
- Examples: search/add/list/delete/configuration operations.
- Pattern: Facade over subsystem managers.

**`ResourceManagerImpl`:**
- Purpose: Central resource lookup and lazy initialization.
- Examples: database engines, embedders, rerankers, language models.
- Pattern: Registry + provider manager composition.

**`AgentToolBase` retrieval interface:**
- Purpose: Standard contract for retrieval-agent tools.
- Examples: `ToolSelectAgent`, `ChainOfQueryAgent`, `SplitQueryAgent`.
- Pattern: Tool-routing strategy with async execution.

## Entry Points

**HTTP Server:**
- Location: `src/memmachine/server/app.py`.
- Triggers: `memmachine-server` CLI or container startup.
- Responsibilities: mount routers, setup middleware, run uvicorn workers.

**MCP Stdio:**
- Location: `src/memmachine/server/mcp_stdio.py`.
- Triggers: `memmachine-mcp-stdio` CLI.
- Responsibilities: initialize lifespan resources and run MCP over stdio.

**MCP HTTP:**
- Location: `src/memmachine/server/mcp_http.py`.
- Triggers: `memmachine-mcp-http` CLI.
- Responsibilities: run MCP app over uvicorn with configurable host/port.

## Error Handling

**Strategy:** Raise domain/config errors in lower layers and normalize at API boundaries.

**Patterns:**
- Router catches domain exceptions and maps to `RestError` with status codes.
- Lifecycle code logs crash context and handles keyboard interrupts gracefully.
- Validation failures use explicit handlers for consistent payload shape.

## Cross-Cutting Concerns

**Logging:**
- Python `logging` used across server and subsystems.

**Validation:**
- Pydantic models at API/config boundaries.

**Metrics:**
- Prometheus instrumentation exposed on API endpoint.

---

*Architecture analysis: 2026-02-27*
*Update when major patterns or boundaries change*
