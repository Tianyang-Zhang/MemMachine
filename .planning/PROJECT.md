# Skill-Orchestrated Retrieval Agent

## What This Is

This project replaced the legacy retrieval-agent pipeline with a skill-first,
workflow-driven retrieval system in MemMachine. Retrieval now runs through a
top-level orchestration layer that can route queries, run decomposition skills,
and aggregate final outputs while preserving direct MemMachine fallback safety.

## Core Value

Every query is handled by the right retrieval workflow, with reliable fallback
to direct memory search when confidence is low or execution is unstable.

## Current State

- Milestone `v1.0 Skill style retrieval agent` shipped on 2026-03-02.
- Roadmap and requirements for v1.0 are archived under `.planning/milestones/`.
- Runtime terminology is skill-first across active retrieval paths.

## Next Milestone Goals

- OPT-01: Tune prompts and routing/fallback policies for retrieval quality.
- OPT-02: Define onboarding checks for adding new skills beyond
  `select/coq/split/fallback`.
- OPT-03: Establish repeatable comparative evaluation baselines for policy
  variants.

## Requirements

### Validated

- [x] ORCH-01: Top-level `retrieve-skill` orchestration entrypoint.
- [x] ORCH-02: Multi-skill retrieval flow with one normalized final result.
- [x] ORCH-03: Retrieval trace metadata exposure for route/execution decisions.
- [x] ROUT-01: `select-skill` routing with explicit confidence output.
- [x] ROUT-02: Multi-hop decomposition via `coq-skill`.
- [x] ROUT-03: Branch decomposition via `split-skill`.
- [x] ROUT-04: Split-branch escalation through `coq-skill` when needed.
- [x] SAFE-01: Low-confidence fallback to direct MemMachine search.
- [x] SAFE-02: Exception fallback to direct MemMachine search.
- [x] SAFE-03: Timeout fallback to direct MemMachine search.
- [x] SAFE-04: Bounded execution controls for hops/branches/steps.
- [x] MIGR-01: Legacy retrieval-agent execution path removed.
- [x] MIGR-02: Retrieval API response compatibility preserved.
- [x] MIGR-03: First-100 WikiMultiHop functional gate completed.
- [x] MIGR-04: Skill-first terminology canonicalized across active paths.

### Active

- [ ] OPT-01: Accuracy/policy tuning campaign.
- [ ] OPT-02: New-skill onboarding contract and safety checklist.
- [ ] OPT-03: Repeatable A/B evaluation harness for retrieval policies.

### Out of Scope

- Long-lived dual execution mode between legacy and skill runtime.
- Broad expansion of skill families before optimization goals are baselined.

## Context

v1.0 completed the migration from legacy retrieval-agent naming and runtime
paths to skill-first runtime wiring. Evaluation and tests now target
`retrieval_skill` paths, and retrieval traces expose orchestration decisions
for inspection.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use SKILL.md-style workflow architecture | Higher orchestration flexibility and explicit skill control | [x] Adopted in v1.0 |
| Introduce top-level `retrieve-skill` above routing | Needed to coordinate multi-skill chains and result aggregation | [x] Adopted in v1.0 |
| Allow multi-skill sequences per query | Improves handling of complex query structures | [x] Adopted in v1.0 |
| Define v1 core skills as `select/coq/split/fallback` | Minimal complete set matching current behavior classes | [x] Adopted in v1.0 |
| Use direct MemMachine pass-through as fallback | Ensures graceful degradation on low confidence/errors/timeouts | [x] Adopted in v1.0 |
| Remove legacy agent path after wiring new flow | Avoid dual-path complexity and single source of truth drift | [x] Adopted in v1.0 |
| Prioritize functionality over score in this milestone | Migration risk reduction before optimization work | [x] Adopted in v1.0 |

---
*Last updated: 2026-03-02 after v1.0 milestone completion*
