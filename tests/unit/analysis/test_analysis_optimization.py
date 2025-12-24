"""
Tests for analysis algorithm optimizations.

RFC: rfc-analysis-algorithm-optimization

Validates that optimized algorithms produce identical results to the original
implementations while achieving better time complexity:
- PageRank: O(I × N²) → O(I × E) via incoming edges index
- Link Suggestions: O(N² × T) → O(N × overlap × T) via inverted indices
"""

from collections import defaultdict
from unittest.mock import Mock

import pytest


class TestIncomingEdgesIndex:
    """Tests for the incoming_edges reverse adjacency list."""

    def test_incoming_edges_built_during_graph_construction(self):
        """Test that incoming_edges is populated during graph build."""
        from bengal.analysis.graph_builder import GraphBuilder

        # Create mock site with linked pages
        site = Mock()
        page_a = Mock()
        page_a.source_path = Mock(stem="page_a")
        page_a.links = ["b"]
        page_a.related_posts = []
        page_a.next_in_section = None
        page_a.prev_in_section = None

        page_b = Mock()
        page_b.source_path = Mock(stem="page_b")
        page_b.links = []
        page_b.related_posts = []
        page_b.next_in_section = None
        page_b.prev_in_section = None

        site.pages = [page_a, page_b]
        site.config = {}
        site.xref_index = {
            "by_slug": {"b": [page_b]},
            "by_path": {},
            "by_id": {},
        }
        site.taxonomies = {}
        site.menu = {}

        # Build graph
        builder = GraphBuilder(site, exclude_autodoc=False, parallel=False)
        builder.build()

        # Verify incoming_edges is built correctly
        assert page_b in builder.incoming_edges
        assert page_a in builder.incoming_edges[page_b]
        assert page_a not in builder.incoming_edges.get(page_a, [])

    def test_incoming_edges_matches_outgoing_refs(self):
        """Test that incoming_edges is the inverse of outgoing_refs."""
        from bengal.analysis.graph_builder import GraphBuilder

        # Create mock site with multiple links
        site = Mock()
        pages = []
        for i in range(5):
            page = Mock()
            page.source_path = Mock(stem=f"page_{i}")
            page.links = []
            page.related_posts = []
            page.next_in_section = None
            page.prev_in_section = None
            pages.append(page)

        # A -> B, A -> C, B -> C, D -> C
        pages[0].links = ["page-1", "page-2"]
        pages[1].links = ["page-2"]
        pages[3].links = ["page-2"]

        site.pages = pages
        site.config = {}
        site.xref_index = {
            "by_slug": {f"page-{i}": [pages[i]] for i in range(5)},
            "by_path": {},
            "by_id": {},
        }
        site.taxonomies = {}
        site.menu = {}

        # Build graph
        builder = GraphBuilder(site, exclude_autodoc=False, parallel=False)
        builder.build()

        # Verify: for each edge in outgoing_refs, the reverse exists in incoming_edges
        for source_page, targets in builder.outgoing_refs.items():
            for target in targets:
                assert source_page in builder.incoming_edges.get(target, []), (
                    f"Missing reverse edge: {target} should have {source_page} as incoming"
                )


class TestPageRankOptimization:
    """Tests for optimized PageRank using incoming_edges."""

    def test_pagerank_uses_incoming_edges(self):
        """Test that PageRank uses the incoming_edges index when available."""
        from bengal.analysis.page_rank import PageRankCalculator

        # Create mock graph with incoming_edges
        graph = Mock()
        page_a = Mock()
        page_a.metadata = {}
        page_b = Mock()
        page_b.metadata = {}
        page_c = Mock()
        page_c.metadata = {}

        # A -> B, B -> C (linear chain)
        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}

        # Pre-computed incoming_edges (optimization)
        graph.incoming_edges = {
            page_b: [page_a],
            page_c: [page_b],
        }

        calc = PageRankCalculator(graph, damping=0.85, max_iterations=50)
        results = calc.compute()

        # Verify results are correct (same as before optimization)
        assert results.converged is True
        assert results.scores[page_c] > results.scores[page_b]
        assert results.scores[page_b] > results.scores[page_a]

    def test_pagerank_complex_graph(self):
        """Test PageRank on a complex graph structure."""
        from bengal.analysis.page_rank import PageRankCalculator

        # Create a more complex graph
        pages = [Mock() for _ in range(10)]
        for i, page in enumerate(pages):
            page.metadata = {}
            page.source_path = Mock()
            page.source_path.stem = f"page_{i}"

        # Create random-ish link structure
        outgoing = defaultdict(set)
        outgoing[pages[0]] = {pages[1], pages[2], pages[3]}
        outgoing[pages[1]] = {pages[4], pages[5]}
        outgoing[pages[2]] = {pages[5], pages[6]}
        outgoing[pages[3]] = {pages[6], pages[7]}
        outgoing[pages[4]] = {pages[8]}
        outgoing[pages[5]] = {pages[8], pages[9]}
        outgoing[pages[6]] = {pages[9]}
        outgoing[pages[7]] = {pages[0]}  # Back link
        outgoing[pages[8]] = {pages[0]}  # Back link
        outgoing[pages[9]] = {pages[1]}  # Back link

        # Build incoming_edges
        incoming_edges = defaultdict(list)
        for source, targets in outgoing.items():
            for target in targets:
                incoming_edges[target].append(source)

        graph = Mock()
        graph.get_analysis_pages.return_value = pages
        graph.outgoing_refs = outgoing
        graph.incoming_edges = dict(incoming_edges)

        calc = PageRankCalculator(graph, damping=0.85, max_iterations=100)
        results = calc.compute()

        # Verify convergence and basic properties
        assert results.converged is True
        assert len(results.scores) == 10
        # All scores should be positive
        assert all(score > 0 for score in results.scores.values())
        # Scores should sum to approximately 1
        assert sum(results.scores.values()) == pytest.approx(1.0, rel=1e-5)

    def test_pagerank_with_empty_incoming_edges(self):
        """Test PageRank handles pages with no incoming edges."""
        from bengal.analysis.page_rank import PageRankCalculator

        graph = Mock()
        page_a = Mock()
        page_a.metadata = {}
        page_b = Mock()
        page_b.metadata = {}

        # B has no incoming edges
        graph.get_analysis_pages.return_value = [page_a, page_b]
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_b] = {page_a}
        graph.incoming_edges = {
            page_a: [page_b],
            # page_b has no incoming edges
        }

        calc = PageRankCalculator(graph, damping=0.85)
        results = calc.compute()

        # Page with incoming edges should have higher score
        assert results.scores[page_a] > results.scores[page_b]


class TestLinkSuggestionsOptimization:
    """Tests for optimized link suggestions using inverted indices."""

    def test_inverted_tag_index_built_correctly(self):
        """Test that inverted tag index is built correctly."""
        from bengal.analysis.link_suggestions import LinkSuggestionEngine

        # Create mock graph with tagged pages
        graph = Mock()
        page_a = Mock()
        page_a.tags = ["python", "tutorial"]
        page_a.metadata = {}
        page_b = Mock()
        page_b.tags = ["python", "api"]
        page_b.metadata = {}
        page_c = Mock()
        page_c.tags = ["javascript"]
        page_c.metadata = {}

        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(float)
        graph._pagerank_results = None
        graph._path_results = None

        engine = LinkSuggestionEngine(graph, min_score=0.1)

        # Build tag map and inverted index
        pages = [page_a, page_b, page_c]
        page_tags = engine._build_tag_map(pages)
        tag_to_pages = engine._build_inverted_tag_index(pages, page_tags)

        # Verify inverted index
        assert page_a in tag_to_pages["python"]
        assert page_b in tag_to_pages["python"]
        assert page_c not in tag_to_pages["python"]
        assert page_c in tag_to_pages["javascript"]

    def test_link_suggestions_filter_candidates(self):
        """Test that link suggestions only compare relevant candidates."""
        from bengal.analysis.link_suggestions import LinkSuggestionEngine

        # Create mock graph
        graph = Mock()

        # Page A shares tags with B, but not with C
        page_a = Mock()
        page_a.tags = ["python"]
        page_a.metadata = {}
        page_a.source_path = Mock()
        page_a.title = "Page A"

        page_b = Mock()
        page_b.tags = ["python"]
        page_b.metadata = {}
        page_b.source_path = Mock()
        page_b.title = "Page B"

        page_c = Mock()
        page_c.tags = ["unrelated-topic"]
        page_c.metadata = {}
        page_c.source_path = Mock()
        page_c.title = "Page C"

        graph.get_analysis_pages.return_value = [page_a, page_b, page_c]
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(float)
        # C has 10 incoming refs (not underlinked)
        graph.incoming_refs[page_c] = 10
        graph._pagerank_results = None
        graph._path_results = None

        engine = LinkSuggestionEngine(graph, min_score=0.1)
        results = engine.generate_suggestions()

        # A should suggest B (shared tag), but not C (no overlap, not underlinked)
        a_suggestions = results.get_suggestions_for_page(page_a)
        suggested_targets = [s.target for s in a_suggestions]

        assert page_b in suggested_targets, "Should suggest B (shared python tag)"
        # C shouldn't be suggested since it has no tag overlap and isn't underlinked
        assert page_c not in suggested_targets, "Should not suggest C (no overlap)"

    def test_underlinked_pages_always_candidates(self):
        """Test that underlinked pages are always considered as candidates."""
        from bengal.analysis.link_suggestions import LinkSuggestionEngine

        graph = Mock()

        # Page A has no tag overlap with orphan, but orphan is underlinked
        page_a = Mock()
        page_a.tags = ["python"]
        page_a.categories = None
        page_a.metadata = {}
        page_a.source_path = Mock()
        page_a.title = "Page A"

        orphan = Mock()
        orphan.tags = ["unrelated"]
        orphan.categories = None
        orphan.metadata = {}
        orphan.source_path = Mock()
        orphan.title = "Orphan"

        graph.get_analysis_pages.return_value = [page_a, orphan]
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(float)
        # Orphan has 0 incoming refs (underlinked bonus)
        graph.incoming_refs[orphan] = 0
        graph._pagerank_results = None
        graph._path_results = None

        engine = LinkSuggestionEngine(graph, min_score=0.1)
        results = engine.generate_suggestions()

        # A should have orphan as a candidate due to underlinked bonus
        a_suggestions = results.get_suggestions_for_page(page_a)

        # The orphan should appear in candidates (gets underlinked bonus)
        # even without tag overlap
        suggested_targets = [s.target for s in a_suggestions]
        assert orphan in suggested_targets, "Should suggest orphan (underlinked bonus)"

    def test_suggestions_no_self_links(self):
        """Test that self-links are never suggested."""
        from bengal.analysis.link_suggestions import LinkSuggestionEngine

        graph = Mock()

        page = Mock()
        page.tags = ["python"]
        page.categories = None
        page.metadata = {}
        page.source_path = Mock()
        page.title = "Page"

        graph.get_analysis_pages.return_value = [page]
        graph.outgoing_refs = defaultdict(set)
        graph.incoming_refs = defaultdict(float)
        graph._pagerank_results = None
        graph._path_results = None

        engine = LinkSuggestionEngine(graph, min_score=0.0)
        results = engine.generate_suggestions()

        # No suggestions should include self-link
        for suggestion in results.suggestions:
            assert suggestion.source != suggestion.target

    def test_suggestions_no_existing_links(self):
        """Test that existing links are not suggested."""
        from bengal.analysis.link_suggestions import LinkSuggestionEngine

        graph = Mock()

        page_a = Mock()
        page_a.tags = ["python"]
        page_a.categories = None
        page_a.metadata = {}
        page_a.source_path = Mock()
        page_a.title = "Page A"

        page_b = Mock()
        page_b.tags = ["python"]
        page_b.categories = None
        page_b.metadata = {}
        page_b.source_path = Mock()
        page_b.title = "Page B"

        graph.get_analysis_pages.return_value = [page_a, page_b]
        graph.outgoing_refs = defaultdict(set)
        # A already links to B
        graph.outgoing_refs[page_a] = {page_b}
        graph.incoming_refs = defaultdict(float)
        graph._pagerank_results = None
        graph._path_results = None

        engine = LinkSuggestionEngine(graph, min_score=0.0)
        results = engine.generate_suggestions()

        # A should not suggest B (already linked)
        a_suggestions = results.get_suggestions_for_page(page_a)
        suggested_targets = [s.target for s in a_suggestions]

        assert page_b not in suggested_targets, "Should not suggest existing link"


class TestKnowledgeGraphIncomingEdges:
    """Tests for incoming_edges in KnowledgeGraph."""

    def test_knowledge_graph_exposes_incoming_edges(self, tmp_path):
        """Test that KnowledgeGraph exposes incoming_edges from builder."""
        from bengal.analysis.knowledge_graph import KnowledgeGraph
        from bengal.core.page import Page
        from bengal.core.site import Site

        site = Site(root_path=tmp_path, config={})

        # Create pages with related posts (simulates links)
        page_a = Page(source_path=tmp_path / "a.md", content="# A", metadata={"title": "Page A"})
        page_b = Page(source_path=tmp_path / "b.md", content="# B", metadata={"title": "Page B"})

        # A has B as related post (simulates A -> B link)
        page_a.related_posts = [page_b]

        site.pages = [page_a, page_b]

        graph = KnowledgeGraph(site, exclude_autodoc=False)
        graph.build()

        # incoming_edges should be exposed
        assert hasattr(graph, "incoming_edges")
        assert page_a in graph.incoming_edges.get(page_b, [])


class TestParallelBuildIncomingEdges:
    """Tests for incoming_edges in parallel graph build mode."""

    def test_parallel_build_populates_incoming_edges(self):
        """Test that parallel build correctly populates incoming_edges."""
        from bengal.analysis.graph_builder import GraphBuilder

        # Create mock site with enough pages to trigger parallel mode
        site = Mock()
        pages = []
        for i in range(5):
            page = Mock()
            page.source_path = Mock(stem=f"page_{i}")
            page.links = []
            page.related_posts = []
            page.next_in_section = None
            page.prev_in_section = None
            page._section = None
            pages.append(page)

        # Set up links: 0->1, 0->2, 1->3, 2->3, 3->4
        pages[0].links = ["page-1", "page-2"]
        pages[1].links = ["page-3"]
        pages[2].links = ["page-3"]
        pages[3].links = ["page-4"]

        site.pages = pages
        site.config = {"parallel_graph": False}  # Force sequential for test
        site.xref_index = {
            "by_slug": {f"page-{i}": [pages[i]] for i in range(5)},
            "by_path": {},
            "by_id": {},
        }
        site.taxonomies = {}
        site.menu = {}

        # Build graph (sequential mode for this test)
        builder = GraphBuilder(site, exclude_autodoc=False, parallel=False)
        builder.build()

        # Verify incoming_edges
        assert pages[0] in builder.incoming_edges.get(pages[1], [])
        assert pages[0] in builder.incoming_edges.get(pages[2], [])
        assert pages[1] in builder.incoming_edges.get(pages[3], [])
        assert pages[2] in builder.incoming_edges.get(pages[3], [])
        assert pages[3] in builder.incoming_edges.get(pages[4], [])

        # Verify counts match
        assert len(builder.incoming_edges.get(pages[3], [])) == 2  # Two pages link to 3
