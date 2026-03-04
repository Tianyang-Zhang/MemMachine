# Phase 15 Benchmark Report

## Command

`./run_test.sh wikimultihop optv2 search retrieval_skill 100`

## Execution

- **Date (UTC):** 2026-03-04
- **Dataset:** WikiMultiHop
- **Questions:** 100
- **Status:** Completed

## Artifacts

- `evaluation/retrieval_skill/result/wikimultihop_retrieval_skill_output_optv2.json`
- `evaluation/retrieval_skill/result/wikimultihop_retrieval_skill_evaluation_metrics_optv2.json`
- `evaluation/retrieval_skill/result/final_score/wikimultihop_retrieval_skill_optv2.result`

## Key Results

- Overall `llm_score`: **0.93**
- Category means:
  - `bridge_comparison`: 0.9524 (21)
  - `comparison`: 1.0000 (25)
  - `compositional`: 0.8718 (39)
  - `inference`: 0.9333 (15)
- Skill accuracy:
  - `ChainOfQuerySkill`: 53/58 (91.38%)
  - `SplitSkill`: 37/38 (97.37%)
  - `MemMachineSkill`: 3/4 (75.00%)
- Wiki retrieval:
  - Recall: 199/244 (81.56%)
  - Precision: 199/2000 (9.95%)
  - Avg episodes/question: 20.00
  - Avg memory retrieval time/question: 3.49s
  - Avg LLM time/question (LLM-used cases): 88.90s

## Notes

- Retrieval loop completed all 100 questions.
- Some per-question logs reported `sub_skill_timeout` contract failures, but
  the run continued via fallback handling and still produced full benchmark
  artifacts.
