"""
Unit tests for PageExplainer protocol compliance.

Verifies that PageExplainer only uses public methods from the TemplateEngine
protocol, not private implementation details.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

from bengal.debug import PageExplainer
from bengal.protocols.rendering import TemplateEngine


class TestExplainerProtocolCompliance:
    """PageExplainer must only use public TemplateEngine methods."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.theme = "default"
        site.pages = []
        return site

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create mock page for testing."""
        page = MagicMock()
        page.metadata = {"template": "custom.html"}
        page.source_path = Path("content/test.md")
        page.is_virtual = False
        page._source = "# Test\n\nContent here."
        page.core = MagicMock()
        page.core.type = "doc"
        page._section = None
        return page

    def test_uses_public_get_template_path(
        self,
        mock_site: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """Must use get_template_path(), not _find_template_path().

        This test verifies that PageExplainer uses the public protocol
        method `get_template_path` instead of the private implementation
        method `_find_template_path`.
        """
        # Create mock that ONLY has public protocol methods (spec=TemplateEngine)
        # This will raise AttributeError if private methods are accessed
        mock_engine = MagicMock(spec=TemplateEngine)
        mock_engine.get_template_path.return_value = None
        mock_engine.template_dirs = []

        explainer = PageExplainer(
            site=mock_site,
            template_engine=mock_engine,
        )

        # This should work using public method
        explainer._resolve_template_chain(mock_page)

        # Verify public method was called
        mock_engine.get_template_path.assert_called_with("custom.html")

    def test_template_chain_resolution_uses_protocol(
        self,
        mock_site: MagicMock,
        mock_page: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Template chain resolution should work with any TemplateEngine implementation."""
        # Create template files
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        custom_template = template_dir / "custom.html"
        custom_template.write_text(
            '{% extends "base.html" %}\n{% block content %}...{% endblock %}'
        )

        base_template = template_dir / "base.html"
        base_template.write_text("<!DOCTYPE html>\n<html>{% block content %}{% endblock %}</html>")

        # Create mock engine with realistic behavior
        mock_engine = MagicMock(spec=TemplateEngine)
        mock_engine.template_dirs = [template_dir]

        def get_path(name: str) -> Path | None:
            path = template_dir / name
            return path if path.exists() else None

        mock_engine.get_template_path.side_effect = get_path

        explainer = PageExplainer(
            site=mock_site,
            template_engine=mock_engine,
        )

        chain = explainer._resolve_template_chain(mock_page)

        # Should resolve the chain through extends
        assert len(chain) >= 1
        assert chain[0].name == "custom.html"

        # If chain is fully resolved, should include base.html
        if len(chain) > 1:
            assert chain[1].name == "base.html"

    def test_diagnose_issues_uses_public_method(
        self,
        mock_site: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """_diagnose_issues must use get_template_path for template checking."""
        mock_engine = MagicMock(spec=TemplateEngine)
        mock_engine.get_template_path.return_value = None  # Template not found
        mock_engine.template_dirs = [Path("/templates")]

        explainer = PageExplainer(
            site=mock_site,
            template_engine=mock_engine,
        )

        issues = explainer._diagnose_issues(mock_page)

        # Should have called get_template_path to check if template exists
        mock_engine.get_template_path.assert_called()

        # Should report template not found
        template_issues = [i for i in issues if i.issue_type == "template_not_found"]
        assert len(template_issues) == 1

    def test_no_private_method_access(
        self,
        mock_site: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """Ensure no private methods are accessed on template engine.

        This test uses spec=TemplateEngine which will raise AttributeError
        if any method not in the protocol is accessed.
        """
        mock_engine = MagicMock(spec=TemplateEngine)
        mock_engine.get_template_path.return_value = None
        mock_engine.template_dirs = []

        explainer = PageExplainer(
            site=mock_site,
            template_engine=mock_engine,
        )

        # These operations should not access any private methods
        try:
            explainer._resolve_template_chain(mock_page)
            explainer._diagnose_issues(mock_page)
        except AttributeError as e:
            pytest.fail(f"Accessed non-protocol method on TemplateEngine: {e}")


class TestExplainerTemplateChainExtraction:
    """Test template chain extraction from files."""

    @pytest.fixture
    def explainer(self) -> PageExplainer:
        """Create explainer with mock site."""
        site = MagicMock()
        site.root_path = Path("/test")
        site.theme = "default"
        return PageExplainer(site)

    def test_extract_extends_single_quotes(self, explainer: PageExplainer) -> None:
        """Should extract extends with single quotes."""
        content = "{% extends 'base.html' %}"
        result = explainer._extract_extends(content)
        assert result == "base.html"

    def test_extract_extends_double_quotes(self, explainer: PageExplainer) -> None:
        """Should extract extends with double quotes."""
        content = '{% extends "layouts/page.html" %}'
        result = explainer._extract_extends(content)
        assert result == "layouts/page.html"

    def test_extract_extends_with_whitespace(self, explainer: PageExplainer) -> None:
        """Should handle whitespace variations."""
        content = '{%   extends   "base.html"   %}'
        result = explainer._extract_extends(content)
        assert result == "base.html"

    def test_extract_includes_multiple(self, explainer: PageExplainer) -> None:
        """Should extract all includes."""
        content = """
{% include "header.html" %}
<main>Content</main>
{% include 'sidebar.html' %}
{% include "footer.html" %}
"""
        result = explainer._extract_includes(content)

        assert len(result) == 3
        assert "header.html" in result
        assert "sidebar.html" in result
        assert "footer.html" in result


class TestExplainerWithoutTemplateEngine:
    """Test PageExplainer behavior when no template engine is provided."""

    def test_graceful_fallback_without_engine(self) -> None:
        """Should provide basic info even without template engine."""
        site = MagicMock()
        site.root_path = Path("/test")
        site.theme = "default"
        site.pages = []

        mock_page = MagicMock()
        mock_page.metadata = {"type": "post"}
        mock_page.source_path = Path("content/post.md")
        mock_page.is_virtual = False
        mock_page._source = "# Post"
        mock_page.core = MagicMock()
        mock_page.core.type = "post"

        # No template_engine provided
        explainer = PageExplainer(site, template_engine=None)

        chain = explainer._resolve_template_chain(mock_page)

        # Should return basic info without full chain resolution
        assert len(chain) == 1
        assert chain[0].name == "post.html"  # Inferred from type
        assert chain[0].source_path is None  # Can't resolve without engine
