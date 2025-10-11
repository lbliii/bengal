"""
Unit tests for path analysis algorithms.
"""

from unittest.mock import Mock
from pathlib import Path
from collections import defaultdict

from bengal.analysis.path_analysis import (
    PathAnalyzer,
    PathAnalysisResults,
    analyze_paths
)


class TestPathAnalysisResults:
    """Tests for PathAnalysisResults dataclass."""
    
    def test_get_top_bridges(self):
        """Test getting top bridge pages."""
        pages = [Mock(source_path=Path(f"page{i}.md")) for i in range(5)]
        
        betweenness = {
            pages[0]: 0.5,
            pages[1]: 0.3,
            pages[2]: 0.8,
            pages[3]: 0.1,
            pages[4]: 0.6,
        }
        
        results = PathAnalysisResults(
            betweenness_centrality=betweenness,
            closeness_centrality={},
            avg_path_length=2.5,
            diameter=5
        )
        
        bridges = results.get_top_bridges(3)
        
        assert len(bridges) == 3
        assert bridges[0][0] == pages[2]  # 0.8
        assert bridges[1][0] == pages[4]  # 0.6
        assert bridges[2][0] == pages[0]  # 0.5
    
    def test_get_most_accessible(self):
        """Test getting most accessible pages."""
        pages = [Mock(source_path=Path(f"page{i}.md")) for i in range(3)]
        
        closeness = {
            pages[0]: 0.4,
            pages[1]: 0.9,
            pages[2]: 0.6,
        }
        
        results = PathAnalysisResults(
            betweenness_centrality={},
            closeness_centrality=closeness,
            avg_path_length=2.0,
            diameter=3
        )
        
        accessible = results.get_most_accessible(2)
        
        assert len(accessible) == 2
        assert accessible[0][0] == pages[1]  # 0.9
        assert accessible[1][0] == pages[2]  # 0.6
    
    def test_get_betweenness(self):
        """Test getting betweenness for specific page."""
        page1 = Mock(source_path=Path("page1.md"))
        page2 = Mock(source_path=Path("page2.md"))
        
        results = PathAnalysisResults(
            betweenness_centrality={page1: 0.5},
            closeness_centrality={},
            avg_path_length=2.0,
            diameter=3
        )
        
        assert results.get_betweenness(page1) == 0.5
        assert results.get_betweenness(page2) == 0.0  # Not in results


class TestPathAnalyzer:
    """Tests for path analysis algorithms."""
    
    def test_find_shortest_path_direct(self):
        """Test finding shortest path when direct link exists."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        
        site = Mock()
        site.pages = [page_a, page_b]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        
        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_b)
        
        assert path == [page_a, page_b]
    
    def test_find_shortest_path_indirect(self):
        """Test finding shortest path through intermediate page."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})
        
        site = Mock()
        site.pages = [page_a, page_b, page_c]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}
        
        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_c)
        
        assert path == [page_a, page_b, page_c]
    
    def test_find_shortest_path_no_path(self):
        """Test when no path exists."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        
        site = Mock()
        site.pages = [page_a, page_b]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)  # No connections
        
        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_b)
        
        assert path is None
    
    def test_find_shortest_path_same_page(self):
        """Test when source equals target."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        
        site = Mock()
        site.pages = [page_a]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        analyzer = PathAnalyzer(graph)
        path = analyzer.find_shortest_path(page_a, page_a)
        
        assert path == [page_a]
    
    def test_analyze_empty_graph(self):
        """Test analysis on empty graph."""
        site = Mock()
        site.pages = []
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()
        
        assert len(results.betweenness_centrality) == 0
        assert len(results.closeness_centrality) == 0
        assert results.avg_path_length == 0.0
        assert results.diameter == 0
    
    def test_analyze_single_page(self):
        """Test analysis with single page."""
        page = Mock(source_path=Path("page.md"), metadata={})
        
        site = Mock()
        site.pages = [page]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()
        
        # Single isolated page has zero centrality
        assert results.betweenness_centrality[page] == 0.0
        assert results.closeness_centrality[page] == 0.0
    
    def test_analyze_chain(self):
        """Test analysis on chain: A -> B -> C."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})
        
        site = Mock()
        site.pages = [page_a, page_b, page_c]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b}
        graph.outgoing_refs[page_b] = {page_c}
        
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()
        
        # B should have highest betweenness (it's on the path from A to C)
        assert results.betweenness_centrality[page_b] > results.betweenness_centrality[page_a]
        assert results.betweenness_centrality[page_b] > results.betweenness_centrality[page_c]
        
        # Network diameter should be 2 (A to C)
        assert results.diameter == 2
    
    def test_analyze_star(self):
        """Test analysis on star graph: center connected to all spokes."""
        center = Mock(source_path=Path("center.md"), metadata={})
        spokes = [Mock(source_path=Path(f"spoke{i}.md"), metadata={}) for i in range(4)]
        
        site = Mock()
        site.pages = [center] + spokes
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        # Center connects to all spokes (directed out from center)
        graph.outgoing_refs[center] = set(spokes)
        
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()
        
        # Center should have high closeness (can reach all spokes easily)
        center_closeness = results.closeness_centrality[center]
        for spoke in spokes:
            # Spokes can't reach each other, only center can reach them
            assert center_closeness > results.closeness_centrality[spoke]
    
    def test_analyze_fully_connected(self):
        """Test analysis on fully connected graph."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(4)]
        
        site = Mock()
        site.pages = pages
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        # Fully connected
        for page in pages:
            graph.outgoing_refs[page] = {p for p in pages if p != page}
        
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()
        
        # In fully connected graph, all pages should have similar centrality
        betweenness_values = list(results.betweenness_centrality.values())
        avg_betweenness = sum(betweenness_values) / len(betweenness_values)
        
        for value in betweenness_values:
            # Should be within 10% of average
            assert abs(value - avg_betweenness) / (avg_betweenness + 1e-10) < 0.1
        
        # Diameter should be 1 (all connected directly)
        assert results.diameter == 1
    
    def test_find_all_paths(self):
        """Test finding all paths between pages."""
        page_a = Mock(source_path=Path("a.md"), metadata={})
        page_b = Mock(source_path=Path("b.md"), metadata={})
        page_c = Mock(source_path=Path("c.md"), metadata={})
        
        site = Mock()
        site.pages = [page_a, page_b, page_c]
        
        # Create diamond: A -> B -> C and A -> C
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[page_a] = {page_b, page_c}
        graph.outgoing_refs[page_b] = {page_c}
        
        analyzer = PathAnalyzer(graph)
        paths = analyzer.find_all_paths(page_a, page_c, max_length=10)
        
        # Should find 2 paths: A->C and A->B->C
        assert len(paths) == 2
        assert [page_a, page_c] in paths
        assert [page_a, page_b, page_c] in paths
    
    def test_find_all_paths_max_length(self):
        """Test that max_length constraint works."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(5)]
        
        site = Mock()
        site.pages = pages
        
        # Create chain: 0 -> 1 -> 2 -> 3 -> 4
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        for i in range(4):
            graph.outgoing_refs[pages[i]] = {pages[i+1]}
        
        analyzer = PathAnalyzer(graph)
        
        # Max length 2 should not find path from 0 to 4 (needs length 4)
        paths = analyzer.find_all_paths(pages[0], pages[4], max_length=2)
        assert len(paths) == 0
        
        # Max length 5 should find the path
        paths = analyzer.find_all_paths(pages[0], pages[4], max_length=5)
        assert len(paths) == 1
        assert paths[0] == pages
    
    def test_filters_generated_pages(self):
        """Test that generated pages are excluded from analysis."""
        real_page = Mock(source_path=Path("real.md"), metadata={})
        generated_page = Mock(source_path=Path("generated.md"), metadata={'_generated': True})
        
        site = Mock()
        site.pages = [real_page, generated_page]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        analyzer = PathAnalyzer(graph)
        results = analyzer.analyze()
        
        # Only real page should be analyzed
        assert len(results.betweenness_centrality) == 1
        assert real_page in results.betweenness_centrality
        assert generated_page not in results.betweenness_centrality


class TestAnalyzePathsFunction:
    """Tests for convenience function."""
    
    def test_analyze_paths(self):
        """Test the convenience function."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(3)]
        
        site = Mock()
        site.pages = pages
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        graph.outgoing_refs[pages[0]] = {pages[1]}
        graph.outgoing_refs[pages[1]] = {pages[2]}
        
        results = analyze_paths(graph)
        
        assert isinstance(results, PathAnalysisResults)
        assert len(results.betweenness_centrality) == 3
        assert len(results.closeness_centrality) == 3
        assert results.diameter > 0

