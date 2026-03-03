# Research Summary — Skill style retrieval agent (v1.0)

**Date:** 2026-02-27

## Stack additions

- No mandatory new runtime dependency is needed for v1 migration.
- Implement skill runtime/spec handling with current Python stack and existing
  MemMachine abstractions.
- Optional markdown/frontmatter parsing dependencies should be deferred unless
  spec complexity proves high.

## Feature table stakes

- `retrieve-skill` orchestration lifecycle with deterministic stage boundaries.
- `select-skill`, `coq-skill`, `split-skill`, `fallback-skill` parity behavior.
- Hard fallback policy for low-confidence, failure, and timeout conditions.
- Structured trace metadata for route decisions and execution outcomes.

## Architecture direction

- Add new skill package under `src/memmachine/retrieval_agent/skills/`.
- Keep API response shape stable while replacing legacy execution internals.
- Build order should prioritize safety first: contracts -> fallback -> routing ->
  decomposition -> cutover -> benchmark.

## Watch out for

- Unbounded decomposition loops or branch fan-out.
- Output schema drift across skills.
- Long-lived dual-path execution (legacy + skill).
- Missing deterministic benchmark slice and result schema.

## Recommendation

Proceed with milestone requirements and roadmap focused on a strict migration
sequence: establish contracts/safety, implement skills incrementally, cut over,
and verify with first-100 WikiMultiHop functional gate.
