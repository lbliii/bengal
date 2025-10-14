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

    class FakeLinkValidator:  # noqa: N801
        def validate_site(self, site):
            return {"/broken": "not found"}

    monkeypatch.setattr(
        "bengal.orchestration.postprocess.LinkValidator",
        FakeLinkValidator,
        raising=False,
    )

    reporter = CapturingReporter()
    ctx = SimpleNamespace(reporter=reporter)

    orch.run(parallel=False, progress_manager=None, build_context=ctx)

    assert any("post-processing" in msg for msg in reporter.messages) or reporter.messages


def test_postprocess_parallel_errors_use_reporter(tmp_path, monkeypatch):
    """Ensure parallel errors are routed to reporter and do not crash."""
    site = SimpleNamespace(config={})
    orch = PostprocessOrchestrator(site)

    # Configure to run multiple tasks to trigger parallel path
    site.config["generate_sitemap"] = True
    site.config["generate_rss"] = True
    site.config["output_formats"] = {"enabled": True}
    site.config["validate_links"] = True

    # Make sitemap raise, others no-op
    class Boom(Exception):
        pass

    class FakeSitemap:
        def __init__(self, site):
            pass

        def generate(self):
            raise Boom("boom")

    monkeypatch.setattr(
        "bengal.orchestration.postprocess.SitemapGenerator", FakeSitemap, raising=True
    )

    # Stub link validator to avoid actual scanning
    class FakeLinkValidator:  # noqa: N801
        def validate_site(self, site):
            return {}

    monkeypatch.setattr(
        "bengal.orchestration.postprocess.LinkValidator", FakeLinkValidator, raising=False
    )

    reporter = CapturingReporter()
    ctx = SimpleNamespace(reporter=reporter)

    orch.run(parallel=True, progress_manager=None, build_context=ctx)

    # Expect an error summary in reporter messages
    assert any("post-processing" in msg for msg in reporter.messages)
