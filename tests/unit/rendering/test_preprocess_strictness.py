from unittest.mock import MagicMock

import pytest

from bengal.rendering.pipeline.core import RenderingPipeline


def test_preprocess_strictness_disabled():
    """Verify that preprocessing uses strict=False to allow doc examples."""
    site = MagicMock()
    site.config = {"template_engine": "kida"}

    # Mock engine
    engine = MagicMock()
    pipeline = RenderingPipeline(site)
    pipeline.template_engine = engine

    page = MagicMock()
    page.content = "Example: {{ undefined_var }}"
    page.source_path = "test.md"

    # Trigger pre-processing
    pipeline._preprocess_content(page)

    # Verify render_string was called with strict=False
    args, kwargs = engine.render_string.call_args
    assert kwargs["strict"] is False
    assert args[0] == page.content


def test_preprocess_syntax_error_reporting():
    """Verify that actual syntax errors are still reported during preprocessing."""
    from bengal.rendering.engines.kida import KidaTemplateEngine

    site = MagicMock()
    site.config = {}
    site.root_path = MagicMock()
    engine = KidaTemplateEngine(site)

    # Valid but undefined var (OK with strict=False)
    # Returns "" or "None" depending on implementation
    out = engine.render_string("{{ undefined }}", {}, strict=False)
    assert out in ("", "None")

    # Actual syntax error (Should still fail)
    with pytest.raises(Exception) as excinfo:
        engine.render_string("{{ invalid syntax %", {}, strict=False)
    assert "syntax" in str(excinfo.value).lower()
