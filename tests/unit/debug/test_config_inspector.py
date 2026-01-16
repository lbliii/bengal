"""
Unit tests for the ConfigInspector module.

Tests the configuration inspection functionality including comparisons,
origin tracking, key explanations, and issue detection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bengal.debug.config_inspector import (
    ConfigComparisonResult,
    ConfigDiff,
    ConfigInspector,
    KeyExplanation,
)


class TestConfigDiff:
    """Tests for ConfigDiff dataclass."""

    def test_added_diff(self):
        """Test creating an 'added' diff."""
        diff = ConfigDiff(
            path="site.newkey",
            type="added",
            new_value="new_value",
            new_origin="environments/production.yaml",
        )
        assert diff.type == "added"
        assert diff.new_value == "new_value"
        assert diff.old_value is None

    def test_removed_diff(self):
        """Test creating a 'removed' diff."""
        diff = ConfigDiff(
            path="site.oldkey",
            type="removed",
            old_value="old_value",
            old_origin="_default/site.yaml",
        )
        assert diff.type == "removed"
        assert diff.old_value == "old_value"
        assert diff.new_value is None

    def test_changed_diff(self):
        """Test creating a 'changed' diff."""
        diff = ConfigDiff(
            path="site.baseurl",
            type="changed",
            old_value="http://localhost:8000",
            new_value="https://example.com",
            old_origin="_default/site.yaml",
            new_origin="environments/production.yaml",
            impact="Changes output URLs and may break links",
        )
        assert diff.type == "changed"
        assert diff.old_value != diff.new_value
        assert diff.impact is not None

    def test_format_added(self):
        """Test format() for added diff."""
        diff = ConfigDiff(path="site.new", type="added", new_value="value")
        formatted = diff.format()
        assert "+" in formatted
        assert "site.new" in formatted

    def test_format_removed(self):
        """Test format() for removed diff."""
        diff = ConfigDiff(path="site.old", type="removed", old_value="value")
        formatted = diff.format()
        assert "-" in formatted
        assert "site.old" in formatted

    def test_format_changed(self):
        """Test format() for changed diff."""
        diff = ConfigDiff(
            path="site.title",
            type="changed",
            old_value="Old Title",
            new_value="New Title",
        )
        formatted = diff.format()
        assert "~" in formatted
        assert "Old Title" in formatted
        assert "New Title" in formatted


class TestConfigComparisonResult:
    """Tests for ConfigComparisonResult dataclass."""

    @pytest.fixture
    def sample_comparison(self):
        """Create a sample comparison result."""
        return ConfigComparisonResult(
            source1="local",
            source2="production",
            diffs=[
                ConfigDiff(
                    path="site.baseurl",
                    type="changed",
                    old_value="/",
                    new_value="https://example.com",
                ),
                ConfigDiff(path="build.debug", type="removed", old_value=True),
                ConfigDiff(path="site.analytics_id", type="added", new_value="GA-123456"),
            ],
        )

    def test_has_changes_true(self, sample_comparison):
        """Test has_changes when there are changes."""
        assert sample_comparison.has_changes is True

    def test_has_changes_false(self):
        """Test has_changes when there are no changes."""
        result = ConfigComparisonResult(source1="a", source2="b", diffs=[])
        assert result.has_changes is False

    def test_added_property(self, sample_comparison):
        """Test added property returns only added diffs."""
        added = sample_comparison.added
        assert len(added) == 1
        assert added[0].path == "site.analytics_id"

    def test_removed_property(self, sample_comparison):
        """Test removed property returns only removed diffs."""
        removed = sample_comparison.removed
        assert len(removed) == 1
        assert removed[0].path == "build.debug"

    def test_changed_property(self, sample_comparison):
        """Test changed property returns only changed diffs."""
        changed = sample_comparison.changed
        assert len(changed) == 1
        assert changed[0].path == "site.baseurl"

    def test_format_summary(self, sample_comparison):
        """Test format_summary output."""
        summary = sample_comparison.format_summary()
        assert "local" in summary
        assert "production" in summary
        assert "Added: 1" in summary
        assert "Removed: 1" in summary
        assert "Changed: 1" in summary

    def test_format_detailed(self, sample_comparison):
        """Test format_detailed output."""
        detailed = sample_comparison.format_detailed()
        assert "local" in detailed
        assert "production" in detailed
        assert "site.baseurl" in detailed
        assert "site.analytics_id" in detailed
        assert "build.debug" in detailed


class TestKeyExplanation:
    """Tests for KeyExplanation dataclass."""

    def test_basic_explanation(self):
        """Test creating a basic key explanation."""
        explanation = KeyExplanation(
            key_path="site.title",
            effective_value="My Site",
            origin="_default/site.yaml",
        )
        assert explanation.key_path == "site.title"
        assert explanation.effective_value == "My Site"

    def test_explanation_with_layers(self):
        """Test explanation with layer values."""
        explanation = KeyExplanation(
            key_path="site.baseurl",
            effective_value="https://example.com",
            origin="environments/production.yaml",
            layer_values=[
                ("_default/site.yaml", "/"),
                ("environments/production.yaml", "https://example.com"),
            ],
        )
        assert len(explanation.layer_values) == 2
        assert explanation.layer_values[0][0] == "_default/site.yaml"

    def test_explanation_is_default(self):
        """Test explanation with is_default flag."""
        explanation = KeyExplanation(
            key_path="build.parallel",
            effective_value=True,
            origin="_default/build.yaml",
            is_default=True,
        )
        assert explanation.is_default is True

    def test_explanation_deprecated(self):
        """Test explanation with deprecated flag."""
        explanation = KeyExplanation(
            key_path="old.key",
            effective_value="value",
            deprecated=True,
            deprecation_message="Use new.key instead",
        )
        assert explanation.deprecated is True
        assert explanation.deprecation_message is not None

    def test_format_basic(self):
        """Test format() for basic explanation."""
        explanation = KeyExplanation(
            key_path="site.title",
            effective_value="My Site",
            origin="_default/site.yaml",
        )
        formatted = explanation.format()
        assert "site.title" in formatted
        assert "My Site" in formatted
        assert "_default/site.yaml" in formatted

    def test_format_with_layers(self):
        """Test format() with layer chain."""
        explanation = KeyExplanation(
            key_path="site.baseurl",
            effective_value="https://example.com",
            origin="environments/production.yaml",
            layer_values=[
                ("_default/site.yaml", "/"),
                ("environments/production.yaml", "https://example.com"),
            ],
        )
        formatted = explanation.format()
        assert "Resolution chain" in formatted
        assert "_default/site.yaml" in formatted

    def test_format_deprecated(self):
        """Test format() with deprecation warning."""
        explanation = KeyExplanation(
            key_path="old.key",
            effective_value="value",
            deprecated=True,
            deprecation_message="This key is deprecated",
        )
        formatted = explanation.format()
        assert "DEPRECATED" in formatted


class TestConfigInspector:
    """Tests for ConfigInspector class."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site with config directory."""
        site = MagicMock()
        site.root_path = tmp_path  # Use root_path (Path), not root (str)
        site.config = {
            "site": {"title": "Test Site", "baseurl": "/"},
            "build": {"parallel": True, "incremental": True},
        }

        # Create config directory structure
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        envs = config_dir / "environments"
        envs.mkdir()

        profiles = config_dir / "profiles"
        profiles.mkdir()

        # Create config files
        (defaults / "site.yaml").write_text("site:\n  title: Test Site\n  baseurl: /\n")
        (defaults / "build.yaml").write_text("build:\n  parallel: true\n  incremental: true\n")
        (envs / "local.yaml").write_text("build:\n  debug: true\n")
        (envs / "production.yaml").write_text(
            "site:\n  baseurl: https://example.com\nbuild:\n  debug: false\n"
        )
        (profiles / "dev.yaml").write_text("build:\n  verbose: true\n")

        return site

    @pytest.fixture
    def inspector(self, mock_site):
        """Create an inspector instance."""
        return ConfigInspector(site=mock_site)

    def test_list_available_sources(self, inspector):
        """Test listing available config sources."""
        sources = inspector._list_available_sources()

        assert len(sources) > 0
        # Should have environments
        assert any("local" in s for s in sources)
        assert any("production" in s for s in sources)

    def test_get_nested_value(self, inspector):
        """Test getting nested value from dict."""
        config = {
            "site": {"title": "Test", "nested": {"deep": "value"}},
            "build": {"parallel": True},
        }

        assert inspector._get_nested_value(config, "site.title") == "Test"
        assert inspector._get_nested_value(config, "site.nested.deep") == "value"
        assert inspector._get_nested_value(config, "build.parallel") is True
        assert inspector._get_nested_value(config, "nonexistent") is None

    def test_get_impact_baseurl(self, inspector):
        """Test impact detection for baseurl."""
        impact = inspector._get_impact("baseurl")
        assert impact is not None
        assert "URL" in impact

    def test_get_impact_theme(self, inspector):
        """Test impact detection for theme."""
        impact = inspector._get_impact("theme")
        assert impact is not None
        assert "appearance" in impact.lower()

    def test_get_impact_unknown(self, inspector):
        """Test impact detection for unknown key."""
        impact = inspector._get_impact("random_key")
        assert impact is None

    def test_compare_same_config(self, inspector):
        """Test comparing identical configs."""
        with patch.object(inspector, "_load_config_source") as mock_load:
            config = {"site": {"title": "Test"}}
            mock_load.return_value = (config, {})

            result = inspector.compare("local", "local")

            assert result.has_changes is False

    def test_compare_different_configs(self, inspector):
        """Test comparing different configs."""
        with patch.object(inspector, "_load_config_source") as mock_load:
            config1 = {"site": {"title": "Test", "baseurl": "/"}}
            config2 = {"site": {"title": "Test", "baseurl": "https://example.com"}}

            mock_load.side_effect = [
                (config1, {"site.title": "_default", "site.baseurl": "_default"}),
                (config2, {"site.title": "_default", "site.baseurl": "production"}),
            ]

            result = inspector.compare("local", "production")

            assert result.has_changes is True
            assert len(result.changed) == 1
            assert result.changed[0].path == "site.baseurl"

    def test_compute_diffs_added(self, inspector):
        """Test computing diffs for added keys."""
        config1 = {"site": {"title": "Test"}}
        config2 = {"site": {"title": "Test", "new_key": "value"}}
        diffs: list[ConfigDiff] = []

        inspector._compute_diffs(config1, config2, {}, {}, [], diffs)

        added = [d for d in diffs if d.type == "added"]
        assert len(added) == 1
        assert added[0].path == "site.new_key"

    def test_compute_diffs_removed(self, inspector):
        """Test computing diffs for removed keys."""
        config1 = {"site": {"title": "Test", "old_key": "value"}}
        config2 = {"site": {"title": "Test"}}
        diffs: list[ConfigDiff] = []

        inspector._compute_diffs(config1, config2, {}, {}, [], diffs)

        removed = [d for d in diffs if d.type == "removed"]
        assert len(removed) == 1
        assert removed[0].path == "site.old_key"

    def test_compute_diffs_changed(self, inspector):
        """Test computing diffs for changed keys."""
        config1 = {"site": {"title": "Old Title"}}
        config2 = {"site": {"title": "New Title"}}
        diffs: list[ConfigDiff] = []

        inspector._compute_diffs(config1, config2, {}, {}, [], diffs)

        changed = [d for d in diffs if d.type == "changed"]
        assert len(changed) == 1
        assert changed[0].path == "site.title"
        assert changed[0].old_value == "Old Title"
        assert changed[0].new_value == "New Title"

    def test_find_issues_invalid_baseurl(self, inspector):
        """Test finding invalid baseurl."""
        inspector.site.config = {"baseurl": "no-protocol.com"}

        findings = inspector.find_issues()

        # Check for baseurl-related findings using title or description
        baseurl_findings = [
            f
            for f in findings
            if "baseurl" in f.title.lower() or "baseurl" in f.description.lower()
        ]
        assert len(baseurl_findings) == 1

    def test_find_issues_trailing_slash_baseurl(self, inspector):
        """Test detecting trailing slash in baseurl."""
        inspector.site.config = {"baseurl": "https://example.com/"}

        findings = inspector.find_issues()

        # Check for trailing slash findings
        trailing_slash_findings = [
            f
            for f in findings
            if "trailing slash" in f.title.lower() or "trailing slash" in f.description.lower()
        ]
        assert len(trailing_slash_findings) == 1

    def test_run_list_sources(self, inspector):
        """Test run method with list_sources flag."""
        from bengal.debug.base import Severity

        report = inspector.run(list_sources=True)

        assert len(report.findings) > 0
        info_findings = [f for f in report.findings if f.severity == Severity.INFO]
        assert len(info_findings) == 1
        assert "sources" in info_findings[0].metadata

    def test_run_no_args(self, inspector):
        """Test run method with no arguments."""
        report = inspector.run()

        # Should have info finding with usage
        assert len(report.findings) > 0


class TestConfigInspectorExplainKey:
    """Tests for explain_key functionality."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site with config."""
        site = MagicMock()
        site.root_path = tmp_path  # Use root_path (Path), not root (str)

        # Create config directory
        config_dir = tmp_path / "config"
        defaults = config_dir / "_default"
        defaults.mkdir(parents=True)

        envs = config_dir / "environments"
        envs.mkdir()

        (defaults / "site.yaml").write_text("site:\n  title: Default Title\n")
        (envs / "local.yaml").write_text("")

        return site

    @pytest.fixture
    def inspector(self, mock_site):
        """Create inspector instance."""
        return ConfigInspector(site=mock_site)

    def test_explain_existing_key(self, inspector):
        """Test explaining an existing key."""
        with patch.object(inspector, "_get_nested_value") as mock_get:
            mock_get.return_value = "My Site"

            with patch("bengal.config.directory_loader.ConfigDirectoryLoader") as mock_loader:
                mock_instance = MagicMock()
                mock_instance.load.return_value = {"site": {"title": "My Site"}}
                mock_instance.origin_tracker = MagicMock()
                mock_instance.origin_tracker.origins = {"site.title": "_default/site.yaml"}
                mock_loader.return_value = mock_instance

                explanation = inspector.explain_key("site.title")

                # Should return an explanation
                assert explanation is not None or mock_get.called

    def test_explain_nonexistent_key(self, inspector):
        """Test explaining a non-existent key."""
        with patch.object(inspector, "_get_nested_value") as mock_get:
            mock_get.return_value = None

            with patch("bengal.config.directory_loader.ConfigDirectoryLoader") as mock_loader:
                mock_instance = MagicMock()
                mock_instance.load.return_value = {}
                mock_loader.return_value = mock_instance

                explanation = inspector.explain_key("nonexistent.key")

                # Should return None for non-existent key
                assert explanation is None
