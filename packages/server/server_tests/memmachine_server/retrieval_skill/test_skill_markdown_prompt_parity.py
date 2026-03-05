from __future__ import annotations

from pathlib import Path

from memmachine_server.retrieval_skill.skills.spec_loader import load_skill_spec

SPEC_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "memmachine_server"
    / "retrieval_skill"
    / "skills"
    / "specs"
    / "top_level"
    / "retrieve_skill.md"
)


def _policy_markdown() -> str:
    spec = load_skill_spec(SPEC_PATH)
    assert spec.policy_markdown is not None
    return spec.policy_markdown


def _assert_contains_all(policy: str, snippets: list[str]) -> None:
    for snippet in snippets:
        assert snippet in policy, f"missing policy anchor: {snippet}"


def test_prompt_keeps_required_sections_in_order() -> None:
    policy = _policy_markdown()
    section_order = [
        "## Intent",
        "## Rules",
        "## Actions",
        "## Completion",
    ]
    previous_idx = -1
    for heading in section_order:
        current_idx = policy.find(heading)
        assert current_idx >= 0, f"missing required section heading: {heading}"
        assert current_idx > previous_idx, (
            f"section order violation: {heading} appeared out of order"
        )
        previous_idx = current_idx


def test_prompt_includes_mm_strengths_and_limits_guidance() -> None:
    policy = _policy_markdown()
    _assert_contains_all(
        policy,
        [
            "MemMachine strengths",
            "MemMachine limitations",
            "Single-hop factual lookups",
            "One-shot multi-hop relation chains",
            "Query-construction policy",
            "entity + target attribute + timeframe",
        ],
    )


def test_prompt_requires_memmachine_search_and_return_final_only() -> None:
    spec = load_skill_spec(SPEC_PATH)
    assert spec.allowed_actions == ["memmachine_search", "return_final"]
    assert spec.allowed_tools == ["memmachine_search", "return_final"]


def test_prompt_has_no_legacy_wording() -> None:
    policy = _policy_markdown().lower()
    assert "legacy" not in policy
    assert "spawn_sub_skill" not in policy
    assert "direct_memory_search" not in policy
