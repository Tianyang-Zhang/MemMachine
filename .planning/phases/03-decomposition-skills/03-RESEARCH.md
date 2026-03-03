# Phase 3: Decomposition Skills - Research

**Researched:** 2026-02-28
**Domain:** Markdown-driven decomposition (`coq` + `split`) with pass-through
and top-level rerank
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Top-level begins with `tool_select` but supports pass-through direct memory
  when decomposition is unnecessary.
- Low-confidence selector output triggers direct-memory fallback.
- Malformed selector output retries once, then falls back to direct memory.
- `tool_select`, `coq`, and `split` behavior must be translated from legacy
  prompt constants into markdown skill files.
- `coq` must run sequentially.
- `split` branches run in parallel with hard cap `5`.
- Split branches may route through `coq` for branch-local multi-hop needs.
- Branch failure retries once; all branches must succeed for split success.
- Top-level returns all sub-skill outputs; Python runtime performs final rerank
  on original query.
- Dedup uses episode UID only.
- Top-level remains state owner and retains full sub-skill trace/metrics.

### Deferred Ideas (OUT OF SCOPE)
- Contradiction/conflict-resolution policy for branch evidence.
- Advanced ranking/merging beyond one top-level rerank pass.
</user_constraints>

<research_summary>
## Summary

Current runtime already supports:
- one persistent top-level live session with function-calling callbacks,
- sub-skill markdown loading and execution,
- UID-based episode merge semantics in session state.

Phase 3 should add decomposition behavior in two layers:
1. Prompt-policy parity layer:
   - create `coq.md` and `split.md`,
   - upgrade `tool_select.md` to output direct skill intent including
     pass-through.
2. Runtime behavior layer:
   - implement sequential `coq` loops,
   - implement capped parallel split branch execution with branch-to-coq,
   - rerank once at top-level after aggregation and UID dedup.

This sequencing isolates policy translation from branch orchestration complexity
and matches roadmap split (`03-01`, `03-02`).
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Existing `SkillLanguageModel` live session runtime | existing | top-level and sub-skill function-calling flow | Already integrated in phases 2.1/2.2 |
| Existing `RetrieveSkill` + `SubSkillRunner` | existing | orchestration and sub-skill execution | Current control-plane/runtime boundary |
| Existing Pydantic contracts (`skills/types.py`) | existing | strict selector/decomposition payload contracts | Existing contract baseline |
| pytest / pytest-asyncio | existing | async runtime coverage | Existing repo test stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` (`Semaphore`, `gather`, timeout helpers) | stdlib | capped parallel split branches | split branch execution |
| Existing reranker abstraction (`AgentToolBase._do_rerank`) | existing | final top-level rerank by original query | post-aggregation ranking |

### Installation
```bash
# No new dependency expected for Phase 3.
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Markdown-first decomposition policies
**What:** Keep decomposition rules in skill markdown files (`tool_select.md`,
`coq.md`, `split.md`) with strict output contracts.
**When:** Any changes to decomposition behavior, thresholds, or prompting.

### Pattern 2: Top-level as stateful control plane
**What:** Top-level session remains active, owns cumulative state, and decides
next sub-skill or completion based on sub-skill outputs.
**When:** Entire query lifecycle.

### Pattern 3: Sub-skill specialization
**What:** `coq` handles sequential rewrite/sufficiency hops; `split` handles
parallel branch fan-out and branch-local routing.
**When:** Query complexity requires decomposition beyond direct memory.

### Pattern 4: Aggregate -> Dedup -> Rerank
**What:** Merge all branch/sub-skill outputs, dedup by UID, then rerank once
using original query in Python runtime.
**When:** Before final top-level response emission.

### Anti-patterns to avoid
- Hard-coding decomposition decisions in Python instead of markdown policy.
- Branch-level rerank only without final top-level rerank.
- Dedup by content/title heuristics instead of stable UID.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel branch control | ad-hoc thread pools | `asyncio` + bounded semaphore | deterministic async behavior |
| Selector contract parsing | free-form string checks | strict Pydantic model validation | stable fallback behavior |
| Trace aggregation | custom nested dict mutation | existing session-state models + explicit counters | compatibility with current metrics surfaces |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Selector emits route categories but runtime expects skill names
**Mitigation:** Normalize to explicit selected skill contract
(`direct_memory`/`coq`/`split`) before spawn logic.

### Pitfall 2: Parallel split branches exceed bounds or hang
**Mitigation:** enforce cap=5, per-branch retry budget, and existing global/sub
timeouts with deterministic fallback reason emission.

### Pitfall 3: Missing top-level rerank after branch aggregation
**Mitigation:** apply one final rerank pass in `RetrieveSkill` against original
query after UID dedup and before return.
</common_pitfalls>

<code_examples>
## Code Examples (Current Anchors)

### Existing top-level merge semantics (UID dedup)
```python
# src/memmachine/retrieval_agent/skills/session_state.py
def merge_episodes(self, episodes: list[Episode]) -> None:
    existing_uids = {episode.uid for episode in self.merged_episodes}
    ...
```

### Existing top-level function-calling entry
```python
# src/memmachine/retrieval_agent/skills/retrieve_skill.py
session_result = await self._session_model.run_live_session(...)
```

### Existing sub-skill execution abstraction
```python
# src/memmachine/retrieval_agent/skills/sub_skill_runner.py
async def run(..., skill_name: str, ...):
    ...
```
</code_examples>

<open_questions>
## Open Questions

1. Should selector keep backward-compatible `selected_route` field in addition
   to `selected_skill` during transition?
   Recommendation: yes, emit both in v1.0 while runtime reads strict
   `selected_skill`.

2. Should split branch scheduling prefer completion order or input order for
   aggregation?
   Recommendation: preserve input branch order in trace metadata and apply
   rerank for final ordering.
</open_questions>

<sources>
## Sources

### Primary
- `.planning/phases/03-decomposition-skills/03-CONTEXT.md`
- `src/memmachine/retrieval_agent/skills/retrieve_skill.py`
- `src/memmachine/retrieval_agent/skills/sub_skill_runner.py`
- `src/memmachine/retrieval_agent/skills/tool_protocol.py`
- `src/memmachine/retrieval_agent/skills/session_state.py`
- `src/memmachine/retrieval_agent/skills/specs/top_level/retrieve_skill.md`
- `src/memmachine/retrieval_agent/skills/specs/sub_skills/tool_select.md`
- `src/memmachine/retrieval_agent/agents/coq_agent.py`
- `src/memmachine/retrieval_agent/agents/split_query_agent.py`
- `src/memmachine/retrieval_agent/agents/tool_select_agent.py`

### Secondary
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `tests/memmachine/retrieval_agent/test_retrieve_skill_*.py`

</sources>

<metadata>
## Metadata

**Research scope:**
- Decomposition policy translation into markdown skills
- Sequential `coq` and parallel `split` execution strategy
- Top-level aggregation/rerank/dedup/trace contracts

**Confidence breakdown:**
- Prompt translation feasibility: HIGH
- Runtime integration points: HIGH
- Testability with current harness: HIGH

**Research date:** 2026-02-28
**Valid until:** 2026-03-31
</metadata>

---

*Phase: 03-decomposition-skills*
