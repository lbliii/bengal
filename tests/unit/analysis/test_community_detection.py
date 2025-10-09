"""
Unit tests for community detection algorithm.
"""

import pytest
from unittest.mock import Mock
from pathlib import Path
from collections import defaultdict

from bengal.analysis.community_detection import (
    LouvainCommunityDetector,
    Community,
    CommunityDetectionResults,
    detect_communities
)


class TestCommunity:
    """Tests for Community dataclass."""
    
    def test_community_size(self):
        """Test community size property."""
        pages = {Mock(source_path=Path(f"page{i}.md")) for i in range(5)}
        community = Community(id=1, pages=pages)
        
        assert community.size == 5
    
    def test_community_empty(self):
        """Test empty community."""
        community = Community(id=1, pages=set())
        assert community.size == 0


class TestCommunityDetectionResults:
    """Tests for CommunityDetectionResults."""
    
    def test_get_community_for_page(self):
        """Test finding which community a page belongs to."""
        page1 = Mock(source_path=Path("page1.md"))
        page2 = Mock(source_path=Path("page2.md"))
        page3 = Mock(source_path=Path("page3.md"))
        
        comm1 = Community(id=0, pages={page1, page2})
        comm2 = Community(id=1, pages={page3})
        
        results = CommunityDetectionResults(
            communities=[comm1, comm2],
            modularity=0.5,
            iterations=5
        )
        
        assert results.get_community_for_page(page1) == comm1
        assert results.get_community_for_page(page2) == comm1
        assert results.get_community_for_page(page3) == comm2
        
        # Page not in any community
        page4 = Mock(source_path=Path("page4.md"))
        assert results.get_community_for_page(page4) is None
    
    def test_get_largest_communities(self):
        """Test getting largest communities."""
        comm1 = Community(id=0, pages={Mock() for _ in range(10)})
        comm2 = Community(id=1, pages={Mock() for _ in range(5)})
        comm3 = Community(id=2, pages={Mock() for _ in range(15)})
        
        results = CommunityDetectionResults(
            communities=[comm1, comm2, comm3],
            modularity=0.5,
            iterations=5
        )
        
        largest = results.get_largest_communities(2)
        
        assert len(largest) == 2
        assert largest[0] == comm3  # 15 pages
        assert largest[1] == comm1  # 10 pages
    
    def test_get_communities_above_size(self):
        """Test filtering communities by size."""
        comm1 = Community(id=0, pages={Mock() for _ in range(10)})
        comm2 = Community(id=1, pages={Mock() for _ in range(5)})
        comm3 = Community(id=2, pages={Mock() for _ in range(15)})
        
        results = CommunityDetectionResults(
            communities=[comm1, comm2, comm3],
            modularity=0.5,
            iterations=5
        )
        
        # Get communities with at least 10 pages
        large_communities = results.get_communities_above_size(10)
        
        assert len(large_communities) == 2
        assert comm1 in large_communities
        assert comm3 in large_communities
        assert comm2 not in large_communities


class TestLouvainCommunityDetector:
    """Tests for Louvain algorithm."""
    
    def test_empty_graph(self):
        """Test detection on empty graph."""
        site = Mock()
        site.pages = []
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        detector = LouvainCommunityDetector(graph)
        results = detector.detect()
        
        assert len(results.communities) == 0
        assert results.modularity == 0.0
        assert results.iterations == 0
    
    def test_single_page(self):
        """Test detection with single page."""
        page = Mock()
        page.source_path = Path("page.md")
        page.metadata = {}
        
        site = Mock()
        site.pages = [page]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Single page with no connections forms one community
        assert len(results.communities) == 1
        assert results.communities[0].size == 1
        assert page in results.communities[0].pages
    
    def test_disconnected_pages(self):
        """Test detection with disconnected pages."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(5)]
        
        site = Mock()
        site.pages = pages
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Each disconnected page forms its own community
        assert len(results.communities) == 5
        for community in results.communities:
            assert community.size == 1
    
    def test_fully_connected_graph(self):
        """Test detection with fully connected graph."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(5)]
        
        site = Mock()
        site.pages = pages
        
        # Create fully connected graph
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        for page in pages:
            for other_page in pages:
                if page != other_page:
                    graph.outgoing_refs[page].add(other_page)
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Fully connected graph should form single community
        assert len(results.communities) == 1
        assert results.communities[0].size == 5
    
    def test_two_clusters(self):
        """Test detection with two distinct clusters."""
        # Cluster 1: pages 0-2
        cluster1_pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(3)]
        
        # Cluster 2: pages 3-5
        cluster2_pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(3, 6)]
        
        all_pages = cluster1_pages + cluster2_pages
        
        site = Mock()
        site.pages = all_pages
        
        # Connect within clusters only
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        # Cluster 1 connections
        for page in cluster1_pages:
            for other_page in cluster1_pages:
                if page != other_page:
                    graph.outgoing_refs[page].add(other_page)
        
        # Cluster 2 connections
        for page in cluster2_pages:
            for other_page in cluster2_pages:
                if page != other_page:
                    graph.outgoing_refs[page].add(other_page)
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Should find two communities
        assert len(results.communities) == 2
        
        # Each community should have 3 pages
        sizes = sorted([c.size for c in results.communities])
        assert sizes == [3, 3]
        
        # Modularity should be positive for good clustering
        assert results.modularity > 0
    
    def test_chain_graph(self):
        """Test detection with chain: A -> B -> C -> D."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(4)]
        
        site = Mock()
        site.pages = pages
        
        # Create chain
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        for i in range(len(pages) - 1):
            graph.outgoing_refs[pages[i]].add(pages[i+1])
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Chain should form communities (exact number depends on algorithm)
        assert len(results.communities) >= 1
        assert len(results.communities) <= 4
        
        # All pages should be assigned
        total_pages = sum(c.size for c in results.communities)
        assert total_pages == 4
    
    def test_star_graph(self):
        """Test detection with star: center connected to all others."""
        center = Mock(source_path=Path("center.md"), metadata={})
        spokes = [Mock(source_path=Path(f"spoke{i}.md"), metadata={}) for i in range(5)]
        
        all_pages = [center] + spokes
        
        site = Mock()
        site.pages = all_pages
        
        # Create star
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        for spoke in spokes:
            graph.outgoing_refs[spoke].add(center)
            graph.outgoing_refs[center].add(spoke)
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Star should typically form one community
        # (all connected through center)
        assert len(results.communities) >= 1
        
        # All pages should be assigned
        total_pages = sum(c.size for c in results.communities)
        assert total_pages == 6
    
    def test_resolution_parameter(self):
        """Test that resolution parameter affects number of communities."""
        # Create graph with two loosely connected clusters
        cluster1 = [Mock(source_path=Path(f"c1_{i}.md"), metadata={}) for i in range(3)]
        cluster2 = [Mock(source_path=Path(f"c2_{i}.md"), metadata={}) for i in range(3)]
        all_pages = cluster1 + cluster2
        
        site = Mock()
        site.pages = all_pages
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        # Strong connections within clusters
        for page in cluster1:
            for other in cluster1:
                if page != other:
                    graph.outgoing_refs[page].add(other)
        
        for page in cluster2:
            for other in cluster2:
                if page != other:
                    graph.outgoing_refs[page].add(other)
        
        # Weak connection between clusters
        graph.outgoing_refs[cluster1[0]].add(cluster2[0])
        
        # Lower resolution -> fewer communities
        detector_low = LouvainCommunityDetector(graph, resolution=0.5, random_seed=42)
        results_low = detector_low.detect()
        
        # Higher resolution -> more communities
        detector_high = LouvainCommunityDetector(graph, resolution=2.0, random_seed=42)
        results_high = detector_high.detect()
        
        # Higher resolution should produce at least as many communities
        assert len(results_high.communities) >= len(results_low.communities)
    
    def test_random_seed_reproducibility(self):
        """Test that random seed makes results reproducible."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(10)]
        
        site = Mock()
        site.pages = pages
        
        # Create some connections
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        for i in range(len(pages) - 1):
            graph.outgoing_refs[pages[i]].add(pages[i+1])
        
        # Run twice with same seed
        detector1 = LouvainCommunityDetector(graph, random_seed=42)
        results1 = detector1.detect()
        
        detector2 = LouvainCommunityDetector(graph, random_seed=42)
        results2 = detector2.detect()
        
        # Should get same number of communities
        assert len(results1.communities) == len(results2.communities)
        assert results1.modularity == results2.modularity
    
    def test_filters_generated_pages(self):
        """Test that generated pages are excluded."""
        real_page = Mock(source_path=Path("real.md"), metadata={})
        generated_page = Mock(source_path=Path("generated.md"), metadata={'_generated': True})
        
        site = Mock()
        site.pages = [real_page, generated_page]
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        detector = LouvainCommunityDetector(graph, random_seed=42)
        results = detector.detect()
        
        # Only real page should be in communities
        assert len(results.communities) == 1
        assert real_page in results.communities[0].pages
        assert generated_page not in results.communities[0].pages


class TestDetectCommunitiesFunction:
    """Tests for convenience function."""
    
    def test_detect_communities(self):
        """Test the convenience function."""
        pages = [Mock(source_path=Path(f"page{i}.md"), metadata={}) for i in range(5)]
        
        site = Mock()
        site.pages = pages
        
        graph = Mock()
        graph.site = site
        graph.outgoing_refs = defaultdict(set)
        
        # Create some connections
        for i in range(len(pages) - 1):
            graph.outgoing_refs[pages[i]].add(pages[i+1])
        
        # Use convenience function
        results = detect_communities(graph, random_seed=42)
        
        assert isinstance(results, CommunityDetectionResults)
        assert len(results.communities) > 0
        assert results.modularity >= -1.0  # Modularity is in range [-1, 1]
        assert results.modularity <= 1.0

