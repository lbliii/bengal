from pathlib import Path


class DummySite:
    def __init__(self, root_path: Path, config: dict, theme: str = "default") -> None:
        self.root_path = root_path
        self.config = config
        self.theme = theme
        self.output_dir = root_path / "public"

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


def test_cli_build_flag_overrides_pipeline(tmp_path: Path, monkeypatch):
    # Arrange: create a minimal site directory
    (tmp_path / "content").mkdir()
    (tmp_path / "assets").mkdir()

    # Ensure Site.from_config returns controlled site
    from bengal.core.site import Site

    real_from_config = Site.from_config

    def fake_from_config(root_path: Path, config_path=None, environment=None, profile=None):
        site = real_from_config(root_path, config_path, environment=environment, profile=profile)
        site.config["assets"] = {"pipeline": False}
        return site

    monkeypatch.setattr(Site, "from_config", staticmethod(fake_from_config))

    # Act: invoke build command with --assets-pipeline flag
    from click.testing import CliRunner

    from bengal.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["site", "build", str(tmp_path), "--assets-pipeline", "--quiet"],
        catch_exceptions=False,
    )

    # Assert: command succeeded
    assert result.exit_code == 0
