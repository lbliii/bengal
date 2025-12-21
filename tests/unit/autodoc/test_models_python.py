"""
Unit tests for Python autodoc metadata dataclasses.
"""

from __future__ import annotations

import pytest

from bengal.autodoc.models import (
    PythonAliasMetadata,
    PythonAttributeMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
    PythonModuleMetadata,
)
from bengal.autodoc.models.python import (
    ParameterInfo,
    ParsedDocstring,
    RaisesInfo,
)


class TestParameterInfo:
    """Tests for ParameterInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic ParameterInfo creation."""
        param = ParameterInfo(name="path")
        assert param.name == "path"
        assert param.type_hint is None
        assert param.default is None
        assert param.kind == "positional_or_keyword"

    def test_with_type_and_default(self) -> None:
        """Test ParameterInfo with type hint and default."""
        param = ParameterInfo(
            name="force",
            type_hint="bool",
            default="False",
            kind="keyword",
            description="Force rebuild",
        )
        assert param.name == "force"
        assert param.type_hint == "bool"
        assert param.default == "False"
        assert param.kind == "keyword"
        assert param.description == "Force rebuild"

    def test_frozen(self) -> None:
        """Test that ParameterInfo is frozen."""
        param = ParameterInfo(name="test")
        with pytest.raises(AttributeError):
            param.name = "other"  # type: ignore[misc]


class TestRaisesInfo:
    """Tests for RaisesInfo dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic RaisesInfo creation."""
        raises = RaisesInfo(type_name="ValueError")
        assert raises.type_name == "ValueError"
        assert raises.description == ""

    def test_with_description(self) -> None:
        """Test RaisesInfo with description."""
        raises = RaisesInfo(type_name="FileNotFoundError", description="If file doesn't exist")
        assert raises.type_name == "FileNotFoundError"
        assert raises.description == "If file doesn't exist"


class TestParsedDocstring:
    """Tests for ParsedDocstring dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic ParsedDocstring creation."""
        doc = ParsedDocstring(summary="Short summary.")
        assert doc.summary == "Short summary."
        assert doc.description == ""
        assert doc.params == ()
        assert doc.returns is None

    def test_full_docstring(self) -> None:
        """Test ParsedDocstring with all fields."""
        params = (
            ParameterInfo(name="path", type_hint="Path"),
            ParameterInfo(name="force", type_hint="bool", default="False"),
        )
        raises = (RaisesInfo(type_name="ValueError", description="If path is invalid"),)
        doc = ParsedDocstring(
            summary="Build the site.",
            description="Build the site with optional force rebuild.",
            params=params,
            returns="None",
            raises=raises,
            examples=(">>> build(Path('.'))",),
        )
        assert doc.summary == "Build the site."
        assert doc.description == "Build the site with optional force rebuild."
        assert len(doc.params) == 2
        assert doc.params[0].name == "path"
        assert doc.returns == "None"
        assert len(doc.raises) == 1
        assert doc.raises[0].type_name == "ValueError"

    def test_frozen(self) -> None:
        """Test that ParsedDocstring is frozen."""
        doc = ParsedDocstring(summary="Test")
        with pytest.raises(AttributeError):
            doc.summary = "Other"  # type: ignore[misc]


class TestPythonModuleMetadata:
    """Tests for PythonModuleMetadata dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic PythonModuleMetadata creation."""
        meta = PythonModuleMetadata(file_path="bengal/core/site.py")
        assert meta.file_path == "bengal/core/site.py"
        assert meta.is_package is False
        assert meta.has_all is False
        assert meta.all_exports == ()

    def test_package(self) -> None:
        """Test package metadata."""
        meta = PythonModuleMetadata(
            file_path="bengal/core/__init__.py",
            is_package=True,
            has_all=True,
            all_exports=("Site", "Page", "Section"),
        )
        assert meta.file_path == "bengal/core/__init__.py"
        assert meta.is_package is True
        assert meta.has_all is True
        assert meta.all_exports == ("Site", "Page", "Section")

    def test_frozen(self) -> None:
        """Test that PythonModuleMetadata is frozen."""
        meta = PythonModuleMetadata(file_path="test.py")
        with pytest.raises(AttributeError):
            meta.file_path = "other.py"  # type: ignore[misc]


class TestPythonClassMetadata:
    """Tests for PythonClassMetadata dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic PythonClassMetadata creation."""
        meta = PythonClassMetadata()
        assert meta.bases == ()
        assert meta.decorators == ()
        assert meta.is_exception is False
        assert meta.is_dataclass is False
        assert meta.is_abstract is False
        assert meta.parsed_doc is None

    def test_with_bases_and_decorators(self) -> None:
        """Test class metadata with bases and decorators."""
        meta = PythonClassMetadata(
            bases=("BaseClass", "Mixin"),
            decorators=("dataclass", "frozen"),
            is_dataclass=True,
        )
        assert meta.bases == ("BaseClass", "Mixin")
        assert meta.decorators == ("dataclass", "frozen")
        assert meta.is_dataclass is True

    def test_exception_class(self) -> None:
        """Test exception class metadata."""
        meta = PythonClassMetadata(
            bases=("Exception",),
            is_exception=True,
        )
        assert meta.is_exception is True

    def test_abstract_class(self) -> None:
        """Test abstract class metadata."""
        meta = PythonClassMetadata(
            bases=("ABC",),
            is_abstract=True,
        )
        assert meta.is_abstract is True

    def test_frozen(self) -> None:
        """Test that PythonClassMetadata is frozen."""
        meta = PythonClassMetadata()
        with pytest.raises(AttributeError):
            meta.bases = ("Other",)  # type: ignore[misc]


class TestPythonFunctionMetadata:
    """Tests for PythonFunctionMetadata dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic PythonFunctionMetadata creation."""
        meta = PythonFunctionMetadata()
        assert meta.signature == ""
        assert meta.parameters == ()
        assert meta.return_type is None
        assert meta.is_async is False
        assert meta.is_classmethod is False
        assert meta.is_staticmethod is False
        assert meta.is_property is False
        assert meta.is_generator is False
        assert meta.decorators == ()

    def test_with_signature(self) -> None:
        """Test function metadata with signature."""
        params = (
            ParameterInfo(name="self"),
            ParameterInfo(name="path", type_hint="Path"),
        )
        meta = PythonFunctionMetadata(
            signature="def build(self, path: Path) -> None",
            parameters=params,
            return_type="None",
        )
        assert meta.signature == "def build(self, path: Path) -> None"
        assert len(meta.parameters) == 2
        assert meta.return_type == "None"

    def test_async_function(self) -> None:
        """Test async function metadata."""
        meta = PythonFunctionMetadata(
            signature="async def fetch(url: str) -> bytes",
            is_async=True,
        )
        assert meta.is_async is True

    def test_classmethod(self) -> None:
        """Test classmethod metadata."""
        meta = PythonFunctionMetadata(
            decorators=("classmethod",),
            is_classmethod=True,
        )
        assert meta.is_classmethod is True
        assert "classmethod" in meta.decorators

    def test_staticmethod(self) -> None:
        """Test staticmethod metadata."""
        meta = PythonFunctionMetadata(
            decorators=("staticmethod",),
            is_staticmethod=True,
        )
        assert meta.is_staticmethod is True

    def test_property(self) -> None:
        """Test property metadata."""
        meta = PythonFunctionMetadata(
            decorators=("property",),
            is_property=True,
        )
        assert meta.is_property is True

    def test_generator(self) -> None:
        """Test generator metadata."""
        meta = PythonFunctionMetadata(is_generator=True)
        assert meta.is_generator is True

    def test_frozen(self) -> None:
        """Test that PythonFunctionMetadata is frozen."""
        meta = PythonFunctionMetadata()
        with pytest.raises(AttributeError):
            meta.is_async = True  # type: ignore[misc]


class TestPythonAttributeMetadata:
    """Tests for PythonAttributeMetadata dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic PythonAttributeMetadata creation."""
        meta = PythonAttributeMetadata()
        assert meta.annotation is None
        assert meta.is_class_var is False
        assert meta.default_value is None

    def test_with_annotation(self) -> None:
        """Test attribute with annotation."""
        meta = PythonAttributeMetadata(
            annotation="str",
            is_class_var=True,
            default_value="'default'",
        )
        assert meta.annotation == "str"
        assert meta.is_class_var is True
        assert meta.default_value == "'default'"

    def test_frozen(self) -> None:
        """Test that PythonAttributeMetadata is frozen."""
        meta = PythonAttributeMetadata()
        with pytest.raises(AttributeError):
            meta.annotation = "int"  # type: ignore[misc]


class TestPythonAliasMetadata:
    """Tests for PythonAliasMetadata dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic PythonAliasMetadata creation."""
        meta = PythonAliasMetadata(alias_of="bengal.core.site.Site")
        assert meta.alias_of == "bengal.core.site.Site"
        assert meta.alias_kind == "assignment"

    def test_import_alias(self) -> None:
        """Test import alias metadata."""
        meta = PythonAliasMetadata(
            alias_of="os.path.join",
            alias_kind="import",
        )
        assert meta.alias_of == "os.path.join"
        assert meta.alias_kind == "import"

    def test_frozen(self) -> None:
        """Test that PythonAliasMetadata is frozen."""
        meta = PythonAliasMetadata(alias_of="test")
        with pytest.raises(AttributeError):
            meta.alias_of = "other"  # type: ignore[misc]


