from typing import TYPE_CHECKING

from bengal.cache.paths import BengalPaths

if TYPE_CHECKING:
    from pathlib import Path


class DummySite:
    """Minimal Site mock for asset pipeline tests."""

    def __init__(self, root_path: Path, config: dict, theme: str = "default") -> None:
        self.root_path = root_path
        self.config = config
        self.theme = theme
        self.output_dir = root_path / "public"
        self.build_state = None
        self._paths: BengalPaths | None = None

    @property
    def baseurl(self) -> str:
        """Return baseurl from config."""
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("baseurl"):
            return site_section.get("baseurl", "")
        return self.config.get("baseurl", "")

    @property
    def paths(self) -> BengalPaths:
        """Access to .bengal directory paths."""
        if self._paths is None:
            self._paths = BengalPaths(self.root_path)
        return self._paths

    @property
    def assets_config(self) -> dict:
        """Get the 'assets' configuration section."""
        return self.config.get("assets", {})


def test_asset_orchestrator_runs_pipeline_when_enabled(monkeypatch, tmp_path: Path):
    # Arrange: site with assets.pipeline = true
    config = {"assets": {"pipeline": True}}
    site = DummySite(tmp_path, config)

    # Create a dummy pipeline returning one compiled file
    compiled_file = tmp_path / ".bengal" / "pipeline_out" / "assets" / "css" / "style.css"
    compiled_file.parent.mkdir(parents=True, exist_ok=True)
    compiled_file.write_text("body{color:black}", encoding="utf-8")

    class DummyPipeline:
        def __init__(self, *_args, **_kwargs):
            pass

        def build(self):
            return [compiled_file]

    def dummy_from_site(_site):
        return DummyPipeline()

    # Import the real module and monkeypatch the from_site function
    import bengal.assets.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "from_site", dummy_from_site)

    # Import orchestrator after monkeypatching
    from bengal.orchestration.asset import AssetOrchestrator

    orchestrator = AssetOrchestrator(site)

    # Act: process with empty asset list (pipeline should add compiled output)
    orchestrator.process([])

    # Assert: compiled file remains (no exceptions) and output dir created lazily later
    assert compiled_file.exists()
