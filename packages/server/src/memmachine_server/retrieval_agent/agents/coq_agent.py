"""Chain-of-query agent for iterative retrieval sufficiency checking."""

import asyncio
import datetime
import json
import logging
import time
import uuid
from collections.abc import Iterable
from typing import Any, cast

from memmachine_server.common.episode_store import Episode
from memmachine_server.common.episode_store.episode_model import episodes_to_string
from memmachine_server.common.language_model.language_model import LanguageModel
from memmachine_server.retrieval_agent.common.agent_api import (
    AgentToolBase,
    AgentToolBaseParam,
    QueryParam,
    QueryPolicy,
)

logger = logging.getLogger(__name__)

# Latest optimized version
# Citation: Luo et al. (2025), "Agent Lightning: Train ANY AI Agents with
# Reinforcement Learning", arXiv:2508.03680.
COMBINED_SUFFICIENCY_AND_REWRITE_PROMPT = """You are a meticulous expert in retrieval-augmented question answering evaluation and query rewriting.

Task: progress multi-hop retrieval in one LLM turn.
Given the original query, current query, prior sub-queries, prior stage-results,
and retrieved documents, you must:
1) Decompose remaining hops.
2) Resolve every hop that can be answered from the current retrieved documents.
3) Emit exactly ONE latest unresolved subquery to search next (if any).

Hard constraints:
- Use ONLY provided retrieved documents. No external knowledge.
- Do NOT invent entities not present in original query or retrieved docs.
- Output ONLY a valid JSON object with EXACTLY these keys:
  - "is_sufficient" (boolean)
  - "evidence_indices" (list[int], 0-based over Retrieved Documents)
  - "new_query" (string, single-line)
  - "confidence_score" (number 0..1)
  - "stage_results" (list[object])
  - "generated_sub_queries" (list[string])

Meaning of fields:
- stage_results: newly solved hops from THIS turn.
  Each item must have EXACTLY keys:
  - "query" (string)
  - "stage_result" (string)
  - "confidence_score" (number 0..1)
- generated_sub_queries: sub-queries considered/generated THIS turn in order.
- new_query: the latest unresolved subquery requiring another memory search.
  If no unresolved subquery remains, set new_query = original query exactly.

Required workflow:
1) Build/continue ordered hop plan for Original Query using Existing Stage Results.
2) Generate missing hop sub-queries in order (entity-resolution hops included).
3) For each generated hop query, check whether current retrieved docs already answer it.
   - If yes: add to stage_results.
   - If no: keep unresolved.
4) Choose new_query:
   - unresolved exists -> pick the latest unresolved one.
   - none unresolved -> new_query = original query.
5) Set is_sufficient = true ONLY if Original Query is fully answerable from
   (Existing Stage Results + stage_results + Retrieved Documents).
   Otherwise false.
6) If uncertain, set is_sufficient = false.

Quality requirements:
- Prefer earliest missing hop first, but new_query must be latest unresolved hop.
- Avoid duplicate sub-queries against Rewritten Queries Tried and Existing Sub Queries.
- stage_result must be concise and directly answer its query.
- evidence_indices should include all docs that contribute to solved hops/original sufficiency.

Inputs:
**Original Query**
{original_query}

**Current Query/Subquery**
{current_query}

**Rewritten Queries Tried**
{used_query}

**Existing Sub Queries**
{known_sub_queries}

**Existing Stage Results**
{existing_stage_results}

**Retrieved Documents**
{retrieved_episodes}
"""


class ChainOfQueryAgent(AgentToolBase):
    """Iteratively rewrite queries until evidence is sufficient."""

    def __init__(self, param: AgentToolBaseParam) -> None:
        """Initialize rewrite prompt and stopping thresholds."""
        super().__init__(param)
        extra_params = param.extra_params or {}
        self._combined_prompt: str = extra_params.get(
            "combined_prompt",
            COMBINED_SUFFICIENCY_AND_REWRITE_PROMPT,
        )
        self._max_attempts: int = extra_params.get("max_attempts", 3)
        self._confidence_score: float = extra_params.get("confidence_score", 0.8)
        self._stage_result_output_confidence: float = extra_params.get(
            "stage_result_output_confidence", 0.8
        )
        if self._model is None:
            raise ValueError("Model is not set")

    @property
    def agent_name(self) -> str:
        return "ChainOfQueryAgent"

    @property
    def agent_description(self) -> str:
        return (
            "This agent checks evidence sufficiency and rewrites the query "
            "for the next missing retrieval hop."
        )

    @property
    def accuracy_score(self) -> int:
        return 10

    @property
    def token_cost(self) -> int:
        return 9

    @property
    def time_cost(self) -> int:
        return 10

    def _last_brace_block(self, text: str) -> str:
        end = text.rfind("}")
        if end == -1:
            return ""

        depth = 0
        for i in range(end, -1, -1):
            ch = text[i]
            if ch == "}":
                depth += 1
            elif ch == "{":
                depth -= 1
                if depth == 0:
                    return text[i : end + 1]
        return ""

    def _init_perf_metrics(self) -> dict[str, Any]:
        return {
            "queries": [],
            "sub_queries": [],
            "generated_sub_queries": [],
            "is_sufficient": [],
            "evidence": [],
            "confidence_scores": [],
            "stage_results": [],
            "memory_retrieval_time": 0.0,
            "memory_search_called": 0,
            "llm_time": 0.0,
            "input_token": 0,
            "output_token": 0,
            "stage_result_memory_returned": False,
            "returned_stage_result_count": 0,
            "agent": self.agent_name,
        }

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.strip().lower().split())

    def _append_unique_sub_query(self, target: list[str], query: str) -> None:
        query_text = query.strip()
        if query_text == "":
            return
        query_norm = self._normalize_query(query_text)
        for existing in target:
            if self._normalize_query(existing) == query_norm:
                return
        target.append(query_text)

    def _append_unique_stage_result(
        self,
        target: list[dict[str, Any]],
        stage_result: dict[str, Any],
    ) -> None:
        query_text = str(stage_result.get("query", "")).strip()
        answer_text = str(stage_result.get("stage_result", "")).strip()
        if query_text == "" or answer_text == "":
            return

        query_norm = self._normalize_query(query_text)
        answer_norm = self._normalize_query(answer_text)
        for existing in target:
            if (
                self._normalize_query(str(existing.get("query", ""))) == query_norm
                and self._normalize_query(str(existing.get("stage_result", "")))
                == answer_norm
            ):
                return

        confidence = stage_result.get("confidence_score", 0.0)
        if not isinstance(confidence, int | float):
            confidence = 0.0
        target.append(
            {
                "query": query_text,
                "stage_result": answer_text,
                "confidence_score": float(confidence),
            }
        )

    def _build_stage_result_episodes(
        self,
        query: QueryParam,
        stage_results: list[dict[str, Any]],
        sub_queries: list[str],
    ) -> list[Episode]:
        if len(stage_results) == 0:
            return []

        now = datetime.datetime.now(tz=datetime.UTC)
        episodes: list[Episode] = []
        for idx, stage_item in enumerate(stage_results, start=1):
            stage_query = str(stage_item.get("query", "")).strip()
            stage_result = str(stage_item.get("stage_result", "")).strip()
            confidence = stage_item.get("confidence_score", 0.0)
            confidence_str = (
                f"{float(confidence):.2f}"
                if isinstance(confidence, int | float)
                else "0.00"
            )
            if stage_query == "" or stage_result == "":
                continue
            episodes.append(
                Episode(
                    uid=f"retrieval-agent-stage-result-{uuid.uuid4()}",
                    content=(
                        f"[StageResult {idx}] Query: {stage_query}\n"
                        f"Answer: {stage_result} (confidence={confidence_str})"
                    ),
                    session_key=query.memory.session_key,
                    created_at=now + datetime.timedelta(seconds=len(episodes)),
                    producer_id="retrieval-agent-stage-result",
                    producer_role="assistant",
                )
            )

        for idx, sub_query in enumerate(sub_queries, start=1):
            query_text = str(sub_query).strip()
            if query_text == "":
                continue
            episodes.append(
                Episode(
                    uid=f"retrieval-agent-sub-query-{uuid.uuid4()}",
                    content=f"[SubQuery {idx}] {query_text}",
                    session_key=query.memory.session_key,
                    created_at=now + datetime.timedelta(seconds=len(episodes)),
                    producer_id="retrieval-agent-stage-result",
                    producer_role="assistant",
                )
            )
        return episodes

    def _filter_stage_results_for_output(
        self, stage_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for stage_item in stage_results:
            confidence = stage_item.get("confidence_score", 0.0)
            if not isinstance(confidence, int | float):
                continue
            if float(confidence) <= self._stage_result_output_confidence:
                continue
            filtered.append(stage_item)
        return filtered

    async def combined_check_and_rewrite(  # noqa: C901
        self,
        query: QueryParam,
        current_query: str,
        retrieved_episodes: Iterable[Episode],
        retrived_evidence: Iterable[Episode],
        used_queries: list[str],
        known_sub_queries: list[str],
        existing_stage_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        context: str = ""
        evidence = set(retrived_evidence)
        episodes = sorted(
            set(retrieved_episodes).union(retrived_evidence),
            key=lambda e: (e.created_at is None, e.created_at),
        )
        for idx, episode in enumerate(episodes):
            context += f"[{idx}] {episodes_to_string([episode])}"
        used_query_str = "\n".join(used_queries)
        known_sub_queries_str = "\n".join(known_sub_queries)
        existing_stage_results_str = json.dumps(
            existing_stage_results, ensure_ascii=False
        )
        prompt = self._combined_prompt.format(
            original_query=query.query,
            current_query=current_query,
            used_query=used_query_str,
            known_sub_queries=known_sub_queries_str,
            existing_stage_results=existing_stage_results_str,
            retrieved_episodes=context,
        )
        m = cast(LanguageModel, self._model)
        rsp, _, input_token, output_token = await m.generate_response_with_token_usage(
            user_prompt=prompt
        )
        logger.debug("Combined Check and Rewrite: %s", rsp)
        json_parsable_str = ""
        response = {}
        retry = True
        while retry:
            try:
                # Get last {} JSON block
                json_parsable_str = self._last_brace_block(rsp)
                response = json.loads(json_parsable_str)
                break
            except Exception as e:
                logger.warning(
                    "Failed to parse combined check and rewrite response JSON: "
                    "response=%s final_string=%s error=%s",
                    rsp,
                    json_parsable_str,
                    e,
                )
                if not retry:
                    break
                retry = False
                continue
        for idx_val in response.get("evidence_indices", []):
            if idx_val < 0 or idx_val >= len(episodes):
                continue
            evidence.add(episodes[idx_val])

        final_episodes = set(evidence).union(retrieved_episodes)
        final_episodes = sorted(
            final_episodes, key=lambda e: (e.created_at is None, e.created_at)
        )

        parsed_stage_results: list[dict[str, Any]] = []
        for stage_item in response.get("stage_results", []):
            if not isinstance(stage_item, dict):
                continue
            query_text = str(stage_item.get("query", "")).strip()
            stage_text = str(stage_item.get("stage_result", "")).strip()
            if query_text == "" or stage_text == "":
                continue
            confidence_val = stage_item.get("confidence_score", 0.0)
            if not isinstance(confidence_val, int | float):
                confidence_val = 0.0
            parsed_stage_results.append(
                {
                    "query": query_text,
                    "stage_result": stage_text,
                    "confidence_score": float(confidence_val),
                }
            )

        parsed_generated_sub_queries: list[str] = []
        for sub_query in response.get("generated_sub_queries", []):
            if not isinstance(sub_query, str):
                continue
            query_text = sub_query.strip()
            if query_text == "":
                continue
            parsed_generated_sub_queries.append(query_text)

        legacy_stage_result = str(response.get("stage_result", "")).strip()
        if legacy_stage_result != "":
            parsed_stage_results.append(
                {
                    "query": current_query,
                    "stage_result": legacy_stage_result,
                    "confidence_score": float(response.get("confidence_score", 0.0)),
                }
            )

        response_new_query = str(response.get("new_query", query.query)).strip()
        if response_new_query == "":
            response_new_query = query.query

        answered_query_norms = {
            self._normalize_query(str(stage_item.get("query", "")))
            for stage_item in parsed_stage_results
        }
        unresolved_from_generated = [
            sub_query
            for sub_query in parsed_generated_sub_queries
            if self._normalize_query(sub_query) not in answered_query_norms
        ]
        if len(unresolved_from_generated) > 0:
            response_new_query = unresolved_from_generated[-1]

        return {
            "is_sufficient": response.get("is_sufficient", False),
            "evidence": evidence,
            "new_query": response_new_query,
            "confidence_score": response.get("confidence_score", 0.0),
            "stage_results": parsed_stage_results,
            "generated_sub_queries": parsed_generated_sub_queries,
            "episodes": final_episodes,
            "input_token": input_token,
            "output_token": output_token,
        }

    async def _do_default_query(
        self,
        policy: QueryPolicy,
        query: QueryParam,
    ) -> tuple[list[Episode], dict[str, Any]]:
        q = query.model_copy()
        # TODO: make this self-adaptive
        # if q.limit >= 15:
        #     q.limit /= 3
        success = False
        max_retry = 60
        while not success:
            try:
                result, metrics = await super().do_query(policy, q)
                success = True
            except Exception as e:
                max_retry -= 1
                if max_retry == 0:
                    logger.exception("Reranker failed after maximum retries.")
                    raise
                if "ThrottlingException" in str(e):
                    logger.warning(
                        "Reranker throttling exception, retrying after 5 seconds..."
                    )
                    await asyncio.sleep(5)
                else:
                    raise
        return result, metrics

    async def do_query(  # noqa: C901
        self,
        policy: QueryPolicy,
        query: QueryParam,
    ) -> tuple[list[Episode], dict[str, Any]]:
        logger.info("CALLING %s with query: %s", self.agent_name, query.query)
        perf_metrics = self._init_perf_metrics()
        retrieved_evidence: set[Episode] = set()
        sufficiency_response: dict[str, Any] = {
            "is_sufficient": False,
            "evidence": set(),
            "new_query": query.query,
            "confidence_score": 0.0,
            "stage_results": [],
            "generated_sub_queries": [],
            "episodes": [],
            "input_token": 0,
            "output_token": 0,
        }
        used_query: list[str] = []
        all_sub_queries: list[str] = []
        all_stage_results: list[dict[str, Any]] = []

        curr_query = query.model_copy()
        for _ in range(self._max_attempts):
            curr_query.query = str(
                sufficiency_response.get("new_query", query.query)
            ).strip()
            curr_query_norm = self._normalize_query(curr_query.query)
            if curr_query_norm == "":
                break
            if any(
                self._normalize_query(searched_q) == curr_query_norm
                for searched_q in used_query
            ):
                # print("The model did not rewrite the query")
                break
            used_query.append(curr_query.query)
            self._append_unique_sub_query(all_sub_queries, curr_query.query)
            # Step 1: Perform the query
            result, p_metrics = await self._do_default_query(policy, curr_query)
            self._update_perf_metrics(p_metrics, perf_metrics)

            # Step 2: Check if the evidence is enough to answer the original query
            llm_start = time.time()
            sufficiency_response = await self.combined_check_and_rewrite(
                query,
                curr_query.query,
                result,
                retrieved_evidence,
                used_query,
                all_sub_queries,
                all_stage_results,
            )
            perf_metrics["llm_time"] += time.time() - llm_start
            retrieved_evidence.update(sufficiency_response["evidence"])

            perf_metrics["queries"].append(curr_query.query)
            perf_metrics["is_sufficient"].append(sufficiency_response["is_sufficient"])
            perf_metrics["evidence"].append(
                [episodes_to_string([e]) for e in sufficiency_response["evidence"]]
            )
            perf_metrics["confidence_scores"].append(
                sufficiency_response["confidence_score"]
            )

            prior_stage_count = len(all_stage_results)
            for stage_item in sufficiency_response.get("stage_results", []):
                if not isinstance(stage_item, dict):
                    continue
                self._append_unique_stage_result(all_stage_results, stage_item)
            if len(all_stage_results) > prior_stage_count:
                perf_metrics["stage_results"].extend(
                    all_stage_results[prior_stage_count:]
                )

            prior_sub_query_count = len(all_sub_queries)
            for generated_sub_query in sufficiency_response.get(
                "generated_sub_queries", []
            ):
                if not isinstance(generated_sub_query, str):
                    continue
                self._append_unique_sub_query(all_sub_queries, generated_sub_query)
            if len(all_sub_queries) > prior_sub_query_count:
                perf_metrics["generated_sub_queries"].extend(
                    all_sub_queries[prior_sub_query_count:]
                )

            perf_metrics["input_token"] += sufficiency_response["input_token"]
            perf_metrics["output_token"] += sufficiency_response["output_token"]
            if (
                sufficiency_response["is_sufficient"]
                and sufficiency_response["confidence_score"] >= self._confidence_score
            ):
                logger.debug(
                    "The default agent can answer the query with enough confidence"
                )
                # print(f"Enough evidence with rewrites: {used_query}")
                break

        perf_metrics["sub_queries"] = list(all_sub_queries)
        perf_metrics["stage_results"] = list(all_stage_results)
        output_stage_results = self._filter_stage_results_for_output(all_stage_results)
        output_sub_queries: list[str] = []
        for stage_item in output_stage_results:
            self._append_unique_sub_query(output_sub_queries, str(stage_item["query"]))
        stage_result_episodes = self._build_stage_result_episodes(
            query=query,
            stage_results=output_stage_results,
            sub_queries=output_sub_queries,
        )

        if (
            sufficiency_response["is_sufficient"]
            and sufficiency_response["confidence_score"] >= self._confidence_score
            and len(stage_result_episodes) > 0
        ):
            perf_metrics["stage_result_memory_returned"] = True
            perf_metrics["returned_stage_result_count"] = len(stage_result_episodes)
            return stage_result_episodes, perf_metrics

        # Rerank base on all queries used
        q = query.model_copy()
        q.query = query.query + "\n".join(used_query)
        final_episodes = await self._do_rerank(q, sufficiency_response["episodes"])

        if len(stage_result_episodes) > 0:
            perf_metrics["stage_result_memory_returned"] = True
            perf_metrics["returned_stage_result_count"] = len(stage_result_episodes)
            merged_episodes: list[Episode] = []
            seen_uids: set[str] = set()
            for episode in [*stage_result_episodes, *final_episodes]:
                if episode.uid in seen_uids:
                    continue
                seen_uids.add(episode.uid)
                merged_episodes.append(episode)
            return merged_episodes, perf_metrics

        return final_episodes, perf_metrics
