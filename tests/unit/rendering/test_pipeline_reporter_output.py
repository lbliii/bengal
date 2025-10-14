from __future__ import annotations

from types import SimpleNamespace

from bengal.core.page import Page
from bengal.rendering.pipeline import RenderingPipeline


class CapturingReporter:
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


def test_pipeline_routes_output_via_reporter(tmp_path):
    site = SimpleNamespace(config={}, root_path=tmp_path, output_dir=tmp_path / "public")
    page = Page(source_path=tmp_path / "content" / "p.md", content="# Title", metadata={})
    page.output_path = site.output_dir / "p" / "index.html"
    reporter = CapturingReporter()

    # Inject a dummy template engine to avoid needing a full Site with theme
    class DummyTemplateEngine:
        def __init__(self, site):
            self.site = site
            self.env = SimpleNamespace()

    ctx = SimpleNamespace(reporter=reporter, template_engine=DummyTemplateEngine(site))

    pipeline = RenderingPipeline(site, build_context=ctx, quiet=False)
    # Ensure write path exists
    page.output_path.parent.mkdir(parents=True, exist_ok=True)

    # Simulate already-rendered content to avoid invoking parser complexity
    page.parsed_ast = "<h1>Title</h1>"
    pipeline.renderer = SimpleNamespace(
        render_content=lambda s: s,
        render_page=lambda p, c: "<html>\n<body>\n" + c + "\n</body>\n</html>",
    )

    pipeline._write_output(page)

    assert any("index.html" in msg for msg in reporter.messages)
