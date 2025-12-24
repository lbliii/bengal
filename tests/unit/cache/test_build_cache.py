"""
Unit tests for BuildCache.
"""

from bengal.cache.build_cache import BuildCache
from bengal.utils.sentinel import MISSING


class TestBuildCache:
    """Test suite for BuildCache."""

    def test_init_empty_cache(self):
        """Test creating an empty cache."""
        cache = BuildCache()

        assert cache.file_fingerprints == {}
        assert cache.dependencies == {}
        assert cache.output_sources == {}
        assert cache.taxonomy_deps == {}
        assert cache.last_build is None

    def test_hash_file(self, tmp_path):
        """Test file hashing."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # Hash it
        hash1 = cache.hash_file(test_file)
        assert len(hash1) == 64  # SHA256 produces 64-char hex string

        # Hash again - should be same
        hash2 = cache.hash_file(test_file)
        assert hash1 == hash2

        # Modify file
        test_file.write_text("Hello, World! Modified")
        hash3 = cache.hash_file(test_file)
        assert hash3 != hash1

    def test_update_file(self, tmp_path):
        """Test updating file hashes in cache."""
        cache = BuildCache()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        # Update file in cache
        cache.update_file(test_file)

        assert str(test_file) in cache.file_fingerprints
        assert cache.file_fingerprints[str(test_file)].get("hash") is not None
        assert len(cache.file_fingerprints[str(test_file)].get("hash", "")) == 64

    def test_is_changed_new_file(self, tmp_path):
        """Test detecting a new file."""
        cache = BuildCache()

        test_file = tmp_path / "new.txt"
        test_file.write_text("New content")

        # New file should be detected as changed
        assert cache.is_changed(test_file) is True

    def test_is_changed_unchanged_file(self, tmp_path):
        """Test detecting an unchanged file."""
        cache = BuildCache()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        # Add to cache
        cache.update_file(test_file)

        # Should not be changed
        assert cache.is_changed(test_file) is False

    def test_is_changed_modified_file(self, tmp_path):
        """Test detecting a modified file."""
        cache = BuildCache()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Original content")

        # Add to cache
        cache.update_file(test_file)

        # Modify file with different content AND different size
        # (ensures detection even if mtime precision is low on some systems)
        test_file.write_text("This is modified content with a different length!")

        # Should be detected as changed
        assert cache.is_changed(test_file) is True

    def test_is_changed_deleted_file(self, tmp_path):
        """Test detecting a deleted file."""
        cache = BuildCache()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        # Add to cache
        cache.update_file(test_file)

        # Delete file
        test_file.unlink()

        # Should be detected as changed
        assert cache.is_changed(test_file) is True

    def test_add_dependency(self, tmp_path):
        """Test adding dependencies."""
        cache = BuildCache()

        source = tmp_path / "page.md"
        template = tmp_path / "template.html"

        cache.add_dependency(source, template)

        assert str(source) in cache.dependencies
        assert str(template) in cache.dependencies[str(source)]

    def test_add_multiple_dependencies(self, tmp_path):
        """Test adding multiple dependencies."""
        cache = BuildCache()

        source = tmp_path / "page.md"
        template = tmp_path / "template.html"
        partial = tmp_path / "partial.html"

        cache.add_dependency(source, template)
        cache.add_dependency(source, partial)

        assert len(cache.dependencies[str(source)]) == 2
        assert str(template) in cache.dependencies[str(source)]
        assert str(partial) in cache.dependencies[str(source)]

    def test_add_taxonomy_dependency(self, tmp_path):
        """Test adding taxonomy dependencies."""
        cache = BuildCache()

        page = tmp_path / "post.md"

        cache.add_taxonomy_dependency("tag:python", page)
        cache.add_taxonomy_dependency("tag:tutorial", page)

        assert "tag:python" in cache.taxonomy_deps
        assert str(page) in cache.taxonomy_deps["tag:python"]

    def test_get_affected_pages(self, tmp_path):
        """Test finding affected pages when a dependency changes."""
        cache = BuildCache()

        page1 = tmp_path / "page1.md"
        page2 = tmp_path / "page2.md"
        template = tmp_path / "template.html"

        cache.add_dependency(page1, template)
        cache.add_dependency(page2, template)

        # When template changes, both pages should be affected
        affected = cache.get_affected_pages(template)

        assert len(affected) == 2
        assert str(page1) in affected
        assert str(page2) in affected

    def test_get_affected_pages_self(self, tmp_path):
        """Test that a changed source file affects itself."""
        cache = BuildCache()

        page = tmp_path / "page.md"
        template = tmp_path / "template.html"

        cache.add_dependency(page, template)

        # When page itself changes
        affected = cache.get_affected_pages(page)

        assert str(page) in affected

    def test_invalidate_file(self, tmp_path):
        """Test invalidating a file."""
        cache = BuildCache()

        page = tmp_path / "page.md"
        template = tmp_path / "template.html"

        page.write_text("Content")
        cache.update_file(page)
        cache.add_dependency(page, template)

        # Invalidate the page
        cache.invalidate_file(page)

        assert str(page) not in cache.file_fingerprints
        assert str(page) not in cache.dependencies

    def test_clear(self, tmp_path):
        """Test clearing the cache."""
        cache = BuildCache()

        page = tmp_path / "page.md"
        template = tmp_path / "template.html"

        page.write_text("Content")
        cache.update_file(page)
        cache.add_dependency(page, template)

        cache.clear()

        assert len(cache.file_fingerprints) == 0
        assert len(cache.dependencies) == 0
        assert cache.last_build is None

    def test_save_and_load(self, tmp_path):
        """Test saving and loading cache."""
        cache = BuildCache()

        page = tmp_path / "page.md"
        template = tmp_path / "template.html"

        page.write_text("Content")
        cache.update_file(page)
        cache.add_dependency(page, template)
        cache.add_taxonomy_dependency("tag:python", page)

        # Save cache (compressed by default - .json.zst)
        cache_file = tmp_path / ".bengal-cache.json"
        cache.save(cache_file)

        # With compression enabled, the file is saved as .json.zst
        compressed_file = cache_file.with_suffix(".json.zst")
        assert compressed_file.exists()

        # Load cache
        loaded_cache = BuildCache.load(cache_file)

        assert str(page) in loaded_cache.file_fingerprints
        assert str(page) in loaded_cache.dependencies
        assert str(template) in loaded_cache.dependencies[str(page)]
        assert "tag:python" in loaded_cache.taxonomy_deps

    def test_load_nonexistent_cache(self, tmp_path):
        """Test loading a cache file that doesn't exist."""
        cache_file = tmp_path / ".bengal-cache.json"

        cache = BuildCache.load(cache_file)

        # Should return empty cache
        assert len(cache.file_fingerprints) == 0
        assert len(cache.dependencies) == 0

    def test_load_corrupted_cache(self, tmp_path):
        """Test loading a corrupted cache file."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_text("{ invalid json }")

        cache = BuildCache.load(cache_file)

        # Should return empty cache
        assert len(cache.file_fingerprints) == 0

    def test_get_stats(self, tmp_path):
        """Test getting cache statistics."""
        cache = BuildCache()

        page1 = tmp_path / "page1.md"
        page2 = tmp_path / "page2.md"
        template = tmp_path / "template.html"

        page1.write_text("Content 1")
        page2.write_text("Content 2")

        cache.update_file(page1)
        cache.update_file(page2)
        cache.add_dependency(page1, template)
        cache.add_dependency(page2, template)
        cache.add_taxonomy_dependency("tag:python", page1)

        stats = cache.get_stats()

        assert stats["tracked_files"] == 2
        assert stats["dependencies"] == 2
        assert stats["taxonomy_terms"] == 1

    def test_repr(self):
        """Test string representation."""
        cache = BuildCache()
        repr_str = repr(cache)

        assert "BuildCache" in repr_str
        assert "files=" in repr_str
        assert "deps=" in repr_str


class TestBuildCacheConfigHash:
    """Test suite for BuildCache config hash validation."""

    def test_validate_config_first_build(self):
        """First build initializes config_hash without invalidating."""
        cache = BuildCache()
        assert cache.config_hash is None

        # First validation should succeed and store hash
        result = cache.validate_config("abc123def456")

        assert result is True
        assert cache.config_hash == "abc123def456"

    def test_validate_config_same_hash(self):
        """Same config hash validates successfully."""
        cache = BuildCache()
        cache.config_hash = "abc123def456"

        # Same hash should validate
        result = cache.validate_config("abc123def456")

        assert result is True
        # Cache should NOT be cleared
        assert cache.config_hash == "abc123def456"

    def test_validate_config_different_hash_clears_cache(self, tmp_path):
        """Different config hash clears the cache."""
        cache = BuildCache()
        cache.config_hash = "old_hash_12345"

        # Add some data to the cache
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        cache.update_file(test_file)
        cache.add_dependency(test_file, tmp_path / "template.html")

        assert len(cache.file_fingerprints) > 0
        assert len(cache.dependencies) > 0

        # Different hash should invalidate
        result = cache.validate_config("new_hash_67890")

        assert result is False
        # Cache should be cleared
        assert len(cache.file_fingerprints) == 0
        assert len(cache.dependencies) == 0
        # New hash should be stored
        assert cache.config_hash == "new_hash_67890"

    def test_validate_config_clears_all_fields(self, tmp_path):
        """Config hash change clears all cache fields."""
        cache = BuildCache()
        cache.config_hash = "old_hash"

        # Populate various cache fields
        test_file = tmp_path / "test.md"
        test_file.write_text("content")
        cache.update_file(test_file)
        cache.add_dependency(test_file, tmp_path / "template.html")
        cache.add_taxonomy_dependency("tag:python", test_file)
        cache.update_page_tags(test_file, {"python", "web"})

        # Validate with different hash
        cache.validate_config("new_hash")

        # All fields should be cleared
        assert len(cache.file_fingerprints) == 0
        assert len(cache.dependencies) == 0
        assert len(cache.taxonomy_deps) == 0
        assert len(cache.page_tags) == 0
        assert len(cache.tag_to_pages) == 0
        assert len(cache.known_tags) == 0

    def test_config_hash_persists_through_save_load(self, tmp_path):
        """Config hash is saved and loaded correctly."""
        cache = BuildCache()
        cache.config_hash = "test_hash_abc"

        # Save cache (compressed by default - .json.zst)
        cache_file = tmp_path / "cache.json"
        cache.save(cache_file)

        # Load cache (auto-detects format)
        loaded_cache = BuildCache.load(cache_file)

        assert loaded_cache.config_hash == "test_hash_abc"

    def test_config_hash_none_in_old_cache(self, tmp_path):
        """Old cache without config_hash loads with None."""
        import json

        # Create an old-format cache file without config_hash
        cache_file = tmp_path / "cache.json"
        old_cache_data = {
            "version": 2,  # Old version before config_hash
            "file_fingerprints": {},
            "dependencies": {},
            "output_sources": {},
            "taxonomy_deps": {},
            "page_tags": {},
            "tag_to_pages": {},
            "known_tags": [],
            "parsed_content": {},
            "validation_results": {},
            "last_build": None,
        }
        cache_file.write_text(json.dumps(old_cache_data))

        # Load should work and config_hash should be None
        loaded_cache = BuildCache.load(cache_file)

        assert loaded_cache.config_hash is None

    def test_clear_also_clears_config_hash(self):
        """Clear method also clears config_hash."""
        cache = BuildCache()
        cache.config_hash = "some_hash"

        cache.clear()

        assert cache.config_hash is None


class TestRenderedOutputCache:
    """Test suite for rendered output caching (Optimization #3)."""

    def test_store_and_get_rendered_output(self, tmp_path):
        """Test storing and retrieving rendered HTML output."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output
        metadata = {"title": "Test Page", "date": "2025-01-01"}
        cache.store_rendered_output(
            test_file,
            "<html><body>Rendered content</body></html>",
            "default.html",
            metadata,
            dependencies=[str(tmp_path / "templates" / "default.html")],
        )

        # Get it back
        result = cache.get_rendered_output(test_file, "default.html", metadata)

        assert result is not None
        assert "Rendered content" in result

    def test_rendered_output_invalid_on_content_change(self, tmp_path):
        """Rendered output cache is invalidated when content file changes."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Original Content")
        cache.update_file(test_file)

        # Store rendered output
        metadata = {"title": "Test Page"}
        cache.store_rendered_output(
            test_file,
            "<html>Original</html>",
            "default.html",
            metadata,
        )

        # Modify the file with different content AND different size
        # (ensures detection even if mtime precision is low on some systems)
        test_file.write_text("# Modified Content with additional text to change size!")

        # Cache should be invalid
        result = cache.get_rendered_output(test_file, "default.html", metadata)
        assert result is MISSING

    def test_rendered_output_invalid_on_metadata_change(self, tmp_path):
        """Rendered output cache is invalidated when metadata changes."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output with initial metadata
        metadata_v1 = {"title": "Original Title"}
        cache.store_rendered_output(
            test_file,
            "<html>Original</html>",
            "default.html",
            metadata_v1,
        )

        # Try to get with different metadata
        metadata_v2 = {"title": "Modified Title"}
        result = cache.get_rendered_output(test_file, "default.html", metadata_v2)
        assert result is MISSING

    def test_rendered_output_invalid_on_template_change(self, tmp_path):
        """Rendered output cache is invalidated when template name changes."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output with initial template
        metadata = {"title": "Test Page"}
        cache.store_rendered_output(
            test_file,
            "<html>Original</html>",
            "default.html",
            metadata,
        )

        # Try to get with different template
        result = cache.get_rendered_output(test_file, "custom.html", metadata)
        assert result is MISSING

    def test_rendered_output_invalid_on_dependency_change(self, tmp_path):
        """Rendered output cache is invalidated when a dependency file changes."""
        cache = BuildCache()

        # Create files
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        template_file = tmp_path / "templates" / "base.html"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text("<html>{% block content %}{% endblock %}</html>")
        cache.update_file(template_file)

        # Store rendered output with dependency
        metadata = {"title": "Test Page"}
        cache.store_rendered_output(
            test_file,
            "<html>Rendered</html>",
            "default.html",
            metadata,
            dependencies=[str(template_file)],
        )

        # Verify cache hit before change
        result = cache.get_rendered_output(test_file, "default.html", metadata)
        assert result is not None

        # Modify the dependency
        template_file.write_text("<html>Modified template</html>")

        # Cache should be invalid
        result = cache.get_rendered_output(test_file, "default.html", metadata)
        assert result is MISSING

    def test_invalidate_rendered_output(self, tmp_path):
        """Test explicit invalidation of rendered output."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output
        metadata = {"title": "Test Page"}
        cache.store_rendered_output(
            test_file,
            "<html>Rendered</html>",
            "default.html",
            metadata,
        )

        # Explicitly invalidate
        cache.invalidate_rendered_output(test_file)

        # Cache should be invalid
        result = cache.get_rendered_output(test_file, "default.html", metadata)
        assert result is MISSING

    def test_rendered_output_stats(self, tmp_path):
        """Test rendered output cache statistics."""
        cache = BuildCache()

        # Initially empty
        stats = cache.get_rendered_output_stats()
        assert stats["cached_pages"] == 0

        # Add some entries
        for i in range(3):
            test_file = tmp_path / f"page{i}.md"
            test_file.write_text(f"# Page {i}")
            cache.update_file(test_file)
            cache.store_rendered_output(
                test_file,
                f"<html>Page {i}</html>",
                "default.html",
                {"title": f"Page {i}"},
            )

        stats = cache.get_rendered_output_stats()
        assert stats["cached_pages"] == 3
        assert stats["total_size_mb"] > 0

    def test_clear_also_clears_rendered_output(self, tmp_path):
        """Clear method also clears rendered output cache."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output
        cache.store_rendered_output(
            test_file,
            "<html>Rendered</html>",
            "default.html",
            {"title": "Test"},
        )

        # Clear and check
        cache.clear()
        assert len(cache.rendered_output) == 0

    def test_invalidate_file_clears_rendered_output(self, tmp_path):
        """invalidate_file also clears rendered output for that file."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output
        cache.store_rendered_output(
            test_file,
            "<html>Rendered</html>",
            "default.html",
            {"title": "Test"},
        )

        # Invalidate the file
        cache.invalidate_file(test_file)

        # Rendered output should be gone
        assert str(test_file) not in cache.rendered_output

    def test_rendered_output_persists_through_save_load(self, tmp_path):
        """Rendered output cache persists across save/load cycles (cold build support)."""
        cache = BuildCache()

        # Create a test file
        test_file = tmp_path / "page.md"
        test_file.write_text("# Test Content")
        cache.update_file(test_file)

        # Store rendered output
        metadata = {"title": "Test Page", "date": "2025-01-01"}
        cache.store_rendered_output(
            test_file,
            "<html><body>Rendered content for cold build test</body></html>",
            "default.html",
            metadata,
            dependencies=[str(tmp_path / "templates" / "default.html")],
        )

        # Verify it's stored
        assert str(test_file) in cache.rendered_output

        # Save cache (compressed by default - .json.zst)
        cache_file = tmp_path / ".bengal-cache.json"
        cache.save(cache_file)

        # Load into a fresh cache instance (simulates cold build)
        loaded_cache = BuildCache.load(cache_file)

        # Rendered output should be present after load
        assert str(test_file) in loaded_cache.rendered_output
        assert loaded_cache.rendered_output[str(test_file)]["html"] == (
            "<html><body>Rendered content for cold build test</body></html>"
        )
        assert loaded_cache.rendered_output[str(test_file)]["template"] == "default.html"

    def test_rendered_output_tolerates_missing_in_old_cache(self, tmp_path):
        """Loading old cache without rendered_output field works correctly."""
        import json

        # Create an old-format cache file without rendered_output
        cache_file = tmp_path / "cache.json"
        old_cache_data = {
            "version": 5,  # Old version before rendered_output was persisted
            "file_fingerprints": {},
            "dependencies": {},
            "output_sources": {},
            "taxonomy_deps": {},
            "page_tags": {},
            "tag_to_pages": {},
            "known_tags": [],
            "parsed_content": {},
            "validation_results": {},
            "autodoc_dependencies": {},
            "synthetic_pages": {},
            "url_claims": {},
            "config_hash": None,
            "last_build": None,
            # Note: no rendered_output field
        }
        cache_file.write_text(json.dumps(old_cache_data))

        # Load should work and rendered_output should be empty dict
        loaded_cache = BuildCache.load(cache_file)

        assert loaded_cache.rendered_output == {}
