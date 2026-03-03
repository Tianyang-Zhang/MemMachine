from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from memmachine.common.episode_store import Episode, EpisodeResponse
from memmachine.common.language_model.language_model import LanguageModel
from memmachine.common.reranker.reranker import Reranker
from memmachine.episodic_memory import EpisodicMemory
from memmachine.retrieval_skill.common.skill_api import (
    QueryParam,
    QueryPolicy,
    SkillToolBaseParam,
)
from memmachine.retrieval_skill.skills.retrieve_skill import RetrieveSkill
from memmachine.retrieval_skill.subskills.direct_memory_skill import MemMachineSkill
from tests.memmachine.retrieval_skill.skill_session_stub import (
    ScriptedSkillSessionModel,
)


class ScriptedLanguageModel(LanguageModel):
    def __init__(
        self,
        *,
        outputs: list[tuple[str, list[dict[str, Any]] | None]],
    ) -> None:
        self._outputs = outputs

    async def generate_parsed_response(
        self,
        output_format: type[Any],
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        max_attempts: int = 1,
    ) -> Any | None:
        _ = output_format, system_prompt, user_prompt, max_attempts
        return None

    async def generate_response(
        self,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, str] | None = None,
        max_attempts: int = 1,
    ) -> tuple[str, Any]:
        _ = system_prompt, user_prompt, tools, tool_choice, max_attempts
        if not self._outputs:
            return "", []
        return self._outputs.pop(0)

    async def generate_response_with_token_usage(
        self,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, str] | None = None,
        max_attempts: int = 1,
    ) -> tuple[str, Any, int, int]:
        _ = system_prompt, user_prompt, tools, tool_choice, max_attempts
        return "", None, 0, 0


class DummyReranker(Reranker):
    async def score(self, query: str, candidates: list[str]) -> list[float]:
        _ = query
        return [float(len(candidates) - idx) for idx in range(len(candidates))]


class FakeEpisodicMemory(EpisodicMemory):
    def __init__(self, episodes_by_query: dict[str, list[Episode]]) -> None:
        self._episodes_by_query = episodes_by_query
        self._session_key = "test-session"

    async def query_memory(
        self,
        query: str,
        *,
        limit: int | None = None,
        expand_context: int = 0,
        score_threshold: float = -float("inf"),
        property_filter: Any | None = None,
        mode: EpisodicMemory.QueryMode = EpisodicMemory.QueryMode.BOTH,
    ) -> EpisodicMemory.QueryResponse | None:
        _ = expand_context, score_threshold, property_filter, mode
        episodes = self._episodes_by_query.get(query, [])
        search_limit = limit if limit is not None else len(episodes)
        return EpisodicMemory.QueryResponse(
            long_term_memory=EpisodicMemory.QueryResponse.LongTermMemoryResponse(
                episodes=[
                    EpisodeResponse(score=1.0, **episode.model_dump())
                    for episode in episodes[:search_limit]
                ]
            ),
            short_term_memory=EpisodicMemory.QueryResponse.ShortTermMemoryResponse(
                episodes=[],
                episode_summary=[],
            ),
        )


@pytest.fixture
def query_policy() -> QueryPolicy:
    return QueryPolicy(
        token_cost=0,
        time_cost=0,
        accuracy_score=0.0,
        confidence_score=0.0,
    )


def _build_skill(model: LanguageModel) -> RetrieveSkill:
    reranker = DummyReranker()
    memory_tool = MemMachineSkill(
        SkillToolBaseParam(
            model=None,
            children_tools=[],
            extra_params={},
            reranker=reranker,
        )
    )
    return RetrieveSkill(
        SkillToolBaseParam(
            model=model,
            children_tools=[memory_tool],
            extra_params={
                "fallback_tool_name": "MemMachineSkill",
                "skill_session_model": ScriptedSkillSessionModel(model),
            },
            reranker=reranker,
        )
    )


def _build_episode(uid: str) -> Episode:
    return Episode(
        uid=uid,
        content="hello",
        session_key="test-session",
        created_at=datetime.now(tz=UTC),
        producer_id="unit-test",
        producer_role="assistant",
    )


@pytest.mark.asyncio
async def test_tool_select_sub_skill_summary_sets_route_metrics(
    query_policy: QueryPolicy,
) -> None:
    episode = _build_episode("route-1")
    memory = FakeEpisodicMemory({"hello": [episode]})
    model = ScriptedLanguageModel(
        outputs=[
            (
                "top-level",
                [
                    {
                        "function": {
                            "name": "spawn_sub_skill",
                            "arguments": {
                                "skill_name": "tool_select",
                                "query": "hello",
                                "rationale": "classify route",
                            },
                        }
                    },
                    {
                        "function": {
                            "name": "direct_memory_search",
                            "arguments": {"query": "hello"},
                        }
                    },
                    {
                        "function": {
                            "name": "return_final",
                            "arguments": {"final_response": "ok"},
                        }
                    },
                ],
            ),
            (
                "selector",
                [
                    {
                        "function": {
                            "name": "return_sub_skill_result",
                            "arguments": {
                                "summary": (
                                    '{"selected_route":"direct_memory",'
                                    '"confidence_score":0.83,'
                                    '"reason_code":"single_hop"}'
                                )
                            },
                        }
                    }
                ],
            ),
        ]
    )

    skill = _build_skill(model)
    episodes, metrics = await skill.do_query(
        query_policy,
        QueryParam(query="hello", limit=5, memory=memory),
    )

    assert [item.uid for item in episodes] == ["route-1"]
    assert metrics["selected_route"] == "direct_memory"
    assert metrics["selected_skill"] == "direct_memory"
    assert metrics["confidence_score"] == 0.83
    assert metrics["reason_code"] == "single_hop"
    assert metrics["orchestrator_sub_skill_count"] == 1
    assert metrics["top_level_session_invocation_count"] == 1
    trace = metrics["orchestrator_trace"]
    assert isinstance(trace, dict)
    spawn_call = trace["tool_calls"][0]
    assert spawn_call["tool_name"] == "spawn_sub_skill"
    assert spawn_call["arguments"]["summary"] == (
        '{"selected_route":"direct_memory","confidence_score":0.83,'
        '"reason_code":"single_hop"}'
    )
    selector_decision = spawn_call["arguments"]["selector_decision"]
    assert selector_decision["selected_route"] == "direct_memory"
    assert selector_decision["selected_skill"] == "direct_memory"


@pytest.mark.asyncio
async def test_invalid_tool_select_summary_is_ignored(
    query_policy: QueryPolicy,
) -> None:
    episode = _build_episode("route-2")
    memory = FakeEpisodicMemory({"hello": [episode]})
    model = ScriptedLanguageModel(
        outputs=[
            (
                "top-level",
                [
                    {
                        "function": {
                            "name": "spawn_sub_skill",
                            "arguments": {
                                "skill_name": "tool_select",
                                "query": "hello",
                            },
                        }
                    },
                    {
                        "function": {
                            "name": "direct_memory_search",
                            "arguments": {"query": "hello"},
                        }
                    },
                    {
                        "function": {
                            "name": "return_final",
                            "arguments": {"final_response": "ok"},
                        }
                    },
                ],
            ),
            (
                "selector",
                [
                    {
                        "function": {
                            "name": "return_sub_skill_result",
                            "arguments": {"summary": "not-json"},
                        }
                    }
                ],
            ),
        ]
    )

    skill = _build_skill(model)
    _episodes, metrics = await skill.do_query(
        query_policy,
        QueryParam(query="hello", limit=5, memory=memory),
    )

    assert "selected_route" not in metrics
    trace = metrics["orchestrator_trace"]
    assert isinstance(trace, dict)
    assert any(
        event.get("event_type") == "tool_select_invalid_summary"
        for event in trace.get("events", [])
    )


@pytest.mark.asyncio
async def test_tool_select_invalid_summary_retries_once_then_fallback(
    query_policy: QueryPolicy,
) -> None:
    fallback_episode = _build_episode("route-fallback")
    memory = FakeEpisodicMemory({"hello": [fallback_episode]})
    model = ScriptedLanguageModel(
        outputs=[
            (
                "top-level",
                [
                    {
                        "function": {
                            "name": "spawn_sub_skill",
                            "arguments": {
                                "skill_name": "tool_select",
                                "query": "hello",
                            },
                        }
                    },
                    {
                        "function": {
                            "name": "return_final",
                            "arguments": {"final_response": "ok"},
                        }
                    },
                ],
            ),
            (
                "selector-1",
                [
                    {
                        "function": {
                            "name": "return_sub_skill_result",
                            "arguments": {"summary": "not-json"},
                        }
                    }
                ],
            ),
            (
                "selector-2",
                [
                    {
                        "function": {
                            "name": "return_sub_skill_result",
                            "arguments": {"summary": "still-not-json"},
                        }
                    }
                ],
            ),
        ]
    )

    skill = _build_skill(model)
    episodes, metrics = await skill.do_query(
        query_policy,
        QueryParam(query="hello", limit=5, memory=memory),
    )

    assert [item.uid for item in episodes] == ["route-fallback"]
    assert metrics["fallback_trigger_reason"] == "selector_unclassifiable"
    malformed = metrics["selector_malformed_results"]
    assert isinstance(malformed, list)
    assert len(malformed) == 2
    assert malformed[0]["summary"] == "not-json"
    assert malformed[1]["summary"] == "still-not-json"
    trace = metrics["orchestrator_trace"]
    assert isinstance(trace, dict)
    assert any(
        event.get("event_type") == "tool_select_retry"
        for event in trace.get("events", [])
    )
    fallback_call = trace["tool_calls"][-1]
    assert fallback_call["tool_name"] == "direct_memory_search"
    assert fallback_call["arguments"]["selector_malformed_results"] == malformed


@pytest.mark.asyncio
async def test_tool_select_low_confidence_forces_direct_memory_fallback(
    query_policy: QueryPolicy,
) -> None:
    fallback_episode = _build_episode("route-low-confidence")
    memory = FakeEpisodicMemory({"hello": [fallback_episode]})
    model = ScriptedLanguageModel(
        outputs=[
            (
                "top-level",
                [
                    {
                        "function": {
                            "name": "spawn_sub_skill",
                            "arguments": {
                                "skill_name": "tool_select",
                                "query": "hello",
                            },
                        }
                    },
                    {
                        "function": {
                            "name": "return_final",
                            "arguments": {"final_response": "ok"},
                        }
                    },
                ],
            ),
            (
                "selector",
                [
                    {
                        "function": {
                            "name": "return_sub_skill_result",
                            "arguments": {
                                "summary": (
                                    '{"selected_skill":"coq",'
                                    '"confidence_score":0.15,'
                                    '"reason_code":"low_conf"}'
                                )
                            },
                        }
                    }
                ],
            ),
        ]
    )

    skill = _build_skill(model)
    episodes, metrics = await skill.do_query(
        query_policy,
        QueryParam(query="hello", limit=5, memory=memory),
    )

    assert [item.uid for item in episodes] == ["route-low-confidence"]
    assert metrics["fallback_trigger_reason"] == "low_confidence_route"
