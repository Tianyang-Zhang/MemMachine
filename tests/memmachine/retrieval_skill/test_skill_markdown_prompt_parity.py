from __future__ import annotations

from pathlib import Path

from memmachine.retrieval_skill.skills.spec_loader import load_skill_spec

SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "memmachine"
    /("retrieval_skill")
    / "skills"
    / "specs"
    / "sub_skills"
)


def _raw_text(file_name: str) -> str:
    return (SPEC_ROOT / file_name).read_text(encoding="utf-8")


def _policy_markdown(file_name: str) -> str:
    spec = load_skill_spec(SPEC_ROOT / file_name)
    assert spec.policy_markdown is not None
    return spec.policy_markdown


def _assert_section_order(policy: str) -> None:
    section_order = [
        "## Intent",
        "## Rules",
        "## Tools",
        "## Output Contract",
        "## Examples",
        "## Failure Modes",
    ]
    previous_idx = -1
    for heading in section_order:
        current_idx = policy.find(heading)
        assert current_idx >= 0, f"missing required section heading: {heading}"
        assert current_idx > previous_idx, (
            f"section order violation: {heading} appeared out of order"
        )
        previous_idx = current_idx


def _assert_contains_all(policy: str, snippets: list[str]) -> None:
    for snippet in snippets:
        assert snippet in policy, f"missing policy anchor: {snippet}"


def test_fixed_section_order_is_consistent_across_translated_sub_skills() -> None:
    for file_name in ("tool_select.md", "coq.md", "split.md"):
        policy = _policy_markdown(file_name)
        _assert_section_order(policy)


def test_translated_sub_skills_expose_examples_and_failure_modes() -> None:
    for file_name in ("tool_select.md", "coq.md", "split.md"):
        policy = _policy_markdown(file_name)
        assert policy.count("### Example") >= 3
        assert policy.count("### Example") <= 5
        assert "## Failure Modes" in policy


def test_tool_select_prompt_parity_anchors_are_preserved() -> None:
    policy = _policy_markdown("tool_select.md")
    _assert_contains_all(
        policy,
        [
            "Validate input first",
            "Classify query type using only query text",
            "Multi-hop dependency chain -> `coq`",
            "Single-hop with multiple independent entities/keywords -> `split`",
            "Single-hop direct lookup -> `direct_memory`",
            "Tie-breaker: if any explicit dependency chain exists, classify as multi-hop.",
            "Deterministic mapping",
            "If uncertain, lower confidence rather than inventing certainty.",
        ],
    )


def test_tool_select_output_contract_is_strict_v1_and_fail_closed() -> None:
    policy = _policy_markdown("tool_select.md")
    _assert_contains_all(
        policy,
        [
            "`v1` required fields",
            "`selected_skill`: enum `direct_memory | coq | split`",
            "`selected_route`: enum `direct_memory | decompose`",
            "`confidence_score`: number in `[0.0, 1.0]`",
            "Do not omit required keys.",
            "selector_unclassifiable",
        ],
    )


def test_tool_select_keeps_unclassifiable_fail_closed_path() -> None:
    policy = _policy_markdown("tool_select.md")
    _assert_contains_all(
        policy,
        [
            "If classification is impossible, still emit valid JSON",
            "`selected_skill=direct_memory`",
            "`selected_route=direct_memory`",
            "`confidence_score` near `0.0`",
            "`reason_code=selector_unclassifiable`",
        ],
    )


def test_coq_prompt_parity_anchors_are_preserved() -> None:
    policy = _policy_markdown("coq.md")
    _assert_contains_all(
        policy,
        [
            "Use only retrieved documents for sufficiency decisions.",
            "Do not invent new entities.",
            "Strict sufficiency standard",
            "If uncertain, choose `is_sufficient=false`.",
            "Next-best rewritten query objective",
            "earliest blocking hop",
            "avoid duplicates of tried rewritten queries",
            "Confidence calibration",
            "evidence_indices",
        ],
    )


def test_coq_output_contract_is_strict_v1_and_fail_closed() -> None:
    policy = _policy_markdown("coq.md")
    _assert_contains_all(
        policy,
        [
            "`v1` required fields",
            "`is_sufficient`: boolean",
            "`evidence_indices`: array of integer indices (0-based, no negatives)",
            "`new_query`: single-line string",
            "`confidence_score`: number in `[0.0, 1.0]`",
            "when sufficient, `new_query` must equal original query exactly",
        ],
    )


def test_split_prompt_parity_anchors_are_preserved() -> None:
    policy = _policy_markdown("split.md")
    _assert_contains_all(
        policy,
        [
            "Decide whether to split (default: do not split)",
            "Tie-breaker: when unsure, prefer not splitting.",
            "single-hop fact lookups only",
            "Explicit ban on derived-operation wording",
            "Pronouns/ambiguous references",
            "Duplicate guardrail",
            "if not splitting, return one line equal to original query",
            "each line must be a full question ending with `?`",
        ],
    )


def test_split_output_contract_is_strict_v1_and_fail_closed() -> None:
    policy = _policy_markdown("split.md")
    _assert_contains_all(
        policy,
        [
            "`v1` required fields",
            "`sub_queries`: array of query strings",
            "`reason_code`: short snake_case code",
            "`reason_note`: short human-readable note",
            "`sub_queries` must contain 1-6 lines total",
            "if splitting occurred, line count must be 2-6",
        ],
    )


def test_split_keeps_derived_operation_ban_keywords() -> None:
    policy = _policy_markdown("split.md").lower()
    for keyword in (
        "compare",
        "difference",
        "between",
        "rate",
        "top",
        "average",
        "change",
        "increase",
        "decrease",
        "percent",
        "rank",
        "versus",
        "more than",
        "less than",
    ):
        assert keyword in policy


def test_translated_sub_skills_do_not_reintroduce_placeholder_language() -> None:
    disallowed_snippets = [
        "translated from legacy",
        "placeholder summary",
        "summary placeholder",
        "todo: translate",
    ]
    for file_name in ("tool_select.md", "coq.md", "split.md"):
        lower_text = _raw_text(file_name).lower()
        for snippet in disallowed_snippets:
            assert snippet not in lower_text


def test_translated_sub_skills_keep_explicit_v1_contract_markers() -> None:
    for file_name in ("tool_select.md", "coq.md", "split.md"):
        policy = _policy_markdown(file_name)
        assert "`v1` required fields" in policy
        assert "Fail-closed requirements" in policy
