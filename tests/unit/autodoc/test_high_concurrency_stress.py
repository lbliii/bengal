"""High-concurrency stress test for PythonExtractor indexing and inheritance."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bengal.autodoc.extractors.python.extractor import PythonExtractor


@pytest.mark.unit
class TestHighConcurrencyStress:
    """
    Stress test for PythonExtractor to ensure thread safety during parallel extraction.
    """

    def test_indexing_thread_safety_large_scale(self, tmp_path: Path):
        """
        Generate many modules with name collisions and verify that the
        sequential post-processing pass builds a correct index.
        """
        pkg_dir = tmp_path / "stress_pkg"
        pkg_dir.mkdir()

        num_modules = 100
        num_classes_per_module = 5

        # Names that will collide across all modules
        colliding_names = [f"CommonClass{i}" for i in range(num_classes_per_module)]

        for m_idx in range(num_modules):
            module_content = [f'"""Module {m_idx}."""'] + [
                f"class {c_name}: pass" for c_name in colliding_names
            ]
            (pkg_dir / f"module{m_idx}.py").write_text("\n".join(module_content))

        # Initialize extractor with parallel mode forced
        extractor = PythonExtractor(config={"parallel_autodoc": True})

        # Mock core count to force high concurrency if machine has few cores
        with patch("multiprocessing.cpu_count", return_value=16), patch(
            "bengal.autodoc.extractors.python.extractor.get_optimal_workers", return_value=16
        ):
            elements = extractor.extract(pkg_dir)

        # 1. Total modules extracted
        assert len(elements) == num_modules

        # 2. Check simple_name_index for collisions
        # Each colliding name should have exactly num_modules qualified entries
        for c_name in colliding_names:
            assert c_name in extractor.simple_name_index
            entries = extractor.simple_name_index[c_name]
            assert len(entries) == num_modules, (
                f"Lost entries for {c_name}! Expected {num_modules}, got {len(entries)}"
            )

            # Ensure all entries are unique
            assert len(set(entries)) == num_modules, f"Duplicate entries for {c_name}!"

        # 3. Check class_index
        # Total classes should be num_modules * num_classes_per_module
        expected_total_classes = num_modules * num_classes_per_module
        assert len(extractor.class_index) == expected_total_classes

    def test_inheritance_resolution_in_stress_env(self, tmp_path: Path):
        """
        Verify that inheritance synthesis works correctly even when
        base classes are extracted in different threads.
        """
        pkg_dir = tmp_path / "inherit_stress"
        pkg_dir.mkdir()

        # 1. Create a base module with many classes
        base_content = ['"""Base module."""']
        for i in range(50):
            base_content.append(f"class Base{i}:")
            base_content.append(f"    def method{i}(self): pass")
        (pkg_dir / "base.py").write_text("\n".join(base_content))

        # 2. Create many derived modules, each inheriting from some base classes
        for i in range(1, 51):
            derived_content = [
                f'"""Derived {i}."""',
                f"from .base import Base{i - 1}",
                f"class Derived{i}(Base{i - 1}):",
                "    def derived_method(self): pass",
            ]
            (pkg_dir / f"derived{i}.py").write_text("\n".join(derived_content))

        # Run extraction with inheritance enabled
        extractor = PythonExtractor(config={"include_inherited": True, "parallel_autodoc": True})

        elements = extractor.extract(pkg_dir)

        # Find all derived classes and verify they have synthesized members
        found_derived = 0
        for element in elements:
            if "derived" in element.name:
                for child in element.children:
                    if child.element_type == "class":
                        found_derived += 1
                        # Each derived class should have 2 methods: its own + 1 inherited
                        method_names = [m.name for m in child.children]
                        assert "derived_method" in method_names
                        # Look for method{i-1}
                        inherited_methods = [m for m in method_names if m.startswith("method")]
                        assert len(inherited_methods) == 1, (
                            f"Missing inherited method in {child.name}"
                        )

        assert found_derived == 50
