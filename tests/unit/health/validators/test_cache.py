"""Tests for cache validator.

Tests health/validators/cache.py:
- CacheValidator: incremental build cache integrity checks
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.cache import CacheValidator


@pytest.fixture
def validator():
    """Create CacheValidator instance."""
    return CacheValidator()


@pytest.fixture
def mock_site(tmp_path):
    """Create mock site with configurable cache."""
    site = MagicMock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.output_dir.mkdir(parents=True, exist_ok=True)
    site.config = {"incremental": True}
    return site


class TestCacheValidatorBasics:
    """Tests for CacheValidator basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Cache Integrity"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates incremental build cache"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestCacheValidatorIncrementalDisabled:
    """Tests when incremental builds are disabled."""

    def test_skips_when_incremental_disabled(self, validator, mock_site):
        """Returns info when incremental builds not enabled."""
        mock_site.config = {"incremental": False}
        results = validator.validate(mock_site)
        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert "not enabled" in results[0].message


class TestCacheValidatorNoCacheFile:
    """Tests when cache file doesn't exist."""

    def test_info_when_no_cache_exists(self, validator, mock_site):
        """Returns info when no cache file exists (first build)."""
        results = validator.validate(mock_site)
        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert len(info_results) >= 1
        assert any("No cache file" in r.message or "first build" in r.message for r in info_results)


class TestCacheValidatorLegacyLocation:
    """Tests for legacy cache location handling."""

    def test_warns_about_legacy_location(self, validator, mock_site):
        """Warns when cache is at legacy location."""
        # Create cache at old location
        old_cache_path = mock_site.output_dir / ".bengal-cache.json"
        old_cache_path.write_text(
            json.dumps({"file_hashes": {}, "dependencies": {}})
        )

        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("legacy location" in r.message.lower() for r in warning_results)


class TestCacheValidatorCacheReadable:
    """Tests for cache file readability."""

    def test_success_when_cache_readable(self, validator, mock_site):
        """Returns success when cache file is readable."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(json.dumps({"file_hashes": {}, "dependencies": {}}))

        results = validator.validate(mock_site)
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("readable" in r.message.lower() for r in success_results)

    def test_error_when_cache_invalid_json(self, validator, mock_site):
        """Returns error when cache file has invalid JSON."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text("not valid json {{{")

        results = validator.validate(mock_site)
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1


class TestCacheValidatorStructure:
    """Tests for cache structure validation."""

    def test_success_when_structure_valid(self, validator, mock_site):
        """Returns success when cache has valid structure."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(json.dumps({"file_hashes": {}, "dependencies": {}}))

        results = validator.validate(mock_site)
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("structure valid" in r.message.lower() for r in success_results)

    def test_error_when_missing_file_hashes(self, validator, mock_site):
        """Returns error when cache missing file_hashes."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(json.dumps({"dependencies": {}}))

        results = validator.validate(mock_site)
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("invalid" in r.message.lower() for r in error_results)

    def test_error_when_file_hashes_not_dict(self, validator, mock_site):
        """Returns error when file_hashes is not a dict."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(json.dumps({"file_hashes": "not a dict", "dependencies": {}}))

        results = validator.validate(mock_site)
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1


class TestCacheValidatorSize:
    """Tests for cache size validation."""

    def test_reasonable_size_success(self, validator, mock_site):
        """Returns success for reasonably sized cache."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        # Small cache
        cache_path.write_text(json.dumps({"file_hashes": {}, "dependencies": {}}))

        results = validator.validate(mock_site)
        # Should have a success message about size
        size_results = [
            r for r in results
            if "size" in r.message.lower() or "MB" in r.message
        ]
        assert len(size_results) >= 1

    def test_warns_on_large_file_count(self, validator, mock_site):
        """Warns when tracking many files."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"

        # Create cache with many files (over 10000)
        file_hashes = {f"file_{i}.md": f"hash_{i}" for i in range(11000)}
        cache_path.write_text(json.dumps({"file_hashes": file_hashes, "dependencies": {}}))

        results = validator.validate(mock_site)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("large" in r.message.lower() or "10,000" in r.message for r in warning_results)


class TestCacheValidatorDependencies:
    """Tests for dependency tracking validation."""

    def test_info_when_no_dependencies(self, validator, mock_site):
        """Returns info when no dependencies tracked."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(json.dumps({"file_hashes": {}, "dependencies": {}}))

        results = validator.validate(mock_site)
        info_results = [r for r in results if r.status == CheckStatus.INFO]
        assert any(
            "no dependencies" in r.message.lower() or "not tracked" in r.message.lower()
            for r in info_results
        )

    def test_success_when_dependencies_valid(self, validator, mock_site):
        """Returns success when dependencies point to existing files."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"

        # Create a real file that's in dependencies
        test_file = mock_site.root_path / "content" / "test.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")

        cache_data = {
            "file_hashes": {},
            "dependencies": {str(test_file): ["dep1.md"]},
        }
        cache_path.write_text(json.dumps(cache_data))

        results = validator.validate(mock_site)
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("valid" in r.message.lower() for r in success_results)


class TestCacheValidatorPrivateMethods:
    """Tests for private helper methods."""

    def test_check_cache_readable_valid_json(self, validator, tmp_path):
        """_check_cache_readable returns True for valid JSON."""
        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps({"test": "data"}))

        readable, data = validator._check_cache_readable(cache_path)
        assert readable is True
        assert data == {"test": "data"}

    def test_check_cache_readable_invalid_json(self, validator, tmp_path):
        """_check_cache_readable returns False for invalid JSON."""
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("not json")

        readable, data = validator._check_cache_readable(cache_path)
        assert readable is False
        assert data == {}

    def test_check_cache_structure_valid(self, validator):
        """_check_cache_structure returns True for valid structure."""
        cache_data = {"file_hashes": {}, "dependencies": {}}
        valid, issues = validator._check_cache_structure(cache_data)
        assert valid is True
        assert issues == []

    def test_check_cache_structure_missing_key(self, validator):
        """_check_cache_structure returns False when key missing."""
        cache_data = {"file_hashes": {}}  # Missing dependencies
        valid, issues = validator._check_cache_structure(cache_data)
        assert valid is False
        assert len(issues) >= 1


class TestCacheValidatorCorrectLocation:
    """Tests for cache location correctness."""

    def test_success_when_at_correct_location(self, validator, mock_site):
        """Returns success when cache is at correct .bengal/ location."""
        cache_dir = mock_site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"
        cache_path.write_text(json.dumps({"file_hashes": {}, "dependencies": {}}))

        results = validator.validate(mock_site)
        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("correct location" in r.message.lower() for r in success_results)



