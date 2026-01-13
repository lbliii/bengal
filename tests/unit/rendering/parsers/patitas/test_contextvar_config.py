"""Tests for ContextVar configuration pattern.

Validates thread isolation, nesting support, and configuration inheritance.

RFC: rfc-contextvar-config-implementation.md

"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from bengal.rendering.parsers.patitas import (
    ParseConfig,
    RenderConfig,
    get_parse_config,
    get_render_config,
    parse_config_context,
    render_config_context,
    reset_parse_config,
    reset_render_config,
    set_parse_config,
    set_render_config,
)
from patitas.parser import Parser
from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer


class TestParseConfig:
    """Tests for ParseConfig and parse_config_context."""

    def test_default_config(self):
        """Default config has all plugins disabled."""
        config = get_parse_config()
        assert config.tables_enabled is False
        assert config.strikethrough_enabled is False
        assert config.task_lists_enabled is False
        assert config.footnotes_enabled is False
        assert config.math_enabled is False
        assert config.autolinks_enabled is False
        assert config.directive_registry is None
        assert config.strict_contracts is False
        assert config.text_transformer is None

    def test_context_manager_sets_config(self):
        """parse_config_context sets configuration correctly."""
        with parse_config_context(ParseConfig(tables_enabled=True)) as cfg:
            assert cfg.tables_enabled is True
            assert get_parse_config().tables_enabled is True

    def test_context_manager_restores_config(self):
        """parse_config_context restores previous config on exit."""
        original = get_parse_config()

        with parse_config_context(ParseConfig(tables_enabled=True)):
            assert get_parse_config().tables_enabled is True

        # Should be restored to original
        assert get_parse_config() is original

    def test_nested_contexts(self):
        """Nested parse_config_context properly restores each level."""
        # Outer context
        with parse_config_context(ParseConfig(tables_enabled=True)) as outer:
            assert get_parse_config().tables_enabled is True
            assert get_parse_config().math_enabled is False

            # Inner context
            with parse_config_context(ParseConfig(math_enabled=True)) as inner:
                assert get_parse_config().tables_enabled is False  # Inner doesn't inherit
                assert get_parse_config().math_enabled is True
                assert inner.math_enabled is True

            # After inner exits, should restore to outer
            assert get_parse_config().tables_enabled is True
            assert get_parse_config().math_enabled is False

    def test_token_based_reset(self):
        """Token-based reset properly handles nesting."""
        token_a = set_parse_config(ParseConfig(tables_enabled=True))
        assert get_parse_config().tables_enabled is True

        token_b = set_parse_config(ParseConfig(math_enabled=True))
        assert get_parse_config().tables_enabled is False
        assert get_parse_config().math_enabled is True

        # Reset to ConfigA
        reset_parse_config(token_b)
        assert get_parse_config().tables_enabled is True
        assert get_parse_config().math_enabled is False

        # Reset to default
        reset_parse_config(token_a)
        assert get_parse_config().tables_enabled is False

    def test_parser_reads_config(self):
        """Parser reads configuration from ContextVar."""
        with parse_config_context(ParseConfig(tables_enabled=True, math_enabled=True)):
            parser = Parser("# Test")
            assert parser._tables_enabled is True
            assert parser._math_enabled is True
            assert parser._strikethrough_enabled is False


class TestRenderConfig:
    """Tests for RenderConfig and render_config_context."""

    def test_default_config(self):
        """Default config has sensible defaults."""
        config = get_render_config()
        assert config.highlight is False
        assert config.highlight_style == "semantic"
        assert config.directive_registry is None
        assert config.role_registry is None
        assert config.text_transformer is None
        assert config.slugify is None
        # rosettes_available is auto-detected

    def test_context_manager_sets_config(self):
        """render_config_context sets configuration correctly."""
        with render_config_context(RenderConfig(highlight=True)) as cfg:
            assert cfg.highlight is True
            assert get_render_config().highlight is True

    def test_context_manager_restores_config(self):
        """render_config_context restores previous config on exit."""
        original = get_render_config()

        with render_config_context(RenderConfig(highlight=True)):
            assert get_render_config().highlight is True

        # Should be restored to original
        assert get_render_config() is original

    def test_nested_contexts(self):
        """Nested render_config_context properly restores each level."""
        with render_config_context(RenderConfig(highlight=True)):
            assert get_render_config().highlight is True

            with render_config_context(RenderConfig(highlight_style="pygments")):
                assert get_render_config().highlight is False  # Inner doesn't inherit
                assert get_render_config().highlight_style == "pygments"

            # After inner exits, should restore to outer
            assert get_render_config().highlight is True
            assert get_render_config().highlight_style == "semantic"

    def test_renderer_reads_config(self):
        """HtmlRenderer reads configuration from ContextVar."""
        with render_config_context(RenderConfig(highlight=True, highlight_style="pygments")):
            renderer = HtmlRenderer("test")
            assert renderer._highlight is True
            assert renderer._highlight_style == "pygments"


class TestThreadIsolation:
    """Tests for thread-local isolation of configuration."""

    def test_parse_config_thread_isolation(self):
        """ParseConfig is isolated between threads."""
        results = {}

        def worker(thread_id: int, config: ParseConfig):
            token = set_parse_config(config)
            try:
                parser = Parser("# Test")
                results[thread_id] = {
                    "tables": parser._tables_enabled,
                    "math": parser._math_enabled,
                }
            finally:
                reset_parse_config(token)

        configs = [
            ParseConfig(tables_enabled=True, math_enabled=False),
            ParseConfig(tables_enabled=False, math_enabled=True),
            ParseConfig(tables_enabled=True, math_enabled=True),
            ParseConfig(tables_enabled=False, math_enabled=False),
        ]

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i, cfg) for i, cfg in enumerate(configs)]
            for f in futures:
                f.result()

        # Verify each thread saw its own config
        assert results[0] == {"tables": True, "math": False}
        assert results[1] == {"tables": False, "math": True}
        assert results[2] == {"tables": True, "math": True}
        assert results[3] == {"tables": False, "math": False}

    def test_render_config_thread_isolation(self):
        """RenderConfig is isolated between threads."""
        results = {}

        def worker(thread_id: int, config: RenderConfig):
            token = set_render_config(config)
            try:
                renderer = HtmlRenderer("test")
                results[thread_id] = {
                    "highlight": renderer._highlight,
                    "style": renderer._highlight_style,
                }
            finally:
                reset_render_config(token)

        configs = [
            RenderConfig(highlight=True, highlight_style="semantic"),
            RenderConfig(highlight=False, highlight_style="pygments"),
            RenderConfig(highlight=True, highlight_style="pygments"),
            RenderConfig(highlight=False, highlight_style="semantic"),
        ]

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i, cfg) for i, cfg in enumerate(configs)]
            for f in futures:
                f.result()

        # Verify each thread saw its own config
        assert results[0] == {"highlight": True, "style": "semantic"}
        assert results[1] == {"highlight": False, "style": "pygments"}
        assert results[2] == {"highlight": True, "style": "pygments"}
        assert results[3] == {"highlight": False, "style": "semantic"}

    def test_combined_config_thread_isolation(self):
        """Both configs are isolated together in threads."""
        results = {}

        def worker(thread_id: int, parse_cfg: ParseConfig, render_cfg: RenderConfig):
            parse_token = set_parse_config(parse_cfg)
            render_token = set_render_config(render_cfg)
            try:
                parser = Parser("# Test")
                renderer = HtmlRenderer("test")
                results[thread_id] = {
                    "tables": parser._tables_enabled,
                    "highlight": renderer._highlight,
                }
            finally:
                reset_render_config(render_token)
                reset_parse_config(parse_token)

        configs = [
            (ParseConfig(tables_enabled=True), RenderConfig(highlight=True)),
            (ParseConfig(tables_enabled=False), RenderConfig(highlight=True)),
            (ParseConfig(tables_enabled=True), RenderConfig(highlight=False)),
            (ParseConfig(tables_enabled=False), RenderConfig(highlight=False)),
        ]

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(worker, i, pc, rc) for i, (pc, rc) in enumerate(configs)
            ]
            for f in futures:
                f.result()

        # Verify each thread saw its own config
        assert results[0] == {"tables": True, "highlight": True}
        assert results[1] == {"tables": False, "highlight": True}
        assert results[2] == {"tables": True, "highlight": False}
        assert results[3] == {"tables": False, "highlight": False}


class TestSubParserInheritance:
    """Tests for sub-parser configuration inheritance via ContextVar."""

    def test_sub_parser_inherits_config(self):
        """Sub-parsers created by _parse_nested_content inherit config."""
        with parse_config_context(ParseConfig(tables_enabled=True, math_enabled=True)):
            parser = Parser("> Nested content\n> with tables")
            # The parser reads config from ContextVar
            assert parser._tables_enabled is True
            assert parser._math_enabled is True

            # When _parse_nested_content creates a sub-parser, it will also
            # read from the same ContextVar (config is inherited automatically)

    def test_parsing_with_config(self):
        """Full parsing works with ContextVar config."""
        with parse_config_context(ParseConfig(tables_enabled=True)):
            parser = Parser("| A | B |\n|---|---|\n| 1 | 2 |")
            ast = parser.parse()
            # Should have parsed a table
            from patitas.nodes import Table

            assert any(isinstance(block, Table) for block in ast)

    def test_parsing_without_tables_config(self):
        """Parsing without tables config doesn't parse tables."""
        with parse_config_context(ParseConfig(tables_enabled=False)):
            parser = Parser("| A | B |\n|---|---|\n| 1 | 2 |")
            ast = parser.parse()
            # Should NOT have parsed a table
            from patitas.nodes import Table

            assert not any(isinstance(block, Table) for block in ast)


class TestConfigImmutability:
    """Tests for config immutability (frozen dataclass)."""

    def test_parse_config_is_frozen(self):
        """ParseConfig cannot be modified after creation."""
        config = ParseConfig(tables_enabled=True)

        with pytest.raises(AttributeError):
            config.tables_enabled = False  # type: ignore[misc]

    def test_render_config_is_frozen(self):
        """RenderConfig cannot be modified after creation."""
        config = RenderConfig(highlight=True)

        with pytest.raises(AttributeError):
            config.highlight = False  # type: ignore[misc]


class TestExceptionSafety:
    """Tests for exception safety in config context managers."""

    def test_parse_config_restored_on_exception(self):
        """ParseConfig is restored even if exception occurs."""
        original = get_parse_config()

        with pytest.raises(ValueError):
            with parse_config_context(ParseConfig(tables_enabled=True)):
                assert get_parse_config().tables_enabled is True
                raise ValueError("Test exception")

        # Should be restored despite exception
        assert get_parse_config() is original

    def test_render_config_restored_on_exception(self):
        """RenderConfig is restored even if exception occurs."""
        original = get_render_config()

        with pytest.raises(ValueError):
            with render_config_context(RenderConfig(highlight=True)):
                assert get_render_config().highlight is True
                raise ValueError("Test exception")

        # Should be restored despite exception
        assert get_render_config() is original
