from __future__ import annotations

from memmachine.retrieval_skill.skills.route_policy import (
    ROUTE_DECOMPOSE,
    ROUTE_DIRECT_MEMORY,
    choose_route_decision,
    parse_route_decision_output,
)


def test_parse_route_decision_output_from_json() -> None:
    decision = parse_route_decision_output(
        '{"selected_skill":"direct_memory","confidence_score":0.72,"reason_code":"simple_query","reason_note":"single hop"}'
    )

    assert decision is not None
    assert decision.selected_route == ROUTE_DIRECT_MEMORY
    assert decision.selected_skill == "direct_memory"
    assert decision.confidence_score == 0.72
    assert decision.reason_code == "simple_query"


def test_parse_route_decision_output_rejects_non_json_payload() -> None:
    decision = parse_route_decision_output("MemMachineSkill")
    assert decision is None


def test_choose_route_decision_uses_higher_confidence_on_conflict() -> None:
    first = parse_route_decision_output(
        '{"selected_route":"direct_memory","confidence_score":0.41,"reason_code":"first"}'
    )
    second = parse_route_decision_output(
        '{"selected_route":"decompose","confidence_score":0.88,"reason_code":"second"}'
    )

    assert first is not None
    assert second is not None

    selected = choose_route_decision(first_attempt=first, second_attempt=second)

    assert selected.selected_route == ROUTE_DECOMPOSE
    assert selected.confidence_score == 0.88


def test_choose_route_decision_returns_unclassifiable_default_when_both_invalid() -> None:
    selected = choose_route_decision(first_attempt=None, second_attempt=None)

    assert selected.selected_route == ROUTE_DIRECT_MEMORY
    assert selected.confidence_score == 0.0
    assert selected.reason_code == "selector_unclassifiable"
    assert selected.fallback_trigger_reason == "selector_unclassifiable"
