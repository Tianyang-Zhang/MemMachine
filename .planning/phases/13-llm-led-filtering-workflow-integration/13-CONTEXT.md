# Phase 13 Context

## Goal
Implement LLM-led episode review/filtering workflow semantics in markdown and
runtime surfaces, while keeping runtime non-authoritative for filtering.

## User-locked Decisions
- Filtering outputs are for perf metrics/evaluation/debug only.
- If insufficient and no high-confidence related episodes, fallback behavior is
  to keep all episodes.
- If sufficient and selected evidence is empty, fallback is all episodes.

## Requirement IDs
- FILT-01
- FILT-02
- FILT-03

