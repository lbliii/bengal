"""
Integration tests for path analysis with KnowledgeGraph.
"""

from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.analysis.knowledge_graph import KnowledgeGraph
from bengal.analysis.path_analysis import PathAnalysisResults


@pytest.fixture
def connected_site():
    """Create a mock site with well-connected pages for testing."""
    # Hub page (highly connected)
    hub = Mock()
    hub.source_path = Path("hub.md")
    hub.title = "Hub Page"
    hub.metadata = {}

    # Bridge page (connects two groups)
    bridge = Mock()
    bridge.source_path = Path("bridge.md")
    bridge.title = "Bridge Page"
    bridge.metadata = {}

    # Cluster A pages
    cluster_a = []
    for i in range(3):
        page = Mock()
        page.source_path = Path(f"cluster_a/page{i}.md")
        page.title = f"Cluster A Page {i}"
        page.metadata = {}
        cluster_a.append(page)

    # Cluster B pages
    cluster_b = []
    for i in range(3):
        page = Mock()
        page.source_path = Path(f"cluster_b/page{i}.md")
        page.title = f"Cluster B Page {i}"
        page.metadata = {}
        cluster_b.append(page)

    all_pages = [hub, bridge] + cluster_a + cluster_b

    # Create mock site
    site = Mock()
    site.pages = all_pages
    site.sections = []
    site.menus = {}
    site.config = {"taxonomies": {}}

    # Build graph with bridge structure
    graph = KnowledgeGraph(site)
    graph._built = True
    graph.incoming_refs = defaultdict(int)
    graph.outgoing_refs = defaultdict(set)

    # Hub connects to everything
    for page in all_pages:
        if page != hub:
            graph.outgoing_refs[hub].add(page)
            graph.incoming_refs[page] += 1

    # Cluster A pages connect to each other and hub
    for page in cluster_a:
        graph.outgoing_refs[page].add(hub)
        graph.incoming_refs[hub] += 1
        for other in cluster_a:
            if page != other:
                graph.outgoing_refs[page].add(other)
                graph.incoming_refs[other] += 1

    # Cluster B pages connect to each other and bridge
    for page in cluster_b:
        graph.outgoing_refs[page].add(bridge)
        graph.incoming_refs[bridge] += 1
        for other in cluster_b:
            if page != other:
                graph.outgoing_refs[page].add(other)
                graph.incoming_refs[other] += 1

    # Bridge connects hub to cluster B
    graph.outgoing_refs[bridge].add(hub)
    graph.incoming_refs[hub] += 1
    graph.outgoing_refs[hub].add(bridge)
    graph.incoming_refs[bridge] += 1

    return site, graph, hub, bridge, cluster_a, cluster_b


class TestPathAnalysisIntegration:
    """Integration tests for path analysis with knowledge graph."""

    def test_analyze_paths(self, connected_site):
        """Test basic path analysis."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        # Analyze paths
        results = graph.analyze_paths()

        # Verify results structure
        assert isinstance(results, PathAnalysisResults)
        assert len(results.betweenness_centrality) > 0
        assert len(results.closeness_centrality) > 0
        assert results.avg_path_length > 0
        assert results.diameter > 0

    def test_identify_bridge_pages(self, connected_site):
        """Test that bridge pages have high betweenness centrality."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        results = graph.analyze_paths()

        # Bridge should have high betweenness (it connects two clusters)
        bridge_betweenness = results.get_betweenness(bridge)

        # Bridge betweenness should be higher than most pages
        avg_betweenness = sum(results.betweenness_centrality.values()) / len(
            results.betweenness_centrality
        )
        assert bridge_betweenness > avg_betweenness

    def test_identify_accessible_pages(self, connected_site):
        """Test that well-connected pages have high closeness centrality."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        results = graph.analyze_paths()

        # Hub should have high closeness (connects to everything)
        hub_closeness = results.get_closeness(hub)

        # Hub should be more accessible than average
        avg_closeness = sum(results.closeness_centrality.values()) / len(
            results.closeness_centrality
        )
        assert hub_closeness > avg_closeness

    def test_path_analysis_caching(self, connected_site):
        """Test that path analysis results are cached."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        # First analysis
        results1 = graph.analyze_paths()

        # Second analysis should return cached results
        results2 = graph.analyze_paths()

        # Should be the same object
        assert results1 is results2

        # Force recompute
        results3 = graph.analyze_paths(force_recompute=True)

        # Should be different object but same values
        assert results3 is not results1
        assert len(results3.betweenness_centrality) == len(results1.betweenness_centrality)

    def test_get_betweenness_centrality(self, connected_site):
        """Test getting betweenness centrality for specific page."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        # Get betweenness (should auto-analyze)
        betweenness = graph.get_betweenness_centrality(hub)

        assert betweenness >= 0.0
        assert isinstance(betweenness, float)

    def test_get_closeness_centrality(self, connected_site):
        """Test getting closeness centrality for specific page."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        # Get closeness (should auto-analyze)
        closeness = graph.get_closeness_centrality(hub)

        assert closeness >= 0.0
        assert isinstance(closeness, float)

    def test_path_analysis_without_build(self, connected_site):
        """Test that path analysis requires graph to be built first."""
        from bengal.errors import BengalError

        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        # Create new graph without building
        new_graph = KnowledgeGraph(site)

        with pytest.raises(BengalError, match="not built"):
            new_graph.analyze_paths()

    def test_top_bridges(self, connected_site):
        """Test getting top bridge pages."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        results = graph.analyze_paths()

        bridges = results.get_top_bridges(3)

        assert len(bridges) <= 3
        # Each result is (page, score)
        for _page, score in bridges:
            assert score >= 0.0

        # Scores should be in descending order
        scores = [score for _, score in bridges]
        assert scores == sorted(scores, reverse=True)

    def test_most_accessible(self, connected_site):
        """Test getting most accessible pages."""
        site, graph, hub, bridge, cluster_a, cluster_b = connected_site

        results = graph.analyze_paths()

        accessible = results.get_most_accessible(3)

        assert len(accessible) <= 3
        # Each result is (page, score)
        for _page, score in accessible:
            assert score >= 0.0

        # Scores should be in descending order
        scores = [score for _, score in accessible]
        assert scores == sorted(scores, reverse=True)


class TestPathAnalysisScalability:
    """Test path analysis performance characteristics."""

    def test_large_connected_graph(self):
        """Test path analysis on larger graph (30 pages)."""
        # Create 30 pages in 3 groups with cross-group connections
        groups = []
        for group_id in range(3):
            group = []
            for i in range(10):
                page = Mock()
                page.source_path = Path(f"group{group_id}/page{i}.md")
                page.title = f"Group {group_id} Page {i}"
                page.metadata = {}
                group.append(page)
            groups.append(group)

        all_pages = [page for group in groups for page in group]

        # Create mock site
        site = Mock()
        site.pages = all_pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph with connections
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Connect within each group
        for group in groups:
            for page in group:
                for other in group:
                    if page != other:
                        graph.outgoing_refs[page].add(other)
                        graph.incoming_refs[other] += 1

        # Connect groups through first page of each
        for i in range(len(groups)):
            next_group = (i + 1) % len(groups)
            graph.outgoing_refs[groups[i][0]].add(groups[next_group][0])
            graph.incoming_refs[groups[next_group][0]] += 1

        # Analyze paths
        results = graph.analyze_paths()

        # Should complete successfully
        assert len(results.betweenness_centrality) == 30
        assert len(results.closeness_centrality) == 30
        assert results.diameter > 0

        # Bridge pages (first in each group) should have higher betweenness
        bridge_pages = [group[0] for group in groups]
        avg_betweenness = sum(results.betweenness_centrality.values()) / len(
            results.betweenness_centrality
        )

        for bridge in bridge_pages:
            assert results.betweenness_centrality[bridge] >= avg_betweenness

    def test_sparse_graph(self):
        """Test path analysis on sparse graph (few connections)."""
        # Create 20 pages with minimal connections
        pages = [
            Mock(source_path=Path(f"page{i}.md"), title=f"Page {i}", metadata={}) for i in range(20)
        ]

        site = Mock()
        site.pages = pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build sparse graph - only sequential connections
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Chain: 0 -> 1 -> 2 -> ... -> 19
        for i in range(len(pages) - 1):
            graph.outgoing_refs[pages[i]].add(pages[i + 1])
            graph.incoming_refs[pages[i + 1]] += 1

        # Analyze paths
        results = graph.analyze_paths()

        # Should handle sparse graphs
        assert len(results.betweenness_centrality) == 20
        assert results.diameter == 19  # Longest path from 0 to 19

        # Middle pages should have higher betweenness than endpoints
        middle_page = pages[10]
        first_page = pages[0]
        last_page = pages[-1]

        assert (
            results.betweenness_centrality[middle_page] > results.betweenness_centrality[first_page]
        )
        assert (
            results.betweenness_centrality[middle_page] > results.betweenness_centrality[last_page]
        )

    def test_disconnected_components(self):
        """Test path analysis with disconnected components."""
        # Create two separate components
        component1 = [
            Mock(source_path=Path(f"c1_{i}.md"), title=f"C1 {i}", metadata={}) for i in range(5)
        ]

        component2 = [
            Mock(source_path=Path(f"c2_{i}.md"), title=f"C2 {i}", metadata={}) for i in range(5)
        ]

        all_pages = component1 + component2

        site = Mock()
        site.pages = all_pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph with two disconnected components
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Connect within component 1
        for i in range(len(component1) - 1):
            graph.outgoing_refs[component1[i]].add(component1[i + 1])
            graph.incoming_refs[component1[i + 1]] += 1

        # Connect within component 2
        for i in range(len(component2) - 1):
            graph.outgoing_refs[component2[i]].add(component2[i + 1])
            graph.incoming_refs[component2[i + 1]] += 1

        # Analyze paths
        results = graph.analyze_paths()

        # Should handle disconnected components
        assert len(results.betweenness_centrality) == 10

        # First page in each component can reach others in that component
        assert results.closeness_centrality[component1[0]] > 0
        assert results.closeness_centrality[component2[0]] > 0

        # Last pages in chains have no outgoing edges, so 0 closeness
        assert results.closeness_centrality[component1[-1]] == 0
        assert results.closeness_centrality[component2[-1]] == 0
