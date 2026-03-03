# Phase 06: Skill Terminology Canonicalization - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning/execution

## Phase Boundary

Replace legacy retrieval "agent" terminology and interface naming in active
runtime paths with "skill" terminology, while preserving behavior and benchmark
compatibility.

## Locked Decisions

- The new concept is `skill`, not `agent`, for retrieval orchestration and
  sub-skill execution.
- `agent_name` style fields should migrate to `skill_name` in active retrieval
  paths.
- Legacy retrieval agent code paths and labels should be removed once skill
  naming is fully wired.

## Claude's Discretion

- Keep temporary compatibility shims only where needed to avoid breaking
  external callers during migration.
- Sequence migration by interface layer first, runtime layer second, then
  tests/evaluation/docs cleanup.

## Deferred Ideas

- No provider expansion work (non-OpenAI function-calling providers stay out of
  scope for this phase).
- No retrieval quality tuning campaign; this phase is naming and architecture
  cleanup only.
