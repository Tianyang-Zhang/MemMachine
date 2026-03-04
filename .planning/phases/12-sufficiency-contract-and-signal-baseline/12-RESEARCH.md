# Phase 12 Research

## Existing Runtime Facts
- Sub-skill summaries are already parsed for `is_sufficient` in top-level
  metrics, but top-level finalization does not emit first-class sufficiency
  fields.
- `return_final` tool schema currently lacks explicit sufficiency fields.

## Implementation Direction
- Extend top-level tool contract with optional sufficiency fields.
- Record top-level sufficiency into metrics/trace without coupling control flow
  to child sufficiency booleans.

