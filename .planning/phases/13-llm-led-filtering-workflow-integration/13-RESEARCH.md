# Phase 13 Research

## Existing Runtime Facts
- Runtime currently returns accumulated episode sets from search/tool calls.
- LLM has no explicit contract fields for selected evidence on top-level
  `return_final`.

## Implementation Direction
- Add optional selected/related evidence fields to tool output contracts.
- Keep returned episode list unchanged by runtime filtering logic.

