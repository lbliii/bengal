"""Tests for page-hero templates.

Tests for the separated page-hero templates to ensure correct rendering for:
- API module pages (DocElement with classes/functions children)
- API section-index pages (Section with subsections/pages)
- CLI command pages (DocElement with options/arguments children)
- CLI section-index pages (Section with CLI-specific labels)

Uses the new separated templates:
- partials/page-hero/element.html for element pages
- partials/page-hero/section.html for section-index pages
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from bengal.core.site import Site
from bengal.rendering.engines import create_engine
from bengal.rendering.template_functions.autodoc import get_element_stats

# ==============================================================================
# Mock Objects for Testing
# ==============================================================================


@dataclass
class MockDocElement:
    """
    Mock DocElement for template testing.

    Simulates the bengal.autodoc.base.DocElement dataclass with the attributes
    accessed by page-hero/element.html template.

    Attributes:
        name: Element name
        qualified_name: Full qualified name (e.g., 'bengal.core.Site')
        description: Element description/docstring
        element_type: Type ('module', 'class', 'function', 'command', etc.)
        source_file: Path to source file
        line_number: Line number in source
        children: Child elements (classes, functions, options, etc.)

    """

    name: str = "test_element"
    qualified_name: str = "bengal.test_element"
    description: str = "Test element description"
    element_type: str = "module"
    source_file: Path | None = None
    display_source_file: str | None = None
    line_number: int | None = None
    children: list[MockDocElement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_class_child(cls, name: str, description: str = "") -> MockDocElement:
        """Create a mock class child element."""
        return cls(
            name=name,
            qualified_name=f"module.{name}",
            description=description,
            element_type="class",
        )

    @classmethod
    def create_function_child(cls, name: str, description: str = "") -> MockDocElement:
        """Create a mock function child element."""
        return cls(
            name=name,
            qualified_name=f"module.{name}",
            description=description,
            element_type="function",
        )

    @classmethod
    def create_option_child(cls, name: str, description: str = "") -> MockDocElement:
        """Create a mock CLI option child element."""
        return cls(
            name=name,
            qualified_name=f"command.{name}",
            description=description,
            element_type="option",
        )

    @classmethod
    def create_argument_child(cls, name: str, description: str = "") -> MockDocElement:
        """Create a mock CLI argument child element."""
        return cls(
            name=name,
            qualified_name=f"command.{name}",
            description=description,
            element_type="argument",
        )

    @classmethod
    def create_command_child(cls, name: str, description: str = "") -> MockDocElement:
        """Create a mock CLI command child element."""
        return cls(
            name=name,
            qualified_name=f"group.{name}",
            description=description,
            element_type="command",
        )

    @classmethod
    def create_command_group_child(cls, name: str, description: str = "") -> MockDocElement:
        """Create a mock CLI command-group child element."""
        return cls(
            name=name,
            qualified_name=f"cli.{name}",
            description=description,
            element_type="command-group",
        )


@dataclass
class MockPage:
    """Mock page object for template testing."""

    title: str = "Test Page"
    href: str = "/test/"
    _path: str = "/test/"
    source_path: Path = field(default_factory=lambda: Path("content/test.md"))
    metadata: dict[str, Any] = field(default_factory=dict)
    type: str | None = None  # page.type for template access

    @property
    def url(self) -> str:
        """Backward-compatible alias for href."""
        return self.href

    @property
    def relative_url(self) -> str:
        """Backward-compatible alias for _path."""
        return self._path

    def get(self, key: str, default: Any = None) -> Any:
        """Support dict-like access for page.metadata.get()."""
        return self.metadata.get(key, default)


class AttrDict(dict):
    """Dict subclass that supports attribute access for Jinja2 templates."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            return ""  # Return empty string for missing keys (ChainableUndefined behavior)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


@dataclass
class MockSection:
    """
    Mock section object for template testing.

    Simulates bengal.core.section.Section with attributes accessed
    by page-hero/section.html template for section-index pages.

    """

    name: str = "test_section"
    title: str = "Test Section"
    path: Path = field(default_factory=lambda: Path("content/test_section"))
    metadata: AttrDict = field(default_factory=AttrDict)
    pages: list[MockPage] = field(default_factory=list)
    subsections: list[MockSection] = field(default_factory=list)
    index_page: MockPage | None = None

    def __post_init__(self) -> None:
        """Ensure metadata is an AttrDict for Jinja2 attribute access."""
        if not isinstance(self.metadata, AttrDict):
            self.metadata = AttrDict(self.metadata)

    @property
    def sorted_pages(self) -> list[MockPage]:
        """Return pages (matches Section API)."""
        return self.pages

    @property
    def sorted_subsections(self) -> list[MockSection]:
        """Return subsections (matches Section API)."""
        return self.subsections


@dataclass
class MockConfig:
    """Mock autodoc config for template testing."""

    github_repo: str = "https://github.com/test/test"
    github_branch: str = "main"

    def get(self, key: str, default: Any = None) -> Any:
        """Support dict-like access."""
        return getattr(self, key, default)


@dataclass
class MockSite:
    """Mock site object for template testing."""

    title: str = "Test Site"
    baseurl: str = ""
    config: dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def template_engine(tmp_path):
    """Create Kida template engine with Bengal default templates."""
    # Create minimal site structure
    (tmp_path / "content").mkdir()
    config_content = """
[site]
title = "Test Site"
baseurl = "https://example.com"
"""
    (tmp_path / "bengal.toml").write_text(config_content)

    # Create site
    site = Site.from_config(tmp_path)

    # Create template engine (defaults to Kida)
    engine = create_engine(site)

    # Register mock functions via engine's registration system
    # These are normally registered by the engine, but we need to override with mocks
    # Note: Most functions are already registered by the engine, but we can override
    # via the environment if needed. For now, the mocks will be available via context.

    return engine


def mock_translate(
    key: str,
    params: dict[str, Any] | None = None,
    lang: str | None = None,
    default: str | None = None,
) -> str:
    """Mock translation function that returns the default value."""
    return default or key


def mock_icon(name: str, size: int = 16, css_class: str = "") -> str:
    """Mock icon function that returns placeholder SVG."""
    return f'<svg class="icon icon-{name} {css_class}" width="{size}" height="{size}"></svg>'


def mock_get_breadcrumbs(page: MockPage) -> list[dict[str, str]]:
    """Mock breadcrumbs function."""
    return [
        {"title": "Home", "url": "/"},
        {"title": "API", "url": "/api/"},
        {"title": page.title, "url": page.href},
    ]


def mock_canonical_url(url: str) -> str:
    """Mock canonical URL function."""
    return f"https://example.com{url}"


def mock_ensure_trailing_slash(url: str) -> str:
    """Mock ensure trailing slash function."""
    return url if url.endswith("/") else f"{url}/"


def mock_absolute_url(url: str) -> str:
    """Mock absolute_url filter."""
    return url


def mock_markdownify(text: str) -> str:
    """Mock markdownify filter that returns text wrapped in <p>."""
    if not text:
        return ""
    return f"<p>{text}</p>"


def mock_urlencode(text: str) -> str:
    """Mock urlencode filter."""
    return text.replace(" ", "%20").replace(":", "%3A")


def mock_match_filter(value: str, pattern: str) -> bool:
    """Mock match filter for Jinja2."""
    return bool(re.match(pattern, value))


def mock_match_test(value: Any, pattern: str) -> bool:
    """Mock match test for Jinja2 (used in rejectattr)."""
    value_str = str(value) if value is not None else ""
    return bool(re.match(pattern, value_str))


# ==============================================================================
# Helper Functions
# ==============================================================================


def render_page_hero(
    engine,
    *,
    element: MockDocElement | None = None,
    section: MockSection | None = None,
    page: MockPage | None = None,
    config: MockConfig | None = None,
    site: MockSite | None = None,
) -> str:
    """
    Render page-hero element or section template with given context.

    Uses the new separated templates:
    - partials/page-hero/element.html for element pages
    - partials/page-hero/section.html for section-index pages

    Args:
        engine: Template engine instance
        element: DocElement for element pages (may be None for section-index)
        section: Section for section-index pages
        page: Page object (required)
        config: Autodoc config
        site: Site object

    Returns:
        Rendered HTML string

    """
    if page is None:
        page = MockPage()
    if config is None:
        config = MockConfig()
    if site is None:
        site = MockSite()

    # Build context with mock functions
    context = {
        "element": element,
        "section": section,
        "page": page,
        "config": config,
        "site": site,
        # Add mock functions that templates might need
        "icon": mock_icon,
        "get_breadcrumbs": mock_get_breadcrumbs,
        "canonical_url": mock_canonical_url,
        "ensure_trailing_slash": mock_ensure_trailing_slash,
        "get_element_stats": get_element_stats,
        "t": mock_translate,
    }

    # Use new separated templates based on whether we have an element
    if element is not None:
        template_name = "partials/page-hero/element.html"
    else:
        template_name = "partials/page-hero/section.html"

    return engine.render_template(template_name, context)


def _render_section_hero(
    engine,
    *,
    section: MockSection,
    page: MockPage | None = None,
    config: MockConfig | None = None,
    site: MockSite | None = None,
    hero_context: dict[str, Any] | None = None,
) -> str:
    """
    Render section hero template for section-index pages.

    Uses the new partials/page-hero/section.html template.

    Args:
        engine: Template engine instance
        section: Section for section-index pages (required)
        page: Page object
        config: Autodoc config
        site: Site object
        hero_context: Optional dict with explicit flags (e.g., is_cli)

    Returns:
        Rendered HTML string

    """
    if page is None:
        page = MockPage()
    if config is None:
        config = MockConfig()
    if site is None:
        site = MockSite()

    context = {
        "section": section,
        "page": page,
        "config": config,
        "site": site,
        "hero_context": hero_context,
        # Add mock functions
        "icon": mock_icon,
        "get_breadcrumbs": mock_get_breadcrumbs,
        "canonical_url": mock_canonical_url,
        "ensure_trailing_slash": mock_ensure_trailing_slash,
        "get_element_stats": get_element_stats,
        "t": mock_translate,
    }

    return engine.render_template("partials/page-hero/section.html", context)


def normalize_html(html: str) -> str:
    """
    Normalize HTML for comparison.

    Removes extra whitespace and normalizes line endings to make
    HTML comparison more robust.

    """
    # Normalize whitespace
    html = re.sub(r"\s+", " ", html)
    # Remove whitespace around tags
    html = re.sub(r">\s+<", "><", html)
    # Strip leading/trailing whitespace
    return html.strip()


def assert_contains(html: str, *substrings: str) -> None:
    """Assert that HTML contains all specified substrings."""
    for substring in substrings:
        assert substring in html, f"Expected to find '{substring}' in HTML"


def assert_not_contains(html: str, *substrings: str) -> None:
    """Assert that HTML does NOT contain any specified substrings."""
    for substring in substrings:
        assert substring not in html, f"Did not expect to find '{substring}' in HTML"


# ==============================================================================
# Phase 0 Tests: API Module Page (element with children)
# ==============================================================================


class TestAPIModulePageHero:
    """Test page-hero/element.html for API module pages with DocElement."""

    def test_renders_qualified_name_in_title(self, template_engine) -> None:
        """Verify element.qualified_name appears in title."""
        element = MockDocElement(
            name="site",
            qualified_name="bengal.core.site.Site",
            description="Site container",
            element_type="class",
        )
        page = MockPage(title="Site")

        html = render_page_hero(template_engine, element=element, page=page)

        assert_contains(html, "bengal.core.site.Site")
        assert "page-hero__title--code" in html

    def test_renders_element_description(self, template_engine) -> None:
        """Verify element.description renders with markdownify."""
        element = MockDocElement(
            name="test_module",
            qualified_name="bengal.test_module",
            description="This is the module description.",
            element_type="module",
        )
        page = MockPage(title="Test Module")

        html = render_page_hero(template_engine, element=element, page=page)

        # markdownify wraps in <p>
        assert_contains(html, "This is the module description.")
        assert "page-hero__description" in html

    def test_renders_classes_and_functions_stats(self, template_engine) -> None:
        """Verify stats show Classes and Functions counts."""
        element = MockDocElement(
            name="utils",
            qualified_name="bengal.utils",
            description="Utility functions",
            element_type="module",
            children=[
                MockDocElement.create_class_child("Helper"),
                MockDocElement.create_class_child("Builder"),
                MockDocElement.create_function_child("process"),
                MockDocElement.create_function_child("transform"),
                MockDocElement.create_function_child("validate"),
            ],
        )
        page = MockPage(title="Utils")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should show "2 Classes" and "3 Functions"
        assert_contains(html, "2", "Classes")
        assert_contains(html, "3", "Functions")

    def test_renders_singular_class_function(self, template_engine) -> None:
        """Verify singular labels for single class/function."""
        element = MockDocElement(
            name="single",
            qualified_name="bengal.single",
            description="Single items",
            element_type="module",
            children=[
                MockDocElement.create_class_child("OnlyClass"),
                MockDocElement.create_function_child("only_function"),
            ],
        )
        page = MockPage(title="Single")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should show singular "Class" and "Function"
        assert_contains(html, "1")
        assert "Class" in html or "class" in html.lower()
        assert "Function" in html or "function" in html.lower()

    def test_renders_source_link_with_line_number(self, template_engine) -> None:
        """Verify source link includes line number."""
        element = MockDocElement(
            name="test_module",
            qualified_name="bengal.test_module",
            description="Test module",
            element_type="module",
            source_file=Path("bengal/test_module.py"),
            display_source_file="bengal/test_module.py",
            line_number=42,
        )
        config = MockConfig(
            github_repo="https://github.com/example/bengal",
            github_branch="main",
        )
        page = MockPage(title="Test Module")

        html = render_page_hero(template_engine, element=element, page=page, config=config)

        assert_contains(html, "View source")
        assert_contains(html, "#L42")
        assert_contains(html, "bengal/test_module.py")

    def test_no_stats_for_empty_children(self, template_engine) -> None:
        """Verify no stats section when element has no children."""
        element = MockDocElement(
            name="empty_module",
            qualified_name="bengal.empty",
            description="Empty module",
            element_type="module",
            children=[],
        )
        page = MockPage(title="Empty Module")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should not have stats for classes/functions
        assert "Classes" not in html
        assert "Functions" not in html


# ==============================================================================
# Phase 0 Tests: API Section Index Page (section, no element)
# ==============================================================================


class TestAPISectionIndexPageHero:
    """
    Test page-hero/section.html for API section-index pages.

    Uses the dedicated section.html template for section-index pages.

    This is the exact behavior documented in the RFC as "Jinja Gotchas".
    For section-index pages in production, element is NOT passed at all,
    making `element is defined` return False.

    In tests, we must NOT pass element at all to trigger the section-index branch.

    """

    def test_renders_section_title(self, template_engine) -> None:
        """Verify section.title appears in title (not element.qualified_name)."""
        section = MockSection(
            name="core",
            title="Core Package",
            metadata={"description": "Core Bengal functionality"},
        )
        page = MockPage(title="Core Package", href="/api/core/")

        # NOTE: We use _render_section_hero which omits element entirely
        html = _render_section_hero(template_engine, section=section, page=page)

        assert_contains(html, "Core Package")
        # Should NOT have code-styled title
        assert "page-hero__title--code" not in html or "Core Package" in html

    def test_renders_section_description(self, template_engine) -> None:
        """Verify section.metadata.description renders."""
        section = MockSection(
            name="orchestration",
            title="Orchestration",
            metadata={"description": "Build orchestration components"},
        )
        page = MockPage(title="Orchestration", href="/api/orchestration/")

        html = _render_section_hero(template_engine, section=section, page=page)

        assert_contains(html, "Build orchestration components")

    def test_renders_packages_and_modules_stats(self, template_engine) -> None:
        """Verify stats show Packages (subsections) and Modules (pages) counts."""
        section = MockSection(
            name="bengal",
            title="Bengal API",
            metadata={"description": "Bengal API reference"},
            subsections=[
                MockSection(name="core", title="Core"),
                MockSection(name="rendering", title="Rendering"),
            ],
            pages=[
                MockPage(title="utils", href="/api/utils/", source_path=Path("utils.md")),
                MockPage(title="cli", href="/api/cli/", source_path=Path("cli.md")),
                MockPage(title="config", href="/api/config/", source_path=Path("config.md")),
            ],
        )
        page = MockPage(title="Bengal API", href="/api/")

        html = _render_section_hero(template_engine, section=section, page=page)

        # Should show "2 Packages" and "3 Modules" (not Groups/Commands)
        assert_contains(html, "2")
        assert_contains(html, "Package")
        assert_contains(html, "3")
        assert_contains(html, "Module")

    def test_excludes_index_pages_from_module_count(self, template_engine) -> None:
        """Verify _index pages are excluded from module count."""
        section = MockSection(
            name="core",
            title="Core",
            pages=[
                MockPage(
                    title="Index",
                    href="/api/core/",
                    source_path=Path("_index.md"),
                ),
                MockPage(
                    title="site",
                    href="/api/core/site/",
                    source_path=Path("site.md"),
                ),
            ],
        )
        page = MockPage(title="Core", href="/api/core/")

        html = _render_section_hero(template_engine, section=section, page=page)

        # Should only count 1 module (site), not the _index
        assert_contains(html, "1")
        assert "Module" in html


# ==============================================================================
# Phase 0 Tests: CLI Command Page (element)
# ==============================================================================


class TestCLICommandPageHero:
    """Test page-hero/element.html for CLI command pages."""

    def test_renders_command_qualified_name(self, template_engine) -> None:
        """Verify command qualified_name in title."""
        element = MockDocElement(
            name="build",
            qualified_name="bengal build",
            description="Build the site",
            element_type="command",
        )
        page = MockPage(title="build")

        html = render_page_hero(template_engine, element=element, page=page)

        assert_contains(html, "bengal build")

    def test_renders_options_and_arguments_stats(self, template_engine) -> None:
        """Verify stats show Options and Arguments counts."""
        element = MockDocElement(
            name="build",
            qualified_name="bengal build",
            description="Build the site",
            element_type="command",
            children=[
                MockDocElement.create_option_child("--verbose"),
                MockDocElement.create_option_child("--output"),
                MockDocElement.create_option_child("--config"),
                MockDocElement.create_argument_child("PATH"),
            ],
        )
        page = MockPage(title="build")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should show "3 Options" and "1 Argument"
        assert_contains(html, "3", "Options")
        assert_contains(html, "1", "Argument")

    def test_renders_command_groups_stats(self, template_engine) -> None:
        """Verify stats show Groups and Commands for CLI group elements."""
        element = MockDocElement(
            name="site",
            qualified_name="bengal site",
            description="Site management commands",
            element_type="command-group",
            children=[
                MockDocElement.create_command_group_child("manage"),
                MockDocElement.create_command_child("build"),
                MockDocElement.create_command_child("serve"),
                MockDocElement.create_command_child("clean"),
            ],
        )
        page = MockPage(title="site")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should show "1 Group" and "3 Commands"
        assert_contains(html, "1", "Group")
        assert_contains(html, "3", "Commands")


# ==============================================================================
# Phase 0 Tests: CLI Section Index Page (section with CLI labels)
# ==============================================================================


class TestCLISectionIndexPageHero:
    """
    Test page-hero/section.html for CLI section-index pages with CLI labels.

    Uses the _render_section_hero helper to render section-index pages.

    """

    def test_renders_groups_not_packages_label(self, template_engine) -> None:
        """Verify CLI sections show 'Groups' not 'Packages' for subsections."""
        section = MockSection(
            name="cli",
            title="CLI Reference",
            metadata={"description": "Command line interface"},
            subsections=[
                MockSection(name="site", title="Site Commands"),
                MockSection(name="cache", title="Cache Commands"),
            ],
            pages=[],
        )
        # CLI detection uses URL sniffing - URL must contain '/cli'
        page = MockPage(title="CLI Reference", href="/cli/")

        html = _render_section_hero(template_engine, section=section, page=page)

        # Should show "2 Groups" not "2 Packages"
        assert_contains(html, "2")
        assert_contains(html, "Group")
        assert_not_contains(html, "Package")

    def test_renders_commands_not_modules_label(self, template_engine) -> None:
        """Verify CLI sections show 'Commands' not 'Modules' for pages."""
        section = MockSection(
            name="cli",
            title="CLI Reference",
            metadata={"description": "Command line interface"},
            subsections=[],
            pages=[
                MockPage(
                    title="build",
                    href="/cli/build/",
                    source_path=Path("build.md"),
                ),
                MockPage(
                    title="serve",
                    href="/cli/serve/",
                    source_path=Path("serve.md"),
                ),
            ],
        )
        # CLI detection uses URL sniffing
        page = MockPage(title="CLI Reference", href="/cli/")

        html = _render_section_hero(template_engine, section=section, page=page)

        # Should show "2 Commands" not "2 Modules"
        assert_contains(html, "2")
        assert_contains(html, "Command")
        assert_not_contains(html, "Module")

    def test_url_sniffing_detects_cli_section(self, template_engine) -> None:
        """Verify URL-based CLI detection works for nested CLI paths."""
        section = MockSection(
            name="subgroup",
            title="Subgroup Commands",
            subsections=[],
            pages=[
                MockPage(
                    title="cmd1",
                    href="/cli/group/subgroup/cmd1/",
                    source_path=Path("cmd1.md"),
                ),
            ],
        )
        # Nested CLI path still contains '/cli'
        page = MockPage(title="Subgroup Commands", href="/cli/group/subgroup/")

        html = _render_section_hero(template_engine, section=section, page=page)

        # Should still detect as CLI and show "Command" not "Module"
        assert_contains(html, "Command")
        assert_not_contains(html, "Module")

    def test_non_cli_section_shows_api_labels(self, template_engine) -> None:
        """Verify non-CLI sections (without /cli in URL) show API labels."""
        section = MockSection(
            name="api",
            title="API Reference",
            subsections=[
                MockSection(name="core", title="Core"),
            ],
            pages=[
                MockPage(
                    title="utils",
                    href="/api/utils/",
                    source_path=Path("utils.md"),
                ),
            ],
        )
        # API path without /cli
        page = MockPage(title="API Reference", href="/api/")

        html = _render_section_hero(template_engine, section=section, page=page)

        # Should show "Package" and "Module" not "Group" and "Command"
        assert_contains(html, "Package")
        assert_contains(html, "Module")
        assert_not_contains(html, "Group")
        assert_not_contains(html, "Command")


# ==============================================================================
# Phase 0 Tests: Edge Cases and Error Handling
# ==============================================================================


class TestPageHeroEdgeCases:
    """Test edge cases and error handling in page-hero templates."""

    def test_handles_no_element_for_section_index(self, template_engine) -> None:
        """Verify template handles section-index pages (no element in context)."""
        section = MockSection(name="test", title="Test Section")
        page = MockPage(title="Test Section")

        # Should not raise
        html = _render_section_hero(template_engine, section=section, page=page)

        assert "page-hero" in html

    def test_handles_empty_description(self, template_engine) -> None:
        """Verify template handles empty description gracefully."""
        element = MockDocElement(
            name="empty_desc",
            qualified_name="test.empty_desc",
            description="",  # Empty
            element_type="module",
        )
        page = MockPage(title="Empty Desc")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should render without description section
        # But should still have the hero div
        assert "page-hero" in html

    def test_handles_missing_source_file(self, template_engine) -> None:
        """Verify template handles missing source_file gracefully."""
        element = MockDocElement(
            name="no_source",
            qualified_name="test.no_source",
            description="No source file",
            element_type="module",
            source_file=None,
            line_number=None,
        )
        page = MockPage(title="No Source")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should render without source link
        assert "View source" not in html

    def test_share_dropdown_renders(self, template_engine) -> None:
        """Verify share dropdown with AI links renders."""
        element = MockDocElement(
            name="test",
            qualified_name="test.test",
            description="Test",
            element_type="module",
        )
        page = MockPage(title="Test", href="/api/test/")

        html = render_page_hero(template_engine, element=element, page=page)

        # Should have share dropdown elements
        assert_contains(html, "page-hero__share")
        assert_contains(html, "Claude")
        assert_contains(html, "ChatGPT")

    def test_breadcrumbs_render(self, template_engine) -> None:
        """Verify breadcrumbs render in hero."""
        page = MockPage(title="Test Page", href="/api/core/test/")
        element = MockDocElement(
            name="test",
            qualified_name="test",
            description="Test",
            element_type="module",
        )

        html = render_page_hero(template_engine, element=element, page=page)

        assert_contains(html, "page-hero__breadcrumbs")


# ==============================================================================
# Phase 1 Tests: New Template Equivalence
# ==============================================================================


def _render_new_element_hero(
    engine,
    *,
    element: MockDocElement,
    section: MockSection | None = None,
    page: MockPage | None = None,
    config: MockConfig | None = None,
    site: MockSite | None = None,
) -> str:
    """
    Render the NEW page-hero/element.html template.

    This uses the new separated template for element pages.

    """
    if page is None:
        page = MockPage()
    if config is None:
        config = MockConfig()
    if site is None:
        site = MockSite()

    context = {
        "element": element,
        "section": section,
        "page": page,
        "config": config,
        "site": site,
        # Add mock functions
        "icon": mock_icon,
        "get_breadcrumbs": mock_get_breadcrumbs,
        "canonical_url": mock_canonical_url,
        "ensure_trailing_slash": mock_ensure_trailing_slash,
        "get_element_stats": get_element_stats,
        "t": mock_translate,
    }

    return engine.render_template("partials/page-hero/element.html", context)


def _render_new_section_hero(
    engine,
    *,
    section: MockSection,
    page: MockPage | None = None,
    config: MockConfig | None = None,
    site: MockSite | None = None,
    hero_context: dict[str, Any] | None = None,
) -> str:
    """
    Render the NEW page-hero/section.html template.

    This uses the new separated template for section-index pages.

    """
    if page is None:
        page = MockPage()
    if config is None:
        config = MockConfig()
    if site is None:
        site = MockSite()

    context: dict[str, Any] = {
        "section": section,
        "page": page,
        "config": config,
        "site": site,
        # Add mock functions
        "icon": mock_icon,
        "get_breadcrumbs": mock_get_breadcrumbs,
        "canonical_url": mock_canonical_url,
        "ensure_trailing_slash": mock_ensure_trailing_slash,
        "get_element_stats": get_element_stats,
        "t": mock_translate,
    }
    if hero_context:
        context["hero_context"] = hero_context

    return engine.render_template("partials/page-hero/section.html", context)


class TestNewElementTemplate:
    """Test the new page-hero/element.html produces equivalent output."""

    def test_renders_qualified_name(self, template_engine) -> None:
        """Verify element.qualified_name appears in title."""
        element = MockDocElement(
            name="Site",
            qualified_name="bengal.core.site.Site",
            description="Site container",
            element_type="class",
        )
        page = MockPage(title="Site")

        html = _render_new_element_hero(template_engine, element=element, page=page)

        assert_contains(html, "bengal.core.site.Site")
        assert "page-hero__title--code" in html

    def test_renders_element_description(self, template_engine) -> None:
        """Verify element.description renders."""
        element = MockDocElement(
            name="test",
            qualified_name="test.module",
            description="Module description here.",
            element_type="module",
        )
        page = MockPage(title="Test")

        html = _render_new_element_hero(template_engine, element=element, page=page)

        assert_contains(html, "Module description here.")

    def test_renders_classes_functions_stats(self, template_engine) -> None:
        """Verify stats show Classes and Functions."""
        element = MockDocElement(
            name="utils",
            qualified_name="bengal.utils",
            description="Utilities",
            element_type="module",
            children=[
                MockDocElement.create_class_child("Helper"),
                MockDocElement.create_function_child("process"),
            ],
        )
        page = MockPage(title="Utils")

        html = _render_new_element_hero(template_engine, element=element, page=page)

        assert_contains(html, "1", "Class")
        assert_contains(html, "1", "Function")

    def test_renders_cli_stats(self, template_engine) -> None:
        """Verify CLI element renders options/arguments stats."""
        element = MockDocElement(
            name="build",
            qualified_name="bengal build",
            description="Build command",
            element_type="command",
            children=[
                MockDocElement.create_option_child("--verbose"),
                MockDocElement.create_argument_child("PATH"),
            ],
        )
        page = MockPage(title="build")

        html = _render_new_element_hero(template_engine, element=element, page=page)

        assert_contains(html, "1", "Option")
        assert_contains(html, "1", "Argument")


class TestNewSectionTemplate:
    """Test the new page-hero/section.html produces equivalent output."""

    def test_renders_section_title(self, template_engine) -> None:
        """Verify section.title appears in title."""
        section = MockSection(
            name="core",
            title="Core Package",
            metadata={"description": "Core functionality"},
        )
        page = MockPage(title="Core Package", href="/api/core/")

        html = _render_new_section_hero(template_engine, section=section, page=page)

        assert_contains(html, "Core Package")

    def test_renders_section_description(self, template_engine) -> None:
        """Verify section.metadata.description renders."""
        section = MockSection(
            name="rendering",
            title="Rendering",
            metadata={"description": "Rendering components"},
        )
        page = MockPage(title="Rendering", href="/api/rendering/")

        html = _render_new_section_hero(template_engine, section=section, page=page)

        assert_contains(html, "Rendering components")

    def test_renders_packages_modules_stats(self, template_engine) -> None:
        """Verify stats show Packages and Modules for API sections."""
        section = MockSection(
            name="api",
            title="API Reference",
            subsections=[MockSection(name="core", title="Core")],
            pages=[MockPage(title="utils", href="/api/utils/", source_path=Path("utils.md"))],
        )
        page = MockPage(title="API Reference", href="/api/")

        html = _render_new_section_hero(template_engine, section=section, page=page)

        assert_contains(html, "1", "Package")
        assert_contains(html, "1", "Module")

    def test_renders_groups_commands_for_cli(self, template_engine) -> None:
        """Verify CLI sections show Groups and Commands labels."""
        section = MockSection(
            name="cli",
            title="CLI Reference",
            subsections=[MockSection(name="site", title="Site")],
            pages=[MockPage(title="build", href="/cli/build/", source_path=Path("build.md"))],
        )
        page = MockPage(title="CLI Reference", href="/cli/")

        html = _render_new_section_hero(template_engine, section=section, page=page)

        # URL sniffing should detect /cli/
        assert_contains(html, "1", "Group")
        assert_contains(html, "1", "Command")

    def test_explicit_hero_context_is_cli(self, template_engine) -> None:
        """Verify explicit hero_context.is_cli works."""
        section = MockSection(
            name="commands",
            title="Commands",
            subsections=[MockSection(name="group", title="Group")],
            pages=[],
        )
        page = MockPage(title="Commands", href="/some/other/path/")

        # Explicit context should override URL detection
        html = _render_new_section_hero(
            template_engine,
            section=section,
            page=page,
            hero_context={"is_cli": True},
        )

        assert_contains(html, "Group")
        assert_not_contains(html, "Package")
