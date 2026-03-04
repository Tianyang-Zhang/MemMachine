# Milestones

## v1.1 Sufficiency-Aware Skill Verification (Shipped: 2026-03-04)

**Delivered:** Added sufficiency-aware retrieval observability, split live
verification with rerun, and benchmarked the updated runtime on 100
WikiMultiHop questions.

**Phases completed:** 4 phases (12-15), 8 plans, 16 tasks

**Key accomplishments:**
- Added first-class top-level sufficiency outputs (`is_sufficient`, confidence,
  reason/evidence indices) to runtime finalization metrics and traces.
- Added LLM-led filtering metadata contracts for top-level/coq/split workflows
  while preserving runtime return-all episode behavior.
- Refactored split into live planner -> execute -> verify flow with optional
  verification-triggered rerun.
- Updated evaluation hinting to prioritize top-level sufficiency signals.
- Executed benchmark gate:
  `./run_test.sh wikimultihop optv2 search retrieval_skill 100`.

**Stats:**
- 11 tracked implementation files changed from milestone start commit to ship
  (+816 / -106 before archival docs)
- Benchmark artifacts produced:
  - `evaluation/retrieval_skill/result/wikimultihop_retrieval_skill_output_optv2.json`
  - `evaluation/retrieval_skill/result/wikimultihop_retrieval_skill_evaluation_metrics_optv2.json`
  - `evaluation/retrieval_skill/result/final_score/wikimultihop_retrieval_skill_optv2.result`

**Known gaps:**
- No milestone audit file was present before completion
  (`.planning/v1.1-MILESTONE-AUDIT.md`).
- Summary artifacts are phase-level rather than per-plan.

**Archive files:**
- `.planning/milestones/v1.1-ROADMAP.md`
- `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## v1.0 Skill style retrieval agent (Shipped: 2026-03-02)

**Phases completed:** 11 phases, 22 plans, 0 tasks

**Key accomplishments:**
- Built a strict `retrieve-skill` orchestration runtime with typed v1 contracts and deterministic contract-failure handling.
- Added persistent top-level OpenAI Responses function-calling sessions with a single top-level invocation invariant per query.
- Implemented route selection plus bounded, reason-coded fallback policies for low-confidence, timeout, and exception paths.
- Delivered `coq` and `split` decomposition skills with branch-aware aggregation and markdown prompt parity hardening.
- Completed runtime/evaluation/test caller cutover to skill-first execution and finalized skill terminology canonicalization.
- Executed and documented the first-100 WikiMultiHop functional benchmark gate.

**Known gaps:**
- No milestone audit file was present at completion time (`.planning/v1.0-MILESTONE-AUDIT.md`).

---
