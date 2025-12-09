"""
Integration tests for Python extractor typed_metadata output.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.models import (
    PythonAliasMetadata,
    PythonAttributeMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
    PythonModuleMetadata,
)


@pytest.fixture
def extractor() -> PythonExtractor:
    """Create a PythonExtractor instance."""
    return PythonExtractor()


@pytest.fixture
def sample_module(tmp_path: Path) -> Path:
    """Create a sample Python module for testing."""
    module_file = tmp_path / "sample.py"
    module_file.write_text(dedent('''
        """Sample module docstring."""

        from dataclasses import dataclass


        @dataclass
        class SampleClass:
            """A sample dataclass.

            Attributes:
                name: The name attribute.
                value: The value attribute.
            """
            name: str
            value: int = 0

            def get_info(self, detailed: bool = False) -> str:
                """Get information about this instance.

                Args:
                    detailed: Include detailed info.

                Returns:
                    Information string.
                """
                return f"{self.name}: {self.value}"

            @classmethod
            def from_name(cls, name: str) -> "SampleClass":
                """Create from name only."""
                return cls(name=name)

            @staticmethod
            def validate(name: str) -> bool:
                """Validate a name."""
                return bool(name)

            @property
            def display_name(self) -> str:
                """Get display name."""
                return self.name.title()


        async def async_fetch(url: str) -> bytes:
            """Fetch data asynchronously."""
            return b""


        def generator_func() -> int:
            """A generator function."""
            yield 1
            yield 2


        # Alias
        Sample = SampleClass
    ''').lstrip())
    return module_file


class TestPythonExtractorTypedMetadata:
    """Tests for typed_metadata in Python extractor output."""

    def test_module_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that module elements have typed_metadata."""
        elements = extractor.extract(sample_module)

        assert len(elements) >= 1
        module = elements[0]
        assert module.element_type == "module"
        assert module.typed_metadata is not None
        assert isinstance(module.typed_metadata, PythonModuleMetadata)
        assert module.typed_metadata.file_path == str(sample_module)
        assert module.typed_metadata.is_package is False

    def test_class_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that class elements have typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        # Find the SampleClass
        class_elem = None
        for child in module.children:
            if child.name == "SampleClass" and child.element_type == "class":
                class_elem = child
                break

        assert class_elem is not None
        assert class_elem.typed_metadata is not None
        assert isinstance(class_elem.typed_metadata, PythonClassMetadata)
        assert class_elem.typed_metadata.is_dataclass is True
        # Check decorators include dataclass
        assert any("dataclass" in d for d in class_elem.typed_metadata.decorators)

    def test_method_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that method elements have typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        # Find the SampleClass
        class_elem = None
        for child in module.children:
            if child.name == "SampleClass":
                class_elem = child
                break

        assert class_elem is not None

        # Find get_info method
        method = None
        for child in class_elem.children:
            if child.name == "get_info":
                method = child
                break

        assert method is not None
        assert method.typed_metadata is not None
        assert isinstance(method.typed_metadata, PythonFunctionMetadata)
        assert method.typed_metadata.return_type == "str"
        # Check parameters
        assert len(method.typed_metadata.parameters) >= 1
        param_names = [p.name for p in method.typed_metadata.parameters]
        assert "detailed" in param_names

    def test_classmethod_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that classmethod has correct typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        class_elem = None
        for child in module.children:
            if child.name == "SampleClass":
                class_elem = child
                break

        assert class_elem is not None

        # Find from_name classmethod
        method = None
        for child in class_elem.children:
            if child.name == "from_name":
                method = child
                break

        assert method is not None
        assert method.typed_metadata is not None
        assert isinstance(method.typed_metadata, PythonFunctionMetadata)
        assert method.typed_metadata.is_classmethod is True

    def test_staticmethod_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that staticmethod has correct typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        class_elem = None
        for child in module.children:
            if child.name == "SampleClass":
                class_elem = child
                break

        assert class_elem is not None

        # Find validate staticmethod
        method = None
        for child in class_elem.children:
            if child.name == "validate":
                method = child
                break

        assert method is not None
        assert method.typed_metadata is not None
        assert isinstance(method.typed_metadata, PythonFunctionMetadata)
        assert method.typed_metadata.is_staticmethod is True

    def test_property_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that property has correct typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        class_elem = None
        for child in module.children:
            if child.name == "SampleClass":
                class_elem = child
                break

        assert class_elem is not None

        # Find display_name property
        prop = None
        for child in class_elem.children:
            if child.name == "display_name":
                prop = child
                break

        assert prop is not None
        assert prop.typed_metadata is not None
        assert isinstance(prop.typed_metadata, PythonFunctionMetadata)
        assert prop.typed_metadata.is_property is True

    def test_async_function_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that async function has correct typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        # Find async_fetch function
        func = None
        for child in module.children:
            if child.name == "async_fetch":
                func = child
                break

        assert func is not None
        assert func.typed_metadata is not None
        assert isinstance(func.typed_metadata, PythonFunctionMetadata)
        assert func.typed_metadata.is_async is True

    def test_generator_function_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that generator function has correct typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        # Find generator_func function
        func = None
        for child in module.children:
            if child.name == "generator_func":
                func = child
                break

        assert func is not None
        assert func.typed_metadata is not None
        assert isinstance(func.typed_metadata, PythonFunctionMetadata)
        assert func.typed_metadata.is_generator is True

    def test_alias_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that alias has correct typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        # Find Sample alias
        alias = None
        for child in module.children:
            if child.name == "Sample" and child.element_type == "alias":
                alias = child
                break

        assert alias is not None
        assert alias.typed_metadata is not None
        assert isinstance(alias.typed_metadata, PythonAliasMetadata)
        assert "SampleClass" in alias.typed_metadata.alias_of

    def test_attribute_has_typed_metadata(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that class attributes have typed_metadata."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        class_elem = None
        for child in module.children:
            if child.name == "SampleClass":
                class_elem = child
                break

        assert class_elem is not None

        # Find name attribute
        attr = None
        for child in class_elem.children:
            if child.name == "name" and child.element_type == "attribute":
                attr = child
                break

        assert attr is not None
        assert attr.typed_metadata is not None
        assert isinstance(attr.typed_metadata, PythonAttributeMetadata)
        assert attr.typed_metadata.annotation == "str"


class TestTypedMetadataMatchesUntyped:
    """Tests to verify typed_metadata matches metadata dict."""

    def test_module_metadata_matches(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that typed_metadata matches metadata dict for modules."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        assert module.typed_metadata is not None
        assert isinstance(module.typed_metadata, PythonModuleMetadata)

        # The file_path should match
        assert module.typed_metadata.file_path == module.metadata.get("file_path")

    def test_class_metadata_matches(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that typed_metadata matches metadata dict for classes."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        class_elem = None
        for child in module.children:
            if child.name == "SampleClass":
                class_elem = child
                break

        assert class_elem is not None
        assert class_elem.typed_metadata is not None
        assert isinstance(class_elem.typed_metadata, PythonClassMetadata)

        # Bases should match
        assert list(class_elem.typed_metadata.bases) == class_elem.metadata.get("bases", [])

        # is_dataclass should match
        assert class_elem.typed_metadata.is_dataclass == class_elem.metadata.get("is_dataclass", False)

    def test_function_metadata_matches(self, extractor: PythonExtractor, sample_module: Path) -> None:
        """Test that typed_metadata matches metadata dict for functions."""
        elements = extractor.extract(sample_module)
        module = elements[0]

        # Find async_fetch function
        func = None
        for child in module.children:
            if child.name == "async_fetch":
                func = child
                break

        assert func is not None
        assert func.typed_metadata is not None
        assert isinstance(func.typed_metadata, PythonFunctionMetadata)

        # is_async should match
        assert func.typed_metadata.is_async == func.metadata.get("is_async", False)

        # return type should match
        assert func.typed_metadata.return_type == func.metadata.get("returns")


