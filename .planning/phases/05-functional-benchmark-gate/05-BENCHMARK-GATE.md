# Phase 05 Benchmark Gate: WikiMultiHop First 100

**Run date (UTC):** 2026-02-28
**Phase requirement:** MIGR-03
**Status:** passed (functional gate executed)

## Commands

```bash
.venv/bin/python evaluation/retrieval_agent/wikimultihop_ingest.py \
  --data-path evaluation/data/wikimultihop.json \
  --length 100

.venv/bin/python evaluation/retrieval_agent/wikimultihop_search.py \
  --data-path evaluation/data/wikimultihop.json \
  --eval-result-path evaluation/retrieval_agent/result/wikimultihop_retrieval_agent_first100_v1.json \
  --length 100 \
  --test-target retrieval_agent
```

## Artifact

- `evaluation/retrieval_agent/result/wikimultihop_retrieval_agent_first100_v1.json`

## Record Counts

- Total questions: `100`
- Pass (>=1 supporting fact hit): `100`
- Fail (0 supporting fact hits): `0`
- Error (missing answer payload): `0`

## Runtime Behavior Categories

- `selected_skill=direct_memory`: `100`
- `fallback_trigger_reason=downstream_tool_failure`: `100`
- `skill_contract_error_code=SKILL_CONTRACT_INVALID_OUTPUT`: `100`

## Aggregate Matrix (from artifact)

```text
wiki Recall: 185/244 = 75.82%
wiki Precision: 185/2000 = 9.25%
wiki Average Episodes Retrieved per Question: 20.00
wiki Average Memory Retrieval Time per Question: 5.11 seconds
wiki Average LLM Time per Question (only for questions that used LLM): 0.00 seconds
Tool: MemMachineAgent
    Recall: 185/244 = 75.82%
    Precision: 185/2000 = 9.25%
    Avg Episodes Retrieved per Question: 20.00
```
