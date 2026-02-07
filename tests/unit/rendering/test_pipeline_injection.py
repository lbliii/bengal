from types import SimpleNamespace

from bengal.rendering.pipeline import RenderingPipeline


class DummyParser:
    def __init__(self):
        self.enabled = {}

    def enable_cross_references(self, xref_index):
        self.enabled["xref"] = True

    def parse(self, content, metadata):
        return content


class DummyTemplateEngine:
    def __init__(self, site):
        self.site = site
        self.env = SimpleNamespace()


def test_pipeline_uses_injected_parser_and_engine(tmp_path):
    site = SimpleNamespace(config={}, root_path=tmp_path, output_dir=tmp_path / "public")
    parser = DummyParser()
    engine = DummyTemplateEngine(site)
    ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

    pipeline = RenderingPipeline(site, build_context=ctx)

    assert pipeline.parser is parser
    assert pipeline.template_engine is engine
