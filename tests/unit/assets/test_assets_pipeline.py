from typing import TYPE_CHECKING

from bengal.assets.manifest import AssetManifest, inspect_asset_outputs
from bengal.cache.paths import BengalPaths

if TYPE_CHECKING:
    from pathlib import Path


class _DummyConfigService:
    """Minimal ConfigService mock exposing paths/assets_config."""

    def __init__(self, site: DummySite) -> None:
        self._site = site

    @property
    def paths(self) -> BengalPaths:
        if self._site._paths is None:
            self._site._paths = BengalPaths(self._site.root_path)
        return self._site._paths

    @property
    def assets_config(self) -> dict:
        return self._site.config.get("assets", {})


class DummySite:
    """Minimal Site mock for asset pipeline tests."""

    def __init__(self, root_path: Path, config: dict, theme: str = "default") -> None:
        self.root_path = root_path
        self.config = config
        self.theme = theme
        self.output_dir = root_path / "public"
        self.build_state = None
        self._paths: BengalPaths | None = None
        self.config_service = _DummyConfigService(self)

    @property
    def baseurl(self) -> str:
        """Return baseurl from config."""
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("baseurl"):
            return site_section.get("baseurl", "")
        return self.config.get("baseurl", "")


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


def test_asset_orchestrator_writes_empty_manifest_when_no_assets(tmp_path: Path):
    """Sites with no processed assets still get an empty asset manifest."""
    from bengal.orchestration.asset import AssetOrchestrator

    site = DummySite(tmp_path, config={})
    orchestrator = AssetOrchestrator(site)

    orchestrator.process([])

    manifest_path = tmp_path / "public" / "asset-manifest.json"
    manifest = AssetManifest.load(manifest_path)

    assert manifest is not None
    assert manifest.entries == {}

    integrity = inspect_asset_outputs(tmp_path / "public")
    assert integrity.is_complete is True
    assert integrity.total_entries == 0


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
    from bengal.cli import cli

    result = cli.invoke(["build", "--source", str(tmp_path), "--assets-pipeline", "--quiet"])

    # Assert: command succeeded
    assert result.exit_code == 0


def test_asset_manifest_importable_from_package() -> None:
    """The documented public import ``from bengal.assets import AssetManifest`` works.

    Regression guard for #447: ``bengal/assets/__init__.py`` previously had no
    re-export, so the documented import (docstring + theming/assets docs) raised
    ImportError. This asserts both names are re-exported from the package root
    and are the same objects as the ones defined in ``bengal.assets.manifest``.
    """
    from bengal.assets import AssetManifest as PackageManifest
    from bengal.assets import AssetManifestEntry as PackageEntry
    from bengal.assets.manifest import AssetManifest as ModuleManifest
    from bengal.assets.manifest import AssetManifestEntry as ModuleEntry

    assert PackageManifest is ModuleManifest
    assert PackageEntry is ModuleEntry


def test_orchestrator_honors_nested_assets_minify_false(tmp_path: Path, monkeypatch) -> None:
    """``[assets] minify = false`` must disable minification.

    Regression guard for #447: the orchestrator used to read the deprecated flat
    key ``minify_assets`` (which never exists once the loader flattens
    ``assets.*`` to bare keys), so the documented nested ``[assets] minify``
    setting was silently ignored and minification stayed on. This spies on the
    derived ``minify`` flag handed to processing. It is discriminating: if the
    orchestrator reverted to reading ``minify_assets``, ``captured["minify"]``
    would be the ``True`` default and the assertion would fail.
    """
    from bengal.orchestration.asset import AssetOrchestrator

    # Nested [assets] config as documented; note this is the section dict that
    # config_service.assets_config returns.
    site = DummySite(tmp_path, config={"assets": {"minify": False}})
    orchestrator = AssetOrchestrator(site)

    captured: dict = {}

    def fake_sequential(
        self,
        css_entries,
        other_assets,
        minify,
        optimize,
        fingerprint,
        progress_manager,
        css_modules_count=0,
    ):
        captured["minify"] = minify
        captured["optimize"] = optimize
        captured["fingerprint"] = fingerprint

    monkeypatch.setattr(AssetOrchestrator, "_process_sequentially", fake_sequential)

    class _FakeAsset:
        def __init__(self) -> None:
            self.source_path = tmp_path / "app.js"

        def is_css_entry_point(self) -> bool:
            return False

        def is_css_module(self) -> bool:
            return False

        def is_js_module(self) -> bool:
            return False

    orchestrator.process([_FakeAsset()])

    assert captured["minify"] is False


def test_orchestrator_minify_defaults_true_without_assets_config(
    tmp_path: Path, monkeypatch
) -> None:
    """With no ``[assets]`` config, minification defaults to on (proves the guard
    above fails for the right reason, not because the flag is always False)."""
    from bengal.orchestration.asset import AssetOrchestrator

    site = DummySite(tmp_path, config={})
    orchestrator = AssetOrchestrator(site)

    captured: dict = {}

    def fake_sequential(
        self,
        css_entries,
        other_assets,
        minify,
        optimize,
        fingerprint,
        progress_manager,
        css_modules_count=0,
    ):
        captured["minify"] = minify

    monkeypatch.setattr(AssetOrchestrator, "_process_sequentially", fake_sequential)

    class _FakeAsset:
        def __init__(self) -> None:
            self.source_path = tmp_path / "app.js"

        def is_css_entry_point(self) -> bool:
            return False

        def is_css_module(self) -> bool:
            return False

        def is_js_module(self) -> bool:
            return False

    orchestrator.process([_FakeAsset()])

    assert captured["minify"] is True
