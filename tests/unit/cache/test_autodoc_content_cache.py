"""
Tests for autodoc content caching.

RFC: rfc-build-performance-optimizations Phase 3
Tests the AutodocContentCacheMixin for caching parsed module data to skip AST parsing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.autodoc.base import DocElement
from bengal.cache.build_cache.autodoc_content_cache import CachedModuleInfo
from bengal.cache.build_cache.core import BuildCache
from bengal.utils.primitives.hashing import hash_file, hash_str


class TestCachedModuleInfo:
    """Tests for CachedModuleInfo dataclass."""

    def test_cached_module_info_structure(self) -> None:
        """Test CachedModuleInfo stores source hash and module element dict."""
        module_dict = {
            "name": "test_module",
            "qualified_name": "test.test_module",
            "description": "Test module",
            "element_type": "module",
            "children": [],
        }
        
        cached = CachedModuleInfo(
            source_hash="abc123def456",
            module_element_dict=module_dict,
        )
        
        assert cached.source_hash == "abc123def456"
        assert cached.module_element_dict == module_dict

    def test_cached_module_info_with_children(self) -> None:
        """Test CachedModuleInfo stores module with children."""
        module_dict = {
            "name": "test_module",
            "qualified_name": "test.test_module",
            "description": "Test module",
            "element_type": "module",
            "children": [
                {
                    "name": "TestClass",
                    "qualified_name": "test.test_module.TestClass",
                    "description": "Test class",
                    "element_type": "class",
                    "children": [],
                }
            ],
        }
        
        cached = CachedModuleInfo(
            source_hash="abc123",
            module_element_dict=module_dict,
        )
        
        assert len(cached.module_element_dict["children"]) == 1
        assert cached.module_element_dict["children"][0]["name"] == "TestClass"


class TestAutodocContentCacheMixin:
    """Tests for AutodocContentCacheMixin cache operations."""

    def test_get_cached_module_cache_hit(self) -> None:
        """Test cache hit returns CachedModuleInfo when hash matches."""
        cache = BuildCache()
        
        module_dict = {
            "name": "test_module",
            "qualified_name": "test.test_module",
            "description": "Test",
            "element_type": "module",
            "children": [],
        }
        
        cached_info = CachedModuleInfo(
            source_hash="abc123",
            module_element_dict=module_dict,
        )
        
        cache.cache_module("test/module.py", cached_info)
        
        # Cache hit
        result = cache.get_cached_module("test/module.py", "abc123")
        assert result is not None
        assert result.source_hash == "abc123"
        assert result.module_element_dict == module_dict

    def test_get_cached_module_cache_miss_hash_mismatch(self) -> None:
        """Test cache miss when hash doesn't match."""
        cache = BuildCache()
        
        cached_info = CachedModuleInfo(
            source_hash="abc123",
            module_element_dict={"name": "test", "element_type": "module"},
        )
        
        cache.cache_module("test/module.py", cached_info)
        
        # Cache miss - hash mismatch
        result = cache.get_cached_module("test/module.py", "xyz789")
        assert result is None

    def test_get_cached_module_cache_miss_no_entry(self) -> None:
        """Test cache miss when no entry exists."""
        cache = BuildCache()
        
        result = cache.get_cached_module("test/module.py", "abc123")
        assert result is None

    def test_cache_module_stores_info(self) -> None:
        """Test cache_module stores CachedModuleInfo."""
        cache = BuildCache()
        
        module_dict = {
            "name": "test_module",
            "qualified_name": "test.test_module",
            "description": "Test",
            "element_type": "module",
            "children": [],
        }
        
        cached_info = CachedModuleInfo(
            source_hash="abc123",
            module_element_dict=module_dict,
        )
        
        cache.cache_module("test/module.py", cached_info)
        
        assert "test/module.py" in cache.autodoc_content_cache
        assert cache.autodoc_content_cache["test/module.py"] == cached_info

    def test_clear_autodoc_content_cache(self) -> None:
        """Test clearing autodoc content cache."""
        cache = BuildCache()
        
        cached_info = CachedModuleInfo(
            source_hash="abc123",
            module_element_dict={"name": "test", "element_type": "module"},
        )
        
        cache.cache_module("test/module.py", cached_info)
        assert len(cache.autodoc_content_cache) == 1
        
        cache.clear_autodoc_content_cache()
        assert len(cache.autodoc_content_cache) == 0


class TestAutodocContentCacheIntegration:
    """Integration tests for autodoc content caching with PythonExtractor."""

    def test_cache_reconstruction_roundtrip(self, tmp_path: Path) -> None:
        """Test that DocElement can be cached and reconstructed."""
        from bengal.autodoc.extractors.python import PythonExtractor
        
        # Create a simple Python module
        # Note: Use name that doesn't match exclude pattern "test_*.py"
        source_file = tmp_path / "sample_module.py"
        source_file.write_text('''"""Sample module docstring."""

class SampleClass:
    """Sample class."""
    pass

def sample_function():
    """Sample function."""
    pass
''')
        
        # Extract without cache
        extractor1 = PythonExtractor(config={})
        elements1 = extractor1.extract(tmp_path)
        assert len(elements1) == 1
        module_element1 = elements1[0]
        
        # Create cache and extract with cache
        cache = BuildCache()
        extractor2 = PythonExtractor(config={}, cache=cache)
        
        # First extraction - should parse and cache
        elements2 = extractor2.extract(tmp_path)
        assert len(elements2) == 1
        module_element2 = elements2[0]
        
        # Verify cache was populated
        # Use hash_file to match what extractor uses for cache lookup
        source_hash = hash_file(source_file, truncate=16)
        cached_info = cache.get_cached_module(str(source_file), source_hash)
        assert cached_info is not None
        
        # Second extraction - should use cache (skip parsing)
        extractor3 = PythonExtractor(config={}, cache=cache)
        elements3 = extractor3.extract(tmp_path)
        assert len(elements3) == 1
        module_element3 = elements3[0]
        
        # Verify elements are equivalent
        assert module_element3.qualified_name == module_element2.qualified_name
        assert module_element3.description == module_element2.description
        assert len(module_element3.children) == len(module_element2.children)

    def test_cache_invalidation_on_source_change(self, tmp_path: Path) -> None:
        """Test that cache is invalidated when source file changes."""
        from bengal.autodoc.extractors.python import PythonExtractor
        
        # Note: Use name that doesn't match exclude pattern "test_*.py"
        source_file = tmp_path / "sample_module.py"
        source_file.write_text('''"""Original docstring."""

def original_function():
    """Original function."""
    pass
''')
        
        cache = BuildCache()
        extractor = PythonExtractor(config={}, cache=cache)
        
        # First extraction - caches
        elements1 = extractor.extract(tmp_path)
        assert len(elements1) == 1
        
        # Modify source file
        source_file.write_text('''"""Modified docstring."""

def modified_function():
    """Modified function."""
    pass
''')
        
        # Second extraction - should re-parse (cache miss)
        extractor2 = PythonExtractor(config={}, cache=cache)
        elements2 = extractor2.extract(tmp_path)
        assert len(elements2) == 1
        
        # Verify new content was extracted
        assert elements2[0].description == "Modified docstring."
        assert len(elements2[0].children) == 1
        assert elements2[0].children[0].name == "modified_function"

    def test_cache_fallback_on_deserialization_error(self, tmp_path: Path) -> None:
        """Test that extractor falls back to parsing if cache deserialization fails."""
        from bengal.autodoc.extractors.python import PythonExtractor
        
        # Note: Use name that doesn't match exclude pattern "test_*.py"
        source_file = tmp_path / "sample_module.py"
        source_file.write_text('''"""Sample module."""

def sample_function():
    """Sample function."""
    pass
''')
        
        cache = BuildCache()
        
        # Manually add corrupted cache entry
        corrupted_dict = {
            "name": "sample_module",
            "qualified_name": "sample.sample_module",
            # Missing required fields to cause deserialization error
        }
        
        cached_info = CachedModuleInfo(
            source_hash=hash_file(source_file, truncate=16),
            module_element_dict=corrupted_dict,
        )
        cache.cache_module(str(source_file), cached_info)
        
        # Extraction should fall back to parsing despite cache hit
        extractor = PythonExtractor(config={}, cache=cache)
        elements = extractor.extract(tmp_path)
        
        # Should still extract successfully (fallback worked)
        assert len(elements) == 1
        assert elements[0].description == "Sample module."
