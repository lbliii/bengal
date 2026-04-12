"""
Tests for directive template rendering path.

Covers:
- _try_template_render() in DirectiveRendererMixin
- get_template_context() on AdmonitionDirective
- Template override via site._directive_template_renderer
- Fallback to handler.render() when no template exists
- Caching integration with template-rendered directives
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from bengal.parsing.backends.patitas.directives.builtins.admonition import (
    AdmonitionDirective,
)


class TestAdmonitionTemplateContext:
    """Tests for AdmonitionDirective.get_template_context()."""

    def _make_node(self, name: str = "note", title: str | None = None, class_: str = "") -> Any:
        """Create a fake admonition directive node."""
        from bengal.parsing.backends.patitas.directives.options import AdmonitionOptions

        opts = AdmonitionOptions(class_=class_)
        node = MagicMock()
        node.name = name
        node.title = title
        node.options = opts
        return node

    def test_returns_dict(self):
        handler = AdmonitionDirective()
        node = self._make_node()
        ctx = handler.get_template_context(node, "<p>content</p>")
        assert isinstance(ctx, dict)

    def test_context_keys(self):
        handler = AdmonitionDirective()
        node = self._make_node()
        ctx = handler.get_template_context(node, "<p>content</p>")
        assert set(ctx.keys()) == {
            "name",
            "title",
            "css_class",
            "icon_name",
            "icon_html",
            "extra_class",
            "children",
        }

    def test_note_defaults(self):
        handler = AdmonitionDirective()
        node = self._make_node(name="note")
        ctx = handler.get_template_context(node, "<p>hi</p>")
        assert ctx["name"] == "note"
        assert ctx["title"] == "Note"
        assert ctx["css_class"] == "note"
        assert ctx["icon_name"] == "note"
        assert ctx["children"] == "<p>hi</p>"

    def test_custom_title(self):
        handler = AdmonitionDirective()
        node = self._make_node(name="warning", title="Watch Out!")
        ctx = handler.get_template_context(node, "")
        assert ctx["title"] == "Watch Out!"
        assert ctx["css_class"] == "warning"

    def test_caution_maps_to_warning_css(self):
        handler = AdmonitionDirective()
        node = self._make_node(name="caution")
        ctx = handler.get_template_context(node, "")
        assert ctx["css_class"] == "warning"

    def test_extra_class(self):
        handler = AdmonitionDirective()
        node = self._make_node(name="tip", class_="custom-highlight")
        ctx = handler.get_template_context(node, "")
        assert ctx["css_class"] == "tip custom-highlight"
        assert ctx["extra_class"] == "custom-highlight"

    def test_kwargs_ignored(self):
        """Extra kwargs (page_context, site, etc.) don't break get_template_context."""
        handler = AdmonitionDirective()
        node = self._make_node()
        ctx = handler.get_template_context(node, "<p>x</p>", page_context="fake", site="fake")
        assert ctx["children"] == "<p>x</p>"


class TestDirectiveTemplateRendering:
    """Integration tests for the template rendering path in _render_directive()."""

    def _make_site_with_renderer(self, templates: dict[str, str] | None = None) -> MagicMock:
        """Create a mock site with a _directive_template_renderer.

        Args:
            templates: Map of directive name -> rendered HTML.
                       None means renderer returns None (no template found).
        """
        site = MagicMock()
        if templates is None:
            site._directive_template_renderer = None
            return site

        def renderer(name: str, context: dict[str, Any]) -> str | None:
            return templates.get(name)

        site._directive_template_renderer = renderer
        return site

    def test_template_override_used(self):
        """When a template exists, its output replaces handler.render()."""
        from bengal.parsing.backends.patitas.wrapper import PatitasParser

        parser = PatitasParser(enable_highlighting=False)

        # Render a note without template override
        html_default = parser.parse(":::{note}\nHello\n:::", {})
        assert "admonition" in html_default

        # Verify get_template_context exists on the handler
        handler = AdmonitionDirective()
        assert hasattr(handler, "get_template_context")

    def test_render_produces_same_output_as_handler(self):
        """get_template_context + render() should produce equivalent HTML."""
        from patitas.stringbuilder import StringBuilder

        handler = AdmonitionDirective()
        node = MagicMock()
        node.name = "note"
        node.title = "My Note"

        from bengal.parsing.backends.patitas.directives.options import AdmonitionOptions

        node.options = AdmonitionOptions(class_="")

        # Get context
        ctx = handler.get_template_context(node, "<p>body</p>")

        # Render via handler
        sb = StringBuilder()
        handler.render(node, "<p>body</p>", sb)
        handler_html = sb.build()

        # Verify context has the right values to reconstruct
        assert ctx["title"] == "My Note"
        assert ctx["css_class"] == "note"
        assert ctx["children"] == "<p>body</p>"

        # The handler output should contain the same structural elements
        assert 'class="admonition note"' in handler_html
        assert "My Note" in handler_html
        assert "<p>body</p>" in handler_html

    def test_try_template_render_returns_none_without_get_template_context(self):
        """Handlers without get_template_context skip template path."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()

        # Handler without get_template_context
        handler = MagicMock(spec=["render"])
        node = MagicMock()
        node.name = "fake"

        result = mixin._try_template_render(node, "", handler, {})
        assert result is None

    def test_try_template_render_returns_none_without_site(self):
        """When site is None, template path is skipped."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()
        # No _site attribute
        handler = MagicMock()
        handler.get_template_context.return_value = {"key": "value"}

        result = mixin._try_template_render(MagicMock(), "", handler, {})
        assert result is None

    def test_try_template_render_returns_none_without_renderer(self):
        """When site has no _directive_template_renderer, template path is skipped."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()
        mixin._site = MagicMock(spec=[])  # type: ignore[attr-defined]  # No _directive_template_renderer

        handler = MagicMock()
        handler.get_template_context.return_value = {"key": "value"}

        result = mixin._try_template_render(MagicMock(), "", handler, {})
        assert result is None

    def test_try_template_render_calls_renderer(self):
        """When all conditions met, renderer is called with correct args."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()
        site = MagicMock()
        site._directive_template_renderer = MagicMock(return_value="<div>custom</div>")
        mixin._site = site  # type: ignore[attr-defined]

        handler = MagicMock()
        ctx = {"title": "Note", "children": "<p>hi</p>"}
        handler.get_template_context.return_value = ctx

        node = MagicMock()
        node.name = "note"

        result = mixin._try_template_render(node, "<p>hi</p>", handler, {})
        assert result == "<div>custom</div>"
        site._directive_template_renderer.assert_called_once_with("note", ctx)

    def test_try_template_render_passes_kwargs(self):
        """kwargs (page_context, site, etc.) are forwarded to get_template_context."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()
        site = MagicMock()
        site._directive_template_renderer = MagicMock(return_value="<div>ok</div>")
        mixin._site = site  # type: ignore[attr-defined]

        handler = MagicMock()
        handler.get_template_context.return_value = {"key": "val"}

        node = MagicMock()
        node.name = "test"
        kwargs = {"page_context": "page", "xref_index": {}}

        mixin._try_template_render(node, "children", handler, kwargs)
        handler.get_template_context.assert_called_once_with(
            node, "children", page_context="page", xref_index={}
        )

    def test_try_template_render_none_context_skips(self):
        """If get_template_context returns None, fall back."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()
        site = MagicMock()
        site._directive_template_renderer = MagicMock()
        mixin._site = site  # type: ignore[attr-defined]

        handler = MagicMock()
        handler.get_template_context.return_value = None

        result = mixin._try_template_render(MagicMock(), "", handler, {})
        assert result is None
        site._directive_template_renderer.assert_not_called()

    def test_try_template_render_renderer_returns_none(self):
        """If renderer returns None (template not found), fall back."""
        from bengal.parsing.backends.patitas.renderers.directives import (
            DirectiveRendererMixin,
        )

        mixin = DirectiveRendererMixin()
        site = MagicMock()
        site._directive_template_renderer = MagicMock(return_value=None)
        mixin._site = site  # type: ignore[attr-defined]

        handler = MagicMock()
        handler.get_template_context.return_value = {"key": "val"}

        node = MagicMock()
        node.name = "test"

        result = mixin._try_template_render(node, "", handler, {})
        assert result is None


class TestEndToEndTemplateOverride:
    """End-to-end test: Kida template override replaces handler.render() output."""

    def test_template_override_replaces_handler_output(self, tmp_path):
        """A custom directive template produces different HTML than the handler."""

        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.parsing.backends.patitas.directives.builtins.admonition import (
            AdmonitionDirective,
        )
        from bengal.parsing.backends.patitas.directives.registry import (
            DirectiveRegistryBuilder,
        )
        from bengal.parsing.backends.patitas.render_config import (
            RenderConfig,
            render_config_context,
        )
        from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer

        # Create a custom admonition template
        directives_dir = tmp_path / "directives"
        directives_dir.mkdir()
        (directives_dir / "note.html").write_text(
            '<aside class="themed-note" data-type="{{ name }}">'
            "<strong>{{ title|e }}</strong>"
            "{{ children|safe }}"
            "</aside>\n"
        )

        env = Environment(loader=FileSystemLoader([str(tmp_path)]))

        def renderer(name: str, context: dict[str, Any]) -> str | None:
            try:
                template = env.get_template(f"directives/{name}.html")
            except Exception:
                return None
            return template.render(context)

        # Build a registry with the admonition handler
        builder = DirectiveRegistryBuilder()
        builder.register(AdmonitionDirective())
        registry = builder.build()

        # Create a mock site with the template renderer
        site = MagicMock()
        site._directive_template_renderer = renderer

        # Parse markdown with a note directive
        source = ":::{note} Important\nSome content here.\n:::\n"

        from bengal.parsing.backends.patitas import Markdown

        md = Markdown(plugins=[], highlight=False, highlight_style="semantic")

        # Override the registry to use our built registry
        config = RenderConfig(
            highlight=False,
            highlight_style="semantic",
            directive_registry=registry,
        )

        with render_config_context(config):
            ast = md._parse_to_ast(source)
            html_renderer = HtmlRenderer(source, site=site)
            html = html_renderer.render(ast)

        # The themed template should have been used
        assert "themed-note" in html
        assert 'data-type="note"' in html
        assert "<strong>Important</strong>" in html
        assert "Some content here." in html
        # The default handler output should NOT be present
        assert 'class="admonition note"' not in html

    def test_fallback_when_no_template(self, tmp_path):
        """Without a template, handler.render() output is used."""
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.parsing.backends.patitas.directives.builtins.admonition import (
            AdmonitionDirective,
        )
        from bengal.parsing.backends.patitas.directives.registry import (
            DirectiveRegistryBuilder,
        )
        from bengal.parsing.backends.patitas.render_config import (
            RenderConfig,
            render_config_context,
        )
        from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer

        # Empty template directory — no directive overrides
        env = Environment(loader=FileSystemLoader([str(tmp_path)]))

        def renderer(name: str, context: dict[str, Any]) -> str | None:
            try:
                template = env.get_template(f"directives/{name}.html")
            except Exception:
                return None
            return template.render(context)

        builder = DirectiveRegistryBuilder()
        builder.register(AdmonitionDirective())
        registry = builder.build()

        site = MagicMock()
        site._directive_template_renderer = renderer

        source = ":::{note} Fallback Test\nContent.\n:::\n"

        from bengal.parsing.backends.patitas import Markdown

        md = Markdown(plugins=[], highlight=False, highlight_style="semantic")
        config = RenderConfig(
            highlight=False,
            highlight_style="semantic",
            directive_registry=registry,
        )

        with render_config_context(config):
            ast = md._parse_to_ast(source)
            html_renderer = HtmlRenderer(source, site=site)
            html = html_renderer.render(ast)

        # Default handler output should be present
        assert 'class="admonition note"' in html
        assert "Fallback Test" in html


class TestKidaDirectiveTemplateRenderer:
    """Tests for KidaTemplateEngine._create_directive_template_renderer()."""

    @pytest.fixture
    def tmp_site(self, tmp_path):
        """Create a minimal mock site with template dirs."""
        site = MagicMock()
        site.root_path = tmp_path
        site.config = {"development": {"auto_reload": False}}
        site.theme = MagicMock()
        site.theme.name = "default"
        return site

    def test_renderer_returns_none_for_missing_template(self, tmp_path):
        """Renderer returns None when template doesn't exist."""
        from kida import Environment
        from kida.environment import FileSystemLoader

        env = Environment(loader=FileSystemLoader([str(tmp_path)]))

        def renderer(name: str, context: dict[str, Any]) -> str | None:
            try:
                template = env.get_template(f"directives/{name}.html")
            except Exception:
                return None
            return template.render(context)

        assert renderer("nonexistent", {}) is None

    def test_renderer_renders_template(self, tmp_path):
        """Renderer renders a directive template when it exists."""
        from kida import Environment
        from kida.environment import FileSystemLoader

        # Create a directive template
        directives_dir = tmp_path / "directives"
        directives_dir.mkdir()
        (directives_dir / "note.html").write_text(
            '<div class="custom-note">{{ title }}: {{ children|safe }}</div>'
        )

        env = Environment(loader=FileSystemLoader([str(tmp_path)]))

        def renderer(name: str, context: dict[str, Any]) -> str | None:
            try:
                template = env.get_template(f"directives/{name}.html")
            except Exception:
                return None
            return template.render(context)

        result = renderer("note", {"title": "Note", "children": "<p>hi</p>"})
        assert result == '<div class="custom-note">Note: <p>hi</p></div>'

    def test_renderer_returns_none_for_other_directives(self, tmp_path):
        """Only directives with templates are overridden."""
        from kida import Environment
        from kida.environment import FileSystemLoader

        directives_dir = tmp_path / "directives"
        directives_dir.mkdir()
        (directives_dir / "note.html").write_text("<div>{{ title }}</div>")

        env = Environment(loader=FileSystemLoader([str(tmp_path)]))

        def renderer(name: str, context: dict[str, Any]) -> str | None:
            try:
                template = env.get_template(f"directives/{name}.html")
            except Exception:
                return None
            return template.render(context)

        assert renderer("note", {"title": "Note"}) is not None
        assert renderer("warning", {"title": "Warning"}) is None
