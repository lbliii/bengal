"""
Unit tests for bengal.build.detectors.data.

Tests DataChangeDetector for data file change detection.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import RebuildReasonCode
from bengal.build.detectors.data import DataChangeDetector, DATA_FILE_EXTENSIONS


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create mock BuildCache."""
    cache = MagicMock()
    cache.is_changed.return_value = False
    cache.get_affected_pages.return_value = []
    return cache


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site with temp directory."""
    site = MagicMock()
    site.root_path = tmp_path
    site.pages = []
    return site


@pytest.fixture
def detector() -> DataChangeDetector:
    """Create DataChangeDetector instance."""
    return DataChangeDetector()


# =============================================================================
# Basic Detection Tests
# =============================================================================


class TestDataChangeDetectorBasics:
    """Basic tests for DataChangeDetector."""

    def test_no_data_dir_returns_empty(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Missing data directory returns empty result."""
        # Don't create data dir
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()
        assert result.data_files_changed == frozenset()

    def test_empty_data_dir_returns_empty(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Empty data directory returns empty result."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.pages_to_rebuild == frozenset()
        assert result.data_files_changed == frozenset()


# =============================================================================
# File Extension Tests
# =============================================================================


class TestFileExtensions:
    """Tests for data file extension handling."""

    def test_supported_extensions(self) -> None:
        """DATA_FILE_EXTENSIONS contains expected types."""
        assert ".yaml" in DATA_FILE_EXTENSIONS
        assert ".yml" in DATA_FILE_EXTENSIONS
        assert ".json" in DATA_FILE_EXTENSIONS
        assert ".toml" in DATA_FILE_EXTENSIONS

    def test_yaml_file_detected(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """YAML files are detected as data files."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("team.yaml" in str(k) for k in result.data_files_changed)

    def test_json_file_detected(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """JSON files are detected as data files."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "config.json").write_text('{"key": "value"}')
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("config.json" in str(k) for k in result.data_files_changed)

    def test_toml_file_detected(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """TOML files are detected as data files."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "settings.toml").write_text('key = "value"')
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("settings.toml" in str(k) for k in result.data_files_changed)

    def test_unsupported_extension_ignored(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Non-data files are ignored."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "readme.txt").write_text("not a data file")
        (data_dir / "script.py").write_text("print('hello')")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.data_files_changed == frozenset()


# =============================================================================
# Change Detection Tests
# =============================================================================


class TestChangeDetection:
    """Tests for data file change detection."""

    def test_unchanged_file_not_detected(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Unchanged data files don't trigger rebuild."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = False
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert result.data_files_changed == frozenset()

    def test_forced_data_file_detected(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Data file in forced_changed is detected."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = False
        
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            forced_changed=frozenset([CacheKey("data:data/team.yaml")]),
        )
        result = detector.detect(ctx)
        
        assert any("team.yaml" in str(k) for k in result.data_files_changed)


# =============================================================================
# Affected Pages Tests
# =============================================================================


class TestAffectedPages:
    """Tests for affected page detection."""

    def test_affected_pages_from_cache(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Pages affected by data file change are detected."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = ["content/about.md", "content/team.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert CacheKey("content/about.md") in result.pages_to_rebuild
        assert CacheKey("content/team.md") in result.pages_to_rebuild

    def test_fallback_to_all_pages_when_no_dependents(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """All pages rebuild when no dependency info available."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        # Add some pages to site
        page1 = MagicMock()
        page1.source_path = mock_site.root_path / "content" / "about.md"
        page1.metadata = {}
        
        page2 = MagicMock()
        page2.source_path = mock_site.root_path / "content" / "contact.md"
        page2.metadata = {}
        
        mock_site.pages = [page1, page2]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = []  # No dependency info
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        # Should rebuild all pages
        assert CacheKey("content/about.md") in result.pages_to_rebuild
        assert CacheKey("content/contact.md") in result.pages_to_rebuild

    def test_generated_pages_excluded_from_fallback(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Generated pages are excluded from fallback rebuild."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        page1 = MagicMock()
        page1.source_path = mock_site.root_path / "content" / "about.md"
        page1.metadata = {}
        
        page2 = MagicMock()
        page2.source_path = mock_site.root_path / "content" / "generated.md"
        page2.metadata = {"_generated": True}
        
        mock_site.pages = [page1, page2]
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = []
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert CacheKey("content/about.md") in result.pages_to_rebuild
        assert CacheKey("content/generated.md") not in result.pages_to_rebuild


# =============================================================================
# Rebuild Reason Tests
# =============================================================================


class TestRebuildReasons:
    """Tests for rebuild reason assignment."""

    def test_rebuild_reason_is_data_file_changed(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason code is DATA_FILE_CHANGED."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = ["content/about.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert reason.code == RebuildReasonCode.DATA_FILE_CHANGED

    def test_rebuild_reason_trigger_contains_file_path(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Rebuild reason trigger contains data file path."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = True
        mock_cache.get_affected_pages.return_value = ["content/about.md"]
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        reason = result.rebuild_reasons.get(CacheKey("content/about.md"))
        assert reason is not None
        assert "team.yaml" in reason.trigger


# =============================================================================
# Nested Data Directory Tests
# =============================================================================


class TestNestedDataDirectories:
    """Tests for nested data directory handling."""

    def test_nested_data_files_detected(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """Data files in nested directories are detected."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        nested_dir = data_dir / "config" / "settings"
        nested_dir.mkdir(parents=True)
        (nested_dir / "app.yaml").write_text("key: value")
        
        mock_cache.is_changed.return_value = True
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        result = detector.detect(ctx)
        
        assert any("app.yaml" in str(k) for k in result.data_files_changed)


# =============================================================================
# Dependency Key Format Tests
# =============================================================================


class TestDependencyKeyFormat:
    """Tests for correct dependency key format."""

    def test_affected_pages_uses_data_prefix_key(
        self, detector: DataChangeDetector, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """get_affected_pages is called with data: prefixed string key."""
        data_dir = mock_site.root_path / "data"
        data_dir.mkdir()
        (data_dir / "team.yaml").write_text("name: Team")
        
        mock_cache.is_changed.return_value = True
        
        # Track what keys get_affected_pages is called with
        called_with_keys: list[str] = []
        
        def track_affected_pages(dep_key: Path) -> set[str]:
            called_with_keys.append(str(dep_key))
            return set()
        
        mock_cache.get_affected_pages.side_effect = track_affected_pages
        
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        detector.detect(ctx)
        
        # Verify the key format includes "data:" prefix
        assert len(called_with_keys) > 0
        for key in called_with_keys:
            assert key.startswith("data:"), f"Expected data: prefix, got: {key}"
