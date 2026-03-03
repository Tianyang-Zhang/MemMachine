# Stack Research — Skill-style Retrieval Agent

**Date:** 2026-02-27
**Scope:** Add SKILL-style retrieval orchestration for MemMachine retrieval-agent flows.

## Existing Stack (already in repo)

- Python 3.12+
- FastAPI/async runtime
- Pydantic v2 models
- Existing retrieval agent modules under `src/memmachine/retrieval_agent/agents/`
- Existing LLM/reranker abstractions under `src/memmachine/common/`

## Recommended Additions for New Capability

## 1) No new hard dependency required (recommended baseline)

The skill-style system can be implemented using existing Python stdlib and current
MemMachine abstractions:
- Define skill specs in markdown (`SKILL.md`) and parse with lightweight rules.
- Keep execution engine in Python with strict typed interfaces.
- Use existing `LanguageModel` and reranker/resource manager plumbing.

Why: minimizes migration risk and avoids unnecessary packaging churn.

## 2) Optional parsing utility (only if markdown complexity increases)

If robust frontmatter and markdown AST parsing becomes necessary:
- `python-frontmatter` (frontmatter extraction)
- `mistune` or `markdown-it-py` (structured markdown parsing)

Recommendation: defer until parser complexity proves high.

## 3) Testing/verification stack for this milestone

Use existing tooling already configured:
- `pytest`, `pytest-asyncio`
- fixture-driven regression tests in `tests/memmachine/retrieval_agent/`
- benchmark harness for first 100 WikiMultiHop queries in `evaluation/retrieval_agent/`

## Integration Points

- Add new skill package:
  - `src/memmachine/retrieval_agent/skills/`
- Keep compatibility entry in service locator:
  - `src/memmachine/retrieval_agent/service_locator.py`
- Route skill orchestrator through `MemMachine.query_search` retrieval mode path.

## What NOT to Add

- Do not introduce external workflow engines for v1 (overkill for migration scope).
- Do not keep dual legacy/new retrieval execution paths after cutover.
- Do not add broad prompt-tuning dependencies in this milestone.

## Migration Safety Guardrails

- Hard fallback to direct MemMachine search on low confidence, timeout, or failure.
- Strong timeout boundaries per sub-skill.
- Deterministic output contracts between skill stages.

---
*Focus: stack changes needed for NEW capability only*
