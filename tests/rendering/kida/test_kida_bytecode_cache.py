"""Tests for Kida bytecode cache.

Tests persistent template caching for fast cold-start.
"""

import time

import pytest

from bengal.rendering.kida.bytecode_cache import BytecodeCache, hash_source


class TestBytecodeCache:
    """Tests for bytecode cache."""

    @pytest.fixture
    def cache_dir(self, tmp_path):
        """Create a temporary cache directory."""
        return tmp_path / "kida_cache"

    @pytest.fixture
    def cache(self, cache_dir):
        """Create a bytecode cache instance."""
        return BytecodeCache(cache_dir)

    def test_cache_directory_created(self, cache_dir):
        """Cache directory is created automatically."""
        assert not cache_dir.exists()
        BytecodeCache(cache_dir)
        assert cache_dir.exists()

    def test_get_miss(self, cache):
        """Get returns None for missing cache entry."""
        result = cache.get("missing.html", "abc123")
        assert result is None

    def test_set_and_get(self, cache):
        """Set stores bytecode and get retrieves it."""
        # Compile a simple code object
        code = compile("x = 1 + 2", "<test>", "exec")
        source_hash = hash_source("x = 1 + 2")

        # Store it
        cache.set("test.html", source_hash, code)

        # Retrieve it
        result = cache.get("test.html", source_hash)
        assert result is not None
        assert result.co_code == code.co_code

    def test_hash_invalidation(self, cache):
        """Changed source hash returns miss."""
        code = compile("x = 1", "<test>", "exec")
        hash1 = hash_source("x = 1")
        hash2 = hash_source("x = 2")

        cache.set("test.html", hash1, code)

        # Original hash hits
        assert cache.get("test.html", hash1) is not None

        # Different hash misses
        assert cache.get("test.html", hash2) is None

    def test_clear_all(self, cache):
        """Clear removes all cache entries."""
        code = compile("x = 1", "<test>", "exec")

        cache.set("a.html", hash_source("a"), code)
        cache.set("b.html", hash_source("b"), code)

        stats = cache.stats()
        assert stats["file_count"] == 2

        removed = cache.clear()
        assert removed == 2

        stats = cache.stats()
        assert stats["file_count"] == 0

    def test_clear_current_version_only(self, cache, cache_dir):
        """Clear with current_version_only only removes current version."""
        code = compile("x = 1", "<test>", "exec")

        cache.set("a.html", hash_source("a"), code)

        # Create a fake cache file for a "different" Python version
        fake_version = "py99"
        fake_file = cache_dir / f"__kida_{fake_version}_b_1234567890123456.pyc"
        fake_file.write_bytes(b"fake")

        # Clear current version only
        removed = cache.clear(current_version_only=True)
        assert removed == 1

        # Fake version file should still exist
        assert fake_file.exists()

    def test_stats(self, cache):
        """Stats returns file count and size."""
        code = compile("x = 1", "<test>", "exec")

        cache.set("test.html", hash_source("test"), code)

        stats = cache.stats()
        assert stats["file_count"] == 1
        assert stats["total_bytes"] > 0

    def test_cleanup_removes_old_files(self, cache, cache_dir):
        """Cleanup removes files older than max_age_days."""
        code = compile("x = 1", "<test>", "exec")

        # Create an old file by manually writing and setting mtime
        old_path = cache_dir / "__kida_py312_old_1234567890123456.pyc"
        old_path.write_bytes(b"old")
        # Set mtime to 35 days ago
        old_mtime = time.time() - (35 * 86400)
        import os

        os.utime(old_path, (old_mtime, old_mtime))

        # Create a recent file
        cache.set("recent.html", hash_source("recent"), code)

        # Verify both files exist
        assert old_path.exists()
        assert cache.stats()["file_count"] == 2

        # Cleanup with 30 day threshold
        removed = cache.cleanup(max_age_days=30)
        assert removed == 1

        # Old file should be gone, recent file should remain
        assert not old_path.exists()
        assert cache.stats()["file_count"] == 1

    def test_cleanup_preserves_recent_files(self, cache):
        """Cleanup preserves files newer than max_age_days."""
        code = compile("x = 1", "<test>", "exec")

        # Create recent files
        cache.set("a.html", hash_source("a"), code)
        cache.set("b.html", hash_source("b"), code)

        assert cache.stats()["file_count"] == 2

        # Cleanup with 30 day threshold (all files are recent)
        removed = cache.cleanup(max_age_days=30)
        assert removed == 0

        # All files should remain
        assert cache.stats()["file_count"] == 2

    def test_cleanup_respects_max_age_days(self, cache, cache_dir):
        """Cleanup respects the max_age_days parameter."""
        code = compile("x = 1", "<test>", "exec")

        # Create files with different ages
        old_path = cache_dir / "__kida_py312_old_1234567890123456.pyc"
        old_path.write_bytes(b"old")
        # Set mtime to 15 days ago
        old_mtime = time.time() - (15 * 86400)
        import os

        os.utime(old_path, (old_mtime, old_mtime))

        # Create a recent file
        cache.set("recent.html", hash_source("recent"), code)

        # Cleanup with 7 day threshold (should remove 15-day-old file)
        removed = cache.cleanup(max_age_days=7)
        assert removed == 1
        assert not old_path.exists()

        # Reset: create another old file
        old_path2 = cache_dir / "__kida_py312_old2_1234567890123456.pyc"
        old_path2.write_bytes(b"old2")
        os.utime(old_path2, (old_mtime, old_mtime))

        # Cleanup with 20 day threshold (should preserve 15-day-old file)
        removed2 = cache.cleanup(max_age_days=20)
        assert removed2 == 0
        assert old_path2.exists()

    def test_sanitize_filename(self, cache):
        """Template names with special chars are sanitized."""
        code = compile("x = 1", "<test>", "exec")

        # Names with path separators
        cache.set("dir/subdir/test.html", hash_source("test"), code)

        # Should be retrievable
        result = cache.get("dir/subdir/test.html", hash_source("test"))
        assert result is not None

    def test_corrupted_cache_file_handled(self, cache, cache_dir):
        """Corrupted cache files are handled gracefully."""
        # Create a corrupted cache file using the same path generation
        source_hash = hash_source("test")
        # Use cache's internal path generation to get exact path
        corrupted_path = cache._make_path("test.html", source_hash)
        corrupted_path.write_bytes(b"not valid bytecode")

        # Should return None, not crash
        result = cache.get("test.html", source_hash)
        assert result is None

        # Corrupted file should be removed
        assert not corrupted_path.exists()


class TestHashSource:
    """Tests for source hashing."""

    def test_hash_consistency(self):
        """Same source produces same hash."""
        source = "Hello, {{ name }}!"
        hash1 = hash_source(source)
        hash2 = hash_source(source)
        assert hash1 == hash2

    def test_hash_uniqueness(self):
        """Different sources produce different hashes."""
        hash1 = hash_source("Hello, {{ name }}!")
        hash2 = hash_source("Goodbye, {{ name }}!")
        assert hash1 != hash2

    def test_hash_length(self):
        """Hash is SHA-256 (64 hex chars)."""
        hash_value = hash_source("test")
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestBytecodeCacheIntegration:
    """Integration tests with Environment."""

    def test_environment_with_bytecode_cache(self, tmp_path):
        """Environment uses bytecode cache correctly."""
        from bengal.rendering.kida import Environment

        cache = BytecodeCache(tmp_path / "cache")
        env = Environment(bytecode_cache=cache)

        # First compilation - cache miss
        template = env.from_string("Hello, {{ name }}!", name="test.html")
        result1 = template.render(name="World")
        assert result1 == "Hello, World!"

        # Check cache was populated
        stats = cache.stats()
        assert stats["file_count"] == 1

        # Second compilation - cache hit
        template2 = env.from_string("Hello, {{ name }}!", name="test.html")
        result2 = template2.render(name="World")
        assert result2 == "Hello, World!"

    def test_cache_with_optimizations(self, tmp_path):
        """Bytecode cache works with optimizations enabled."""
        from bengal.rendering.kida import Environment

        cache = BytecodeCache(tmp_path / "cache")
        env = Environment(bytecode_cache=cache, optimized=True)

        template = env.from_string(
            "{{ 1 + 2 }} {% if false %}hidden{% end %}",
            name="optimized.html",
        )
        result = template.render()
        assert "3" in result
        assert "hidden" not in result

        # Verify cache was used
        stats = cache.stats()
        assert stats["file_count"] == 1

    def test_cache_invalidation_on_source_change(self, tmp_path):
        """Cache is invalidated when source changes."""
        from bengal.rendering.kida import Environment

        cache = BytecodeCache(tmp_path / "cache")
        env = Environment(bytecode_cache=cache)

        # First version
        template1 = env.from_string("Version 1", name="test.html")
        result1 = template1.render()
        assert result1 == "Version 1"

        # Second version (different source)
        template2 = env.from_string("Version 2", name="test.html")
        result2 = template2.render()
        assert result2 == "Version 2"

        # Both versions should be cached (different hashes)
        stats = cache.stats()
        assert stats["file_count"] == 2


class TestBytecodeCacheAutoDetection:
    """Tests for automatic bytecode cache detection."""

    def test_auto_enabled_with_filesystem_loader(self, tmp_path):
        """Bytecode cache is auto-enabled for FileSystemLoader."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        # Create a template directory with a template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("Hello, {{ name }}!")

        # Environment with FileSystemLoader
        env = Environment(loader=FileSystemLoader(template_dir))

        # Bytecode cache should be auto-created
        assert env._bytecode_cache is not None

        # Render template to populate cache
        result = env.get_template("test.html").render(name="World")
        assert result == "Hello, World!"

        # Cache directory should be created in __pycache__/kida
        cache_dir = template_dir / "__pycache__" / "kida"
        assert cache_dir.exists()

        # Stats should show cached file
        stats = env._bytecode_cache.stats()
        assert stats["file_count"] == 1

    def test_auto_disabled_with_dict_loader(self):
        """Bytecode cache is not auto-enabled for DictLoader."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import DictLoader

        loader = DictLoader({"test.html": "Hello!"})
        env = Environment(loader=loader)

        # No auto-detection possible for DictLoader
        assert env._bytecode_cache is None

    def test_auto_disabled_with_no_loader(self):
        """Bytecode cache is not auto-enabled without a loader."""
        from bengal.rendering.kida import Environment

        env = Environment()
        assert env._bytecode_cache is None

    def test_explicit_disable(self, tmp_path):
        """bytecode_cache=False explicitly disables auto-detection."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("Hello!")

        # Explicitly disable
        env = Environment(
            loader=FileSystemLoader(template_dir),
            bytecode_cache=False,
        )

        assert env._bytecode_cache is None

    def test_explicit_cache_overrides_auto(self, tmp_path):
        """User-provided BytecodeCache overrides auto-detection."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("Hello!")

        custom_cache_dir = tmp_path / "my-custom-cache"
        custom_cache = BytecodeCache(custom_cache_dir)

        env = Environment(
            loader=FileSystemLoader(template_dir),
            bytecode_cache=custom_cache,
        )

        # Should use custom cache, not auto-detected one
        assert env._bytecode_cache is custom_cache

        # Render to populate
        env.get_template("test.html").render()

        # Cache should be in custom location
        assert custom_cache_dir.exists()
        assert not (template_dir / "__pycache__" / "kida").exists()

    def test_cache_info_includes_bytecode(self, tmp_path):
        """cache_info() includes bytecode stats when available."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("Hello!")

        env = Environment(loader=FileSystemLoader(template_dir))
        env.get_template("test.html").render()

        info = env.cache_info()
        assert "bytecode" in info
        assert info["bytecode"] is not None
        assert info["bytecode"]["file_count"] == 1

    def test_cache_info_none_when_disabled(self):
        """cache_info() shows None for bytecode when disabled."""
        from bengal.rendering.kida import Environment

        env = Environment(bytecode_cache=False)
        info = env.cache_info()
        assert info["bytecode"] is None

    def test_clear_bytecode_cache(self, tmp_path):
        """clear_bytecode_cache() removes cached files."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("Hello!")

        env = Environment(loader=FileSystemLoader(template_dir))
        env.get_template("test.html").render()

        # Verify cache exists
        assert env._bytecode_cache.stats()["file_count"] == 1

        # Clear
        removed = env.clear_bytecode_cache()
        assert removed == 1

        # Cache should be empty
        assert env._bytecode_cache.stats()["file_count"] == 0

    def test_clear_cache_with_bytecode_flag(self, tmp_path):
        """clear_cache(include_bytecode=True) clears everything."""
        from bengal.rendering.kida import Environment
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.html").write_text("Hello!")

        env = Environment(loader=FileSystemLoader(template_dir))
        env.get_template("test.html").render()

        # Both memory and disk caches populated
        assert env._cache.stats()["size"] == 1
        assert env._bytecode_cache.stats()["file_count"] == 1

        # Clear everything
        env.clear_cache(include_bytecode=True)

        # All caches cleared
        assert env._cache.stats()["size"] == 0
        assert env._bytecode_cache.stats()["file_count"] == 0
