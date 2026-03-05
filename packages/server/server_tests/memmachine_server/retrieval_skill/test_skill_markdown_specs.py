from __future__ import annotations

from pathlib import Path

import pytest

from memmachine_server.retrieval_skill.skills.spec_loader import load_skill_spec
from memmachine_server.retrieval_skill.skills.types import (
    SkillContractError,
    SkillContractErrorCode,
)

SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "memmachine_server"
    / "retrieval_skill"
    / "skills"
    / "specs"
)


def test_load_markdown_top_level_spec_file() -> None:
    spec_path = SPEC_ROOT / "top_level" / "retrieve_skill.md"
    spec = load_skill_spec(spec_path)

    assert spec.name == "retrieve-skill"
    assert spec.kind == "top-level"
    assert spec.allowed_actions == ["memmachine_search", "return_final"]
    assert spec.allowed_tools == ["memmachine_search", "return_final"]
    assert spec.policy_markdown is not None
    assert "## Actions" in spec.policy_markdown
    assert "MemMachine strengths" in spec.policy_markdown
    assert "MemMachine limitations" in spec.policy_markdown
    assert "legacy" not in spec.policy_markdown.lower()


def test_markdown_spec_missing_required_section_fails(tmp_path: Path) -> None:
    broken_spec = tmp_path / "broken.md"
    broken_spec.write_text(
        """---
name: retrieve-skill
version: v1
kind: top-level
description: broken
route_name: retrieve-skill
required_sections:
  - Intent
  - Rules
  - Actions
  - Completion
---

## Intent
intent text

## Rules
rules text
""",
        encoding="utf-8",
    )

    with pytest.raises(SkillContractError) as exc_info:
        load_skill_spec(broken_spec)

    assert exc_info.value.code == SkillContractErrorCode.INVALID_SPEC.value
    assert "missing required section" in exc_info.value.payload.why.lower()


def test_markdown_spec_unknown_frontmatter_field_fails(tmp_path: Path) -> None:
    bad_frontmatter = tmp_path / "bad-frontmatter.md"
    bad_frontmatter.write_text(
        """---
name: retrieve-skill
version: v1
kind: top-level
description: invalid frontmatter
route_name: retrieve-skill
unknown_field: true
required_sections:
  - Intent
---

## Intent
intent text
""",
        encoding="utf-8",
    )

    with pytest.raises(SkillContractError) as exc_info:
        load_skill_spec(bad_frontmatter)

    assert exc_info.value.code == SkillContractErrorCode.INVALID_SPEC.value
