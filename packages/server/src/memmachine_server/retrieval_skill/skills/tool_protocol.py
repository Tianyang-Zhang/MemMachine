"""Tool protocol contracts for markdown-driven retrieval orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from memmachine_server.retrieval_skill.skills.types import (
    SkillContractError,
    SkillContractErrorCode,
    SkillContractErrorPayload,
)

TOP_LEVEL_TOOL_NAMES = (
    "memmachine_search",
    "return_final",
)


class TopLevelToolAction(BaseModel):
    """Validated top-level tool action emitted by LLM tool calls."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["memmachine_search", "return_final"]
    query: str | None = None
    final_response: str | None = None
    rationale: str = ""
    # Optional top-level sufficiency signal fields for metrics/evaluation traces.
    is_sufficient: bool | None = None
    confidence_score: float | None = None
    reason_code: str | None = None
    reason_note: str | None = None
    related_episode_indices: list[int] | None = None
    selected_episode_indices: list[int] | None = None


def top_level_tool_schemas(allowed_tools: list[str]) -> list[dict[str, object]]:
    """Return function-call schemas for allowed top-level orchestration tools."""
    names = set(allowed_tools) if allowed_tools else set(TOP_LEVEL_TOOL_NAMES)
    schemas: list[dict[str, object]] = []
    if "memmachine_search" in names:
        schemas.append(
            {
                "type": "function",
                "name": "memmachine_search",
                "description": "Search MemMachine memory with the provided query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            }
        )
    if "return_final" in names:
        schemas.append(
            {
                "type": "function",
                "name": "return_final",
                "description": "Finalize top-level orchestration response.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "final_response": {"type": "string"},
                        "rationale": {"type": "string"},
                        "is_sufficient": {"type": "boolean"},
                        "confidence_score": {"type": "number"},
                        "reason_code": {"type": "string"},
                        "reason_note": {"type": "string"},
                        "related_episode_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "selected_episode_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            }
        )
    return schemas


def _invalid_tool_call_error(*, where: str, why: str) -> SkillContractError:
    return SkillContractError(
        code=SkillContractErrorCode.INVALID_OUTPUT,
        payload=SkillContractErrorPayload(
            what_failed="Tool call validation failed",
            why=why,
            how_to_fix="Emit only allowed function calls with valid arguments.",
            where=where,
            fallback_trigger_reason="invalid_tool_call",
        ),
    )


def parse_top_level_tool_call(
    *,
    tool_name: str,
    arguments: dict[str, object],
) -> TopLevelToolAction:
    """Validate and normalize a top-level tool call."""
    if tool_name not in TOP_LEVEL_TOOL_NAMES:
        raise _invalid_tool_call_error(
            where="skills.tool_protocol.parse_top_level_tool_call",
            why=f"Unsupported top-level tool name: {tool_name}",
        )

    payload = dict(arguments)
    payload["action"] = tool_name
    try:
        return TopLevelToolAction.model_validate(payload)
    except ValidationError as err:
        raise _invalid_tool_call_error(
            where="skills.tool_protocol.parse_top_level_tool_call",
            why=str(err),
        ) from err
