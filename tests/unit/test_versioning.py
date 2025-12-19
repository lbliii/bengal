"""
Tests for versioned documentation support.

Tests cover:
- Version and VersionConfig models
- Version discovery from config
- Version-aware URL generation
- Cross-version links (future)
"""

from __future__ import annotations

from pathlib import Path

from bengal.core.version import Version, VersionBanner, VersionConfig


class TestVersion:
    """Tests for the Version model."""

    def test_version_defaults(self) -> None:
        """Test Version default values."""
        v = Version(id="v3")

        assert v.id == "v3"
        assert v.label == "v3"  # Defaults to id
        assert v.source == "_versions/v3"  # Defaults to _versions/<id>
        assert v.latest is False
        assert v.banner is None
        assert v.deprecated is False

    def test_version_latest_defaults(self) -> None:
        """Test Version defaults for latest version."""
        v = Version(id="v3", latest=True)

        assert v.id == "v3"
        assert v.source == ""  # Latest uses main content dir
        assert v.latest is True

    def test_version_custom_label(self) -> None:
        """Test Version with custom label."""
        v = Version(id="v1", label="1.0 LTS")

        assert v.id == "v1"
        assert v.label == "1.0 LTS"

    def test_version_url_prefix(self) -> None:
        """Test Version URL prefix generation."""
        latest = Version(id="v3", latest=True)
        older = Version(id="v2")

        assert latest.url_prefix == ""  # No prefix for latest
        assert older.url_prefix == "/v2"  # Prefix for older versions

    def test_version_to_dict(self) -> None:
        """Test Version serialization to dict."""
        v = Version(id="v2", label="2.0", deprecated=True)
        d = v.to_dict()

        assert d["id"] == "v2"
        assert d["label"] == "2.0"
        assert d["latest"] is False
        assert d["deprecated"] is True
        assert d["url_prefix"] == "/v2"


class TestVersionBanner:
    """Tests for VersionBanner model."""

    def test_banner_defaults(self) -> None:
        """Test VersionBanner default values."""
        banner = VersionBanner()

        assert banner.type == "warning"
        assert "older version" in banner.message.lower()
        assert banner.show_latest_link is True

    def test_banner_custom(self) -> None:
        """Test VersionBanner with custom values."""
        banner = VersionBanner(
            type="danger",
            message="This version is no longer supported.",
            show_latest_link=False,
        )

        assert banner.type == "danger"
        assert banner.message == "This version is no longer supported."
        assert banner.show_latest_link is False


class TestVersionConfig:
    """Tests for VersionConfig model."""

    def test_config_disabled_by_default(self) -> None:
        """Test VersionConfig disabled by default."""
        config = VersionConfig()

        assert config.enabled is False
        assert config.versions == []

    def test_config_with_versions(self) -> None:
        """Test VersionConfig with versions."""
        v3 = Version(id="v3", latest=True)
        v2 = Version(id="v2")
        v1 = Version(id="v1")

        config = VersionConfig(
            enabled=True,
            versions=[v3, v2, v1],
        )

        assert config.enabled is True
        assert len(config.versions) == 3
        assert config.latest_version == v3

    def test_config_auto_latest(self) -> None:
        """Test that first version is marked latest if none specified."""
        v3 = Version(id="v3")
        v2 = Version(id="v2")

        config = VersionConfig(enabled=True, versions=[v3, v2])

        # First version should be auto-marked as latest
        assert config.versions[0].latest is True
        assert config.latest_version == v3

    def test_config_auto_latest_alias(self) -> None:
        """Test that 'latest' alias is auto-added."""
        v3 = Version(id="v3", latest=True)

        config = VersionConfig(enabled=True, versions=[v3])

        assert "latest" in config.aliases
        assert config.aliases["latest"] == "v3"

    def test_get_version(self) -> None:
        """Test getting version by id."""
        v3 = Version(id="v3", latest=True)
        v2 = Version(id="v2")

        config = VersionConfig(enabled=True, versions=[v3, v2])

        assert config.get_version("v3") == v3
        assert config.get_version("v2") == v2
        assert config.get_version("v1") is None

    def test_resolve_alias(self) -> None:
        """Test resolving version aliases."""
        v3 = Version(id="v3", latest=True)
        v1 = Version(id="v1")

        config = VersionConfig(
            enabled=True,
            versions=[v3, v1],
            aliases={"latest": "v3", "stable": "v3", "lts": "v1"},
        )

        assert config.resolve_alias("latest") == "v3"
        assert config.resolve_alias("stable") == "v3"
        assert config.resolve_alias("lts") == "v1"
        assert config.resolve_alias("unknown") is None

    def test_get_version_or_alias(self) -> None:
        """Test getting version by id or alias."""
        v3 = Version(id="v3", latest=True)
        v2 = Version(id="v2")

        config = VersionConfig(
            enabled=True,
            versions=[v3, v2],
            aliases={"latest": "v3"},
        )

        # By id
        assert config.get_version_or_alias("v3") == v3
        assert config.get_version_or_alias("v2") == v2

        # By alias
        assert config.get_version_or_alias("latest") == v3

        # Unknown
        assert config.get_version_or_alias("unknown") is None

    def test_is_versioned_section(self) -> None:
        """Test checking if section is versioned."""
        config = VersionConfig(
            enabled=True,
            versions=[Version(id="v1")],
            sections=["docs", "api"],
        )

        assert config.is_versioned_section("docs") is True
        assert config.is_versioned_section("docs/guide") is True
        assert config.is_versioned_section("api") is True
        assert config.is_versioned_section("blog") is False

    def test_get_version_for_path_versions_dir(self) -> None:
        """Test determining version from _versions/ path."""
        v3 = Version(id="v3", latest=True)
        v2 = Version(id="v2")

        config = VersionConfig(
            enabled=True,
            versions=[v3, v2],
            sections=["docs"],
        )

        # _versions/v2/docs/guide.md → v2
        path = Path("_versions/v2/docs/guide.md")
        assert config.get_version_for_path(path) == v2

    def test_get_version_for_path_main_content(self) -> None:
        """Test determining version from main content path."""
        v3 = Version(id="v3", latest=True)
        v2 = Version(id="v2")

        config = VersionConfig(
            enabled=True,
            versions=[v3, v2],
            sections=["docs"],
        )

        # docs/guide.md → latest (v3)
        path = Path("docs/guide.md")
        assert config.get_version_for_path(path) == v3

    def test_to_template_context(self) -> None:
        """Test conversion to template context."""
        v3 = Version(id="v3", latest=True, label="3.0")
        v2 = Version(id="v2", label="2.0")

        config = VersionConfig(
            enabled=True,
            versions=[v3, v2],
            aliases={"latest": "v3"},
        )

        ctx = config.to_template_context()

        assert ctx["enabled"] is True
        assert len(ctx["versions"]) == 2
        assert ctx["versions"][0]["id"] == "v3"
        assert ctx["versions"][0]["latest"] is True
        assert ctx["aliases"] == {"latest": "v3"}
        assert ctx["latest"]["id"] == "v3"


class TestVersionConfigFromConfig:
    """Tests for VersionConfig.from_config()."""

    def test_from_config_disabled(self) -> None:
        """Test from_config with versioning disabled."""
        config = VersionConfig.from_config({})
        assert config.enabled is False

        config = VersionConfig.from_config({"versioning": {"enabled": False}})
        assert config.enabled is False

    def test_from_config_simple_versions(self) -> None:
        """Test from_config with simple version list."""
        config = VersionConfig.from_config(
            {
                "versioning": {
                    "enabled": True,
                    "versions": ["v3", "v2", "v1"],
                }
            }
        )

        assert config.enabled is True
        assert len(config.versions) == 3
        assert config.versions[0].id == "v3"
        assert config.versions[0].latest is True
        assert config.versions[1].id == "v2"
        assert config.versions[2].id == "v1"

    def test_from_config_full_versions(self) -> None:
        """Test from_config with full version objects."""
        config = VersionConfig.from_config(
            {
                "versioning": {
                    "enabled": True,
                    "versions": [
                        {"id": "v3", "source": "docs", "label": "3.0", "latest": True},
                        {"id": "v2", "source": "_versions/v2/docs", "label": "2.0"},
                        {
                            "id": "v1",
                            "label": "1.0 (Legacy)",
                            "deprecated": True,
                            "banner": {"type": "warning", "message": "Old version!"},
                        },
                    ],
                }
            }
        )

        assert config.enabled is True
        assert len(config.versions) == 3

        v3 = config.versions[0]
        assert v3.id == "v3"
        assert v3.source == "docs"
        assert v3.label == "3.0"
        assert v3.latest is True

        v2 = config.versions[1]
        assert v2.id == "v2"
        assert v2.source == "_versions/v2/docs"
        assert v2.label == "2.0"

        v1 = config.versions[2]
        assert v1.id == "v1"
        assert v1.label == "1.0 (Legacy)"
        assert v1.deprecated is True
        assert v1.banner is not None
        assert v1.banner.type == "warning"
        assert v1.banner.message == "Old version!"

    def test_from_config_with_aliases(self) -> None:
        """Test from_config with custom aliases."""
        config = VersionConfig.from_config(
            {
                "versioning": {
                    "enabled": True,
                    "versions": ["v3", "v2", "v1"],
                    "aliases": {
                        "latest": "v3",
                        "stable": "v3",
                        "lts": "v1",
                    },
                }
            }
        )

        assert config.aliases["latest"] == "v3"
        assert config.aliases["stable"] == "v3"
        assert config.aliases["lts"] == "v1"

    def test_from_config_with_sections(self) -> None:
        """Test from_config with custom sections."""
        config = VersionConfig.from_config(
            {
                "versioning": {
                    "enabled": True,
                    "versions": ["v1"],
                    "sections": ["docs", "api", "sdk"],
                }
            }
        )

        assert config.sections == ["docs", "api", "sdk"]


class TestURLStrategyVersioning:
    """Tests for version-aware URL generation."""

    def test_apply_version_path_transform_latest(self) -> None:
        """Test that latest version paths are unchanged."""
        from unittest.mock import MagicMock

        from bengal.utils.url_strategy import URLStrategy

        # Create mock site with version config
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
        )

        # Create mock page with version
        page = MagicMock()
        page.version = "v3"

        # Latest version: path unchanged
        rel_path = Path("docs/guide.md")
        result = URLStrategy._apply_version_path_transform(rel_path, page, site)
        assert result == Path("docs/guide.md")

    def test_apply_version_path_transform_older_version(self) -> None:
        """Test that older version paths get version prefix."""
        from unittest.mock import MagicMock

        from bengal.utils.url_strategy import URLStrategy

        # Create mock site with version config
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
        )

        # Create mock page with version
        page = MagicMock()
        page.version = "v2"

        # Older version from _versions/v2/: insert version after section
        rel_path = Path("_versions/v2/docs/guide.md")
        result = URLStrategy._apply_version_path_transform(rel_path, page, site)
        assert result == Path("docs/v2/guide.md")

    def test_apply_version_path_transform_disabled(self) -> None:
        """Test that versioning disabled leaves paths unchanged."""
        from unittest.mock import MagicMock

        from bengal.utils.url_strategy import URLStrategy

        # Create mock site with versioning disabled
        site = MagicMock()
        site.version_config = VersionConfig(enabled=False)

        page = MagicMock()
        page.version = None

        rel_path = Path("docs/guide.md")
        result = URLStrategy._apply_version_path_transform(rel_path, page, site)
        assert result == Path("docs/guide.md")

    def test_apply_version_path_transform_strip_versions_dir_latest(self) -> None:
        """Test that _versions/ prefix is stripped for latest version."""
        from unittest.mock import MagicMock

        from bengal.utils.url_strategy import URLStrategy

        # Create mock site
        site = MagicMock()
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
            ],
        )

        # Page from _versions/v3/ (maybe symlinked or copied)
        page = MagicMock()
        page.version = "v3"

        rel_path = Path("_versions/v3/docs/guide.md")
        result = URLStrategy._apply_version_path_transform(rel_path, page, site)
        # Latest version: strip _versions/v3/ prefix
        assert result == Path("docs/guide.md")


class TestVersionResolver:
    """Tests for version resolution utilities."""

    def test_version_resolver_get_version_for_path(self) -> None:
        """Test version resolver path detection."""
        from bengal.discovery.version_resolver import VersionResolver

        config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True, source="docs"),
                Version(id="v2", source="_versions/v2/docs"),
            ],
            sections=["docs"],
        )

        resolver = VersionResolver(config, Path("/site"))

        # _versions/v2/ path → v2
        version = resolver.get_version_for_path("_versions/v2/docs/guide.md")
        assert version is not None
        assert version.id == "v2"

        # docs/ path → latest (v3)
        version = resolver.get_version_for_path("docs/guide.md")
        assert version is not None
        assert version.id == "v3"

        # non-versioned path → None
        version = resolver.get_version_for_path("blog/post.md")
        assert version is None

    def test_version_resolver_get_logical_path(self) -> None:
        """Test logical path extraction."""
        from bengal.discovery.version_resolver import VersionResolver

        config = VersionConfig(
            enabled=True,
            versions=[Version(id="v2")],
        )

        resolver = VersionResolver(config, Path("/site"))

        # _versions/v2/docs/guide.md → docs/guide.md
        logical = resolver.get_logical_path("_versions/v2/docs/guide.md")
        assert logical == Path("docs/guide.md")

        # Regular path unchanged
        logical = resolver.get_logical_path("docs/guide.md")
        assert logical == Path("docs/guide.md")

    def test_version_resolver_disabled(self) -> None:
        """Test resolver when versioning is disabled."""
        from bengal.discovery.version_resolver import VersionResolver

        config = VersionConfig(enabled=False)
        resolver = VersionResolver(config, Path("/site"))

        assert resolver.enabled is False
        assert resolver.get_version_for_path("docs/guide.md") is None
        assert resolver.get_shared_content_paths() == []


class TestVersionCLI:
    """Tests for version CLI commands (smoke tests)."""

    def test_version_list_no_versioning(self, tmp_path: Path) -> None:
        """Test version list with no versioning configured."""
        from click.testing import CliRunner

        from bengal.cli.commands.version import version_cli

        # Create minimal config
        config_file = tmp_path / "bengal.yaml"
        config_file.write_text("site:\n  title: Test\n")

        runner = CliRunner()
        result = runner.invoke(version_cli, ["list", str(tmp_path)])

        # Should warn that versioning is not enabled
        assert "not enabled" in result.output.lower() or result.exit_code == 0

    def test_version_create_dry_run(self, tmp_path: Path) -> None:
        """Test version create with dry run."""
        from click.testing import CliRunner

        from bengal.cli.commands.version import version_cli

        # Create minimal site structure
        config_file = tmp_path / "bengal.yaml"
        config_file.write_text("site:\n  title: Test\n")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Guide\n\nContent")

        runner = CliRunner()
        result = runner.invoke(
            version_cli,
            ["create", "v1", "--dry-run", str(tmp_path)],
        )

        # Should show what would be done
        assert "dry run" in result.output.lower()
        assert result.exit_code == 0

        # Should NOT have created the directory
        assert not (tmp_path / "_versions" / "v1").exists()
