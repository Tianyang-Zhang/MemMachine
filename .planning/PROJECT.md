# Skill-Orchestrated Retrieval Agent

## What This Is

A skill-first retrieval orchestration system for MemMachine. It routes each
query to the right retrieval workflow (`coq`, `split`, direct memory fallback),
tracks sufficiency decisions, and preserves robust fallback behavior.

## Core Value

Every query is handled by the right retrieval workflow, with reliable fallback
to direct memory search when confidence is low or execution is unstable.

## Current State

- Shipped `v1.0` (skill runtime migration + first benchmark gate).
- Shipped `v1.1` (sufficiency-aware verification, split live verification pass,
  top-level metrics parity, 100-question WikiMultiHop benchmark gate).
- Milestone archives:
  - `.planning/milestones/v1.0-ROADMAP.md`
  - `.planning/milestones/v1.0-REQUIREMENTS.md`
  - `.planning/milestones/v1.1-ROADMAP.md`
  - `.planning/milestones/v1.1-REQUIREMENTS.md`

## Current Milestone: v1.2 Stage-Result Return Optimization Loop

**Goal:** Replace episode-only return semantics with stage-result-first
contracts across skill levels, then run benchmark-gated iterative optimization
until target accuracy is reached.

**Target features:**
- CoQ emits structured stage-results and generated sub-queries under
  confidence/sufficiency gates.
- Split remains a pure query-splitting planner (no sufficiency checks, no
  stage-result generation).
- Top-level prioritizes stage-results for reasoning and, when sufficient,
  returns stage-results + sub-queries as retrieval memory instead of raw
  episodes.
- 100-question WikiMultiHop benchmark loop with baseline gate and commit policy
  on every non-regressing iteration.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Parent sufficiency independent of child sufficiency | Avoid chained truth assumptions across levels | ✓ Adopted in v1.1 |
| LLM-owned filtering with runtime metric capture | Preserve model control while improving observability | ✓ Adopted in v1.1 |
| Split post-branch live verification pass | Ensure split can judge final sufficiency with full branch context | ✓ Adopted in v1.1 |
| Benchmark gate kept in milestone scope | Validate runtime behavior under realistic workload | ✓ Completed in v1.1 |
| Markdown-first stage-result behavior | Preserve LLM control and avoid hard-coded filtering logic | Active in v1.2 |

<details>
<summary>Archived v1.1 Planning Snapshot</summary>

The v1.1 live planning sections were archived to milestone files. See:
- `.planning/milestones/v1.1-ROADMAP.md`
- `.planning/milestones/v1.1-REQUIREMENTS.md`

</details>

---
*Last updated: 2026-03-04 for v1.2 milestone start*
