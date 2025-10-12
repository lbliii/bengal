"""
Integration tests for community detection with KnowledgeGraph.
"""

from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.analysis.community_detection import CommunityDetectionResults
from bengal.analysis.knowledge_graph import KnowledgeGraph


@pytest.fixture
def clustered_site():
    """Create a mock site with clear clusters for testing."""
    # Python cluster (pages 0-3)
    python_pages = []
    for i in range(4):
        page = Mock()
        page.source_path = Path(f"python/page{i}.md")
        page.title = f"Python Page {i}"
        page.metadata = {}
        python_pages.append(page)

    # Web cluster (pages 4-7)
    web_pages = []
    for i in range(4, 8):
        page = Mock()
        page.source_path = Path(f"web/page{i}.md")
        page.title = f"Web Page {i}"
        page.metadata = {}
        web_pages.append(page)

    all_pages = python_pages + web_pages

    # Create mock site
    site = Mock()
    site.pages = all_pages
    site.sections = []
    site.menus = {}
    site.config = {"taxonomies": {}}

    # Build graph with two clusters
    graph = KnowledgeGraph(site)
    graph._built = True
    graph.incoming_refs = defaultdict(int)
    graph.outgoing_refs = defaultdict(set)

    # Connect within Python cluster
    for page in python_pages:
        for other in python_pages:
            if page != other:
                graph.outgoing_refs[page].add(other)
                graph.incoming_refs[other] += 1

    # Connect within Web cluster
    for page in web_pages:
        for other in web_pages:
            if page != other:
                graph.outgoing_refs[page].add(other)
                graph.incoming_refs[other] += 1

    return site, graph, python_pages, web_pages


class TestCommunityDetectionIntegration:
    """Integration tests for community detection with knowledge graph."""

    def test_detect_communities(self, clustered_site):
        """Test basic community detection."""
        site, graph, python_pages, web_pages = clustered_site

        # Detect communities
        results = graph.detect_communities(random_seed=42)

        # Verify results structure
        assert isinstance(results, CommunityDetectionResults)
        assert len(results.communities) > 0
        assert results.modularity > 0  # Good clustering should have positive modularity
        assert results.iterations > 0

        # Should find 2 communities (Python and Web)
        assert len(results.communities) == 2

        # Each community should have 4 pages
        sizes = sorted([c.size for c in results.communities])
        assert sizes == [4, 4]

    def test_community_detection_caching(self, clustered_site):
        """Test that community detection results are cached."""
        site, graph, python_pages, web_pages = clustered_site

        # First detection
        results1 = graph.detect_communities(random_seed=42)

        # Second detection should return cached results
        results2 = graph.detect_communities(random_seed=42)

        # Should be the same object
        assert results1 is results2

        # Force recompute
        results3 = graph.detect_communities(random_seed=42, force_recompute=True)

        # Should be different object but same structure
        assert results3 is not results1
        assert len(results3.communities) == len(results1.communities)

    def test_get_community_for_page(self, clustered_site):
        """Test getting community ID for specific page."""
        site, graph, python_pages, web_pages = clustered_site

        # Get community for a Python page
        community_id = graph.get_community_for_page(python_pages[0])

        assert community_id is not None
        assert isinstance(community_id, int)

        # All Python pages should be in same community
        python_community = community_id
        for page in python_pages[1:]:
            assert graph.get_community_for_page(page) == python_community

        # Web pages should be in different community
        web_community = graph.get_community_for_page(web_pages[0])
        assert web_community != python_community

        for page in web_pages[1:]:
            assert graph.get_community_for_page(page) == web_community

    def test_get_largest_communities(self, clustered_site):
        """Test getting largest communities."""
        site, graph, python_pages, web_pages = clustered_site

        results = graph.detect_communities(random_seed=42)

        # Get largest communities
        largest = results.get_largest_communities(2)

        assert len(largest) == 2
        # Both communities have same size (4 pages each)
        assert largest[0].size == 4
        assert largest[1].size == 4

    def test_get_communities_above_size(self, clustered_site):
        """Test filtering communities by size."""
        site, graph, python_pages, web_pages = clustered_site

        results = graph.detect_communities(random_seed=42)

        # Get communities with at least 3 pages
        large_communities = results.get_communities_above_size(3)

        assert len(large_communities) == 2  # Both clusters have 4 pages

        # Get communities with at least 5 pages
        very_large = results.get_communities_above_size(5)

        assert len(very_large) == 0  # No communities that large

    def test_community_detection_without_build(self, clustered_site):
        """Test that community detection requires graph to be built first."""
        site, graph, python_pages, web_pages = clustered_site

        # Create new graph without building
        new_graph = KnowledgeGraph(site)

        with pytest.raises(RuntimeError, match="Must call build"):
            new_graph.detect_communities()

    def test_resolution_parameter(self, clustered_site):
        """Test that resolution parameter affects community count."""
        site, graph, python_pages, web_pages = clustered_site

        # Lower resolution -> fewer communities
        results_low = graph.detect_communities(resolution=0.5, random_seed=42)

        # Higher resolution -> more communities
        results_high = graph.detect_communities(
            resolution=2.0, random_seed=42, force_recompute=True
        )

        # Higher resolution should produce at least as many communities
        assert len(results_high.communities) >= len(results_low.communities)


class TestCommunityDetectionScalability:
    """Test community detection performance characteristics."""

    def test_large_graph(self):
        """Test community detection on larger graph (50 pages)."""
        # Create 50 pages in 5 clusters of 10 each
        clusters = []
        for cluster_id in range(5):
            cluster = []
            for i in range(10):
                page = Mock()
                page.source_path = Path(f"cluster{cluster_id}/page{i}.md")
                page.title = f"Cluster {cluster_id} Page {i}"
                page.metadata = {}
                cluster.append(page)
            clusters.append(cluster)

        all_pages = [page for cluster in clusters for page in cluster]

        # Create mock site
        site = Mock()
        site.pages = all_pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph with 5 clusters
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Connect within each cluster
        for cluster in clusters:
            for page in cluster:
                for other in cluster:
                    if page != other:
                        graph.outgoing_refs[page].add(other)
                        graph.incoming_refs[other] += 1

        # Detect communities
        results = graph.detect_communities(random_seed=42)

        # Should find 5 communities
        assert len(results.communities) == 5

        # Each community should have 10 pages
        sizes = sorted([c.size for c in results.communities])
        assert sizes == [10, 10, 10, 10, 10]

        # Modularity should be positive
        assert results.modularity > 0

    def test_mixed_size_communities(self):
        """Test detection with communities of different sizes."""
        # Small community (3 pages)
        small_cluster = [
            Mock(source_path=Path(f"small{i}.md"), title=f"Small {i}", metadata={})
            for i in range(3)
        ]

        # Large community (10 pages)
        large_cluster = [
            Mock(source_path=Path(f"large{i}.md"), title=f"Large {i}", metadata={})
            for i in range(10)
        ]

        all_pages = small_cluster + large_cluster

        site = Mock()
        site.pages = all_pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Connect within small cluster
        for page in small_cluster:
            for other in small_cluster:
                if page != other:
                    graph.outgoing_refs[page].add(other)
                    graph.incoming_refs[other] += 1

        # Connect within large cluster
        for page in large_cluster:
            for other in large_cluster:
                if page != other:
                    graph.outgoing_refs[page].add(other)
                    graph.incoming_refs[other] += 1

        # Detect communities
        results = graph.detect_communities(random_seed=42)

        # Should find 2 communities
        assert len(results.communities) == 2

        # Sizes should be 3 and 10
        sizes = sorted([c.size for c in results.communities])
        assert sizes == [3, 10]

    def test_weakly_connected_components(self):
        """Test detection with weak inter-cluster connections."""
        # Two clusters with one weak connection between them
        cluster1 = [
            Mock(source_path=Path(f"c1_{i}.md"), title=f"C1 {i}", metadata={}) for i in range(5)
        ]

        cluster2 = [
            Mock(source_path=Path(f"c2_{i}.md"), title=f"C2 {i}", metadata={}) for i in range(5)
        ]

        all_pages = cluster1 + cluster2

        site = Mock()
        site.pages = all_pages
        site.sections = []
        site.menus = {}
        site.config = {"taxonomies": {}}

        # Build graph
        graph = KnowledgeGraph(site)
        graph._built = True
        graph.incoming_refs = defaultdict(int)
        graph.outgoing_refs = defaultdict(set)

        # Strong connections within clusters
        for page in cluster1:
            for other in cluster1:
                if page != other:
                    graph.outgoing_refs[page].add(other)
                    graph.incoming_refs[other] += 1

        for page in cluster2:
            for other in cluster2:
                if page != other:
                    graph.outgoing_refs[page].add(other)
                    graph.incoming_refs[other] += 1

        # One weak connection between clusters
        graph.outgoing_refs[cluster1[0]].add(cluster2[0])
        graph.incoming_refs[cluster2[0]] += 1

        # Detect communities
        results = graph.detect_communities(random_seed=42)

        # Should still find 2 distinct communities
        # (weak connection shouldn't merge them)
        assert len(results.communities) == 2

        sizes = sorted([c.size for c in results.communities])
        assert sizes == [5, 5]
