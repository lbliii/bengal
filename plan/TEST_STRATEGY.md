# Bengal SSG - Testing Strategy & Coverage Plan

**Date:** October 2, 2025  
**Status:** Planning  
**Goal:** 85-90% test coverage with focus on critical paths

---

## 🎯 Testing Philosophy

### Priorities

1. **Core Functionality First**: Site building, rendering, content discovery
2. **User-Facing Features**: CLI, dev server, errors
3. **Edge Cases**: Error handling, malformed input
4. **Performance**: Large sites, stress tests

### Coverage Goals

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| Core (Site, Page, Section, Asset) | 90%+ | Critical |
| Rendering Pipeline | 85%+ | Critical |
| CLI | 80%+ | High |
| Content Discovery | 85%+ | High |
| Template Engine | 75%+ | Medium |
| Dev Server | 70%+ | Medium |
| Utilities (Pagination) | 95%+ | High |
| Post-processing | 80%+ | Medium |

**Overall Target: 85% coverage**

---

## 🧪 Testing Stack

### Tools

```python
# Testing
pytest >= 7.4.0              # Test framework
pytest-cov >= 4.1.0          # Coverage reporting
pytest-mock >= 3.11.0        # Mocking
pytest-xdist >= 3.3.0        # Parallel test execution

# Code Quality
ruff >= 0.1.0                # Linting (fast)
mypy >= 1.5.0                # Type checking
black >= 23.7.0              # Code formatting

# Test Utilities
faker >= 19.6.0              # Generate fake data
hypothesis >= 6.87.0         # Property-based testing
freezegun >= 1.2.2           # Mock datetime
responses >= 0.23.0          # Mock HTTP requests
```

### Configuration Files

**pytest.ini:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=bengal
    --cov-report=html
    --cov-report=term-missing
    --cov-report=xml
    --strict-markers
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    cli: CLI tests
    
# Fail if coverage drops below target
[coverage:report]
fail_under = 85
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

**pyproject.toml additions:**
```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.black]
line-length = 100
target-version = ['py310', 'py311', 'py312']
```

---

## 📁 Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
│
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── core/
│   │   ├── test_page.py
│   │   ├── test_section.py
│   │   ├── test_site.py
│   │   └── test_asset.py
│   ├── rendering/
│   │   ├── test_parser.py
│   │   ├── test_renderer.py
│   │   ├── test_template_engine.py
│   │   └── test_pipeline.py
│   ├── discovery/
│   │   ├── test_content_discovery.py
│   │   └── test_asset_discovery.py
│   ├── utils/
│   │   └── test_pagination.py
│   ├── config/
│   │   └── test_loader.py
│   └── postprocess/
│       ├── test_sitemap.py
│       └── test_rss.py
│
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── test_build_flow.py     # Full build process
│   ├── test_cli.py            # CLI commands
│   ├── test_dev_server.py     # Dev server
│   └── test_themes.py         # Theme system
│
├── e2e/                        # End-to-end tests
│   ├── __init__.py
│   ├── test_example_sites.py  # Build example sites
│   └── test_real_world.py     # Real-world scenarios
│
├── performance/                # Performance tests
│   ├── __init__.py
│   ├── test_build_speed.py    # Build time benchmarks
│   └── test_memory_usage.py   # Memory profiling
│
└── fixtures/                   # Test data
    ├── sites/                  # Test site examples
    │   ├── minimal/            # Minimal site
    │   ├── blog/               # Blog with posts
    │   └── docs/               # Documentation site
    ├── content/                # Test content files
    └── configs/                # Test configurations
```

---

## 🔧 Shared Fixtures (conftest.py)

```python
"""Shared pytest fixtures for Bengal SSG tests."""

import pytest
from pathlib import Path
from typing import Dict, Any
from bengal.core.site import Site
from bengal.core.page import Page
from bengal.config.loader import ConfigLoader


@pytest.fixture
def tmp_site(tmp_path: Path) -> Path:
    """Create a temporary site directory."""
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()
    
    # Create basic structure
    (site_dir / "content").mkdir()
    (site_dir / "assets").mkdir()
    (site_dir / "templates").mkdir()
    
    # Create config
    config_content = """
[site]
title = "Test Site"
base_url = "https://example.com"
"""
    (site_dir / "bengal.toml").write_text(config_content)
    
    return site_dir


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration dictionary."""
    return {
        "title": "Test Site",
        "base_url": "https://example.com",
        "author": {"name": "Test Author"},
        "theme": "default",
        "pagination": {"per_page": 10}
    }


@pytest.fixture
def sample_page(tmp_path: Path) -> Page:
    """Create a sample page."""
    content_file = tmp_path / "test.md"
    content_file.write_text("""---
title: Test Page
date: 2025-10-01
tags: ["test", "sample"]
---

# Test Content

This is a test page.
""")
    
    return Page(
        source_path=content_file,
        content="# Test Content\n\nThis is a test page.",
        metadata={
            "title": "Test Page",
            "date": "2025-10-01",
            "tags": ["test", "sample"]
        }
    )


@pytest.fixture
def site_with_content(tmp_site: Path, sample_config: Dict[str, Any]) -> Site:
    """Create a site with sample content."""
    # Create sample pages
    posts_dir = tmp_site / "content" / "posts"
    posts_dir.mkdir()
    
    for i in range(5):
        post_file = posts_dir / f"post-{i}.md"
        post_file.write_text(f"""---
title: Post {i}
date: 2025-10-{i+1:02d}
tags: ["test"]
---

# Post {i}

Content for post {i}.
""")
    
    # Load site
    loader = ConfigLoader(tmp_site)
    config = loader.load()
    site = Site(root_path=tmp_site, config=config)
    site.discover_content()
    
    return site


@pytest.fixture
def mock_template_engine(mocker):
    """Mock template engine for testing rendering."""
    mock = mocker.Mock()
    mock.render.return_value = "<html>Rendered</html>"
    return mock
```

---

## ✅ Unit Tests

### Core Components

**tests/unit/core/test_page.py:**
```python
"""Unit tests for Page class."""

import pytest
from datetime import datetime
from pathlib import Path
from bengal.core.page import Page


class TestPage:
    """Tests for Page object."""
    
    def test_page_creation(self, tmp_path):
        """Test creating a basic page."""
        source = tmp_path / "test.md"
        page = Page(
            source_path=source,
            content="# Test",
            metadata={"title": "Test"}
        )
        
        assert page.source_path == source
        assert page.content == "# Test"
        assert page.title == "Test"
    
    def test_title_from_metadata(self):
        """Test title is extracted from metadata."""
        page = Page(
            source_path=Path("test.md"),
            metadata={"title": "My Title"}
        )
        
        assert page.title == "My Title"
    
    def test_title_generated_from_filename(self, tmp_path):
        """Test title generated from filename if not in metadata."""
        source = tmp_path / "my-test-page.md"
        page = Page(source_path=source, metadata={})
        
        assert page.title == "My Test Page"
    
    def test_date_property(self):
        """Test date property extraction."""
        date = datetime(2025, 10, 1)
        page = Page(
            source_path=Path("test.md"),
            metadata={"date": date}
        )
        
        assert page.date == date
    
    def test_date_none_when_missing(self):
        """Test date is None when not in metadata."""
        page = Page(source_path=Path("test.md"), metadata={})
        assert page.date is None
    
    def test_slug_from_metadata(self):
        """Test custom slug from metadata."""
        page = Page(
            source_path=Path("test.md"),
            metadata={"slug": "custom-slug"}
        )
        
        assert page.slug == "custom-slug"
    
    def test_slug_from_filename(self, tmp_path):
        """Test slug generated from filename."""
        source = tmp_path / "my-page.md"
        page = Page(source_path=source, metadata={})
        
        assert page.slug == "my-page"
    
    def test_url_property(self, tmp_path):
        """Test URL generation."""
        page = Page(source_path=Path("test.md"), metadata={})
        page.output_path = tmp_path / "public" / "posts" / "my-post" / "index.html"
        
        url = page.url
        assert url == "/posts/my-post/"
    
    def test_url_fallback_to_slug(self):
        """Test URL falls back to slug when output_path is None."""
        page = Page(
            source_path=Path("test.md"),
            metadata={"slug": "my-slug"}
        )
        
        assert page.url == "/my-slug/"
    
    def test_tags_extraction(self):
        """Test tags are extracted from metadata."""
        page = Page(
            source_path=Path("test.md"),
            metadata={"tags": ["python", "testing"]}
        )
        
        assert page.tags == ["python", "testing"]
    
    def test_extract_links_markdown(self):
        """Test extracting Markdown links."""
        page = Page(
            source_path=Path("test.md"),
            content="[Link 1](http://example.com) and [Link 2](/about)"
        )
        
        links = page.extract_links()
        assert "http://example.com" in links
        assert "/about" in links
    
    def test_extract_links_html(self):
        """Test extracting HTML links."""
        page = Page(
            source_path=Path("test.md"),
            content='<a href="http://test.com">Test</a>'
        )
        
        links = page.extract_links()
        assert "http://test.com" in links


class TestPageEdgeCases:
    """Test edge cases for Page."""
    
    def test_empty_content(self):
        """Test page with empty content."""
        page = Page(source_path=Path("test.md"), content="")
        assert page.content == ""
    
    def test_special_characters_in_title(self):
        """Test title with special characters."""
        page = Page(
            source_path=Path("test.md"),
            metadata={"title": "Test & Demo: Part 1"}
        )
        
        assert page.title == "Test & Demo: Part 1"
    
    def test_very_long_content(self):
        """Test page with very long content."""
        long_content = "a" * 1000000  # 1MB
        page = Page(
            source_path=Path("test.md"),
            content=long_content
        )
        
        assert len(page.content) == 1000000
```

### Utilities

**tests/unit/utils/test_pagination.py:**
```python
"""Unit tests for Paginator class."""

import pytest
from bengal.utils.pagination import Paginator


class TestPaginator:
    """Tests for Paginator utility."""
    
    def test_basic_pagination(self):
        """Test basic pagination with 25 items, 10 per page."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)
        
        assert paginator.num_pages == 3
        assert len(paginator.page(1)) == 10
        assert len(paginator.page(2)) == 10
        assert len(paginator.page(3)) == 5
    
    def test_single_page(self):
        """Test pagination with items that fit in one page."""
        items = list(range(5))
        paginator = Paginator(items, per_page=10)
        
        assert paginator.num_pages == 1
        assert len(paginator.page(1)) == 5
    
    def test_empty_list(self):
        """Test pagination with empty list."""
        paginator = Paginator([], per_page=10)
        
        assert paginator.num_pages == 1
        assert len(paginator.page(1)) == 0
    
    def test_page_out_of_range(self):
        """Test requesting page out of range raises error."""
        items = list(range(10))
        paginator = Paginator(items, per_page=10)
        
        with pytest.raises(ValueError):
            paginator.page(2)
        
        with pytest.raises(ValueError):
            paginator.page(0)
    
    def test_page_context(self):
        """Test page_context generates correct data."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)
        
        context = paginator.page_context(2, "/posts/")
        
        assert context['current_page'] == 2
        assert context['total_pages'] == 3
        assert context['has_previous'] is True
        assert context['has_next'] is True
        assert context['previous_page'] == 1
        assert context['next_page'] == 3
        assert context['base_url'] == "/posts/"
    
    def test_page_context_first_page(self):
        """Test page_context for first page."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)
        
        context = paginator.page_context(1, "/posts/")
        
        assert context['has_previous'] is False
        assert context['has_next'] is True
        assert context['previous_page'] is None
    
    def test_page_context_last_page(self):
        """Test page_context for last page."""
        items = list(range(25))
        paginator = Paginator(items, per_page=10)
        
        context = paginator.page_context(3, "/posts/")
        
        assert context['has_previous'] is True
        assert context['has_next'] is False
        assert context['next_page'] is None
    
    def test_page_range(self):
        """Test page_range calculation."""
        items = list(range(100))
        paginator = Paginator(items, per_page=10)
        
        # Should show ±2 pages around current
        context = paginator.page_context(5, "/posts/")
        assert context['page_range'] == [3, 4, 5, 6, 7]
    
    def test_per_page_minimum(self):
        """Test per_page is minimum 1."""
        items = list(range(10))
        paginator = Paginator(items, per_page=0)
        
        assert paginator.per_page == 1
        assert paginator.num_pages == 10
```

---

## 🔗 Integration Tests

**tests/integration/test_build_flow.py:**
```python
"""Integration tests for full build process."""

import pytest
from pathlib import Path
from bengal.core.site import Site
from bengal.config.loader import ConfigLoader


class TestBuildFlow:
    """Test complete build workflows."""
    
    def test_minimal_site_build(self, tmp_site):
        """Test building a minimal site."""
        # Create minimal content
        (tmp_site / "content" / "index.md").write_text("""---
title: Home
---

# Welcome

This is the homepage.
""")
        
        # Load and build
        loader = ConfigLoader(tmp_site)
        config = loader.load()
        site = Site(root_path=tmp_site, config=config)
        
        site.build()
        
        # Check output
        output_file = site.output_dir / "index.html"
        assert output_file.exists()
        assert "Welcome" in output_file.read_text()
    
    def test_blog_with_posts(self, tmp_site):
        """Test building a blog with multiple posts."""
        # Create posts
        posts_dir = tmp_site / "content" / "posts"
        posts_dir.mkdir()
        
        for i in range(15):  # More than one page
            (posts_dir / f"post-{i}.md").write_text(f"""---
title: Post {i}
date: 2025-10-{i+1:02d}
tags: ["test"]
---

# Post {i}

Content.
""")
        
        # Build
        loader = ConfigLoader(tmp_site)
        config = loader.load()
        site = Site(root_path=tmp_site, config=config)
        site.build()
        
        # Check outputs
        assert (site.output_dir / "posts" / "index.html").exists()
        assert (site.output_dir / "posts" / "page" / "2" / "index.html").exists()
        assert (site.output_dir / "tags" / "index.html").exists()
    
    def test_build_with_assets(self, tmp_site):
        """Test build includes assets."""
        # Create asset
        css_dir = tmp_site / "assets" / "css"
        css_dir.mkdir(parents=True)
        (css_dir / "style.css").write_text("body { color: red; }")
        
        # Build
        loader = ConfigLoader(tmp_site)
        config = loader.load()
        site = Site(root_path=tmp_site, config=config)
        site.build()
        
        # Check asset copied
        output_css = site.output_dir / "assets" / "css" / "style.css"
        assert output_css.exists()
        assert "color: red" in output_css.read_text()
    
    def test_taxonomy_collection(self, tmp_site):
        """Test taxonomy collection during build."""
        # Create pages with tags
        (tmp_site / "content" / "page1.md").write_text("""---
title: Page 1
tags: ["python", "testing"]
---
Content 1
""")
        
        (tmp_site / "content" / "page2.md").write_text("""---
title: Page 2
tags: ["python", "tutorial"]
---
Content 2
""")
        
        # Build
        loader = ConfigLoader(tmp_site)
        config = loader.load()
        site = Site(root_path=tmp_site, config=config)
        site.build()
        
        # Check taxonomies collected
        assert "python" in [t.lower() for t in site.taxonomies['tags'].keys()]
        assert "testing" in [t.lower() for t in site.taxonomies['tags'].keys()]
        assert len(site.taxonomies['tags']['python']['pages']) == 2
```

---

## 🎭 CLI Tests

**tests/integration/test_cli.py:**
```python
"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from bengal.cli import cli


class TestCLI:
    """Test CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_version_command(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "Bengal SSG" in result.output
    
    def test_build_command(self, runner, tmp_site):
        """Test build command."""
        with runner.isolated_filesystem(temp_dir=tmp_site.parent):
            result = runner.invoke(cli, ['build'], obj={'root': tmp_site})
            assert result.exit_code == 0
            assert "Build complete" in result.output
    
    def test_clean_command(self, runner, tmp_site):
        """Test clean command."""
        # Create output
        output_dir = tmp_site / "public"
        output_dir.mkdir()
        (output_dir / "test.html").write_text("test")
        
        with runner.isolated_filesystem(temp_dir=tmp_site.parent):
            result = runner.invoke(cli, ['clean'], obj={'root': tmp_site})
            assert result.exit_code == 0
            assert not output_dir.exists()
    
    def test_new_page_command(self, runner, tmp_site):
        """Test new page command."""
        with runner.isolated_filesystem(temp_dir=tmp_site.parent):
            result = runner.invoke(
                cli, 
                ['new', 'page', 'test-page'],
                obj={'root': tmp_site}
            )
            
            assert result.exit_code == 0
            page_file = tmp_site / "content" / "test-page.md"
            assert page_file.exists()
```

---

## 🚀 Performance Tests

**tests/performance/test_build_speed.py:**
```python
"""Performance benchmarks."""

import pytest
import time
from bengal.core.site import Site


@pytest.mark.slow
class TestBuildPerformance:
    """Test build performance."""
    
    def test_build_100_pages(self, tmp_site, benchmark):
        """Benchmark building 100 pages."""
        # Create 100 pages
        for i in range(100):
            (tmp_site / "content" / f"page-{i}.md").write_text(f"""---
title: Page {i}
---
Content {i}
""")
        
        site = Site(root_path=tmp_site, config={})
        
        # Benchmark build
        result = benchmark(site.build)
        
        # Should complete in reasonable time
        assert benchmark.stats['mean'] < 5.0  # 5 seconds average
    
    def test_pagination_performance(self, benchmark):
        """Benchmark pagination with large lists."""
        from bengal.utils.pagination import Paginator
        
        items = list(range(10000))
        
        def paginate():
            p = Paginator(items, per_page=10)
            return p.page(500)
        
        result = benchmark(paginate)
        
        # Should be very fast
        assert benchmark.stats['mean'] < 0.01  # 10ms
```

---

## 📊 Coverage Reports

### Generate Reports

```bash
# HTML report
pytest --cov=bengal --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=bengal --cov-report=term-missing

# XML for CI
pytest --cov=bengal --cov-report=xml

# Check coverage threshold
pytest --cov=bengal --cov-fail-under=85
```

### View Coverage

```bash
# Overall coverage
coverage report

# Detailed by file
coverage report -m

# Find untested lines
coverage report --show-missing
```

---

## ⚡ Running Tests

### Basic

```bash
# All tests
pytest

# With coverage
pytest --cov=bengal

# Verbose
pytest -v

# Specific file
pytest tests/unit/core/test_page.py

# Specific test
pytest tests/unit/core/test_page.py::TestPage::test_title_from_metadata
```

### By Markers

```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# CLI tests only
pytest -m cli
```

### Parallel Execution

```bash
# Use all CPUs
pytest -n auto

# Use specific number
pytest -n 4
```

### Watch Mode

```bash
# Rerun on file changes
pytest-watch
```

---

## 🎯 Coverage Targets by Component

### Critical (90%+)
- `bengal/core/page.py`
- `bengal/core/site.py`
- `bengal/utils/pagination.py`

### High Priority (85%+)
- `bengal/rendering/renderer.py`
- `bengal/rendering/parser.py`
- `bengal/discovery/content_discovery.py`
- `bengal/cli.py`

### Medium Priority (75%+)
- `bengal/rendering/template_engine.py`
- `bengal/config/loader.py`
- `bengal/postprocess/*.py`

### Lower Priority (70%+)
- `bengal/server/dev_server.py`
- `bengal/rendering/link_validator.py`

---

## ✅ Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Set up pytest configuration
- [ ] Create test directory structure
- [ ] Write shared fixtures (conftest.py)
- [ ] Add testing dependencies to pyproject.toml
- [ ] Set up GitHub Actions for CI

### Phase 2: Core Tests (Week 2)
- [ ] Unit tests for Page class (90%+)
- [ ] Unit tests for Site class (90%+)
- [ ] Unit tests for Paginator (95%+)
- [ ] Unit tests for Section class (85%+)
- [ ] Unit tests for Asset class (80%+)

### Phase 3: Rendering Tests (Week 3)
- [ ] Unit tests for Parser (85%+)
- [ ] Unit tests for Renderer (85%+)
- [ ] Unit tests for Template Engine (75%+)
- [ ] Integration tests for rendering pipeline

### Phase 4: CLI & Integration (Week 4)
- [ ] CLI command tests (80%+)
- [ ] Full build flow tests
- [ ] Dev server tests (70%+)
- [ ] End-to-end tests with example sites

### Phase 5: Polish
- [ ] Performance benchmarks
- [ ] Edge case tests
- [ ] Error handling tests
- [ ] Documentation for testing

---

## 🚦 Test Status Tracking

Track test implementation status:

```markdown
## Test Coverage Status

| Component | Coverage | Status | Tests |
|-----------|----------|--------|-------|
| core/page.py | 92% | ✅ | 25/27 |
| core/site.py | 88% | ✅ | 18/20 |
| utils/pagination.py | 96% | ✅ | 15/15 |
| rendering/renderer.py | 82% | 🟡 | 12/15 |
| cli.py | 75% | 🟡 | 8/12 |
| server/dev_server.py | 65% | 🔴 | 4/10 |

Legend:
✅ Meets target
🟡 Close to target
🔴 Needs work
```

---

**Ready to start testing? Begin with Phase 1!**

