"""Sub-skill execution runtime for markdown-guided retrieve-skill orchestration."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from memmachine_server.common.episode_store import Episode
from memmachine_server.common.episode_store.episode_model import episodes_to_string
from memmachine_server.common.language_model import (
    SkillLanguageModel,
    SkillLanguageModelError,
    SkillRunResult,
    SkillSessionLimitError,
    SkillSessionModelProtocol,
    SkillToolCallFormatError,
    SkillToolNotFoundError,
)
from memmachine_server.common.language_model.language_model import LanguageModel
from memmachine_server.retrieval_skill.common.skill_api import (
    QueryParam,
    QueryPolicy,
    SkillToolBase,
)
from memmachine_server.retrieval_skill.skills.route_policy import (
    parse_route_decision_output_detailed,
)
from memmachine_server.retrieval_skill.skills.session_state import SkillToolCallRecord
from memmachine_server.retrieval_skill.skills.spec_loader import load_skill_spec
from memmachine_server.retrieval_skill.skills.tool_protocol import (
    parse_sub_skill_tool_call,
    sub_skill_tool_schemas,
)
from memmachine_server.retrieval_skill.skills.types import (
    SkillContractError,
    SkillContractErrorCode,
    SkillContractErrorPayload,
    SkillSpecV1,
)


class SubSkillExecutionResult(BaseModel):
    """Structured result returned from a sub-skill execution."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    query: str
    status: str
    summary: str = ""
    episodes: list[Episode] = Field(default_factory=list)
    tool_calls: list[SkillToolCallRecord] = Field(default_factory=list)
    fallback_trigger_reason: str | None = None
    llm_time: float = 0.0
    llm_call_count: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    memory_search_called: int = 0
    memory_retrieval_time: float = 0.0
    branch_total: int = 0
    branch_success_count: int = 0
    branch_failure_count: int = 0
    branch_retry_count: int = 0


@dataclass(slots=True)
class _SplitBranchResult:
    query: str
    route: str
    selected_skill: str
    status: str
    episodes: list[Episode]
    retry_count: int
    llm_time: float = 0.0
    llm_call_count: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    memory_search_called: int = 0
    memory_retrieval_time: float = 0.0
    error: str = ""
    nested_tool_calls: list[SkillToolCallRecord] | None = None


@dataclass(slots=True)
class _SplitBranchSelection:
    query: str
    selected_skill: str
    execution_skill: str
    status: str
    llm_time: float = 0.0
    llm_call_count: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    parse_error: str | None = None
    selector_summary: str = ""
    selector_tool_calls: list[SkillToolCallRecord] | None = None


class SubSkillRunner:
    """Run one sub-skill using markdown policy and memory-search tool access."""

    def __init__(
        self,
        *,
        model: LanguageModel,
        memory_tool: SkillToolBase,
        session_model: SkillSessionModelProtocol | None = None,
        spec_root: Path | None = None,
        split_parallel_cap: int = 5,
        split_branch_retry_limit: int = 1,
    ) -> None:
        """Initialize sub-skill runtime dependencies."""
        self._model = model
        self._memory_tool = memory_tool
        self._session_model = (
            session_model
            or SkillLanguageModel.from_openai_responses_language_model(model)
        )
        self._spec_root = spec_root or (
            Path(__file__).resolve().parent / "specs" / "sub_skills"
        )
        self._split_parallel_cap = max(1, split_parallel_cap)
        self._split_branch_retry_limit = max(0, split_branch_retry_limit)

    @staticmethod
    def _normalize_query_for_cache(query: str) -> str:
        return " ".join(query.lower().split())

    @staticmethod
    def _query_tokens(query: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", query.lower()))

    @staticmethod
    def _query_similarity(a_tokens: set[str], b_tokens: set[str]) -> float:
        if not a_tokens or not b_tokens:
            return 0.0
        union = a_tokens | b_tokens
        if not union:
            return 0.0
        return len(a_tokens & b_tokens) / len(union)

    @staticmethod
    def _sanitize_raw_tool_result(raw: object) -> dict[str, object] | None:
        if not isinstance(raw, dict):
            return None
        sanitized: dict[str, object] = {}
        for key, value in raw.items():
            if key in {
                "episodes",
                "episodes_human_readable",
                "episodes_text",
                "episode_lines",
            }:
                continue
            if isinstance(value, str | int | float | bool) or value is None:
                sanitized[key] = value
                continue
            if isinstance(value, dict):
                sanitized[key] = value
                continue
            if isinstance(value, list):
                sanitized[key] = value
                continue
        return sanitized or None

    def _spec_path_for(self, skill_name: str) -> Path:
        candidates = [
            skill_name,
            skill_name.replace("-", "_"),
            skill_name.replace("_", "-"),
        ]
        for candidate in candidates:
            candidate_path = self._spec_root / f"{candidate}.md"
            if candidate_path.exists():
                return candidate_path
        return self._spec_root / f"{skill_name}.md"

    def _load_sub_skill_spec(self, skill_name: str) -> SkillSpecV1:
        spec = load_skill_spec(self._spec_path_for(skill_name))
        if spec.kind != "sub-skill":
            raise SkillContractError(
                code=SkillContractErrorCode.INVALID_SPEC,
                payload=SkillContractErrorPayload(
                    what_failed="Sub-skill spec kind mismatch",
                    why=f"Expected sub-skill, got {spec.kind}",
                    how_to_fix="Set kind: sub-skill in markdown frontmatter.",
                    where="skills.sub_skill_runner._load_sub_skill_spec",
                    fallback_trigger_reason="invalid_sub_skill_spec",
                ),
            )
        return spec

    def _raise_invalid_output(self, *, why: str, fallback_reason: str) -> None:
        raise SkillContractError(
            code=SkillContractErrorCode.INVALID_OUTPUT,
            payload=SkillContractErrorPayload(
                what_failed="Sub-skill function call payload invalid",
                why=why,
                how_to_fix="Return list[dict] function calls with valid arguments.",
                where="skills.sub_skill_runner.run",
                fallback_trigger_reason=fallback_reason,
            ),
        )

    def _normalize_skill_name(self, skill_name: str) -> str:
        return skill_name.replace("-", "_").strip().lower()

    def _query_with_override(self, query: QueryParam, text: str) -> QueryParam:
        next_query = query.model_copy()
        next_query.query = text
        return next_query

    def _dedupe_episodes(self, episodes: list[Episode]) -> list[Episode]:
        seen: set[str] = set()
        deduped: list[Episode] = []
        for episode in episodes:
            if episode.uid in seen:
                continue
            seen.add(episode.uid)
            deduped.append(episode)
        return deduped

    def _extract_split_queries(self, summary: str, query: str) -> list[str]:  # noqa: C901
        stripped = summary.strip()
        if not stripped:
            return [query]

        candidate_queries: list[str] = []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            payloads: list[dict[str, object]] = [parsed]
            wrapped_v1 = parsed.get("v1")
            if isinstance(wrapped_v1, dict):
                # Accept strict contract wrappers like {"v1": {...}}.
                payloads.insert(0, wrapped_v1)

            for payload in payloads:
                for key in ("sub_queries", "queries", "branch_queries"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        candidate_queries.extend(
                            item.strip()
                            for item in value
                            if isinstance(item, str) and item.strip()
                        )
            if not candidate_queries:
                for payload in payloads:
                    value = payload.get("query")
                    if isinstance(value, str) and value.strip():
                        candidate_queries.append(value.strip())
        elif isinstance(parsed, list):
            candidate_queries.extend(
                item.strip()
                for item in parsed
                if isinstance(item, str) and item.strip()
            )
        else:
            for line in stripped.splitlines():
                value = line.strip()
                if value:
                    candidate_queries.append(value)

        if not candidate_queries:
            candidate_queries = [query]

        normalized: list[str] = []
        seen: set[str] = set()
        for text in candidate_queries:
            key = " ".join(text.lower().split())
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)

        if not normalized:
            return [query]
        return normalized[: self._split_parallel_cap]

    def _branch_requires_coq(self, branch_query: str) -> bool:
        lowered = branch_query.lower()
        dependency_markers = (
            " then ",
            " after ",
            " using that",
            " based on that",
            " once you find",
            " given the answer",
            " from there",
            " trace ",
            " derive ",
        )
        if any(marker in lowered for marker in dependency_markers):
            return True
        # Possessive chain heuristic: "A's B's C" usually implies multi-hop.
        return lowered.count("'s") >= 2

    @staticmethod
    def _normalize_selected_skill(skill_name: str | None) -> str:
        if not isinstance(skill_name, str):
            return "direct_memory"
        normalized = skill_name.strip().replace("-", "_").lower()
        if normalized in {"coq", "split", "direct_memory"}:
            return normalized
        return "direct_memory"

    @staticmethod
    def _execution_skill_for_branch(selected_skill: str) -> str:
        # Prevent recursive split-of-split loops at branch execution time.
        if selected_skill == "split":
            return "coq"
        return selected_skill

    @staticmethod
    def _metric_as_int(metrics: dict[str, object], key: str) -> int:
        value = metrics.get(key, 0)
        if isinstance(value, bool):
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        return 0

    @staticmethod
    def _metric_as_float(metrics: dict[str, object], key: str) -> float:
        value = metrics.get(key, 0.0)
        if isinstance(value, bool):
            return 0.0
        if isinstance(value, int | float):
            return float(value)
        return 0.0

    def _tool_calls_from_live_result(  # noqa: C901
        self,
        *,
        live_result: SkillRunResult,
        query: QueryParam,
        memmachine_call_details: list[dict[str, object]] | None = None,
    ) -> list[SkillToolCallRecord]:
        records: list[SkillToolCallRecord] = []
        call_details = memmachine_call_details or []
        memmachine_call_index = 0
        for step_index, execution in enumerate(live_result.tool_executions, start=1):
            action = parse_sub_skill_tool_call(
                tool_name=execution.name,
                arguments=execution.arguments,
            )
            if action.action == "memmachine_search":
                output = execution.output
                episodes_returned = 0
                cached = False
                if isinstance(output, dict):
                    raw_count = output.get("episodes_returned", 0)
                    if isinstance(raw_count, int):
                        episodes_returned = raw_count
                    cached = bool(output.get("cached", False))
                call_arguments: dict[str, object] = {
                    "query": action.query or query.query
                }
                episodes_human_readable: list[str] = []
                if memmachine_call_index < len(call_details):
                    detail = call_details[memmachine_call_index]
                    memmachine_call_index += 1
                    raw_query = detail.get("query")
                    if isinstance(raw_query, str) and raw_query.strip():
                        call_arguments["query"] = raw_query
                    raw_episode_lines = detail.get("episodes_human_readable")
                    if isinstance(raw_episode_lines, list):
                        episodes_human_readable = [
                            line
                            for line in raw_episode_lines
                            if isinstance(line, str) and line.strip()
                        ]
                    raw_cached = detail.get("cached")
                    if isinstance(raw_cached, bool):
                        call_arguments["cached"] = raw_cached
                    cached_from_query = detail.get("cached_from_query")
                    if isinstance(cached_from_query, str) and cached_from_query.strip():
                        call_arguments["cached_from_query"] = cached_from_query
                call_arguments["episodes_human_readable"] = episodes_human_readable
                result_summary = f"episodes={episodes_returned}"
                if cached:
                    result_summary += "; cached=true"
                records.append(
                    SkillToolCallRecord(
                        step=step_index,
                        tool_name=action.action,
                        arguments=call_arguments,
                        status="success",
                        result_summary=result_summary,
                        raw_result=self._sanitize_raw_tool_result(execution.output),
                    )
                )
                continue
            if action.action == "return_sub_skill_result":
                records.append(
                    SkillToolCallRecord(
                        step=step_index,
                        tool_name=action.action,
                        arguments={"summary": action.summary},
                        status="success",
                        result_summary="summary recorded",
                        raw_result=self._sanitize_raw_tool_result(execution.output),
                    )
                )
                continue
            records.append(
                SkillToolCallRecord(
                    step=step_index,
                    tool_name=action.action,
                    arguments=execution.arguments,
                    status="ignored",
                    result_summary="unsupported action ignored",
                    raw_result=self._sanitize_raw_tool_result(execution.output),
                )
            )
        return records

    async def _run_standard_skill(  # noqa: C901
        self,
        *,
        skill_name: str,
        spec: SkillSpecV1,
        policy: QueryPolicy,
        query: QueryParam,
    ) -> SubSkillExecutionResult:
        prompt = spec.policy_markdown or spec.description
        bounded_max_steps = max(1, spec.max_steps)
        result = SubSkillExecutionResult(
            skill_name=skill_name,
            query=query.query,
            status="in_progress",
        )
        collected_episodes: list[Episode] = []
        memmachine_call_details: list[dict[str, object]] = []
        cached_query_results: list[dict[str, object]] = []
        summary_from_tool: str = ""
        memory_search_called = 0
        memory_retrieval_time = 0.0

        async def _tool_memmachine_search(  # noqa: C901
            arguments: dict[str, object],
        ) -> dict[str, object]:
            nonlocal memory_search_called, memory_retrieval_time
            next_query = str(arguments.get("query") or query.query)
            normalized_query = self._normalize_query_for_cache(next_query)
            query_tokens = self._query_tokens(next_query)
            matched_cache: dict[str, object] | None = None
            for cached in cached_query_results:
                cached_norm = cached.get("normalized_query")
                if isinstance(cached_norm, str) and cached_norm == normalized_query:
                    matched_cache = cached
                    break
            if matched_cache is None and len(query_tokens) >= 4:
                best_match: dict[str, object] | None = None
                best_score = 0.0
                for cached in cached_query_results:
                    cached_tokens = cached.get("query_tokens")
                    if not isinstance(cached_tokens, set):
                        continue
                    score = self._query_similarity(query_tokens, cached_tokens)
                    if score > best_score:
                        best_score = score
                        best_match = cached
                if best_match is not None and best_score >= 0.85:
                    matched_cache = best_match

            cached = matched_cache is not None
            cached_from_query: str | None = None
            if matched_cache is not None:
                episodes = matched_cache["episodes"]
                assert isinstance(episodes, list)
                cached_from_query = matched_cache.get("query")
                if not isinstance(cached_from_query, str):
                    cached_from_query = None
            else:
                next_param = self._query_with_override(query, next_query)
                episodes, memory_metrics = await self._memory_tool.do_query(
                    policy, next_param
                )
                memory_search_called += self._metric_as_int(
                    memory_metrics,
                    "memory_search_called",
                )
                memory_retrieval_time += self._metric_as_float(
                    memory_metrics,
                    "memory_retrieval_time",
                )
                collected_episodes.extend(episodes)
                cached_query_results.append(
                    {
                        "query": next_query,
                        "normalized_query": normalized_query,
                        "query_tokens": query_tokens,
                        "episodes": episodes,
                    }
                )

            episode_lines = [
                line
                for line in episodes_to_string(episodes).splitlines()
                if line.strip()
            ]
            memmachine_call_details.append(
                {
                    "query": next_query,
                    "episodes_human_readable": episode_lines,
                    "cached": cached,
                    "cached_from_query": cached_from_query,
                }
            )
            response: dict[str, object] = {
                "episodes_returned": len(episodes),
                "query": next_query,
                "cached": cached,
                "episodes_human_readable": episode_lines,
            }
            if cached_from_query:
                response["cached_from_query"] = cached_from_query
            return response

        async def _tool_return_sub_skill_result(
            arguments: dict[str, object],
        ) -> dict[str, object]:
            nonlocal summary_from_tool
            summary_from_tool = str(arguments.get("summary") or "").strip()
            return {"summary_recorded": bool(summary_from_tool)}

        try:
            live_result = await self._session_model.run_live_session(
                system_prompt=prompt,
                user_prompt=f"sub-skill query: {query.query}",
                tools=sub_skill_tool_schemas(spec.allowed_tools),
                tool_registry={
                    "memmachine_search": _tool_memmachine_search,
                    "return_sub_skill_result": _tool_return_sub_skill_result,
                },
                max_turns=bounded_max_steps,
                timeout_seconds=float(spec.timeout_seconds),
            )
        except SkillToolCallFormatError:
            self._raise_invalid_output(
                why="Sub-skill tool call payload shape was invalid.",
                fallback_reason="invalid_sub_skill_output",
            )
        except SkillToolNotFoundError:
            self._raise_invalid_output(
                why="Sub-skill requested unsupported tool.",
                fallback_reason="invalid_sub_skill_output",
            )
        except SkillSessionLimitError:
            self._raise_invalid_output(
                why="Sub-skill exceeded configured max steps/time budget.",
                fallback_reason="sub_skill_max_steps_exceeded",
            )
        except SkillLanguageModelError as err:
            self._raise_invalid_output(
                why=f"Sub-skill session runtime failed: {err}",
                fallback_reason="invalid_sub_skill_output",
            )

        result.episodes = collected_episodes
        if not result.episodes and "memmachine_search" in spec.allowed_tools:
            # Preserve existing behavior when no explicit tool calls are emitted.
            episodes, memory_metrics = await self._memory_tool.do_query(policy, query)
            memory_search_called += self._metric_as_int(
                memory_metrics,
                "memory_search_called",
            )
            memory_retrieval_time += self._metric_as_float(
                memory_metrics,
                "memory_retrieval_time",
            )
            result.episodes = episodes

        result.tool_calls = self._tool_calls_from_live_result(
            live_result=live_result,
            query=query,
            memmachine_call_details=memmachine_call_details,
        )
        result.llm_time = float(live_result.llm_time_seconds)
        result.llm_call_count = int(live_result.turn_count)
        result.llm_input_tokens = int(live_result.llm_input_tokens)
        result.llm_output_tokens = int(live_result.llm_output_tokens)
        result.memory_search_called = memory_search_called
        result.memory_retrieval_time = memory_retrieval_time
        result.summary = summary_from_tool or live_result.final_response.strip()
        result.episodes = self._dedupe_episodes(result.episodes)
        result.status = "success"
        return result

    async def _select_split_branch(
        self,
        *,
        branch_query: str,
        policy: QueryPolicy,
        query: QueryParam,
        semaphore: asyncio.Semaphore,
    ) -> _SplitBranchSelection:
        async with semaphore:
            fallback_skill = (
                "coq" if self._branch_requires_coq(branch_query) else "direct_memory"
            )
            fallback_execution_skill = self._execution_skill_for_branch(fallback_skill)
            selector_result: SubSkillExecutionResult | None = None
            selector_parse_error: str | None = None
            total_selector_llm_time = 0.0
            total_selector_llm_call_count = 0
            total_selector_llm_input_tokens = 0
            total_selector_llm_output_tokens = 0
            max_selector_attempts = 2

            for _attempt in range(max_selector_attempts):
                try:
                    selector_result = await self.run(
                        skill_name="tool_select",
                        policy=policy,
                        query=self._query_with_override(query, branch_query),
                    )
                except Exception:
                    selector_parse_error = "selector_exception"
                    continue

                total_selector_llm_time += selector_result.llm_time
                total_selector_llm_call_count += selector_result.llm_call_count
                total_selector_llm_input_tokens += selector_result.llm_input_tokens
                total_selector_llm_output_tokens += selector_result.llm_output_tokens
                if selector_result.status != "success":
                    selector_parse_error = (
                        selector_result.fallback_trigger_reason
                        or "selector_status_not_success"
                    )
                    continue

                decision, parse_error = parse_route_decision_output_detailed(
                    selector_result.summary
                )
                if decision is None:
                    selector_parse_error = parse_error or "selector_parse_failed"
                    continue

                selected_skill = self._normalize_selected_skill(decision.selected_skill)
                return _SplitBranchSelection(
                    query=branch_query,
                    selected_skill=selected_skill,
                    execution_skill=self._execution_skill_for_branch(selected_skill),
                    status="success",
                    llm_time=total_selector_llm_time,
                    llm_call_count=total_selector_llm_call_count,
                    llm_input_tokens=total_selector_llm_input_tokens,
                    llm_output_tokens=total_selector_llm_output_tokens,
                    selector_summary=selector_result.summary,
                    selector_tool_calls=selector_result.tool_calls,
                )

            return _SplitBranchSelection(
                query=branch_query,
                selected_skill=fallback_skill,
                execution_skill=fallback_execution_skill,
                status="fallback",
                llm_time=total_selector_llm_time,
                llm_call_count=total_selector_llm_call_count,
                llm_input_tokens=total_selector_llm_input_tokens,
                llm_output_tokens=total_selector_llm_output_tokens,
                parse_error=selector_parse_error or "selector_unclassifiable",
                selector_summary=(
                    selector_result.summary if selector_result is not None else ""
                ),
                selector_tool_calls=(
                    selector_result.tool_calls if selector_result is not None else []
                ),
            )

    async def _execute_split_branch(
        self,
        *,
        branch_selection: _SplitBranchSelection,
        policy: QueryPolicy,
        query: QueryParam,
        semaphore: asyncio.Semaphore,
    ) -> _SplitBranchResult:
        async with semaphore:
            retry_count = 0
            execution_skill = branch_selection.execution_skill
            for attempt in range(self._split_branch_retry_limit + 1):
                try:
                    next_param = self._query_with_override(query, branch_selection.query)
                    if execution_skill in {"coq", "split"}:
                        branch_skill_result = await self.run(
                            skill_name=execution_skill,
                            policy=policy,
                            query=next_param,
                        )
                        if branch_skill_result.status != "success":
                            return _SplitBranchResult(
                                query=branch_selection.query,
                                route=execution_skill,
                                selected_skill=branch_selection.selected_skill,
                                status="failed",
                                episodes=[],
                                retry_count=retry_count,
                                llm_time=branch_skill_result.llm_time,
                                llm_call_count=branch_skill_result.llm_call_count,
                                llm_input_tokens=branch_skill_result.llm_input_tokens,
                                llm_output_tokens=branch_skill_result.llm_output_tokens,
                                memory_search_called=(
                                    branch_skill_result.memory_search_called
                                ),
                                memory_retrieval_time=(
                                    branch_skill_result.memory_retrieval_time
                                ),
                                error=(
                                    f"{execution_skill} branch failed "
                                    f"(status={branch_skill_result.status}, "
                                    f"reason={branch_skill_result.fallback_trigger_reason})"
                                ),
                            )
                        return _SplitBranchResult(
                            query=branch_selection.query,
                            route=execution_skill,
                            selected_skill=branch_selection.selected_skill,
                            status="success",
                            episodes=branch_skill_result.episodes,
                            retry_count=retry_count,
                            llm_time=branch_skill_result.llm_time,
                            llm_call_count=branch_skill_result.llm_call_count,
                            llm_input_tokens=branch_skill_result.llm_input_tokens,
                            llm_output_tokens=branch_skill_result.llm_output_tokens,
                            memory_search_called=(
                                branch_skill_result.memory_search_called
                            ),
                            memory_retrieval_time=(
                                branch_skill_result.memory_retrieval_time
                            ),
                            nested_tool_calls=branch_skill_result.tool_calls,
                        )

                    episodes, memory_metrics = await self._memory_tool.do_query(
                        policy, next_param
                    )
                    return _SplitBranchResult(
                        query=branch_selection.query,
                        route="direct_memory",
                        selected_skill=branch_selection.selected_skill,
                        status="success",
                        episodes=self._dedupe_episodes(episodes),
                        retry_count=retry_count,
                        llm_time=0.0,
                        llm_call_count=0,
                        llm_input_tokens=0,
                        llm_output_tokens=0,
                        memory_search_called=self._metric_as_int(
                            memory_metrics,
                            "memory_search_called",
                        ),
                        memory_retrieval_time=self._metric_as_float(
                            memory_metrics,
                            "memory_retrieval_time",
                        ),
                    )
                except Exception as err:
                    if attempt < self._split_branch_retry_limit:
                        retry_count += 1
                        continue
                    return _SplitBranchResult(
                        query=branch_selection.query,
                        route=execution_skill,
                        selected_skill=branch_selection.selected_skill,
                        status="failed",
                        episodes=[],
                        retry_count=retry_count,
                        llm_time=0.0,
                        llm_call_count=0,
                        llm_input_tokens=0,
                        llm_output_tokens=0,
                        error=str(err),
                    )

        return _SplitBranchResult(
            query=branch_selection.query,
            route=execution_skill,
            selected_skill=branch_selection.selected_skill,
            status="failed",
            episodes=[],
            retry_count=retry_count,
            llm_time=0.0,
            llm_call_count=0,
            llm_input_tokens=0,
            llm_output_tokens=0,
            error="split branch execution exited unexpectedly",
        )

    async def _run_split_skill(
        self,
        *,
        skill_name: str,
        spec: SkillSpecV1,
        policy: QueryPolicy,
        query: QueryParam,
    ) -> SubSkillExecutionResult:
        planner_result = await self._run_standard_skill(
            skill_name=skill_name,
            spec=spec,
            policy=policy,
            query=query,
        )
        branch_queries = self._extract_split_queries(
            planner_result.summary, query.query
        )

        selector_semaphore = asyncio.Semaphore(self._split_parallel_cap)
        selector_tasks = [
            self._select_split_branch(
                branch_query=branch_query,
                policy=policy,
                query=query,
                semaphore=selector_semaphore,
            )
            for branch_query in branch_queries
        ]
        branch_selections = await asyncio.gather(*selector_tasks)

        execution_semaphore = asyncio.Semaphore(self._split_parallel_cap)
        branch_tasks = [
            self._execute_split_branch(
                branch_selection=branch_selection,
                policy=policy,
                query=query,
                semaphore=execution_semaphore,
            )
            for branch_selection in branch_selections
        ]
        branch_results = await asyncio.gather(*branch_tasks)

        result = SubSkillExecutionResult(
            skill_name=skill_name,
            query=query.query,
            status="in_progress",
            summary=planner_result.summary,
            episodes=list(planner_result.episodes),
            tool_calls=list(planner_result.tool_calls),
            llm_time=planner_result.llm_time,
            llm_call_count=planner_result.llm_call_count,
            llm_input_tokens=planner_result.llm_input_tokens,
            llm_output_tokens=planner_result.llm_output_tokens,
            memory_search_called=planner_result.memory_search_called,
            memory_retrieval_time=planner_result.memory_retrieval_time,
        )

        branch_success_count = 0
        branch_failure_count = 0
        branch_retry_count = 0
        for branch_index, (branch_selection, branch_result) in enumerate(
            zip(branch_selections, branch_results, strict=True),
            start=1,
        ):
            branch_retry_count += branch_result.retry_count
            result.llm_time += branch_selection.llm_time
            result.llm_time += branch_result.llm_time
            result.llm_call_count += branch_selection.llm_call_count
            result.llm_call_count += branch_result.llm_call_count
            result.llm_input_tokens += branch_selection.llm_input_tokens
            result.llm_input_tokens += branch_result.llm_input_tokens
            result.llm_output_tokens += branch_selection.llm_output_tokens
            result.llm_output_tokens += branch_result.llm_output_tokens
            result.memory_search_called += branch_result.memory_search_called
            result.memory_retrieval_time += branch_result.memory_retrieval_time
            if branch_result.status == "success":
                branch_success_count += 1
                result.episodes.extend(branch_result.episodes)
            else:
                branch_failure_count += 1

            result.tool_calls.append(
                SkillToolCallRecord(
                    step=len(result.tool_calls) + 1,
                    tool_name="split_branch_selection",
                    arguments={
                        "branch_index": branch_index,
                        "query": branch_selection.query,
                    },
                    status=(
                        "success"
                        if branch_selection.status == "success"
                        else "fallback"
                    ),
                    result_summary=(
                        f"selected_skill={branch_selection.selected_skill}; "
                        f"execution_skill={branch_selection.execution_skill}"
                    ),
                    raw_result={
                        "selected_skill": branch_selection.selected_skill,
                        "execution_skill": branch_selection.execution_skill,
                        "selector_status": branch_selection.status,
                        "selector_parse_error": branch_selection.parse_error,
                        "selector_summary": branch_selection.selector_summary[:400],
                    },
                )
            )
            for selector_record in branch_selection.selector_tool_calls or []:
                result.tool_calls.append(
                    SkillToolCallRecord(
                        step=len(result.tool_calls) + 1,
                        tool_name=f"split_branch_selection.{selector_record.tool_name}",
                        arguments={
                            "branch_index": branch_index,
                            **selector_record.arguments,
                        },
                        status=selector_record.status,
                        result_summary=selector_record.result_summary,
                        raw_result=selector_record.raw_result,
                    )
                )

            result.tool_calls.append(
                SkillToolCallRecord(
                    step=len(result.tool_calls) + 1,
                    tool_name="split_branch_execution",
                    arguments={
                        "branch_index": branch_index,
                        "query": branch_result.query,
                        "selected_skill": branch_result.selected_skill,
                        "execution_skill": branch_result.route,
                    },
                    status=branch_result.status,
                    result_summary=(
                        f"episodes={len(branch_result.episodes)}"
                        if branch_result.status == "success"
                        else f"error={branch_result.error[:160]}"
                    ),
                    raw_result=(
                        {
                            "episodes_returned": len(branch_result.episodes),
                            "selected_skill": branch_result.selected_skill,
                            "execution_skill": branch_result.route,
                        }
                        if branch_result.status == "success"
                        else {
                            "error": branch_result.error[:160],
                            "selected_skill": branch_result.selected_skill,
                            "execution_skill": branch_result.route,
                        }
                    ),
                )
            )
            for nested_record in branch_result.nested_tool_calls or []:
                result.tool_calls.append(
                    SkillToolCallRecord(
                        step=len(result.tool_calls) + 1,
                        tool_name=f"split_branch_execution.{nested_record.tool_name}",
                        arguments={
                            "branch_index": branch_index,
                            **nested_record.arguments,
                        },
                        status=nested_record.status,
                        result_summary=nested_record.result_summary,
                        raw_result=nested_record.raw_result,
                    )
                )

        result.episodes = self._dedupe_episodes(result.episodes)
        result.branch_total = len(branch_results)
        result.branch_success_count = branch_success_count
        result.branch_failure_count = branch_failure_count
        result.branch_retry_count = branch_retry_count
        if branch_failure_count > 0:
            result.status = "failed"
            result.fallback_trigger_reason = "split_branch_failure"
        else:
            result.status = "success"

        if not result.summary.strip():
            result.summary = json.dumps(
                {
                    "branch_total": result.branch_total,
                    "branch_success_count": result.branch_success_count,
                    "branch_failure_count": result.branch_failure_count,
                    "branch_retry_count": result.branch_retry_count,
                }
            )
        return result

    async def run(
        self,
        *,
        skill_name: str,
        policy: QueryPolicy,
        query: QueryParam,
    ) -> SubSkillExecutionResult:
        """Execute one sub-skill and return merged episodes + tool-call records."""
        spec = self._load_sub_skill_spec(skill_name)
        if self._normalize_skill_name(skill_name) == "split":
            return await self._run_split_skill(
                skill_name=skill_name,
                spec=spec,
                policy=policy,
                query=query,
            )
        return await self._run_standard_skill(
            skill_name=skill_name,
            spec=spec,
            policy=policy,
            query=query,
        )
