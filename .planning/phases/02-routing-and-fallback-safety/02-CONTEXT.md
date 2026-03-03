# Phase 2: Routing and Fallback Safety - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Add route selection and fallback safety behavior for retrieval execution:
`select-skill` policy decisions, fallback trigger handling, and bounded execution
controls. This phase clarifies routing and safety behavior, not new retrieval
capabilities.

</domain>

<decisions>
## Implementation Decisions

### Route selection policy
- Phase 2 uses a fully model-driven primary routing mode.
- For borderline confidence outcomes, bias toward decomposition route for
  higher recall.
- Route selection output must return a single selected route with confidence and
  reason code.
- If selector cannot classify query, retry selector once before fallback.
- If first and retry selections conflict, choose the route with higher
  confidence score regardless of route type.

### Bounded execution controls
- Enforce all guardrails in this phase: `max_steps`, `max_hops`,
  `max_branches`, global timeout, and per-sub-skill timeout.
- If any bound is hit, allow one controlled retry before forcing fallback.
- If retry also hits a bound, fallback to direct MemMachine search.
- Keep partially merged evidence when fallback occurs after partial progress.
- Always emit fallback reason metadata for bound-triggered fallback paths.

### Decision output contract
- Top-level route decision must always include: `selected_route`,
  `confidence_score`, `reason_code`, and optional `fallback_trigger_reason`.
- `confidence_score` is a float in `[0.0, 1.0]` (no enum band required).
- Reason reporting uses both a stable enum-style `reason_code` and a short
  human-readable note.
- Response metrics include full per-step/per-tool trace data by default.

### Claude's Discretion
- Exact confidence threshold values and tie-break expression details.
- Exact enum symbol naming for reason/fallback codes.
- Internal trace payload shape as long as it preserves full step/tool detail.

</decisions>

<specifics>
## Specific Ideas

- Keep route outputs deterministic in shape (single route + confidence + reason)
  even when route decision logic is model-driven.
- Prioritize recall for ambiguous cases, then rely on fallback guardrails if
  downstream safety checks fail.
- Keep fallback outcomes explainable: include both machine-parseable codes and
  human-readable rationale in outputs.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-routing-and-fallback-safety*
*Context gathered: 2026-02-27*
