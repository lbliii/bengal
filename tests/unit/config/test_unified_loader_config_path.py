"""
Tests for honoring an explicit ``config_path`` in config loading.

Regression coverage for #444: ``Site.from_config(config_path=...)`` and
``UnifiedConfigLoader.load(config_path=...)`` must load the explicitly
named file instead of silently auto-discovering ``bengal.toml`` in the
site root.
"""

from bengal.config.unified_loader import UnifiedConfigLoader
from bengal.core.site import Site


def _write_competing_configs(tmp_path):
    """Create an auto-discoverable config plus a separate explicit one.

    Returns (root, explicit_path). The root contains an auto-discoverable
    ``bengal.toml`` titled "Auto"; ``explicit_path`` lives in a subdirectory
    where auto-discovery cannot find it and is titled "Explicit".
    """
    (tmp_path / "bengal.toml").write_text('[site]\ntitle = "Auto"\n')

    explicit_dir = tmp_path / "alt"
    explicit_dir.mkdir()
    explicit_path = explicit_dir / "production.toml"
    explicit_path.write_text('[site]\ntitle = "Explicit"\n')

    return tmp_path, explicit_path


class TestLoaderConfigPath:
    def test_explicit_config_path_overrides_autodiscovery(self, tmp_path):
        """An explicit config_path must win over the auto-discovered file."""
        root, explicit_path = _write_competing_configs(tmp_path)

        config_obj = UnifiedConfigLoader().load(root, config_path=explicit_path)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        assert config["title"] == "Explicit"

    def test_no_config_path_preserves_autodiscovery(self, tmp_path):
        """When config_path is None, auto-discovery is unchanged (backward compatible)."""
        root, _ = _write_competing_configs(tmp_path)

        config_obj = UnifiedConfigLoader().load(root)
        config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

        assert config["title"] == "Auto"


class TestSiteFromConfigPath:
    def test_from_config_honors_config_path(self, tmp_path):
        """Site.from_config(config_path=...) must reflect the explicit file."""
        root, explicit_path = _write_competing_configs(tmp_path)

        site = Site.from_config(root, config_path=explicit_path)

        assert site.title == "Explicit"
