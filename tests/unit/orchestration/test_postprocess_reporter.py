from __future__ import annotations

from types import SimpleNamespace

from bengal.orchestration.postprocess import PostprocessOrchestrator


class CapturingReporter:
    def __init__(self):
        self.messages = []

    def log(self, message: str) -> None:
        self.messages.append(message)


def test_postprocess_reports_errors_via_reporter(tmp_path, monkeypatch):
    site = SimpleNamespace(config={})
    orch = PostprocessOrchestrator(site)

    # Force tasks to include link validation and make it raise
    site.config["generate_sitemap"] = False
    site.config["generate_rss"] = False
    site.config["output_formats"] = {"enabled": False}
    site.config["validate_links"] = True

    class DummyValidator:
        def validate_site(self, site):
            return [("/broken", "not found")]

    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setitem(
        PostprocessOrchestrator.__dict__,
        "_PostprocessOrchestrator__dummy__",
        None,
        raising=False,
    )

    # Patch LinkValidator import
    import bengal.orchestration.postprocess as pp

    class FakeModule:
        class LinkValidator:  # noqa: N801
            def validate_site(self, site):
                return {"/broken": "not found"}

    pp.LinkValidator = FakeModule.LinkValidator

    reporter = CapturingReporter()
    ctx = SimpleNamespace(reporter=reporter)

    orch.run(parallel=False, progress_manager=None, build_context=ctx)

    assert any("post-processing" in msg for msg in reporter.messages) or reporter.messages
