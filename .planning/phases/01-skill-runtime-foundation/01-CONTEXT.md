# Phase 1: Skill Runtime Foundation - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the first working skill runtime foundation for retrieval: canonical
contracts, `retrieve-skill` entry path, and baseline behavior needed for
downstream phases. This phase does not add new retrieval capabilities beyond the
existing roadmap scope.

</domain>

<decisions>
## Implementation Decisions

### Contract strictness
- Invalid skill output: attempt one normalization pass, then fail if still
  invalid.
- Required fields are strict from day one.
- Unknown fields are rejected in Phase 1.
- Phase 1 uses a single v1 contract (no mixed variants).

### Skill author experience
- Use a strict, minimal schema template for skill specs.
- Include explicit examples for common patterns in skill authoring guidance.
- Apply opinionated defaults (timeouts/limits/fallback hooks) to reduce
  boilerplate.
- Block execution when a spec is incomplete.

### Runtime error language
- Errors are developer-first and technical.
- Error format must include: what failed, why, how to fix, and where.
- Use stable typed error codes from day one (e.g., `SKILL_CONTRACT_*`).
- Fallback paths must explicitly state the trigger reason each time.

### Compatibility expectations
- Internal trace metadata remains internal by default in Phase 1.
- Low parity with legacy behavior is acceptable in this phase.
- If compatibility and authoring convenience conflict, prioritize authoring
  convenience in Phase 1.
- Target compatibility where practical, but convenience-first is the tie-breaker.

### Claude's Discretion
- Exact wording and formatting of error/help text while preserving the required
  error structure.
- Structure and placement of authoring examples within docs/spec guidance.
- Default-value specifics (exact timeout/limit numbers) if not explicitly
  constrained elsewhere.

</decisions>

<specifics>
## Specific Ideas

- Keep the skill contract intentionally strict early to reduce ambiguity.
- Make fallback reasons explicit and actionable for debugging.
- Favor implementation speed and authoring ergonomics during this foundation
  phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-skill-runtime-foundation*
*Context gathered: 2026-02-27*
