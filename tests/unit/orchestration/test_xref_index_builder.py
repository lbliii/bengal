"""
Tests for ContentOrchestrator._build_xref_index collision resolution.

The two anchor-collision rules are deliberately *opposite*:

- Heading anchors (``_index_headings``): on a same-version collision, KEEP the
  existing entry (a later target directive may still override it).
- Target directives (``_index_target_directives``): on a same-version
  collision, the directive takes precedence -- existing same-version entries
  are EVICTED before the directive entry is appended.

Both rules emit a single ``anchor_collision`` warning event. These tests drive a
real ``_build_xref_index`` run (not the resolver) so the builder's collision
logic is exercised end-to-end. Regression coverage for #380.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bengal.orchestration.content import ContentOrchestrator


def _page(*, source_path, slug=None, version=None, toc_items=None, raw_content=""):
    """Build a minimal page-like object for the xref index builder."""
    return SimpleNamespace(
        source_path=Path(source_path),
        slug=slug,
        version=version,
        metadata={},
        toc_items=toc_items or [],
        # Both attributes are consulted by the target-directive branch:
        # hasattr(page, "content") gate + get_raw_source() reading _raw_content.
        content="",
        _raw_content=raw_content,
    )


def _make_orchestrator(pages, root="/site"):
    site = MagicMock()
    site.root_path = Path(root)
    site.pages = pages
    site.xref_index = {}
    return ContentOrchestrator(site)


class TestHeadingCollisionKeepsExisting:
    """Same-version heading collision keeps the FIRST entry."""

    def test_same_version_heading_collision_keeps_first(self):
        first = _page(
            source_path="/site/content/a.md",
            toc_items=[{"title": "Install", "id": "install"}],
        )
        second = _page(
            source_path="/site/content/b.md",
            toc_items=[{"title": "Install", "id": "install"}],
        )
        orch = _make_orchestrator([first, second])

        orch._build_xref_index()

        entries = orch.site.xref_index["by_anchor"]["install"]
        # Only the first page's entry survives; the collision is dropped.
        assert len(entries) == 1
        kept_page, kept_anchor, kept_version = entries[0]
        assert kept_page is first
        assert kept_anchor == "install"
        assert kept_version is None

    def test_different_versions_coexist(self):
        v1 = _page(
            source_path="/site/content/v1/a.md",
            version="v1",
            toc_items=[{"title": "Install", "id": "install"}],
        )
        v2 = _page(
            source_path="/site/content/v2/a.md",
            version="v2",
            toc_items=[{"title": "Install", "id": "install"}],
        )
        orch = _make_orchestrator([v1, v2])

        orch._build_xref_index()

        entries = orch.site.xref_index["by_anchor"]["install"]
        # Distinct versions are not a collision; both are indexed.
        assert {v for _, _, v in entries} == {"v1", "v2"}


class TestTargetDirectiveEvictsExisting:
    """Same-version target directive evicts the heading entry and wins."""

    def test_target_directive_evicts_heading_same_version(self):
        # Page A contributes a heading anchor 'overview'.
        heading_page = _page(
            source_path="/site/content/a.md",
            toc_items=[{"title": "Overview", "id": "overview"}],
        )
        # Page B contributes a target directive with the same anchor id.
        directive_page = _page(
            source_path="/site/content/b.md",
            raw_content=":::{target} overview\n",
        )
        orch = _make_orchestrator([heading_page, directive_page])

        orch._build_xref_index()

        entries = orch.site.xref_index["by_anchor"]["overview"]
        # Heading entry evicted; only the directive entry remains.
        assert len(entries) == 1
        win_page, win_anchor, _ = entries[0]
        assert win_page is directive_page
        assert win_anchor == "overview"


class TestAnchorCollisionWarning:
    """Both rules emit an ``anchor_collision`` warning with distinct prose."""

    def test_heading_collision_emits_warning(self):
        first = _page(
            source_path="/site/content/a.md",
            toc_items=[{"title": "Install", "id": "install"}],
        )
        second = _page(
            source_path="/site/content/b.md",
            toc_items=[{"title": "Install", "id": "install"}],
        )
        orch = _make_orchestrator([first, second])

        with patch("bengal.orchestration.content.logger") as mock_logger:
            orch._build_xref_index()

        collision_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "anchor_collision"
        ]
        assert collision_calls
        # Heading rule's prose mentions directives may take precedence later.
        details = collision_calls[-1].kwargs["details"]
        assert "Target directives will take precedence if added later" in details

    def test_target_directive_collision_emits_warning(self):
        heading_page = _page(
            source_path="/site/content/a.md",
            toc_items=[{"title": "Overview", "id": "overview"}],
        )
        directive_page = _page(
            source_path="/site/content/b.md",
            raw_content=":::{target} overview\n",
        )
        orch = _make_orchestrator([heading_page, directive_page])

        with patch("bengal.orchestration.content.logger") as mock_logger:
            orch._build_xref_index()

        collision_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "anchor_collision"
        ]
        assert collision_calls
        # Target-directive rule's prose is distinct from the heading prose.
        details = collision_calls[-1].kwargs["details"]
        assert "Target directive takes precedence" in details
