# Feature Research — Skill-style Retrieval Agent

**Date:** 2026-02-27
**Scope:** Define milestone-scope capabilities for skill-style retrieval migration.

## Core Feature Categories

## Retrieval Orchestration (Table Stakes)

- Top-level `retrieve-skill` orchestrator that executes one or more sub-skills per query.
- Deterministic orchestration lifecycle:
  - pre-check
  - route
  - execute
  - aggregate
  - fallback/return
- Explicit execution context passed across sub-skills (query, branch state, evidence, confidence).

## Skill Routing (Table Stakes)

- `select-skill` that chooses direct/coq/split path with confidence score.
- Policy rules for low-confidence behavior (must fallback).
- Route trace metadata for debugging and evaluation.

## Decomposition Skills (Table Stakes)

- `coq-skill` for multi-hop rewrite iteration.
- `split-skill` for independent branch decomposition.
- Branch policy: split branches can route through `coq-skill` when branch is multi-hop.

## Safety and Reliability (Table Stakes)

- `fallback-skill` for direct MemMachine pass-through search.
- Failure handling for any sub-skill exception.
- Timeout boundaries per step and total budget.
- Output normalization before final response.

## Observability and Validation (Differentiators)

- Structured trace of skill sequence and decision reasons.
- Per-skill timing and confidence metrics.
- Benchmark command path that can run first 100 WikiMultiHop queries with consistent output schema.

## Anti-Features / Deferred

- Full prompt-optimization suite for leaderboard gains (defer).
- Broad new skill catalog beyond select/coq/split/fallback (defer).
- Runtime feature flags for dual legacy/new paths after migration complete (avoid long-lived duality).

## Complexity Notes

- Highest complexity: orchestration + fallback correctness under partial failures.
- Medium complexity: preserving parity with existing routing behavior.
- Lower complexity: skill file layout and interfaces.

---
*Feature framing: table stakes vs differentiators for this milestone*
