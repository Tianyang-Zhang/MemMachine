# Codebase Concerns

**Analysis Date:** 2026-02-27

## Tech Debt

**Configuration and environment split:**
- Issue: `configuration.yml` mixes example-like fields and production-shaped values.
- Why: Local convenience and broad provider support evolved in one file.
- Impact: Increases risk of misconfiguration and accidental secret leakage.
- Fix approach: split into `configuration.example.yml` + env-driven runtime secrets.

**Large orchestration surface in `MemMachine`:**
- Issue: Core class owns many responsibilities (defaults, lifecycle, routing).
- Why: Centralization reduced initial integration complexity.
- Impact: Higher regression risk when changing startup/query behavior.
- Fix approach: continue extracting subsystem services with focused unit tests.

## Known Bugs / Fragility Signals

**Environment-dependent test behavior:**
- Symptoms: Integration tests skip frequently based on credentials/Docker availability.
- Trigger: Missing cloud keys or unavailable Docker daemon.
- Workaround: Run only targeted unit tests when infra is unavailable.
- Root cause: Heavy integration surface with optional external providers.

## Security Considerations

**Committed credentials risk:**
- Risk: `configuration.yml` currently contains credential-shaped values.
- Current mitigation: none visible at repository boundary.
- Recommendations: rotate affected credentials, scrub committed values, enforce secret scanning in CI.

**Provider credential sprawl:**
- Risk: multiple provider integrations increase exposed secret surface.
- Current mitigation: partial env usage, but not consistently enforced.
- Recommendations: centralize secret-loading strategy and add startup validation warnings.

## Performance Bottlenecks

**Retrieval-agent fan-out and reranking paths:**
- Problem: Query decomposition and reranking can trigger multiple expensive model/store calls.
- Measurement: No consolidated baseline in repo docs.
- Cause: Multi-tool retrieval quality strategy prioritizes recall.
- Improvement path: add timing metrics by stage and cache/memoization for repeated lookups.

**Cold start in full dependency mode:**
- Problem: initializing external clients/stores can delay startup.
- Cause: heavy provider matrix and database readiness requirements.
- Improvement path: optional lazy initialization and clearer health/readiness diagnostics.

## Fragile Areas

**API model and service coupling:**
- Why fragile: spec model changes can silently break service translation.
- Common failures: response shape drift and optional-field regressions.
- Safe modification: update router/service tests together (`tests/memmachine/server/api_v2/`).
- Test coverage: good base coverage exists, but edge-case expansion is still valuable.

**Retrieval-agent prompt/routing contracts:**
- Why fragile: behavior depends on prompt text and model output formatting.
- Common failures: tool selection drift, query decomposition quality shifts.
- Safe modification: add regression fixtures for representative query sets.
- Test coverage: targeted tests exist, but decision-quality regression tests are limited.

## Scaling Limits

**Stateful external dependencies:**
- Current capacity: bounded by Postgres, Neo4j, and model provider throughput.
- Limit: concurrency and latency degrade when providers or DBs saturate.
- Symptoms at limit: timeouts, slower search latency, resource exhaustion.
- Scaling path: tune pooling/workers, add caching, and profile hot retrieval paths.

## Dependencies at Risk

**Rapidly changing provider SDKs:**
- Risk: OpenAI/Bedrock/Cohere SDK changes can break adapters.
- Impact: provider-specific runtime failures.
- Migration plan: pin versions, add adapter-level contract tests, stage upgrades.

## Test Coverage Gaps

**End-to-end non-happy paths:**
- What's not tested enough: mixed provider failure modes under load.
- Risk: production incidents from timeout/retry edge cases.
- Priority: high.
- Difficulty: requires deterministic harness around external integrations.

---

*Concerns audit: 2026-02-27*
*Update as issues are fixed or new risks are discovered*
