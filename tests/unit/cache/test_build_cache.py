"""
Unit tests for BuildCache.
"""

import pytest
from pathlib import Path
import json
from bengal.cache.build_cache import BuildCache


class TestBuildCache:
    """Test suite for BuildCache."""
    
    def test_init_empty_cache(self):
        """Test creating an empty cache."""
        cache = BuildCache()
        
        assert cache.file_hashes == {}
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
        
        assert str(test_file) in cache.file_hashes
        assert len(cache.file_hashes[str(test_file)]) == 64
    
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
        
        # Modify file
        test_file.write_text("Modified content")
        
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
        
        assert str(page) not in cache.file_hashes
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
        
        assert len(cache.file_hashes) == 0
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
        
        # Save cache
        cache_file = tmp_path / ".bengal-cache.json"
        cache.save(cache_file)
        
        assert cache_file.exists()
        
        # Load cache
        loaded_cache = BuildCache.load(cache_file)
        
        assert str(page) in loaded_cache.file_hashes
        assert str(page) in loaded_cache.dependencies
        assert str(template) in loaded_cache.dependencies[str(page)]
        assert "tag:python" in loaded_cache.taxonomy_deps
    
    def test_load_nonexistent_cache(self, tmp_path):
        """Test loading a cache file that doesn't exist."""
        cache_file = tmp_path / ".bengal-cache.json"
        
        cache = BuildCache.load(cache_file)
        
        # Should return empty cache
        assert len(cache.file_hashes) == 0
        assert len(cache.dependencies) == 0
    
    def test_load_corrupted_cache(self, tmp_path):
        """Test loading a corrupted cache file."""
        cache_file = tmp_path / ".bengal-cache.json"
        cache_file.write_text("{ invalid json }")
        
        cache = BuildCache.load(cache_file)
        
        # Should return empty cache
        assert len(cache.file_hashes) == 0
    
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
        
        assert stats['tracked_files'] == 2
        assert stats['dependencies'] == 2
        assert stats['taxonomy_terms'] == 1
    
    def test_repr(self):
        """Test string representation."""
        cache = BuildCache()
        repr_str = repr(cache)
        
        assert "BuildCache" in repr_str
        assert "files=" in repr_str
        assert "deps=" in repr_str

