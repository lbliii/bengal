from __future__ import annotations

from pathlib import Path

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.pipeline.core import RenderingPipeline


def test_pipeline_can_skip_parse_to_ast_when_single_pass_tokens_enabled(monkeypatch):
    site = Site(
        root_path=Path("."),
        config={"markdown": {"parser": "mistune", "ast_cache": {"single_pass_tokens": True}}},
    )

    pipeline = RenderingPipeline(
        site, dependency_tracker=None, quiet=True, build_stats=None, build_context=None
    )

    # If the pipeline tries to use parse_to_ast, fail the test (the whole point is to skip it).
    if hasattr(pipeline.parser, "parse_to_ast"):
        monkeypatch.setattr(
            pipeline.parser,
            "parse_to_ast",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("parse_to_ast called")),
        )

    page = Page(
        source_path=Path("content/spike.md"),
        content="## Heading\n\n:::{note} Title\nBody\n:::\n",
        metadata={},
    )

    # Force only the parse step
    pipeline._parse_content(page)

    assert isinstance(page.parsed_ast, str) and page.parsed_ast
    assert isinstance(page._ast_cache, list) and page._ast_cache
