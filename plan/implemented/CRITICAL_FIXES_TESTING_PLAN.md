# Testing & Validation Plan for Critical Fixes

**Date**: October 13, 2025  
**Related**: v0.1.2 Critical Bug Fixes

---

## Summary of Gaps Found

### 1. Cache Location Fix
- ❌ **Health Check**: `CacheValidator` still looks at OLD location
- ❌ **Tests**: No tests for cache migration
- ✅ **Logging**: Already added (migration, new location)

### 2. Slugification
- ✅ **Logging**: CLI feedback sufficient
- ❌ **Tests**: No unit tests for `_slugify()` function
- N/A **Health Check**: Not needed

### 3. Clean Command
- ✅ **Logging**: CLI output covers it
- ❌ **Tests**: No CLI tests for new flags
- N/A **Health Check**: Not applicable

---

## Required Updates

### 1. Update CacheValidator (CRITICAL)

**File**: `bengal/health/validators/cache.py`

**Problem**: Lines 58-59 still check old cache location:
```python
cache_path = site.output_dir / ".bengal-cache.json"
if not cache_path.exists():
```

**Solution**: Update to new location and check for migration status

```python
@override
def validate(self, site: "Site") -> list[CheckResult]:
    """Run cache validation checks."""
    results = []

    # Skip if incremental builds not used
    if not site.config.get("incremental", False):
        results.append(
            CheckResult.info(
                "Incremental builds not enabled",
                recommendation="Enable with 'incremental = true' in config for faster rebuilds.",
            )
        )
        return results

    # Check 1: New cache location
    cache_dir = site.root_path / ".bengal"
    cache_path = cache_dir / "cache.json"

    # Check for old cache location (migration needed)
    old_cache_path = site.output_dir / ".bengal-cache.json"
    if old_cache_path.exists() and not cache_path.exists():
        results.append(
            CheckResult.warning(
                "Cache still at old location (public/.bengal-cache.json)",
                recommendation="Run 'bengal build' to migrate cache to .bengal/cache.json automatically.",
            )
        )
        # Still validate the old cache for now
        cache_path = old_cache_path

    if not cache_path.exists():
        results.append(
            CheckResult.info(
                "No cache file found (first build or cache cleared)",
                recommendation="Cache will be created after first build at .bengal/cache.json",
            )
        )
        return results

    # Check 2: Cache file readable
    cache_readable, cache_data = self._check_cache_readable(cache_path)
    if not cache_readable:
        results.append(
            CheckResult.error(
                f"Cache file exists but cannot be read: {cache_path}",
                recommendation="Delete cache and rebuild: 'bengal clean --cache && bengal build'",
            )
        )
        return results

    results.append(CheckResult.success(f"Cache file readable at {cache_path}"))

    # Check 3: Cache structure valid
    structure_valid, structure_issues = self._check_cache_structure(cache_data)
    if not structure_valid:
        results.append(
            CheckResult.error(
                f"Cache structure invalid: {', '.join(structure_issues)}",
                recommendation="Cache may be corrupted: 'bengal clean --cache && bengal build'",
            )
        )
    else:
        results.append(CheckResult.success("Cache structure valid"))

    # Check 4: Cache size reasonable
    results.extend(self._check_cache_size(cache_path, cache_data))

    # Check 5: Cache location (new check)
    if cache_path == cache_dir / "cache.json":
        results.append(CheckResult.success("Cache at correct location (.bengal/)"))
    else:
        results.append(
            CheckResult.info(
                "Cache at legacy location (will be migrated)",
                recommendation="Run build to migrate automatically",
            )
        )

    return results
```

**Impact**: Ensures health checks work with new cache location

---

### 2. Add Cache Migration Tests

**New File**: `tests/unit/orchestration/test_cache_migration.py`

```python
"""
Test cache migration from old location to new location.
"""

from pathlib import Path
import json
import pytest
from bengal.core.site import Site
from bengal.orchestration.incremental import IncrementalOrchestrator


class TestCacheMigration:
    """Test automatic cache migration from public/ to .bengal/"""

    def test_old_cache_migrated_to_new_location(self, tmp_path):
        """Test that cache at old location is migrated automatically."""
        # Create site structure
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Create old cache
        public_dir = tmp_path / "public"
        public_dir.mkdir()
        old_cache = public_dir / ".bengal-cache.json"
        old_cache_data = {
            "file_hashes": {"content/index.md": "abc123"},
            "dependencies": {},
            "last_build": "2025-10-13T10:00:00"
        }
        old_cache.write_text(json.dumps(old_cache_data))

        # Create site and initialize incremental
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir

        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify migration occurred
        new_cache_path = tmp_path / ".bengal" / "cache.json"
        assert new_cache_path.exists(), "New cache should be created"
        assert len(cache.file_hashes) == 1, "Cache data should be migrated"
        assert cache.file_hashes["content/index.md"] == "abc123"

    def test_migration_preserves_cache_data(self, tmp_path):
        """Test that all cache fields are preserved during migration."""
        # Setup
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        # Create comprehensive old cache
        old_cache = public_dir / ".bengal-cache.json"
        old_cache_data = {
            "file_hashes": {
                "content/index.md": "hash1",
                "content/about.md": "hash2"
            },
            "dependencies": {
                "content/index.md": ["templates/base.html"]
            },
            "page_tags": {
                "content/index.md": ["tag1", "tag2"]
            },
            "tag_to_pages": {
                "tag1": ["content/index.md"]
            },
            "known_tags": ["tag1", "tag2"],
            "parsed_content": {
                "content/index.md": {
                    "html": "<p>Content</p>",
                    "toc": "<ul>...</ul>"
                }
            },
            "last_build": "2025-10-13T10:00:00"
        }
        old_cache.write_text(json.dumps(old_cache_data))

        # Migrate
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify all fields preserved
        assert len(cache.file_hashes) == 2
        assert "content/index.md" in cache.dependencies
        assert cache.page_tags["content/index.md"] == {"tag1", "tag2"}
        assert "tag1" in cache.known_tags
        assert "content/index.md" in cache.parsed_content

    def test_new_cache_not_overwritten_by_old(self, tmp_path):
        """Test that existing new cache is not overwritten by old cache."""
        # Create both caches
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        # Old cache (stale data)
        old_cache = public_dir / ".bengal-cache.json"
        old_cache.write_text(json.dumps({
            "file_hashes": {"old": "data"},
            "last_build": "2025-10-01T10:00:00"
        }))

        # New cache (current data)
        new_cache_dir = tmp_path / ".bengal"
        new_cache_dir.mkdir()
        new_cache = new_cache_dir / "cache.json"
        new_cache.write_text(json.dumps({
            "file_hashes": {"new": "data"},
            "last_build": "2025-10-13T10:00:00"
        }))

        # Initialize
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Verify new cache is used
        assert "new" in cache.file_hashes
        assert "old" not in cache.file_hashes

    def test_migration_failure_falls_back_to_fresh_cache(self, tmp_path):
        """Test graceful fallback if migration fails."""
        # Create corrupted old cache
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        public_dir = tmp_path / "public"
        public_dir.mkdir()

        old_cache = public_dir / ".bengal-cache.json"
        old_cache.write_text("invalid json{{{")

        # Should not crash
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        incremental = IncrementalOrchestrator(site)
        cache, tracker = incremental.initialize(enabled=True)

        # Should have fresh cache
        assert len(cache.file_hashes) == 0

    def test_cache_survives_clean_operation(self, tmp_path):
        """Test that cache persists after bengal clean."""
        # Create site with cache
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        public_dir = tmp_path / "public"
        public_dir.mkdir()

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text(json.dumps({"file_hashes": {"test": "data"}}))

        # Create site and clean
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        site.output_dir = public_dir
        site.clean()

        # Verify cache still exists
        assert cache_file.exists(), "Cache should survive clean"
        assert not public_dir.exists() or len(list(public_dir.glob("*"))) == 0, "Output should be empty"
```

**Impact**: Ensures migration works correctly and cache persists

---

### 3. Add Slugification Tests

**New File**: `tests/unit/cli/test_slugify.py`

```python
"""
Test page name slugification.
"""

import pytest
from bengal.cli.commands.new import _slugify


class TestSlugify:
    """Test _slugify() function."""

    def test_basic_slugification(self):
        """Test basic space to hyphen conversion."""
        assert _slugify("My Page") == "my-page"
        assert _slugify("Test Page") == "test-page"

    def test_lowercase_conversion(self):
        """Test that text is lowercased."""
        assert _slugify("UPPERCASE") == "uppercase"
        assert _slugify("MiXeD CaSe") == "mixed-case"

    def test_special_characters_removed(self):
        """Test special character removal."""
        assert _slugify("Hello, World!") == "hello-world"
        assert _slugify("Test@#$%Page") == "testpage"
        assert _slugify("C++ Programming") == "c-programming"

    def test_multiple_spaces_collapsed(self):
        """Test that multiple spaces become single hyphen."""
        assert _slugify("Test   Multiple   Spaces") == "test-multiple-spaces"
        assert _slugify("A  B  C") == "a-b-c"

    def test_multiple_hyphens_collapsed(self):
        """Test that multiple hyphens become single hyphen."""
        assert _slugify("Test--Page") == "test-page"
        assert _slugify("A---B") == "a-b"

    def test_edge_hyphens_stripped(self):
        """Test that leading/trailing hyphens are removed."""
        assert _slugify("-test-") == "test"
        assert _slugify("--test--") == "test"
        assert _slugify(" test ") == "test"

    def test_empty_string(self):
        """Test empty string handling."""
        assert _slugify("") == ""
        assert _slugify("   ") == ""

    def test_only_special_characters(self):
        """Test string with only special characters."""
        assert _slugify("!!!") == ""
        assert _slugify("@#$%") == ""

    def test_unicode_handling(self):
        """Test unicode character handling."""
        # Basic ASCII letters preserved
        assert _slugify("café") == "caf"  # é removed as special char
        # Numbers preserved
        assert _slugify("test123") == "test123"

    def test_existing_hyphenated_slugs(self):
        """Test that proper slugs pass through unchanged."""
        assert _slugify("my-page") == "my-page"
        assert _slugify("test-slug") == "test-slug"

    def test_mixed_separators(self):
        """Test various separator combinations."""
        assert _slugify("test_page-slug name") == "test_page-slug-name"
        # Underscores preserved (word characters)
        assert _slugify("test_name") == "test_name"

    def test_numbers_preserved(self):
        """Test that numbers are kept."""
        assert _slugify("Test 123") == "test-123"
        assert _slugify("Page 2.0") == "page-20"

    def test_real_world_examples(self):
        """Test realistic page names."""
        assert _slugify("Getting Started") == "getting-started"
        assert _slugify("API Reference") == "api-reference"
        assert _slugify("Quick Start Guide") == "quick-start-guide"
        assert _slugify("v1.2.3 Release Notes") == "v123-release-notes"
```

**Impact**: Ensures slugification handles all edge cases

---

### 4. Add Clean Command Tests

**New File**: `tests/unit/cli/test_clean_command.py`

```python
"""
Test clean command with new cache options.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner
from bengal.cli.commands.clean import clean
from bengal.core.site import Site


class TestCleanCommand:
    """Test clean command behavior."""

    def test_clean_default_preserves_cache(self, tmp_path):
        """Test that default clean preserves cache."""
        # Setup site
        self._create_test_site(tmp_path)

        # Create cache
        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        # Create output
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html>test</html>")

        # Run clean
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert cache_file.exists(), "Cache should be preserved"
        assert not (output_dir / "index.html").exists(), "Output should be removed"

    def test_clean_with_cache_flag_removes_cache(self, tmp_path):
        """Test that --cache flag removes cache."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        output_dir = tmp_path / "public"
        output_dir.mkdir()

        # Run clean with --cache
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", "--cache", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert not cache_dir.exists(), "Cache should be removed"

    def test_clean_with_all_flag_removes_cache(self, tmp_path):
        """Test that --all flag removes cache."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        # Run clean with --all
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", "--all", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert not cache_dir.exists(), "Cache should be removed"

    def test_clean_messaging_indicates_cache_status(self, tmp_path):
        """Test that clean command shows correct messaging."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()

        # Test default mode
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", str(tmp_path)])
        assert "cache preserved" in result.output.lower() or "cache" in result.output.lower()

        # Test cache mode
        result = runner.invoke(clean, ["--force", "--cache", str(tmp_path)])
        assert "cache" in result.output.lower()

    def _create_test_site(self, tmp_path):
        """Helper to create test site structure."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"

[build]
output_dir = "public"
""")
```

**Impact**: Ensures clean command flags work correctly

---

### 5. Integration Test for Full Workflow

**New File**: `tests/integration/test_cache_persistence.py`

```python
"""
Integration test for cache persistence through clean operations.
"""

import pytest
from pathlib import Path
from bengal.core.site import Site


class TestCachePersistence:
    """Test that cache persists through typical workflows."""

    def test_build_clean_build_uses_cache(self, tmp_path):
        """Test that incremental build works after clean."""
        # Create site
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")
        (content_dir / "about.md").write_text("---\ntitle: About\n---\n# About")

        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[build]
output_dir = "public"
incremental = true
""")

        # First build (creates cache)
        site = Site.from_config(tmp_path)
        stats1 = site.build(incremental=True)

        # Verify cache created
        cache_path = tmp_path / ".bengal" / "cache.json"
        assert cache_path.exists()

        # Clean (output only)
        site.clean()

        # Verify cache still exists
        assert cache_path.exists()

        # Second build (should use cache)
        site2 = Site.from_config(tmp_path)
        stats2 = site2.build(incremental=True)

        # Verify used cache (would rebuild everything if cache was gone)
        assert cache_path.exists()

    def test_cold_build_after_clean_cache(self, tmp_path):
        """Test clean --cache forces cold build."""
        # Setup
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        config_file = tmp_path / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test"

[build]
output_dir = "public"
incremental = true
""")

        # First build
        site = Site.from_config(tmp_path)
        site.build(incremental=True)

        cache_dir = tmp_path / ".bengal"
        assert cache_dir.exists()

        # Clean with cache removal
        import shutil
        site.clean()
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        # Verify cache gone
        assert not cache_dir.exists()

        # Rebuild (cold build)
        site2 = Site.from_config(tmp_path)
        stats = site2.build(incremental=True)

        # Cache should be recreated
        assert cache_dir.exists()
```

**Impact**: Validates end-to-end cache behavior

---

## Implementation Priority

### Phase 1: Critical (Before v0.1.2 release)
1. ✅ **Update CacheValidator** - 15 minutes
2. ✅ **Add cache migration tests** - 30 minutes
3. ✅ **Add slugification tests** - 20 minutes

### Phase 2: Important (Can ship without)
4. **Add clean command tests** - 30 minutes
5. **Add integration test** - 20 minutes

### Phase 3: Nice to Have
6. **Add logging tests** - If time permits
7. **Performance benchmarks** - Compare cache lookup speeds

---

## Summary

### What's Already Good
✅ Logging is comprehensive (migration, cache location)  
✅ Migration code is robust (graceful fallback)  
✅ CLI messaging is clear  

### What Needs Fixing
❌ CacheValidator checks old location  
❌ No tests for migration logic  
❌ No tests for slugification  
❌ No tests for clean command flags  

### Estimated Time
- Critical updates: **~1 hour**
- Full test suite: **~2 hours**
- Worth it for production confidence: **Absolutely**

---

**Next Steps**: Implement Phase 1 (critical) before releasing v0.1.2
