"""
Unit tests for link suggestion engine.
"""

from collections import defaultdict
from pathlib import Path

from bengal.analysis.links.suggestions import (
    LinkSuggestion,
    LinkSuggestionEngine,
    LinkSuggestionResults,
    suggest_links,
)
from tests._testing.mocks import MockAnalysisPage


def _create_mock_graph(pages: list[MockAnalysisPage]):
    """Create a mock graph with the given pages."""
    from unittest.mock import Mock

    graph = Mock()
    graph.get_analysis_pages.return_value = pages
    graph.outgoing_refs = defaultdict(set)
    graph.incoming_refs = defaultdict(int)
    return graph


class TestLinkSuggestion:
    """Tests for LinkSuggestion dataclass."""

    def test_link_suggestion_creation(self):
        """Test creating a link suggestion."""
        source = MockAnalysisPage(source_path=Path("source.md"), title="Source Page")
        target = MockAnalysisPage(source_path=Path("target.md"), title="Target Page")

        suggestion = LinkSuggestion(
            source=source, target=target, score=0.75, reasons=["Shared tags: python, testing"]
        )

        assert suggestion.source == source
        assert suggestion.target == target
        assert suggestion.score == 0.75
        assert len(suggestion.reasons) == 1

    def test_link_suggestion_repr(self):
        """Test string representation."""
        source = MockAnalysisPage(source_path=Path("source.md"), title="Source")
        target = MockAnalysisPage(source_path=Path("target.md"), title="Target")

        suggestion = LinkSuggestion(source=source, target=target, score=0.5, reasons=[])

        assert "Source" in repr(suggestion)
        assert "Target" in repr(suggestion)
        assert "0.500" in repr(suggestion)


class TestLinkSuggestionResults:
    """Tests for LinkSuggestionResults."""

    def test_get_suggestions_for_page(self):
        """Test getting suggestions for specific page."""
        source1 = MockAnalysisPage(source_path=Path("source1.md"))
        source2 = MockAnalysisPage(source_path=Path("source2.md"))
        target1 = MockAnalysisPage(source_path=Path("target1.md"))
        target2 = MockAnalysisPage(source_path=Path("target2.md"))

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
            LinkSuggestion(
                MockAnalysisPage(source_path=Path("a.md")),
                MockAnalysisPage(source_path=Path("b.md")),
                0.9,
                [],
            ),
            LinkSuggestion(
                MockAnalysisPage(source_path=Path("c.md")),
                MockAnalysisPage(source_path=Path("d.md")),
                0.5,
                [],
            ),
            LinkSuggestion(
                MockAnalysisPage(source_path=Path("e.md")),
                MockAnalysisPage(source_path=Path("f.md")),
                0.7,
                [],
            ),
        ]

        results = LinkSuggestionResults(suggestions, 3, 2)

        top = results.get_top_suggestions(2)

        assert len(top) == 2
        assert top[0].score == 0.9
        assert top[1].score == 0.7

    def test_get_suggestions_by_target(self):
        """Test getting suggestions pointing to specific target."""
        target = MockAnalysisPage(source_path=Path("target.md"))
        other = MockAnalysisPage(source_path=Path("other.md"))

        suggestions = [
            LinkSuggestion(MockAnalysisPage(source_path=Path("a.md")), target, 0.8, []),
            LinkSuggestion(MockAnalysisPage(source_path=Path("b.md")), other, 0.6, []),
            LinkSuggestion(MockAnalysisPage(source_path=Path("c.md")), target, 0.7, []),
        ]

        results = LinkSuggestionResults(suggestions, 3, 2)

        target_suggestions = results.get_suggestions_by_target(target)

        assert len(target_suggestions) == 2
        assert all(s.target == target for s in target_suggestions)


class TestLinkSuggestionEngine:
    """Tests for link suggestion engine."""

    def test_empty_graph(self):
        """Test with empty graph."""
        graph = _create_mock_graph([])

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        assert len(results.suggestions) == 0
        assert results.pages_analyzed == 0

    def test_single_page(self):
        """Test with single page."""
        page = MockAnalysisPage(source_path=Path("page.md"))
        graph = _create_mock_graph([page])

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # No suggestions possible with single page
        assert len(results.suggestions) == 0

    def test_shared_tags_scoring(self):
        """Test that pages with shared tags get higher scores."""
        page1 = MockAnalysisPage(source_path=Path("page1.md"), tags=["python", "testing"])
        page2 = MockAnalysisPage(source_path=Path("page2.md"), tags=["python", "coding"])
        page3 = MockAnalysisPage(source_path=Path("page3.md"), tags=["javascript"])

        graph = _create_mock_graph([page1, page2, page3])

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
        page1 = MockAnalysisPage(source_path=Path("page1.md"), category="Tutorial")
        page2 = MockAnalysisPage(source_path=Path("page2.md"), category="Tutorial")
        page3 = MockAnalysisPage(source_path=Path("page3.md"), category="Reference")

        graph = _create_mock_graph([page1, page2, page3])

        engine = LinkSuggestionEngine(graph, min_score=0.0)
        results = engine.generate_suggestions()

        page1_suggestions = results.get_suggestions_for_page(page1)

        if len(page1_suggestions) > 0:
            # Should prefer same category
            assert page1_suggestions[0].target == page2
            assert any("Shared categories" in reason for reason in page1_suggestions[0].reasons)

    def test_excludes_existing_links(self):
        """Test that existing links are excluded."""
        page1 = MockAnalysisPage(source_path=Path("page1.md"), tags=["python"])
        page2 = MockAnalysisPage(source_path=Path("page2.md"), tags=["python"])

        graph = _create_mock_graph([page1, page2])
        graph.outgoing_refs[page1] = {page2}  # Existing link
        graph.incoming_refs[page2] = 1

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # Should not suggest page2 since it's already linked
        page1_suggestions = results.get_suggestions_for_page(page1)
        assert len(page1_suggestions) == 0

    def test_excludes_self_links(self):
        """Test that self-links are excluded."""
        page = MockAnalysisPage(source_path=Path("page.md"), tags=["python"])
        graph = _create_mock_graph([page])

        engine = LinkSuggestionEngine(graph)
        results = engine.generate_suggestions()

        # No self-links
        page_suggestions = results.get_suggestions_for_page(page)
        assert len(page_suggestions) == 0

    def test_underlinked_bonus(self):
        """Test that underlinked pages get bonus."""
        page1 = MockAnalysisPage(source_path=Path("page1.md"))
        orphan = MockAnalysisPage(source_path=Path("orphan.md"))
        popular = MockAnalysisPage(source_path=Path("popular.md"))

        graph = _create_mock_graph([page1, orphan, popular])
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
        source = MockAnalysisPage(source_path=Path("source.md"), tags=["python"])

        # Create 20 potential targets
        targets = [
            MockAnalysisPage(source_path=Path(f"target{i}.md"), tags=["python"]) for i in range(20)
        ]

        graph = _create_mock_graph([source, *targets])

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
        real_page = MockAnalysisPage(source_path=Path("real.md"), tags=["python"])
        generated = MockAnalysisPage(
            source_path=Path("generated.md"),
            tags=["python"],
            metadata={"_generated": True},
        )

        graph = _create_mock_graph([real_page, generated])

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
        pages = [
            MockAnalysisPage(source_path=Path(f"page{i}.md"), tags=["python"]) for i in range(3)
        ]

        graph = _create_mock_graph(pages)

        results = suggest_links(graph, min_score=0.0)

        assert isinstance(results, LinkSuggestionResults)
        assert results.pages_analyzed == 3
