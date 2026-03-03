"""Route decision contracts and selector reconciliation for retrieve-skill."""

from __future__ import annotations

import json
from typing import cast

from memmachine_server.retrieval_skill.skills.types import RouteDecisionV1

ROUTE_DIRECT_MEMORY = "direct_memory"
ROUTE_DECOMPOSE = "decompose"
SKILL_DIRECT_MEMORY = "direct_memory"
SKILL_COQ = "coq"
SKILL_SPLIT = "split"

ROUTE_SELECTION_PROMPT = """You are select-skill for retrieval orchestration.
Return ONLY a JSON object with keys:
- selected_route: one of [\"direct_memory\", \"decompose\"]
- selected_skill: one of [\"direct_memory\", \"coq\", \"split\"]
- confidence_score: float 0.0 to 1.0
- reason_code: short stable code (snake_case)
- reason_note: short human-readable note

Guidance:
- Use decompose when the query appears multi-hop or branch-heavy.
- Use direct_memory for straightforward direct retrieval.
- If uncertain, lower confidence rather than hallucinating certainty.

Query:
{query}
"""


def _legacy_route_from_text(text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized == ROUTE_DIRECT_MEMORY:
        return ROUTE_DIRECT_MEMORY
    if normalized == ROUTE_DECOMPOSE:
        return ROUTE_DECOMPOSE
    return None


def _skill_from_label(text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized == SKILL_DIRECT_MEMORY:
        return SKILL_DIRECT_MEMORY
    if normalized == SKILL_SPLIT:
        return SKILL_SPLIT
    if normalized == SKILL_COQ:
        return SKILL_COQ
    if normalized == "memmachineskill":
        return SKILL_DIRECT_MEMORY
    if normalized == "splitskill":
        return SKILL_SPLIT
    if normalized == "chainofqueryskill":
        return SKILL_COQ
    return None


def parse_route_decision_output_detailed(  # noqa: C901
    output_text: str,
) -> tuple[RouteDecisionV1 | None, str | None]:
    """Parse selector output into RouteDecisionV1 and return parse diagnostics."""
    stripped = output_text.strip()
    if not stripped:
        return None, "empty_summary"

    try:
        payload = cast(dict[str, object], json.loads(stripped))
    except json.JSONDecodeError as err:
        return None, f"json_decode_error:{err.msg}"

    if not isinstance(payload, dict):
        return None, "non_object_payload"

    route_value = payload.get("selected_route")
    skill_value = payload.get("selected_skill")

    if not isinstance(skill_value, str):
        selected_skill_name = payload.get("selected_skill_name")
        if isinstance(selected_skill_name, str):
            skill_value = _skill_from_label(selected_skill_name)

    if not isinstance(route_value, str):
        route_alias = payload.get("route")
        if isinstance(route_alias, str):
            route_value = _legacy_route_from_text(route_alias)
        elif isinstance(skill_value, str):
            route_value = (
                ROUTE_DIRECT_MEMORY
                if skill_value == SKILL_DIRECT_MEMORY
                else ROUTE_DECOMPOSE
            )

    if not isinstance(route_value, str) and not isinstance(skill_value, str):
        return None, "missing_route_and_skill"

    normalized_payload: dict[str, object] = {
        "selected_route": route_value if isinstance(route_value, str) else None,
        "selected_skill": skill_value if isinstance(skill_value, str) else None,
        "confidence_score": payload.get("confidence_score", 0.0),
        "reason_code": payload.get("reason_code", "selector_decision"),
        "reason_note": payload.get("reason_note", ""),
        "fallback_trigger_reason": payload.get("fallback_trigger_reason"),
    }

    try:
        return RouteDecisionV1.model_validate(normalized_payload), None
    except Exception as err:
        return None, f"route_decision_validation_error:{err}"


def parse_route_decision_output(output_text: str) -> RouteDecisionV1 | None:
    """Parse selector output into strict RouteDecisionV1 when possible."""
    decision, _ = parse_route_decision_output_detailed(output_text)
    return decision


def choose_route_decision(
    *,
    first_attempt: RouteDecisionV1 | None,
    second_attempt: RouteDecisionV1 | None,
) -> RouteDecisionV1:
    """Reconcile one or two selector attempts using retry/tie-break policy."""
    if first_attempt is not None and second_attempt is None:
        return first_attempt
    if first_attempt is None and second_attempt is not None:
        return second_attempt
    if first_attempt is None and second_attempt is None:
        return RouteDecisionV1(
            selected_route=ROUTE_DIRECT_MEMORY,
            confidence_score=0.0,
            reason_code="selector_unclassifiable",
            reason_note="Selector did not emit valid route decision after retry.",
            fallback_trigger_reason="selector_unclassifiable",
        )

    assert first_attempt is not None
    assert second_attempt is not None

    if first_attempt.selected_route == second_attempt.selected_route:
        return (
            second_attempt
            if second_attempt.confidence_score >= first_attempt.confidence_score
            else first_attempt
        )

    if second_attempt.confidence_score > first_attempt.confidence_score:
        return second_attempt
    return first_attempt


__all__ = [
    "ROUTE_DECOMPOSE",
    "ROUTE_DIRECT_MEMORY",
    "ROUTE_SELECTION_PROMPT",
    "choose_route_decision",
    "parse_route_decision_output",
    "parse_route_decision_output_detailed",
]
