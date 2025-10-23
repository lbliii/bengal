"""
Unit tests for connectivity health validator.

Tests the ConnectivityValidator which checks:
- Orphaned pages (no incoming links)
- Over-connected hubs
- Overall connectivity health
- Content discovery issues
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.health.report import CheckResult, CheckStatus
from bengal.health.validators.connectivity import ConnectivityValidator


class TestConnectivityValidator:
    """Tests for ConnectivityValidator."""

    @pytest.fixture
    def validator(self):
        """Create a ConnectivityValidator instance."""
        return ConnectivityValidator()

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site with pages."""
        site = Mock(spec=Site)
        site.root_dir = tmp_path
        site.config = {}
        
        # Create test pages
        pages = []
        for i in range(5):
            page = Mock(spec=Page)
            page.source_path = tmp_path / f"page{i}.md"
            page.source_path.touch()
            page.output_path = tmp_path / "public" / f"page{i}.html"
            page.output_path.parent.mkdir(parents=True, exist_ok=True)
            page.output_path.touch()
            page.url = f"/page{i}/"
            page.metadata = {}
            pages.append(page)
        
        site.pages = pages
        return site

    @pytest.fixture
    def mock_knowledge_graph(self):
        """Create a mock KnowledgeGraph."""
        graph = Mock()
        graph.build = Mock()
        graph.get_metrics = Mock(return_value={
            "nodes": 5,
            "edges": 10,
            "density": 0.5,
            "average_degree": 2.0
        })
        graph.get_orphans = Mock(return_value=[])
        graph.get_hubs = Mock(return_value=[])
        return graph

    def test_validator_properties(self, validator):
        """Test validator basic properties."""
        assert validator.name == "Connectivity"
        assert validator.enabled_by_default is True
        assert "connectivity" in validator.description.lower()

    def test_no_pages(self, validator):
        """Test validation with no pages."""
        site = Mock(spec=Site)
        site.pages = []
        
        results = validator.validate(site)
        
        # Should return info message
        assert any(r.status == CheckStatus.INFO and "no pages" in r.message.lower() 
                  for r in results)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_healthy_connectivity(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test validation with healthy connectivity."""
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should have success results
        assert any(r.status == CheckStatus.SUCCESS for r in results)
        mock_knowledge_graph.build.assert_called_once()

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_orphaned_pages_warning(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test detection of orphaned pages (warning level)."""
        # Create a few orphans (under threshold)
        orphan_pages = [mock_site.pages[0], mock_site.pages[1]]
        mock_knowledge_graph.get_orphans.return_value = orphan_pages
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should have warning about orphans
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("orphan" in r.message.lower() for r in warnings)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_orphaned_pages_error(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test detection of many orphaned pages (error level)."""
        # Create many orphans (over threshold)
        orphan_pages = mock_site.pages  # All pages are orphans
        mock_knowledge_graph.get_orphans.return_value = orphan_pages
        mock_kg_class.return_value = mock_knowledge_graph
        
        # Set low threshold
        mock_site.config = {"health_check": {"orphan_threshold": 2}}
        
        results = validator.validate(mock_site)
        
        # Should have error about orphans
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("orphan" in r.message.lower() for r in errors)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_over_connected_hubs(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test detection of over-connected hub pages."""
        # Create hub pages
        hub_page = Mock(spec=Page)
        hub_page.source_path = Path("/tmp/hub.md")
        hub_page.url = "/hub/"
        
        mock_knowledge_graph.get_hubs.return_value = [(hub_page, 50)]  # 50 incoming links
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should have warning about hubs
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("hub" in r.message.lower() or "connected" in r.message.lower() 
                  for r in warnings)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_connectivity_metrics(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test that connectivity metrics are reported."""
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should report metrics
        assert len(results) > 0
        mock_knowledge_graph.get_metrics.assert_called_once()

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_low_connectivity_density(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test detection of low connectivity density."""
        mock_knowledge_graph.get_metrics.return_value = {
            "nodes": 10,
            "edges": 5,
            "density": 0.05,  # Very low density
            "average_degree": 1.0
        }
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should have warning about low connectivity
        warnings = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(warnings) > 0

    def test_import_error_handling(self, validator, mock_site):
        """Test handling of missing knowledge graph module."""
        with patch('bengal.health.validators.connectivity.KnowledgeGraph', side_effect=ImportError("Module not found")):
            results = validator.validate(mock_site)
            
            # Should return error about unavailable analysis
            errors = [r for r in results if r.status == CheckStatus.ERROR]
            assert any("unavailable" in r.message.lower() for r in errors)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_graph_build_exception(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test handling of exceptions during graph building."""
        mock_knowledge_graph.build.side_effect = Exception("Graph build failed")
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should handle exception gracefully
        assert len(results) > 0

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_custom_orphan_threshold(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test using custom orphan threshold from config."""
        orphan_pages = [mock_site.pages[0], mock_site.pages[1]]
        mock_knowledge_graph.get_orphans.return_value = orphan_pages
        mock_kg_class.return_value = mock_knowledge_graph
        
        # Set custom threshold
        mock_site.config = {"health_check": {"orphan_threshold": 1}}
        
        results = validator.validate(mock_site)
        
        # With threshold=1, should be error (2 orphans > 1)
        errors = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("orphan" in r.message.lower() for r in errors)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_no_orphans_success(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test successful validation with no orphans."""
        mock_knowledge_graph.get_orphans.return_value = []
        mock_knowledge_graph.get_hubs.return_value = []
        mock_kg_class.return_value = mock_knowledge_graph
        
        results = validator.validate(mock_site)
        
        # Should have success message
        assert any(r.status == CheckStatus.SUCCESS for r in results)

    @patch('bengal.health.validators.connectivity.KnowledgeGraph')
    def test_orphan_details_limited(self, mock_kg_class, validator, mock_site, mock_knowledge_graph):
        """Test that orphan details are limited to first 10."""
        # Create 15 orphan pages
        orphan_pages = [Mock(spec=Page) for _ in range(15)]
        for i, page in enumerate(orphan_pages):
            page.source_path = Path(f"/tmp/orphan{i}.md")
        
        mock_knowledge_graph.get_orphans.return_value = orphan_pages
        mock_kg_class.return_value = mock_knowledge_graph
        
        mock_site.config = {"health_check": {"orphan_threshold": 5}}
        
        results = validator.validate(mock_site)
        
        # Should limit details to 10 entries
        errors = [r for r in results if r.status == CheckStatus.ERROR and "orphan" in r.message.lower()]
        if errors and errors[0].details:
            assert len(errors[0].details) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
