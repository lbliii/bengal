"""Regression guards for core compatibility surface budgets."""

from __future__ import annotations

import ast
from pathlib import Path

from bengal.core.section import Section

ROOT = Path(__file__).resolve().parents[3]
SECTION_SOURCE = ROOT / "bengal" / "core" / "section" / "__init__.py"

SECTION_ERGONOMICS_SHIMS = {
    "content_pages",
    "recent_pages",
    "pages_with_tag",
    "featured_posts",
    "post_count",
    "post_count_recursive",
    "word_count",
    "total_reading_time",
    "aggregate_content",
    "apply_section_template",
    "has_nav_children",
    "icon",
}


def test_section_ergonomics_compatibility_shim_budget_does_not_grow() -> None:
    """Section may keep known shims, but new ergonomics belong outside core."""
    source = SECTION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    shim_methods: set[str] = set()
    section_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Section"
    )
    for node in section_class.body:
        if isinstance(node, ast.FunctionDef):
            method_source = ast.get_source_segment(source, node) or ""
            if "from bengal.rendering.section_ergonomics import" in method_source:
                shim_methods.add(node.name)

    assert shim_methods == SECTION_ERGONOMICS_SHIMS


def test_section_does_not_restore_sections_alias() -> None:
    """The old sections -> subsections alias should stay retired."""
    assert "sections" not in vars(Section)
