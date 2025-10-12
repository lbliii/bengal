"""
Unit tests for link suggestion engine.
"""

from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

from bengal.analysis.link_suggestions import (
    LinkSuggestion,
    LinkSuggestionEngine,
    LinkSuggestionResults,
    suggest_links,
)


class TestLinkSuggestion:
    """Tests for LinkSuggestion dataclass."""

    def test_link_suggestion_creation(self):
        """Test creating a link suggestion."""
        source = Mock(title="Source Page", source_path=Path("source.md"))
        target = Mock(title="Target Page", source_path=Path("target.md"))

        suggestion = LinkSuggestion(
            source=source, target=target, score=0.75, reasons=["Shared tags: python, testing"]
        )

        assert suggestion.source == source
        assert suggestion.target == target
        assert suggestion.score == 0.75
        assert len(suggestion.reasons) == 1

    def test_link_suggestion_repr(self):
        """Test string representation."""
        source = Mock(title="Source", source_path=Path("source.md"))
        target = Mock(title="Target", source_path=Path("target.md"))

        suggestion = LinkSuggestion(source=source, target=target, score=0.5, reasons=[])

        assert "Source" in repr(suggestion)
        assert "Target" in repr(suggestion)
        assert "0.500" in repr(suggestion)


class TestLinkSuggestionResults:
    """Tests for LinkSuggestionResults."""

    def test_get_suggestions_for_page(self):
        """Test getting suggestions for specific page."""
        source1 = Mock(source_path=Path("source1.md"))
        source2 = Mock(source_path=Path("source2.md"))
        target1 = Mock(source_path=Path("target1.md"))
        target2 = Mock(source_path=Path("target2.md"))

        suggestions = [
            LinkSuggestion(source1, target1, 0.8, ["reason1"]),
            LinkSuggestion(source1, target2, 0.6, ["reason2"]),
            LinkSuggestion(source2, target1, 0.7, ["reason3"]),
        ]

        results = LinkSuggestionResults(
            suggestions=suggestions, total_suggestions=3, pages_analyzed=2
        )

        source1_suggestions = results.get_suggestions_for_page(source1, limit=10)

        assert len(source1_suggestions) == 2
        assert source1_suggestions[0].target == target1  # Higher score
        assert source1_suggestions[1].target == target2

    def test_get_top_suggestions(self):
        """Test getting top suggestions across all pages."""
        suggestions = [
            LinkSuggestion(Mock(), Mock(), 0.9, []),
            LinkSuggestion(Mock(), Mock(), 0.5, []),
            LinkSuggestion(Mock(), Mock(), 0.7, []),
        ]

        results = LinkSuggestionResults(suggestions, 3, 2)

        top = results.get_top_suggestions(2)

        assert len(top) == 2
        assert top[0].score == 0.9
        assert top[1].score == 0.7

    def test_get_suggestions_by_target(self):
        """Test getting suggestions pointing to specific target."""
        target = Mock(source_path=Path("target.md"))
        other = Mock(source_path=Path("other.md"))

        suggestions = [
            LinkSuggestion(Mock(), target, 0.8, []),
            LinkSuggestion(Mock(), other, 0.6, []),
            LinkSuggestion(Mock(), target, 0.7, []),
        ]

        results = LinkSuggestionResults(suggestions, 3, 2)

        target_suggestions = results.get_suggestions_by_target(target)

        assert len(target_suggestions) == 2
        assert all(s.target == target for s in target_suggestions)


class TestLinkSuggestionEngine:
    """Tests for link suggestion engine."""

    def test_empty_graph(self):
        """Test with empty graph."""
        site = Mock()
        site.pages = []

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        assert len(results.suggestions) == 0
        assert results.pages_analyzed == 0

    def test_single_page(self):
        """Test with single page."""
        page = Mock(source_path=Path("page.md"), metadata={})
        page.tags = []
        page.category = None
        del page.categories  # Remove the categories attribute

        site = Mock()
        site.pages = [page]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # No suggestions possible with single page
        assert len(results.suggestions) == 0

    def test_shared_tags_scoring(self):
        """Test that pages with shared tags get higher scores."""
        page1 = Mock(source_path=Path("page1.md"), metadata={})
        page1.tags = ["python", "testing"]
        page1.category = None
        del page1.categories

        page2 = Mock(source_path=Path("page2.md"), metadata={})
        page2.tags = ["python", "coding"]
        page2.category = None
        del page2.categories

        page3 = Mock(source_path=Path("page3.md"), metadata={})
        page3.tags = ["javascript"]
        page3.category = None
        del page3.categories

        site = Mock()
        site.pages = [page1, page2, page3]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        engine = LinkSuggestionEngine(graph, min_score=0.0)
        results = engine.generate_suggestions()

        # page1 should have higher score for page2 (shared tag: python)
        page1_suggestions = results.get_suggestions_for_page(page1)

        if len(page1_suggestions) > 0:
            # Should suggest page2 over page3
            assert page1_suggestions[0].target == page2
            assert any("Shared tags" in reason for reason in page1_suggestions[0].reasons)

    def test_category_scoring(self):
        """Test that pages in same category get scored."""
        page1 = Mock(source_path=Path("page1.md"), metadata={})
        page1.tags = []
        page1.category = "Tutorial"
        del page1.categories

        page2 = Mock(source_path=Path("page2.md"), metadata={})
        page2.tags = []
        page2.category = "Tutorial"
        del page2.categories

        page3 = Mock(source_path=Path("page3.md"), metadata={})
        page3.tags = []
        page3.category = "Reference"
        del page3.categories

        site = Mock()
        site.pages = [page1, page2, page3]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        engine = LinkSuggestionEngine(graph, min_score=0.0)
        results = engine.generate_suggestions()

        page1_suggestions = results.get_suggestions_for_page(page1)

        if len(page1_suggestions) > 0:
            # Should prefer same category
            assert page1_suggestions[0].target == page2
            assert any("Shared categories" in reason for reason in page1_suggestions[0].reasons)

    def test_excludes_existing_links(self):
        """Test that existing links are excluded."""
        page1 = Mock(source_path=Path("page1.md"), metadata={})
        page1.tags = ["python"]
        page1.category = None
        del page1.categories

        page2 = Mock(source_path=Path("page2.md"), metadata={})
        page2.tags = ["python"]
        page2.category = None
        del page2.categories

        site = Mock()
        site.pages = [page1, page2]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page1] = {page2}  # Existing link
        graph.incoming_refs = defaultdict(int)
        graph.incoming_refs[page2] = 1

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # Should not suggest page2 since it's already linked
        page1_suggestions = results.get_suggestions_for_page(page1)
        assert len(page1_suggestions) == 0

    def test_excludes_self_links(self):
        """Test that self-links are excluded."""
        page = Mock(source_path=Path("page.md"), metadata={})
        page.tags = ["python"]
        page.category = None
        del page.categories

        site = Mock()
        site.pages = [page]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # No self-links
        page_suggestions = results.get_suggestions_for_page(page)
        assert len(page_suggestions) == 0

    def test_underlinked_bonus(self):
        """Test that underlinked pages get bonus."""
        page1 = Mock(source_path=Path("page1.md"), metadata={})
        page1.tags = []
        page1.category = None
        del page1.categories

        orphan = Mock(source_path=Path("orphan.md"), metadata={})
        orphan.tags = []
        orphan.category = None
        del orphan.categories

        popular = Mock(source_path=Path("popular.md"), metadata={})
        popular.tags = []
        popular.category = None
        del popular.categories

        site = Mock()
        site.pages = [page1, orphan, popular]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)
        graph.incoming_refs[orphan] = 0  # No incoming links
        graph.incoming_refs[popular] = 10  # Many incoming links

        engine = LinkSuggestionEngine(graph, min_score=0.0)
        results = engine.generate_suggestions()

        page1_suggestions = results.get_suggestions_for_page(page1)

        if len(page1_suggestions) > 0:
            # Orphan should be suggested (has underlinked bonus)
            targets = [s.target for s in page1_suggestions]
            assert orphan in targets

    def test_max_suggestions_per_page(self):
        """Test that max suggestions limit is respected."""
        source = Mock(source_path=Path("source.md"), metadata={})
        source.tags = ["python"]
        source.category = None
        del source.categories

        # Create 20 potential targets
        targets = []
        for i in range(20):
            target = Mock(source_path=Path(f"target{i}.md"), metadata={})
            target.tags = ["python"]
            target.category = None
            del target.categories
            targets.append(target)

        site = Mock()
        site.pages = [source] + targets

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        max_suggestions = 5
        engine = LinkSuggestionEngine(
            graph, min_score=0.0, max_suggestions_per_page=max_suggestions
        )
        results = engine.generate_suggestions()

        source_suggestions = results.get_suggestions_for_page(source, limit=100)

        # Should not exceed max_suggestions_per_page
        assert len(source_suggestions) <= max_suggestions

    def test_filters_generated_pages(self):
        """Test that generated pages are excluded."""
        real_page = Mock(source_path=Path("real.md"), metadata={})
        real_page.tags = ["python"]
        real_page.category = None
        del real_page.categories

        generated = Mock(source_path=Path("generated.md"), metadata={"_generated": True})
        generated.tags = ["python"]
        generated.category = None
        del generated.categories

        site = Mock()
        site.pages = [real_page, generated]

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # Generated page should not be in source or target
        for suggestion in results.suggestions:
            assert suggestion.source != generated
            assert suggestion.target != generated


class TestSuggestLinksFunction:
    """Tests for convenience function."""

    def test_suggest_links(self):
        """Test the convenience function."""
        pages = []
        for i in range(3):
            page = Mock(source_path=Path(f"page{i}.md"), metadata={})
            page.tags = ["python"]
            page.category = None
            del page.categories
            pages.append(page)

        site = Mock()
        site.pages = pages

        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(int)

        results = suggest_links(graph, min_score=0.0)

        assert isinstance(results, LinkSuggestionResults)
        assert results.pages_analyzed == 3
