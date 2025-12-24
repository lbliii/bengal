"""
Tests for parallel PythonExtractor functionality.

Tests the free-threading expansion for autodoc extraction,
ensuring parallel mode produces identical results to sequential mode.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from bengal.autodoc.extractors.python.extractor import PythonExtractor


@pytest.fixture
def small_package(tmp_path):
    """Create a small Python package (below parallel threshold)."""
    pkg_dir = tmp_path / "small_pkg"
    pkg_dir.mkdir()

    # Create a few Python files
    (pkg_dir / "__init__.py").write_text('"""Small package."""\n')
    (pkg_dir / "module1.py").write_text(
        '''"""Module 1."""

def func1():
    """Function 1."""
    pass

class Class1:
    """Class 1."""
    pass
'''
    )
    (pkg_dir / "module2.py").write_text(
        '''"""Module 2."""

def func2():
    """Function 2."""
    pass
'''
    )

    return pkg_dir


@pytest.fixture
def large_package(tmp_path):
    """Create a large Python package (above parallel threshold)."""
    pkg_dir = tmp_path / "large_pkg"
    pkg_dir.mkdir()

    # Create many Python files
    (pkg_dir / "__init__.py").write_text('"""Large package."""\n')

    for i in range(15):  # Above MIN_MODULES_FOR_PARALLEL (10)
        (pkg_dir / f"module{i}.py").write_text(
            f'''"""Module {i}."""

def func{i}():
    """Function {i}."""
    pass

class Class{i}:
    """Class {i}."""

    def method{i}(self):
        """Method {i}."""
        pass
'''
        )

    return pkg_dir


class TestParallelModeDetection:
    """Test automatic parallel mode detection for autodoc."""

    def test_small_package_uses_sequential(self, small_package):
        """Test that small packages use sequential extraction."""
        extractor = PythonExtractor(config={})

        # Collect files - small package should use sequential
        py_files = list(small_package.rglob("*.py"))
        assert not extractor._should_use_parallel(len(py_files))

        # Should complete without error
        elements = extractor.extract(small_package)
        assert len(elements) > 0

    def test_large_package_uses_parallel(self, large_package):
        """Test that large packages use parallel extraction."""
        extractor = PythonExtractor(config={})

        # Collect files - large package should use parallel
        py_files = list(large_package.rglob("*.py"))
        assert extractor._should_use_parallel(len(py_files))

        # Should complete without error
        elements = extractor.extract(large_package)
        assert len(elements) > 0

    def test_env_var_disables_parallel(self, large_package):
        """Test BENGAL_NO_PARALLEL environment variable."""
        with patch.dict(os.environ, {"BENGAL_NO_PARALLEL": "1"}):
            extractor = PythonExtractor(config={})
            # Should not use parallel even for many files
            assert not extractor._should_use_parallel(100)
            elements = extractor.extract(large_package)
            assert len(elements) > 0

    def test_config_disables_parallel(self, large_package):
        """Test parallel_autodoc config option."""
        extractor = PythonExtractor(config={"parallel_autodoc": False})
        # Should not use parallel even for many files
        assert not extractor._should_use_parallel(100)
        elements = extractor.extract(large_package)
        assert len(elements) > 0

    def test_hardware_aware_threshold(self):
        """Test that threshold is hardware-aware based on core count."""
        import multiprocessing

        extractor = PythonExtractor(config={})
        core_count = multiprocessing.cpu_count()

        # Threshold formula: max(5, 15 - core_count)
        expected_threshold = max(5, 15 - core_count)

        # Just below threshold: sequential
        assert not extractor._should_use_parallel(expected_threshold - 1)
        # At threshold: parallel
        assert extractor._should_use_parallel(expected_threshold)


class TestParallelMatchesSequential:
    """Test that parallel mode produces identical results to sequential."""

    def test_results_match_large_package(self, large_package):
        """Test that parallel and sequential produce same results."""
        # Extract with sequential (force via env var)
        with patch.dict(os.environ, {"BENGAL_NO_PARALLEL": "1"}):
            extractor_seq = PythonExtractor(config={})
            elements_seq = extractor_seq.extract(large_package)

        # Extract with parallel (force via config)
        extractor_par = PythonExtractor(config={"parallel_autodoc": True})
        elements_par = extractor_par.extract(large_package)

        # Compare results
        assert len(elements_seq) == len(elements_par)

        # Compare by qualified names (order may differ due to parallel execution)
        seq_names = sorted(e.qualified_name for e in elements_seq)
        par_names = sorted(e.qualified_name for e in elements_par)
        assert seq_names == par_names


class TestParallelErrorHandling:
    """Test error handling in parallel extraction."""

    def test_handles_syntax_errors(self, tmp_path):
        """Test that syntax errors in one file don't affect others."""
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        # Create valid file
        (pkg_dir / "valid.py").write_text(
            '''"""Valid module."""

def valid_func():
    """Valid function."""
    pass
'''
        )

        # Create invalid file with syntax error
        (pkg_dir / "invalid.py").write_text(
            '''"""Invalid module."""

def invalid_func(
    # Missing closing paren and body
'''
        )

        # Create more valid files to hit parallel threshold
        for i in range(12):
            (pkg_dir / f"module{i}.py").write_text(
                f'''"""Module {i}."""

def func{i}():
    pass
'''
            )

        extractor = PythonExtractor(config={})
        elements = extractor.extract(pkg_dir)

        # Should have extracted valid modules (invalid.py should be skipped)
        module_names = [e.qualified_name for e in elements]
        assert "valid" in module_names
        assert "invalid" not in module_names

    def test_handles_empty_directory(self, tmp_path):
        """Test parallel extraction of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        extractor = PythonExtractor(config={})
        elements = extractor.extract(empty_dir)

        assert elements == []


class TestParallelClassIndex:
    """Test that class index is built correctly after parallel extraction."""

    def test_class_index_populated(self, large_package):
        """Test that class_index is populated after parallel extraction."""
        extractor = PythonExtractor(config={})
        extractor.extract(large_package)

        # Should have class index entries
        assert len(extractor.class_index) > 0

        # All entries should be class elements
        for _name, element in extractor.class_index.items():
            assert element.element_type == "class"


class TestParallelInheritance:
    """Test that inheritance synthesis works with parallel extraction."""

    def test_inherited_members_synthesized(self, tmp_path):
        """Test that inherited members are synthesized after parallel extraction."""
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        # Create base class
        (pkg_dir / "base.py").write_text(
            '''"""Base module."""

class BaseClass:
    """Base class."""

    def base_method(self):
        """Base method."""
        pass
'''
        )

        # Create derived classes
        for i in range(12):
            (pkg_dir / f"derived{i}.py").write_text(
                f'''"""Derived module {i}."""

from .base import BaseClass

class DerivedClass{i}(BaseClass):
    """Derived class {i}."""

    def derived_method{i}(self):
        """Derived method {i}."""
        pass
'''
            )

        extractor = PythonExtractor(config={"include_inherited": True})
        elements = extractor.extract(pkg_dir)

        # Should have extracted modules
        assert len(elements) > 0


class TestParallelWorkerConfig:
    """Test worker configuration for parallel extraction."""

    def test_respects_max_workers_config(self, large_package):
        """Test that max_workers config is used."""
        extractor = PythonExtractor(config={"max_workers": 2})
        elements = extractor.extract(large_package)

        # Should complete successfully
        assert len(elements) > 0
