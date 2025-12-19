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


# =============================================================================
# Phase 3: Cross-Version Linking Tests
# =============================================================================


class TestCrossVersionLinks:
    """Tests for cross-version linking [[v2:path]] syntax."""

    def test_version_link_resolution(self) -> None:
        """Test resolving cross-version link syntax."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
            sections=["docs"],
        )

        plugin = CrossReferencePlugin({}, version_config=config)

        # Test resolving v2 link
        html = plugin._resolve_version_link("v2:docs/guide", None)
        assert 'href="/docs/v2/guide/"' in html
        assert "(v2)" in html

    def test_version_link_latest_no_prefix(self) -> None:
        """Test that latest version links have no version prefix."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
            sections=["docs"],
        )

        plugin = CrossReferencePlugin({}, version_config=config)

        # Latest should have no version prefix
        html = plugin._resolve_version_link("v3:docs/guide", None)
        assert 'href="/docs/guide/"' in html
        assert "/v3/" not in html

    def test_version_link_with_custom_text(self) -> None:
        """Test cross-version link with custom text."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2", label="Version 2.0"),
            ],
            sections=["docs"],
        )

        plugin = CrossReferencePlugin({}, version_config=config)

        # Resolve with custom text
        html = plugin._resolve_version_link("v2:docs/guide", "See v2 Guide")
        assert 'href="/docs/v2/guide/"' in html
        assert "See v2 Guide" in html

    def test_version_link_alias(self) -> None:
        """Test cross-version link using alias (latest)."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
            sections=["docs"],
        )

        plugin = CrossReferencePlugin({}, version_config=config)

        # Use 'latest' alias
        html = plugin._resolve_version_link("latest:docs/guide", None)
        assert 'href="/docs/guide/"' in html  # Latest has no prefix

    def test_version_link_disabled_versioning(self) -> None:
        """Test cross-version link when versioning is disabled."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        # No version config
        plugin = CrossReferencePlugin({}, version_config=None)

        html = plugin._resolve_version_link("v2:docs/guide", None)
        assert 'class="broken-ref"' in html
        assert "Versioning not enabled" in html

    def test_version_link_unknown_version(self) -> None:
        """Test cross-version link with unknown version."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        config = VersionConfig(
            enabled=True,
            versions=[Version(id="v3", latest=True)],
            sections=["docs"],
        )

        plugin = CrossReferencePlugin({}, version_config=config)

        html = plugin._resolve_version_link("v99:docs/guide", None)
        assert 'class="broken-ref"' in html
        assert "Version not found" in html

    def test_version_link_with_anchor(self) -> None:
        """Test cross-version link with anchor fragment."""
        from bengal.rendering.plugins.cross_references import CrossReferencePlugin

        config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
            sections=["docs"],
        )

        plugin = CrossReferencePlugin({}, version_config=config)

        html = plugin._resolve_version_link("v2:docs/guide#section", None)
        assert 'href="/docs/v2/guide/#section"' in html


# =============================================================================
# Phase 3: Version Directive Tests
# =============================================================================


class TestVersionDirectives:
    """Tests for version-aware directives (since, deprecated, changed)."""

    def test_since_directive_badge(self) -> None:
        """Test since directive renders as badge."""
        from bengal.rendering.plugins.directives.versioning import SinceDirective

        directive = SinceDirective()
        html = directive.render(None, "", version="v2.0", has_content=False)

        assert "version-badge-since" in html
        assert "New in v2.0" in html

    def test_since_directive_with_content(self) -> None:
        """Test since directive with content renders as box."""
        from bengal.rendering.plugins.directives.versioning import SinceDirective

        directive = SinceDirective()
        html = directive.render(
            None,
            "<p>This feature was added.</p>",
            version="v2.0",
            has_content=True,
            **{"class": "version-since"},
        )

        assert "version-since" in html
        assert "version-content" in html
        assert "This feature was added." in html

    def test_deprecated_directive_warning(self) -> None:
        """Test deprecated directive renders as warning."""
        from bengal.rendering.plugins.directives.versioning import DeprecatedDirective

        directive = DeprecatedDirective()
        html = directive.render(None, "", version="v3.0", has_content=False)

        assert "admonition warning" in html
        assert "version-badge-deprecated" in html
        assert "Deprecated since v3.0" in html

    def test_deprecated_directive_with_migration(self) -> None:
        """Test deprecated directive with migration content."""
        from bengal.rendering.plugins.directives.versioning import DeprecatedDirective

        directive = DeprecatedDirective()
        html = directive.render(
            None,
            "<p>Use new_function() instead.</p>",
            version="v3.0",
            has_content=True,
            **{"class": "version-deprecated"},
        )

        assert "version-content" in html
        assert "Use new_function()" in html

    def test_changed_directive_info(self) -> None:
        """Test changed directive renders as info note."""
        from bengal.rendering.plugins.directives.versioning import ChangedDirective

        directive = ChangedDirective()
        html = directive.render(None, "", version="v2.5", has_content=False)

        assert "admonition note" in html
        assert "version-badge-changed" in html
        assert "Changed in v2.5" in html

    def test_changed_directive_with_details(self) -> None:
        """Test changed directive with change details."""
        from bengal.rendering.plugins.directives.versioning import ChangedDirective

        directive = ChangedDirective()
        html = directive.render(
            None,
            "<p>Default changed from 10 to 20.</p>",
            version="v2.5",
            has_content=True,
            **{"class": "version-changed"},
        )

        assert "version-content" in html
        assert "Default changed from 10 to 20" in html


# =============================================================================
# Phase 3: SEO & Sitemap Tests
# =============================================================================


class TestVersionedSEO:
    """Tests for version-aware SEO (canonical URLs, sitemap priority)."""

    def test_canonical_url_latest_version(self) -> None:
        """Test canonical URL for latest version page (no change)."""
        from unittest.mock import MagicMock

        from bengal.rendering.template_functions.seo import canonical_url

        # Mock site with versioning
        site = MagicMock()
        site.versioning_enabled = True
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
            sections=["docs"],
        )

        # Mock page on latest version
        page = MagicMock()
        page.version = "v3"

        result = canonical_url("/docs/guide/", "https://example.com", site, page)

        # Latest version - canonical unchanged
        assert result == "https://example.com/docs/guide/"

    def test_canonical_url_older_version(self) -> None:
        """Test canonical URL for older version points to latest."""
        from unittest.mock import MagicMock

        from bengal.rendering.template_functions.seo import canonical_url

        # Mock site with versioning
        site = MagicMock()
        site.versioning_enabled = True
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
            sections=["docs"],
        )

        # Mock page on older version
        page = MagicMock()
        page.version = "v2"

        # Path with version prefix
        result = canonical_url("/docs/v2/guide/", "https://example.com", site, page)

        # Should point to latest (no version prefix)
        assert result == "https://example.com/docs/guide/"

    def test_sitemap_priority_latest(self) -> None:
        """Test sitemap priority for latest version pages."""
        from unittest.mock import MagicMock

        from bengal.postprocess.sitemap import SitemapGenerator

        # Mock site
        site = MagicMock()
        site.versioning_enabled = True
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
        )

        generator = SitemapGenerator(site)

        # Mock page on latest version
        page = MagicMock()
        page.version = "v3"

        priority = generator._get_version_priority(page)
        assert priority == "0.8"  # Higher priority for latest

    def test_sitemap_priority_older_version(self) -> None:
        """Test sitemap priority for older version pages."""
        from unittest.mock import MagicMock

        from bengal.postprocess.sitemap import SitemapGenerator

        # Mock site
        site = MagicMock()
        site.versioning_enabled = True
        site.version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v2"),
            ],
        )

        generator = SitemapGenerator(site)

        # Mock page on older version
        page = MagicMock()
        page.version = "v2"

        priority = generator._get_version_priority(page)
        assert priority == "0.3"  # Lower priority for older

    def test_sitemap_priority_non_versioned(self) -> None:
        """Test sitemap priority for non-versioned pages."""
        from unittest.mock import MagicMock

        from bengal.postprocess.sitemap import SitemapGenerator

        # Mock site (versioning disabled)
        site = MagicMock()
        site.versioning_enabled = False

        generator = SitemapGenerator(site)

        # Mock non-versioned page
        page = MagicMock()
        page.version = None

        priority = generator._get_version_priority(page)
        assert priority == "0.5"  # Default priority
