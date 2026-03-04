# Phase 12 Context

## Goal
Define and implement a consistent sufficiency signal contract across `coq`,
`split`, and top-level retrieval skill paths.

## User-locked Decisions
- Parent skill sufficiency is computed independently from child
  `is_sufficient` values.
- Child sufficiency outputs are logging/metrics/evaluation signals only.
- Runtime should not auto-filter episodes; LLM decides filtering semantics.

## Requirement IDs
- SUFF-01
- SUFF-02
- SUFF-03

