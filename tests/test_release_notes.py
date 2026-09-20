"""Prevent cumulative or mismatched GitHub release descriptions."""

import pytest

from tools.release_notes import release_notes


@pytest.mark.parametrize("version", ["0.10.0", "0.9.1", "0.9.0"])
def test_exact_section_preserves_subheadings(version):
    sections = {
        v: f"## {v} — Release\n\nChanges {v}.\n\n### Upgrade\n\nInstructions.\n"
        for v in ("0.10.0", "0.9.1", "0.9.0")
    }
    assert release_notes("\n".join(sections.values()), version) == sections[version]


@pytest.mark.parametrize(
    "text",
    [
        "## 0.10.0 — Release\n\nChanges.",
        "## 0.1 — Release\n\n## Older\n\nChanges.",
        "## 0.1 — Release\n\nChanges.\n\n## 0.1 — Duplicate\n\nChanges.",
    ],
)
def test_missing_empty_or_duplicate_fails(text):
    with pytest.raises(ValueError):
        release_notes(text, "0.1")
