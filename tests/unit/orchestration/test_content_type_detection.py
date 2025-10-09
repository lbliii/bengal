"""
Tests for content type detection in SectionOrchestrator.
"""

import pytest
from pathlib import Path
from datetime import datetime

from bengal.core.section import Section
from bengal.core.page import Page
from bengal.core.site import Site
from bengal.orchestration.section import SectionOrchestrator


class TestContentTypeDetection:
    """Test automatic content type detection for sections."""
    
    @pytest.fixture
    def site(self, tmp_path):
        """Create a minimal test site."""
        site = Site(root_path=tmp_path)
        site.content_dir = tmp_path / "content"
        site.output_dir = tmp_path / "output"
        return site
    
    @pytest.fixture
    def orchestrator(self, site):
        """Create a SectionOrchestrator."""
        return SectionOrchestrator(site)
    
    def test_explicit_content_type_override(self, orchestrator):
        """Test that explicit content_type in metadata takes precedence."""
        section = Section(
            name="docs",
            path=Path("/content/docs"),
            metadata={"content_type": "custom"}
        )
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == "custom"
    
    def test_api_reference_by_name(self, orchestrator):
        """Test API reference detection by section name."""
        for name in ['api', 'reference', 'api-reference', 'api-docs']:
            section = Section(name=name, path=Path(f"/content/{name}"))
            content_type = orchestrator._detect_content_type(section)
            assert content_type == 'api-reference', f"Failed for name: {name}"
    
    def test_cli_reference_by_name(self, orchestrator):
        """Test CLI reference detection by section name."""
        for name in ['cli', 'commands', 'cli-reference', 'command-line']:
            section = Section(name=name, path=Path(f"/content/{name}"))
            content_type = orchestrator._detect_content_type(section)
            assert content_type == 'cli-reference', f"Failed for name: {name}"
    
    def test_tutorial_by_name(self, orchestrator):
        """Test tutorial detection by section name."""
        for name in ['tutorials', 'guides', 'how-to']:
            section = Section(name=name, path=Path(f"/content/{name}"))
            content_type = orchestrator._detect_content_type(section)
            assert content_type == 'tutorial', f"Failed for name: {name}"
    
    def test_archive_by_name(self, orchestrator):
        """Test archive detection by section name."""
        for name in ['blog', 'posts', 'news', 'articles']:
            section = Section(name=name, path=Path(f"/content/{name}"))
            content_type = orchestrator._detect_content_type(section)
            assert content_type == 'archive', f"Failed for name: {name}"
    
    def test_api_reference_by_page_metadata(self, orchestrator):
        """Test API reference detection by page metadata."""
        section = Section(name="docs", path=Path("/content/docs"))
        
        # Add pages with API reference type
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/docs/module{i}.md"),
                content="API docs",
                metadata={"type": "python-module"}
            )
            section.add_page(page)
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == 'api-reference'
    
    def test_cli_reference_by_page_metadata(self, orchestrator):
        """Test CLI reference detection by page metadata."""
        section = Section(name="commands", path=Path("/content/commands"))
        
        # Add pages with CLI command type
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/commands/cmd{i}.md"),
                content="Command docs",
                metadata={"type": "command"}
            )
            section.add_page(page)
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == 'cli-reference'
    
    def test_archive_by_date_heuristic(self, orchestrator):
        """Test archive detection when pages have dates."""
        section = Section(name="articles", path=Path("/content/articles"))
        
        # Add pages with dates (60%+ should trigger archive)
        for i in range(5):
            page = Page(
                source_path=Path(f"/content/articles/post{i}.md"),
                content="Post content",
                metadata={
                    "title": f"Post {i}",
                    "date": datetime(2025, 1, i+1)
                }
            )
            section.add_page(page)
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == 'archive'
    
    def test_list_when_few_dates(self, orchestrator):
        """Test generic list when less than 60% of pages have dates."""
        section = Section(name="docs", path=Path("/content/docs"))
        
        # Add 2 pages with dates, 3 without (40% with dates)
        for i in range(2):
            page = Page(
                source_path=Path(f"/content/docs/dated{i}.md"),
                content="Content",
                metadata={"date": datetime(2025, 1, i+1)}
            )
            section.add_page(page)
        
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/docs/page{i}.md"),
                content="Content",
                metadata={}
            )
            section.add_page(page)
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == 'list'
    
    def test_list_default_for_unknown(self, orchestrator):
        """Test that unknown sections default to 'list' not 'archive'."""
        section = Section(name="random", path=Path("/content/random"))
        
        # Add some regular pages without dates
        for i in range(3):
            page = Page(
                source_path=Path(f"/content/random/page{i}.md"),
                content="Content",
                metadata={"title": f"Page {i}"}
            )
            section.add_page(page)
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == 'list'
    
    def test_empty_section_defaults_to_list(self, orchestrator):
        """Test that empty sections default to 'list'."""
        section = Section(name="empty", path=Path("/content/empty"))
        
        content_type = orchestrator._detect_content_type(section)
        assert content_type == 'list'


class TestTemplateSelection:
    """Test template selection based on content type."""
    
    @pytest.fixture
    def site(self, tmp_path):
        """Create a minimal test site."""
        site = Site(root_path=tmp_path)
        site.content_dir = tmp_path / "content"
        site.output_dir = tmp_path / "output"
        return site
    
    @pytest.fixture
    def orchestrator(self, site):
        """Create a SectionOrchestrator."""
        return SectionOrchestrator(site)
    
    def test_api_reference_template(self, orchestrator):
        """Test API reference uses api-reference/list.html."""
        template = orchestrator._get_template_for_content_type('api-reference')
        assert template == 'api-reference/list.html'
    
    def test_cli_reference_template(self, orchestrator):
        """Test CLI reference uses cli-reference/list.html."""
        template = orchestrator._get_template_for_content_type('cli-reference')
        assert template == 'cli-reference/list.html'
    
    def test_tutorial_template(self, orchestrator):
        """Test tutorial uses tutorial/list.html."""
        template = orchestrator._get_template_for_content_type('tutorial')
        assert template == 'tutorial/list.html'
    
    def test_archive_template(self, orchestrator):
        """Test archive uses archive.html."""
        template = orchestrator._get_template_for_content_type('archive')
        assert template == 'archive.html'
    
    def test_list_template(self, orchestrator):
        """Test generic list uses index.html."""
        template = orchestrator._get_template_for_content_type('list')
        assert template == 'index.html'
    
    def test_unknown_type_defaults_to_index(self, orchestrator):
        """Test unknown content type defaults to index.html."""
        template = orchestrator._get_template_for_content_type('unknown-type')
        assert template == 'index.html'


class TestPaginationDecision:
    """Test pagination decisions based on content type."""
    
    @pytest.fixture
    def site(self, tmp_path):
        """Create a minimal test site."""
        site = Site(root_path=tmp_path)
        site.content_dir = tmp_path / "content"
        site.output_dir = tmp_path / "output"
        site.config = {
            'pagination': {
                'per_page': 10,
                'threshold': 20
            }
        }
        return site
    
    @pytest.fixture
    def orchestrator(self, site):
        """Create a SectionOrchestrator."""
        return SectionOrchestrator(site)
    
    def test_reference_never_paginates(self, orchestrator):
        """Test that reference docs never paginate."""
        section = Section(name="api", path=Path("/content/api"))
        
        # Add many pages
        for i in range(100):
            page = Page(
                source_path=Path(f"/content/api/page{i}.md"),
                content="Content",
                metadata={}
            )
            section.add_page(page)
        
        # API reference should not paginate
        assert not orchestrator._should_paginate(section, 'api-reference')
        # CLI reference should not paginate
        assert not orchestrator._should_paginate(section, 'cli-reference')
        # Tutorial should not paginate
        assert not orchestrator._should_paginate(section, 'tutorial')
    
    def test_archive_paginates_when_threshold_exceeded(self, orchestrator):
        """Test that archives paginate when exceeding threshold."""
        section = Section(name="blog", path=Path("/content/blog"))
        
        # Add pages exceeding threshold (20)
        for i in range(25):
            page = Page(
                source_path=Path(f"/content/blog/post{i}.md"),
                content="Content",
                metadata={"date": datetime(2025, 1, 1)}
            )
            section.add_page(page)
        
        assert orchestrator._should_paginate(section, 'archive')
    
    def test_archive_no_pagination_below_threshold(self, orchestrator):
        """Test that archives don't paginate below threshold."""
        section = Section(name="blog", path=Path("/content/blog"))
        
        # Add pages below threshold (20)
        for i in range(10):
            page = Page(
                source_path=Path(f"/content/blog/post{i}.md"),
                content="Content",
                metadata={"date": datetime(2025, 1, 1)}
            )
            section.add_page(page)
        
        assert not orchestrator._should_paginate(section, 'archive')
    
    def test_explicit_pagination_override(self, orchestrator):
        """Test explicit pagination metadata overrides heuristics."""
        section = Section(
            name="docs",
            path=Path("/content/docs"),
            metadata={"paginate": True}
        )
        
        # Even with few pages, explicit override should enable pagination
        for i in range(5):
            page = Page(
                source_path=Path(f"/content/docs/page{i}.md"),
                content="Content",
                metadata={}
            )
            section.add_page(page)
        
        # Note: reference docs still won't paginate (explicit check first)
        # But for 'list' type, explicit override works
        assert orchestrator._should_paginate(section, 'list')

