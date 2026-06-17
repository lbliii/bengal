"""Regression tests for directive AST JSON serialization (#558).

Bengal directive options must inherit from Patitas DirectiveOptions so
``patitas.to_dict`` emits JSON-safe option dicts. Parser metadata must store
``_source_path`` as a string, not ``Path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import patitas
import pytest
from patitas.directives.options import DirectiveOptions as PatitasDirectiveOptions

from bengal.core.records import parsed_page_from_page_state
from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator
from bengal.parsing.backends.patitas.wrapper import PatitasParser
from bengal.rendering.pipeline import RenderingPipeline
from bengal.utils.serialization import to_jsonable


class TestDirectiveOptionsInheritance:
    def test_bengal_admonition_options_are_patitas_options(self) -> None:
        from bengal.parsing.backends.patitas.directives.options import AdmonitionOptions

        opts = AdmonitionOptions()
        assert isinstance(opts, PatitasDirectiveOptions)


class TestDirectiveAstJsonSerialization:
    @pytest.fixture
    def parser(self) -> PatitasParser:
        return PatitasParser()

    def test_seealso_ast_is_json_serializable_after_toc_parse(self, parser: PatitasParser) -> None:
        content = """:::{seealso}
See also content.
:::
"""
        metadata = {"_source_path": str(Path("content/page.md"))}
        context: dict = {"config": {}}

        parser.parse_with_toc_and_context(content, metadata, context)
        doc = parser.consume_last_document()
        assert doc is not None

        ast_dict = patitas.to_dict(doc)
        options = ast_dict["children"][0]["options"]
        assert isinstance(options, dict)
        assert options.get("_type") == "DirectiveOptions"

        json.dumps(ast_dict)

    def test_admonition_directives_serialize_options_as_dicts(self, parser: PatitasParser) -> None:
        metadata = {"_source_path": str(Path("content/page.md"))}
        context: dict = {"config": {}}

        for directive in ("note", "seealso"):
            parser.parse_with_toc_and_context(
                f":::{{{directive}}}\nbody\n:::\n",
                metadata,
                context,
            )
            doc = parser.consume_last_document()
            assert doc is not None
            ast_dict = patitas.to_dict(doc)
            directive_nodes = [
                node for node in ast_dict.get("children", []) if node.get("_type") == "Directive"
            ]
            assert directive_nodes, directive
            options = directive_nodes[0]["options"]
            assert isinstance(options, dict), directive
            json.dumps(ast_dict)

    def test_literalinclude_ast_is_json_serializable_after_toc_parse(
        self, parser: PatitasParser
    ) -> None:
        content = """:::{literalinclude} examples/snippet.py
:::
"""
        metadata = {"_source_path": str(Path("content/page.md"))}
        context: dict = {"config": {}}

        parser.parse_with_toc_and_context(content, metadata, context)
        doc = parser.consume_last_document()
        assert doc is not None

        ast_dict = patitas.to_dict(doc)
        options = ast_dict["children"][0]["options"]
        assert isinstance(options, dict)
        assert options.get("_type") == "DirectiveOptions"
        assert options.get("file_path") == "examples/snippet.py"

        json.dumps(ast_dict)


class TestParserMetadataSourcePath:
    def test_parse_content_produces_seealso_html_with_string_metadata(self, tmp_path: Path) -> None:
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text(
            """---
title: Test
---

:::{seealso}
Links here.
:::
"""
        )

        site = Site(
            root_path=tmp_path,
            config={
                "title": "Test",
                "markdown_engine": "patitas",
                "markdown": {"ast_cache": {"persist_tokens": True}},
            },
            theme="default",
        )
        ContentOrchestrator(site).discover_content()
        page = site.pages[0]

        RenderingPipeline(site, quiet=True)._parse_content(page)

        parsed = parsed_page_from_page_state(page)
        assert parsed is not None
        assert "seealso" in (parsed.html_content or "")
        assert "markdown-error" not in (parsed.html_content or "")
        if parsed.ast_cache is not None:
            json.dumps(to_jsonable(parsed.ast_cache))
