"""Top-level markdown-guided retrieval orchestration runtime."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, cast

from memmachine_server.common.episode_store import Episode
from memmachine_server.common.episode_store.episode_model import episodes_to_string
from memmachine_server.common.language_model import (
    SkillLanguageModel,
    SkillLanguageModelError,
    SkillSessionLimitError,
    SkillSessionModelProtocol,
    SkillToolCallFormatError,
    SkillToolNotFoundError,
)
from memmachine_server.retrieval_skill.common.skill_api import (
    QueryParam,
    QueryPolicy,
    SkillToolBase,
    SkillToolBaseParam,
)
from memmachine_server.retrieval_skill.skills.runtime import (
    build_skill_request,
    fallback_for_downstream_error,
)
from memmachine_server.retrieval_skill.skills.session_state import (
    TopLevelSkillSessionState,
)
from memmachine_server.retrieval_skill.skills.spec_loader import load_skill_spec
from memmachine_server.retrieval_skill.skills.tool_protocol import (
    TOP_LEVEL_TOOL_NAMES,
    parse_top_level_tool_call,
    top_level_tool_schemas,
)
from memmachine_server.retrieval_skill.skills.types import (
    SkillContractError,
    SkillContractErrorCode,
    SkillContractErrorPayload,
)

logger = logging.getLogger(__name__)

DEFAULT_RETRIEVE_SKILL_SPEC = (
    Path(__file__).resolve().parent / "specs" / "top_level" / "retrieve_skill.md"
)


class RetrieveSkill(SkillToolBase):
    """Top-level orchestrator that enforces markdown-driven action contracts."""

    def __init__(self, param: SkillToolBaseParam) -> None:
        """Initialize top-level markdown policy and memory tool wiring."""
        super().__init__(param)
        if self._model is None:
            raise ValueError("RetrieveSkill requires a language model.")

        self._extra_params = param.extra_params or {}
        raw_spec = self._extra_params.get("skill_spec", DEFAULT_RETRIEVE_SKILL_SPEC)
        self._spec = load_skill_spec(raw_spec)
        self._global_timeout_seconds = int(
            self._extra_params.get("global_timeout_seconds", self._spec.timeout_seconds)
        )

        fallback_name = self._extra_params.get("fallback_tool_name", "MemMachineSkill")
        self._memory_tool = self._find_child_tool(fallback_name)
        if self._memory_tool is None:
            raise ValueError(
                f"RetrieveSkill requires a fallback child tool named '{fallback_name}'."
            )

        raw_session_model = self._extra_params.get("skill_session_model")
        if raw_session_model is None:
            self._session_model = (
                SkillLanguageModel.from_openai_responses_language_model(self._model)
            )
        elif hasattr(raw_session_model, "run_live_session"):
            self._session_model = cast(SkillSessionModelProtocol, raw_session_model)
        else:
            raise ValueError(
                "RetrieveSkill extra_params['skill_session_model'] must implement "
                "run_live_session(...)."
            )

    @property
    def skill_name(self) -> str:
        return "RetrieveSkill"

    @property
    def skill_description(self) -> str:
        return (
            "Top-level retrieval skill orchestrator driven by markdown policy "
            "tool contracts and explicit fallback reasons."
        )

    @property
    def accuracy_score(self) -> int:
        return 8

    @property
    def token_cost(self) -> int:
        return 7

    @property
    def time_cost(self) -> int:
        return 7

    def _find_child_tool(self, tool_name: str) -> SkillToolBase | None:
        for tool in self._children_tools:
            if tool.skill_name == tool_name:
                return tool
        return None

    def _new_session_state(self, query: QueryParam) -> TopLevelSkillSessionState:
        session = TopLevelSkillSessionState.new(
            route_name=self._spec.route_name,
            policy_name=self._spec.name,
            query=query.query,
        )
        session.record_event(
            actor="top-level",
            event_type="session_started",
            detail="Top-level retrieve-skill session initialized.",
        )
        return session

    def _augment_metrics_with_session_state(
        self,
        *,
        metrics: dict[str, object],
        session: TopLevelSkillSessionState,
    ) -> dict[str, object]:
        metrics["orchestrator_step_count"] = session.current_step
        metrics["orchestrator_event_count"] = len(session.events)
        metrics["orchestrator_tool_call_count"] = len(session.tool_calls)
        metrics["orchestrator_episode_count"] = len(session.merged_episodes)
        metrics["orchestrator_completed"] = session.completed
        metrics["orchestrator_policy_kind"] = self._spec.kind
        metrics["orchestrator_state_snapshot"] = session.prompt_snapshot()
        metrics["orchestrator_final_response"] = session.final_response
        metrics["orchestrator_trace"] = session.full_trace_snapshot()
        return metrics

    def _contract_error(self, *, why: str, fallback_reason: str) -> SkillContractError:
        return SkillContractError(
            code=SkillContractErrorCode.INVALID_OUTPUT,
            payload=SkillContractErrorPayload(
                what_failed="Top-level tool-call contract validation failed",
                why=why,
                how_to_fix=(
                    "Emit only allowed tool calls with valid arguments and "
                    "finish with return_final."
                ),
                where="skills.retrieve_skill.do_query",
                fallback_trigger_reason=fallback_reason,
            ),
        )

    def _raise_contract_error(self, *, why: str, fallback_reason: str) -> None:
        raise self._contract_error(why=why, fallback_reason=fallback_reason)

    def _query_with_override(self, query: QueryParam, text: str) -> QueryParam:
        next_query = query.model_copy()
        next_query.query = text
        return next_query

    @staticmethod
    def _sanitize_tool_raw_result(raw: object) -> dict[str, object] | None:
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

    @staticmethod
    def _normalize_episode_indices(raw: object) -> list[int]:
        if not isinstance(raw, list):
            return []
        normalized: list[int] = []
        seen: set[int] = set()
        for item in raw:
            if isinstance(item, bool):
                continue
            value: int | None = None
            if isinstance(item, int):
                value = item
            elif isinstance(item, float) and item.is_integer():
                value = int(item)
            if value is None or value < 0 or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    async def _finalize_episodes(
        self,
        *,
        query: QueryParam,
        episodes: list[Episode],
    ) -> tuple[list[Episode], bool]:
        reranked = await self._do_rerank(query, episodes)
        rerank_applied = bool(
            self._reranker is not None
            and query.limit > 0
            and len(episodes) > query.limit
        )
        return reranked, rerank_applied

    async def _fallback_with_reason(
        self,
        *,
        policy: QueryPolicy,
        query: QueryParam,
        session: TopLevelSkillSessionState,
        reason: str,
        code: str,
        aggregated_metrics: dict[str, Any] | None = None,
    ) -> tuple[list[Episode], dict[str, object]]:
        session.next_step()
        fallback_episodes, fallback_metrics = await self._memory_tool.do_query(
            policy, query
        )
        fallback_arguments: dict[str, object] = {
            "query": query.query,
            "rationale": f"runtime_fallback:{reason}",
        }
        session.record_tool_call(
            tool_name="memmachine_search",
            arguments=fallback_arguments,
            status="success",
            result_summary=f"episodes={len(fallback_episodes)}",
            raw_result={
                "query": query.query,
                "episodes_returned": len(fallback_episodes),
                "fallback_reason": reason,
            },
        )
        session.record_event(
            actor="top-level",
            event_type="fallback_applied",
            detail=f"Fallback executed with reason={reason}.",
        )
        session.merge_episodes(fallback_episodes)
        session.finalize()

        metrics: dict[str, object] = {}
        if aggregated_metrics is not None:
            metrics.update(cast(dict[str, object], aggregated_metrics))
        metrics.update(fallback_metrics)
        metrics["skill"] = self.skill_name
        metrics["route"] = self.skill_name
        metrics["selected_skill"] = "memmachine_search"
        metrics["selected_skill_name"] = "MemMachineSkill"
        metrics["fallback_trigger_reason"] = reason
        metrics["skill_contract_error_code"] = code
        metrics["top_level_session_invocation_count"] = 1
        metrics.setdefault("llm_call_count", 0)
        metrics.setdefault("input_token", 0)
        metrics.setdefault("output_token", 0)
        metrics.setdefault("top_level_sufficiency_signal_seen", False)
        metrics.setdefault("top_level_is_sufficient", False)

        final_episodes, rerank_applied = await self._finalize_episodes(
            query=query,
            episodes=session.merged_episodes,
        )
        metrics["rerank_applied"] = rerank_applied
        metrics["final_episode_count"] = len(final_episodes)
        return final_episodes, self._augment_metrics_with_session_state(
            metrics=metrics,
            session=session,
        )

    async def do_query(  # noqa: C901
        self,
        policy: QueryPolicy,
        query: QueryParam,
    ) -> tuple[list[Episode], dict[str, object]]:
        route_name = self._spec.route_name
        session = self._new_session_state(query)
        aggregated_metrics: dict[str, Any] = {}
        global_started = time.monotonic()

        def _global_timeout_exceeded() -> bool:
            elapsed = time.monotonic() - global_started
            return elapsed > float(self._global_timeout_seconds)

        try:
            _ = build_skill_request(query, route_name=route_name)
            allowed_tools = set(self._spec.allowed_tools or TOP_LEVEL_TOOL_NAMES)

            async def _execute_memmachine_search(
                arguments: dict[str, object],
            ) -> dict[str, object]:
                session.next_step()
                if _global_timeout_exceeded():
                    self._raise_contract_error(
                        why="Global timeout exceeded during MemMachine search.",
                        fallback_reason="global_timeout",
                    )

                action = parse_top_level_tool_call(
                    tool_name="memmachine_search",
                    arguments=arguments,
                )
                if action.action not in allowed_tools:
                    self._raise_contract_error(
                        why=(
                            f"Tool '{action.action}' not allowed by top-level "
                            "markdown policy."
                        ),
                        fallback_reason="invalid_tool_call",
                    )

                search_query = action.query or query.query
                episodes, perf_metrics = await self._memory_tool.do_query(
                    policy,
                    self._query_with_override(query, search_query),
                )
                aggregated_metrics.update(
                    self._update_perf_metrics(perf_metrics, aggregated_metrics)
                )
                session.merge_episodes(episodes)

                call_arguments: dict[str, object] = {
                    "query": search_query,
                    "rationale": action.rationale,
                }
                episode_lines = [
                    line for line in episodes_to_string(episodes).splitlines() if line
                ]
                response_payload: dict[str, object] = {
                    "episodes_returned": len(episodes),
                    "query": search_query,
                    "episodes_human_readable": episode_lines,
                }
                session.record_tool_call(
                    tool_name="memmachine_search",
                    arguments=call_arguments,
                    status="success",
                    result_summary=f"episodes={len(episodes)}",
                    raw_result=self._sanitize_tool_raw_result(response_payload),
                )
                session.record_event(
                    actor="top-level",
                    event_type="memmachine_search_completed",
                    detail=f"step={session.current_step}; episodes={len(episodes)}",
                )
                return response_payload

            async def _execute_return_final(  # noqa: C901
                arguments: dict[str, object],
            ) -> dict[str, object]:
                session.next_step()
                action = parse_top_level_tool_call(
                    tool_name="return_final",
                    arguments=arguments,
                )
                if action.action not in allowed_tools:
                    self._raise_contract_error(
                        why=(
                            f"Tool '{action.action}' not allowed by top-level "
                            "markdown policy."
                        ),
                        fallback_reason="invalid_tool_call",
                    )

                final_response = (
                    action.final_response.strip()
                    if action.final_response
                    else "Top-level retrieval complete."
                )
                if isinstance(action.is_sufficient, bool):
                    top_level_is_sufficient = action.is_sufficient
                    top_level_signal_source = "explicit"
                else:
                    top_level_is_sufficient = bool(session.merged_episodes)
                    top_level_signal_source = "default_from_evidence"

                confidence_score = action.confidence_score
                normalized_confidence: float | None = None
                if isinstance(confidence_score, int | float) and not isinstance(
                    confidence_score, bool
                ):
                    normalized_confidence = float(confidence_score)

                related_episode_indices = self._normalize_episode_indices(
                    action.related_episode_indices
                )
                selected_episode_indices = self._normalize_episode_indices(
                    action.selected_episode_indices
                )

                aggregated_metrics["top_level_sufficiency_signal_seen"] = True
                aggregated_metrics["top_level_is_sufficient"] = top_level_is_sufficient
                aggregated_metrics["top_level_sufficiency_signal_source"] = (
                    top_level_signal_source
                )
                if normalized_confidence is not None:
                    aggregated_metrics["top_level_confidence_score"] = (
                        normalized_confidence
                    )
                if isinstance(action.reason_code, str) and action.reason_code.strip():
                    aggregated_metrics["top_level_reason_code"] = action.reason_code
                if isinstance(action.reason_note, str) and action.reason_note.strip():
                    aggregated_metrics["top_level_reason_note"] = action.reason_note
                if related_episode_indices:
                    aggregated_metrics["top_level_related_episode_indices"] = (
                        related_episode_indices
                    )
                if selected_episode_indices:
                    aggregated_metrics["top_level_selected_episode_indices"] = (
                        selected_episode_indices
                    )

                return_arguments: dict[str, object] = {
                    "final_response": final_response,
                    "rationale": action.rationale,
                    "is_sufficient": top_level_is_sufficient,
                }
                if normalized_confidence is not None:
                    return_arguments["confidence_score"] = normalized_confidence
                if isinstance(action.reason_code, str) and action.reason_code.strip():
                    return_arguments["reason_code"] = action.reason_code
                if isinstance(action.reason_note, str) and action.reason_note.strip():
                    return_arguments["reason_note"] = action.reason_note
                if related_episode_indices:
                    return_arguments["related_episode_indices"] = (
                        related_episode_indices
                    )
                if selected_episode_indices:
                    return_arguments["selected_episode_indices"] = (
                        selected_episode_indices
                    )

                session.record_tool_call(
                    tool_name="return_final",
                    arguments=return_arguments,
                    status="success",
                    result_summary="orchestration finalized",
                    raw_result={
                        "final_response": final_response,
                        "is_sufficient": top_level_is_sufficient,
                        "confidence_score": normalized_confidence,
                        "reason_code": action.reason_code,
                        "reason_note": action.reason_note,
                        "related_episode_indices": related_episode_indices,
                        "selected_episode_indices": selected_episode_indices,
                    },
                )
                session.record_event(
                    actor="top-level",
                    event_type="orchestration_completed",
                    detail=(
                        f"step={session.current_step}; finalized by top-level policy; "
                        f"is_sufficient={top_level_is_sufficient}; "
                        f"confidence={normalized_confidence if normalized_confidence is not None else 'n/a'}"
                    ),
                )
                session.finalize(response=final_response)
                return {"final_response": final_response}

            tool_registry: dict[str, Any] = {}
            if "memmachine_search" in allowed_tools:
                tool_registry["memmachine_search"] = _execute_memmachine_search
            if "return_final" in allowed_tools:
                tool_registry["return_final"] = _execute_return_final

            session_result = await self._session_model.run_live_session(
                system_prompt=self._spec.policy_markdown or self._spec.description,
                user_prompt=(
                    f"query: {query.query}\n"
                    f"state: {session.prompt_snapshot()}\n"
                    "choose tool calls to complete retrieval"
                ),
                tools=top_level_tool_schemas(self._spec.allowed_tools),
                tool_registry=tool_registry,
                max_turns=self._spec.max_steps,
                timeout_seconds=float(self._global_timeout_seconds),
            )
            aggregated_metrics["llm_time"] = float(
                aggregated_metrics.get("llm_time", 0.0)
            ) + float(session_result.llm_time_seconds)
            self._update_perf_metrics(
                {
                    "llm_call_count": int(session_result.turn_count),
                    "input_token": int(session_result.llm_input_tokens),
                    "output_token": int(session_result.llm_output_tokens),
                    "top_level_input_token": int(session_result.llm_input_tokens),
                    "top_level_output_token": int(session_result.llm_output_tokens),
                    "top_level_llm_call_count": int(session_result.turn_count),
                },
                aggregated_metrics,
            )

            if not session.completed:
                if not session.tool_calls:
                    session.next_step()
                    episodes, perf_metrics = await self._memory_tool.do_query(
                        policy, query
                    )
                    aggregated_metrics = self._update_perf_metrics(
                        perf_metrics,
                        aggregated_metrics,
                    )
                    session.merge_episodes(episodes)
                    session.record_tool_call(
                        tool_name="memmachine_search",
                        arguments={"query": query.query},
                        status="success",
                        result_summary=(
                            "No top-level tool call emitted; MemMachine search "
                            f"executed. episodes={len(episodes)}"
                        ),
                        raw_result={
                            "query": query.query,
                            "episodes_returned": len(episodes),
                        },
                    )
                    session.record_event(
                        actor="top-level",
                        event_type="default_memmachine_search",
                        detail=(
                            "No function calls returned; performed MemMachine search."
                        ),
                    )

                final_response = (
                    session.final_response
                    or session_result.final_response.strip()
                    or "Top-level retrieval complete."
                )
                session.finalize(response=final_response)

            metrics: dict[str, object] = dict(aggregated_metrics)
            metrics["skill"] = self.skill_name
            metrics["route"] = self.skill_name
            metrics["skill_name"] = self._spec.name
            metrics["top_level_session_invocation_count"] = 1
            metrics["top_level_session_turn_count"] = session_result.turn_count
            metrics.setdefault("llm_call_count", 0)
            metrics.setdefault("input_token", 0)
            metrics.setdefault("output_token", 0)
            metrics.setdefault("top_level_sufficiency_signal_seen", False)
            metrics.setdefault("top_level_is_sufficient", bool(session.merged_episodes))
            metrics["selected_skill"] = "memmachine_search"
            metrics["selected_skill_name"] = "MemMachineSkill"

            final_episodes, rerank_applied = await self._finalize_episodes(
                query=query,
                episodes=session.merged_episodes,
            )
            metrics["rerank_applied"] = rerank_applied
            metrics["final_episode_count"] = len(final_episodes)
            metrics = self._augment_metrics_with_session_state(
                metrics=metrics,
                session=session,
            )

        except SkillToolCallFormatError:
            err = self._contract_error(
                why="Top-level tool-call payload shape invalid.",
                fallback_reason="invalid_tool_call",
            )
            return await self._fallback_with_reason(
                policy=policy,
                query=query,
                session=session,
                reason=err.payload.fallback_trigger_reason,
                code=err.code,
                aggregated_metrics=aggregated_metrics,
            )
        except SkillToolNotFoundError:
            err = self._contract_error(
                why="Top-level requested unsupported tool name.",
                fallback_reason="invalid_tool_call",
            )
            return await self._fallback_with_reason(
                policy=policy,
                query=query,
                session=session,
                reason=err.payload.fallback_trigger_reason,
                code=err.code,
                aggregated_metrics=aggregated_metrics,
            )
        except SkillSessionLimitError as err:
            reason = "max_steps_exceeded"
            if "timeout" in str(err).lower():
                reason = "global_timeout"
            contract_error = self._contract_error(
                why=f"Top-level live session exceeded configured guardrails: {err}",
                fallback_reason=reason,
            )
            return await self._fallback_with_reason(
                policy=policy,
                query=query,
                session=session,
                reason=contract_error.payload.fallback_trigger_reason,
                code=contract_error.code,
                aggregated_metrics=aggregated_metrics,
            )
        except SkillLanguageModelError as err:
            contract_error = self._contract_error(
                why=f"Top-level live session failed: {err}",
                fallback_reason="downstream_tool_failure",
            )
            return await self._fallback_with_reason(
                policy=policy,
                query=query,
                session=session,
                reason=contract_error.payload.fallback_trigger_reason,
                code=contract_error.code,
                aggregated_metrics=aggregated_metrics,
            )
        except SkillContractError as err:
            logger.warning(
                "RetrieveSkill contract failure. reason=%s code=%s",
                err.payload.fallback_trigger_reason,
                err.code,
            )
            return await self._fallback_with_reason(
                policy=policy,
                query=query,
                session=session,
                reason=err.payload.fallback_trigger_reason,
                code=err.code,
                aggregated_metrics=aggregated_metrics,
            )
        except Exception as err:
            mapped = fallback_for_downstream_error(
                where="skills.retrieve_skill.do_query",
                error=err,
            )
            logger.exception(
                "RetrieveSkill downstream failure. reason=%s code=%s",
                mapped.payload.fallback_trigger_reason,
                mapped.code,
            )
            return await self._fallback_with_reason(
                policy=policy,
                query=query,
                session=session,
                reason=mapped.payload.fallback_trigger_reason,
                code=mapped.code,
                aggregated_metrics=aggregated_metrics,
            )
        else:
            return final_episodes, metrics
