# Pitfalls Research — Skill-style Retrieval Agent

**Date:** 2026-02-27
**Scope:** Common failure patterns when adding skill-based orchestration to existing retrieval logic.

## Critical Pitfalls

## 1) Soft fallback instead of hard fallback

- Symptom: system returns partial/low-confidence decomposed results instead of direct search fallback.
- Risk: correctness regressions and unstable UX.
- Prevention:
  - enforce strict fallback trigger contract
  - test low-confidence, exception, and timeout branches explicitly.

## 2) Dual-path drift (legacy + skill path both active too long)

- Symptom: inconsistent results and hard-to-debug behavior by environment.
- Risk: prolonged maintenance cost and hidden regressions.
- Prevention:
  - explicit migration cutoff plan
  - remove old execution path after parity gate.

## 3) Unbounded decomposition loops

- Symptom: coq/split loops exceed cost or time budget.
- Risk: latency spikes and API timeouts.
- Prevention:
  - enforce max hops, max branches, max total skill steps, and global timeout budget.

## 4) Schema drift across skill outputs

- Symptom: one skill emits shape that aggregator cannot consume reliably.
- Risk: intermittent runtime errors and malformed results.
- Prevention:
  - typed canonical output model
  - centralized normalizer and validation.

## 5) Missing traceability for routing decisions

- Symptom: impossible to explain why a route was chosen.
- Risk: debugging and benchmark analysis become guesswork.
- Prevention:
  - structured route trace with confidence + reason fields.

## 6) Benchmark non-determinism

- Symptom: first-100 benchmark results vary significantly run-to-run for non-functional reasons.
- Risk: false failure/false confidence in migration quality.
- Prevention:
  - fixed input slice and deterministic output formatting
  - explicit run metadata and error buckets.

## Phase Ownership for Pitfalls

- Early implementation phases: 1, 2, 3, 4 (fallback, contracts, routing bounds)
- Mid migration phase: legacy removal + parity verification
- Final validation phase: benchmark repeatability and reporting

---
*Pitfall focus: migration-specific risks and concrete prevention checks*
