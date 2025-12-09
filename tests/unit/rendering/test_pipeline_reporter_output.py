"""
Tests for RenderingPipeline output writing.

Note: Per-page logging was removed in favor of progress bar feedback.
These tests verify that output files are written correctly.
"""

from types import SimpleNamespace

from bengal.core.page import Page
from bengal.rendering.pipeline import RenderingPipeline


class CapturingReporter:
    """Mock reporter for testing build context injection."""

    def __init__(self):
        self.messages = []

    def add_phase(self, *args, **kwargs):
        pass

    def start_phase(self, *args, **kwargs):
        pass

    def update_phase(self, *args, **kwargs):
        pass

    def complete_phase(self, *args, **kwargs):
        pass

    def log(self, message: str) -> None:
        self.messages.append(message)


def test_pipeline_writes_output_file(tmp_path):
    """Test that _write_output correctly writes the rendered HTML to disk."""
    site = SimpleNamespace(config={}, root_path=tmp_path, output_dir=tmp_path / "public")
    page = Page(source_path=tmp_path / "content" / "p.md", content="# Title", metadata={})
    page.output_path = site.output_dir / "p" / "index.html"

    # Inject a dummy template engine to avoid needing a full Site with theme
    class DummyTemplateEngine:
        def __init__(self, site):
            self.site = site
            self.env = SimpleNamespace()

    ctx = SimpleNamespace(template_engine=DummyTemplateEngine(site))

    pipeline = RenderingPipeline(site, build_context=ctx, quiet=False)
    # Ensure write path exists
    page.output_path.parent.mkdir(parents=True, exist_ok=True)

    # Simulate already-rendered content
    page.parsed_ast = "<h1>Title</h1>"
    page.rendered_html = "<html>\n<body>\n<h1>Title</h1>\n</body>\n</html>"
    pipeline.renderer = SimpleNamespace(
        render_content=lambda s: s,
        render_page=lambda p, c: page.rendered_html,
    )

    pipeline._write_output(page)

    # Verify the file was written with correct content
    assert page.output_path.exists()
    written_content = page.output_path.read_text()
    assert "<h1>Title</h1>" in written_content
    assert "<html>" in written_content


def test_pipeline_accepts_build_context_with_reporter(tmp_path):
    """Test that pipeline accepts build_context with reporter (for future use)."""
    site = SimpleNamespace(config={}, root_path=tmp_path, output_dir=tmp_path / "public")
    reporter = CapturingReporter()

    class DummyTemplateEngine:
        def __init__(self, site):
            self.site = site
            self.env = SimpleNamespace()

    ctx = SimpleNamespace(reporter=reporter, template_engine=DummyTemplateEngine(site))

    # Should not raise - reporter in build_context is accepted
    pipeline = RenderingPipeline(site, build_context=ctx, quiet=False)
    assert pipeline.build_context.reporter is reporter
