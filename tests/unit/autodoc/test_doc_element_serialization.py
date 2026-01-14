"""
Serialization round-trip tests for DocElement typed_metadata.
"""

from __future__ import annotations

from bengal.autodoc.base import DocElement
from bengal.errors import BengalCacheError
from bengal.autodoc.models import (
    CLICommandMetadata,
    CLIGroupMetadata,
    OpenAPIEndpointMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
    PythonModuleMetadata,
)
from bengal.autodoc.models.openapi import (
    OpenAPIParameterMetadata,
    OpenAPIRequestBodyMetadata,
    OpenAPIResponseMetadata,
)
from bengal.autodoc.models.python import ParameterInfo


class TestDocElementSerialization:
    """Tests for DocElement serialization with typed_metadata."""

    def test_to_dict_without_typed_metadata(self) -> None:
        """Test that to_dict works without typed_metadata."""
        element = DocElement(
            name="test",
            qualified_name="module.test",
            description="Test element",
            element_type="module",
        )

        data = element.to_dict()

        assert data["name"] == "test"
        assert data["qualified_name"] == "module.test"
        assert data["typed_metadata"] is None

    def test_to_dict_with_python_module_metadata(self) -> None:
        """Test to_dict with PythonModuleMetadata."""
        typed_meta = PythonModuleMetadata(
            file_path="bengal/core/site.py",
            is_package=False,
            has_all=True,
            all_exports=("Site", "Page"),
        )
        element = DocElement(
            name="site",
            qualified_name="bengal.core.site",
            description="Site module",
            element_type="module",
            typed_metadata=typed_meta,
        )

        data = element.to_dict()

        assert data["typed_metadata"] is not None
        assert data["typed_metadata"]["type"] == "PythonModuleMetadata"
        assert data["typed_metadata"]["data"]["file_path"] == "bengal/core/site.py"
        assert data["typed_metadata"]["data"]["is_package"] is False
        assert data["typed_metadata"]["data"]["has_all"] is True
        assert data["typed_metadata"]["data"]["all_exports"] == ("Site", "Page")

    def test_to_dict_with_python_class_metadata(self) -> None:
        """Test to_dict with PythonClassMetadata."""
        typed_meta = PythonClassMetadata(
            bases=("BaseClass",),
            decorators=("dataclass",),
            is_dataclass=True,
            is_abstract=False,
        )
        element = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="A class",
            element_type="class",
            typed_metadata=typed_meta,
        )

        data = element.to_dict()

        assert data["typed_metadata"]["type"] == "PythonClassMetadata"
        assert data["typed_metadata"]["data"]["bases"] == ("BaseClass",)
        assert data["typed_metadata"]["data"]["is_dataclass"] is True

    def test_to_dict_with_python_function_metadata(self) -> None:
        """Test to_dict with PythonFunctionMetadata."""
        params = (
            ParameterInfo(name="path", type_hint="Path"),
            ParameterInfo(name="force", type_hint="bool", default="False"),
        )
        typed_meta = PythonFunctionMetadata(
            signature="def build(path: Path, force: bool = False) -> None",
            parameters=params,
            return_type="None",
            is_async=False,
        )
        element = DocElement(
            name="build",
            qualified_name="module.build",
            description="Build function",
            element_type="function",
            typed_metadata=typed_meta,
        )

        data = element.to_dict()

        assert data["typed_metadata"]["type"] == "PythonFunctionMetadata"
        assert data["typed_metadata"]["data"]["return_type"] == "None"
        assert len(data["typed_metadata"]["data"]["parameters"]) == 2


class TestDocElementDeserialization:
    """Tests for DocElement deserialization with typed_metadata."""

    def test_from_dict_without_typed_metadata(self) -> None:
        """Test that from_dict works without typed_metadata."""
        data = {
            "name": "test",
            "qualified_name": "module.test",
            "description": "Test element",
            "element_type": "module",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.name == "test"
        assert element.typed_metadata is None

    def test_from_dict_with_python_module_metadata(self) -> None:
        """Test from_dict with PythonModuleMetadata."""
        data = {
            "name": "site",
            "qualified_name": "bengal.core.site",
            "description": "Site module",
            "element_type": "module",
            "source_file": None,
            "line_number": 1,
            "metadata": {},
            "typed_metadata": {
                "type": "PythonModuleMetadata",
                "data": {
                    "file_path": "bengal/core/site.py",
                    "is_package": False,
                    "has_all": True,
                    "all_exports": ["Site", "Page"],
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.typed_metadata is not None
        assert isinstance(element.typed_metadata, PythonModuleMetadata)
        assert element.typed_metadata.file_path == "bengal/core/site.py"
        assert element.typed_metadata.is_package is False
        assert element.typed_metadata.has_all is True
        assert element.typed_metadata.all_exports == ("Site", "Page")

    def test_from_dict_with_python_class_metadata(self) -> None:
        """Test from_dict with PythonClassMetadata."""
        data = {
            "name": "MyClass",
            "qualified_name": "module.MyClass",
            "description": "A class",
            "element_type": "class",
            "source_file": None,
            "line_number": 10,
            "metadata": {},
            "typed_metadata": {
                "type": "PythonClassMetadata",
                "data": {
                    "bases": ["BaseClass"],
                    "decorators": ["dataclass"],
                    "is_exception": False,
                    "is_dataclass": True,
                    "is_abstract": False,
                    "parsed_doc": None,
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.typed_metadata is not None
        assert isinstance(element.typed_metadata, PythonClassMetadata)
        assert element.typed_metadata.bases == ("BaseClass",)
        assert element.typed_metadata.is_dataclass is True

    def test_from_dict_with_cli_command_metadata(self) -> None:
        """Test from_dict with CLICommandMetadata."""
        data = {
            "name": "build",
            "qualified_name": "cli.build",
            "description": "Build command",
            "element_type": "command",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "typed_metadata": {
                "type": "CLICommandMetadata",
                "data": {
                    "callback": "build_cmd",
                    "option_count": 3,
                    "argument_count": 1,
                    "is_group": False,
                    "is_hidden": False,
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.typed_metadata is not None
        assert isinstance(element.typed_metadata, CLICommandMetadata)
        assert element.typed_metadata.callback == "build_cmd"
        assert element.typed_metadata.option_count == 3

    def test_from_dict_with_openapi_endpoint_metadata(self) -> None:
        """Test from_dict with OpenAPIEndpointMetadata."""
        data = {
            "name": "GET /users",
            "qualified_name": "openapi.paths./users.get",
            "description": "Get users",
            "element_type": "openapi_endpoint",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "typed_metadata": {
                "type": "OpenAPIEndpointMetadata",
                "data": {
                    "method": "GET",
                    "path": "/users",
                    "operation_id": "getUsers",
                    "summary": "Get all users",
                    "tags": ["users"],
                    "parameters": [],
                    "request_body": None,
                    "responses": [],
                    "security": [],
                    "deprecated": False,
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        assert element.typed_metadata is not None
        assert isinstance(element.typed_metadata, OpenAPIEndpointMetadata)
        assert element.typed_metadata.method == "GET"
        assert element.typed_metadata.path == "/users"


class TestRoundTrip:
    """Tests for serialization round-trip preservation."""

    def test_round_trip_python_module(self) -> None:
        """Test round-trip for PythonModuleMetadata."""
        typed_meta = PythonModuleMetadata(
            file_path="test.py",
            is_package=True,
            has_all=True,
            all_exports=("A", "B", "C"),
        )
        original = DocElement(
            name="test",
            qualified_name="test",
            description="Test module",
            element_type="module",
            typed_metadata=typed_meta,
        )

        data = original.to_dict()
        restored = DocElement.from_dict(data)

        assert restored.typed_metadata is not None
        assert isinstance(restored.typed_metadata, PythonModuleMetadata)
        assert restored.typed_metadata.file_path == original.typed_metadata.file_path
        assert restored.typed_metadata.is_package == original.typed_metadata.is_package
        assert restored.typed_metadata.has_all == original.typed_metadata.has_all
        assert restored.typed_metadata.all_exports == original.typed_metadata.all_exports

    def test_round_trip_python_class(self) -> None:
        """Test round-trip for PythonClassMetadata."""
        typed_meta = PythonClassMetadata(
            bases=("ABC", "Mixin"),
            decorators=("dataclass", "frozen"),
            is_exception=False,
            is_dataclass=True,
            is_abstract=True,
        )
        original = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="My class",
            element_type="class",
            typed_metadata=typed_meta,
        )

        data = original.to_dict()
        restored = DocElement.from_dict(data)

        assert restored.typed_metadata is not None
        assert isinstance(restored.typed_metadata, PythonClassMetadata)
        assert restored.typed_metadata.bases == original.typed_metadata.bases
        assert restored.typed_metadata.decorators == original.typed_metadata.decorators
        assert restored.typed_metadata.is_dataclass == original.typed_metadata.is_dataclass
        assert restored.typed_metadata.is_abstract == original.typed_metadata.is_abstract

    def test_round_trip_python_function_with_params(self) -> None:
        """Test round-trip for PythonFunctionMetadata with parameters."""
        params = (
            ParameterInfo(name="x", type_hint="int", default="0"),
            ParameterInfo(name="y", type_hint="str"),
        )
        typed_meta = PythonFunctionMetadata(
            signature="def func(x: int = 0, y: str) -> bool",
            parameters=params,
            return_type="bool",
            is_async=True,
        )
        original = DocElement(
            name="func",
            qualified_name="module.func",
            description="A function",
            element_type="function",
            typed_metadata=typed_meta,
        )

        data = original.to_dict()
        restored = DocElement.from_dict(data)

        assert restored.typed_metadata is not None
        assert isinstance(restored.typed_metadata, PythonFunctionMetadata)
        assert restored.typed_metadata.signature == original.typed_metadata.signature
        assert restored.typed_metadata.return_type == original.typed_metadata.return_type
        assert restored.typed_metadata.is_async == original.typed_metadata.is_async
        assert len(restored.typed_metadata.parameters) == 2
        assert restored.typed_metadata.parameters[0].name == "x"
        assert restored.typed_metadata.parameters[0].type_hint == "int"
        assert restored.typed_metadata.parameters[1].name == "y"

    def test_round_trip_cli_group(self) -> None:
        """Test round-trip for CLIGroupMetadata."""
        typed_meta = CLIGroupMetadata(
            callback="main_cli",
            command_count=5,
        )
        original = DocElement(
            name="cli",
            qualified_name="cli",
            description="Main CLI",
            element_type="command-group",
            typed_metadata=typed_meta,
        )

        data = original.to_dict()
        restored = DocElement.from_dict(data)

        assert restored.typed_metadata is not None
        assert isinstance(restored.typed_metadata, CLIGroupMetadata)
        assert restored.typed_metadata.callback == original.typed_metadata.callback
        assert restored.typed_metadata.command_count == original.typed_metadata.command_count

    def test_round_trip_openapi_with_nested_metadata(self) -> None:
        """Test round-trip for OpenAPIEndpointMetadata with nested parameters/request_body/responses.

        This test prevents regression of cache corruption where nested dataclasses
        were serialized as string representations instead of dicts.
        """
        params = (
            OpenAPIParameterMetadata(
                name="page",
                location="query",
                required=False,
                schema_type="integer",
                description="Page number (1-based)",
            ),
            OpenAPIParameterMetadata(
                name="userId",
                location="path",
                required=True,
                schema_type="string",
                description="User identifier",
            ),
        )
        request_body = OpenAPIRequestBodyMetadata(
            content_type="application/json",
            schema_ref="#/components/schemas/UserCreate",
            required=True,
            description="User data",
        )
        responses = (
            OpenAPIResponseMetadata(
                status_code="200",
                description="Success",
                content_type="application/json",
                schema_ref="#/components/schemas/User",
            ),
            OpenAPIResponseMetadata(
                status_code="404",
                description="Not found",
            ),
        )
        typed_meta = OpenAPIEndpointMetadata(
            method="POST",
            path="/users/{userId}",
            operation_id="updateUser",
            summary="Update a user",
            tags=("users", "admin"),
            parameters=params,
            request_body=request_body,
            responses=responses,
            security=("bearerAuth",),
            deprecated=False,
        )
        original = DocElement(
            name="POST /users/{userId}",
            qualified_name="openapi.paths./users/{userId}.post",
            description="Update a user",
            element_type="openapi_endpoint",
            typed_metadata=typed_meta,
        )

        data = original.to_dict()
        restored = DocElement.from_dict(data)

        # Verify top-level metadata
        assert restored.typed_metadata is not None
        assert isinstance(restored.typed_metadata, OpenAPIEndpointMetadata)
        assert restored.typed_metadata.method == "POST"
        assert restored.typed_metadata.path == "/users/{userId}"
        assert restored.typed_metadata.tags == ("users", "admin")

        # Verify nested parameters are dicts → dataclass instances
        assert len(restored.typed_metadata.parameters) == 2
        param1 = restored.typed_metadata.parameters[0]
        assert isinstance(param1, OpenAPIParameterMetadata)
        assert param1.name == "page"
        assert param1.location == "query"
        assert param1.schema_type == "integer"

        param2 = restored.typed_metadata.parameters[1]
        assert isinstance(param2, OpenAPIParameterMetadata)
        assert param2.name == "userId"
        assert param2.required is True

        # Verify nested request_body
        assert restored.typed_metadata.request_body is not None
        assert isinstance(restored.typed_metadata.request_body, OpenAPIRequestBodyMetadata)
        assert restored.typed_metadata.request_body.content_type == "application/json"
        assert restored.typed_metadata.request_body.schema_ref == "#/components/schemas/UserCreate"

        # Verify nested responses
        assert len(restored.typed_metadata.responses) == 2
        resp1 = restored.typed_metadata.responses[0]
        assert isinstance(resp1, OpenAPIResponseMetadata)
        assert resp1.status_code == "200"
        assert resp1.content_type == "application/json"

    def test_round_trip_with_children(self) -> None:
        """Test round-trip preserves children typed_metadata."""
        child_meta = PythonFunctionMetadata(
            signature="def method(self) -> None",
            return_type="None",
        )
        child = DocElement(
            name="method",
            qualified_name="module.MyClass.method",
            description="A method",
            element_type="method",
            typed_metadata=child_meta,
        )

        parent_meta = PythonClassMetadata(
            bases=(),
            decorators=(),
        )
        parent = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="A class",
            element_type="class",
            typed_metadata=parent_meta,
            children=[child],
        )

        data = parent.to_dict()
        restored = DocElement.from_dict(data)

        assert len(restored.children) == 1
        assert restored.children[0].typed_metadata is not None
        assert isinstance(restored.children[0].typed_metadata, PythonFunctionMetadata)
        assert restored.children[0].typed_metadata.return_type == "None"

    def test_round_trip_unknown_type_returns_none(self) -> None:
        """Test that unknown typed_metadata type returns None on deserialize."""
        data = {
            "name": "test",
            "qualified_name": "test",
            "description": "Test",
            "element_type": "custom",
            "source_file": None,
            "line_number": None,
            "metadata": {},
            "typed_metadata": {
                "type": "UnknownMetadataType",
                "data": {"field": "value"},
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        element = DocElement.from_dict(data)

        # Unknown type should be deserialized as None
        assert element.typed_metadata is None


class TestDeserializationErrors:
    """Tests for deserialization error handling with invalid data formats."""

    def test_from_dict_with_string_parameters_raises_clear_error(self) -> None:
        """Test that string parameters (legacy format) raise clear error."""
        import pytest

        data = {
            "name": "func",
            "qualified_name": "module.func",
            "description": "A function",
            "element_type": "function",
            "source_file": None,
            "line_number": 10,
            "metadata": {},
            "typed_metadata": {
                "type": "PythonFunctionMetadata",
                "data": {
                    "signature": "def func(x, y)",
                    "parameters": ["x", "y"],  # Invalid: strings instead of dicts
                    "return_type": "None",
                    "is_async": False,
                    "is_classmethod": False,
                    "is_staticmethod": False,
                    "is_property": False,
                    "is_generator": False,
                    "decorators": [],
                    "parsed_doc": None,
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        with pytest.raises(BengalCacheError, match="Autodoc cache format mismatch"):
            DocElement.from_dict(data)

    def test_from_dict_with_string_parsed_doc_params_raises_clear_error(self) -> None:
        """Test that string params in parsed_doc raise clear error."""
        import pytest

        data = {
            "name": "func",
            "qualified_name": "module.func",
            "description": "A function",
            "element_type": "function",
            "source_file": None,
            "line_number": 10,
            "metadata": {},
            "typed_metadata": {
                "type": "PythonFunctionMetadata",
                "data": {
                    "signature": "def func(x)",
                    "parameters": [
                        {
                            "name": "x",
                            "type_hint": "int",
                            "default": None,
                            "kind": "positional_or_keyword",
                            "description": None,
                        }
                    ],
                    "return_type": "None",
                    "is_async": False,
                    "is_classmethod": False,
                    "is_staticmethod": False,
                    "is_property": False,
                    "is_generator": False,
                    "decorators": [],
                    "parsed_doc": {
                        "summary": "A function",
                        "description": "",
                        "params": ["x"],  # Invalid: strings instead of dicts
                        "returns": None,
                        "raises": [],
                        "examples": [],
                    },
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        with pytest.raises(BengalCacheError, match="Autodoc cache format mismatch"):
            DocElement.from_dict(data)

    def test_error_message_includes_cache_clear_hint(self) -> None:
        """Test that error message includes hint to clear cache."""
        import pytest

        data = {
            "name": "func",
            "qualified_name": "module.func",
            "description": "A function",
            "element_type": "function",
            "source_file": None,
            "line_number": 10,
            "metadata": {},
            "typed_metadata": {
                "type": "PythonFunctionMetadata",
                "data": {
                    "signature": "def func(x)",
                    "parameters": ["x"],  # Invalid format
                    "return_type": "None",
                    "is_async": False,
                    "is_classmethod": False,
                    "is_staticmethod": False,
                    "is_property": False,
                    "is_generator": False,
                    "decorators": [],
                    "parsed_doc": None,
                },
            },
            "children": [],
            "examples": [],
            "see_also": [],
            "deprecated": None,
        }

        with pytest.raises(BengalCacheError) as exc_info:
            DocElement.from_dict(data)

        # Verify helpful error message - now in suggestion field
        assert "cache" in exc_info.value.suggestion.lower()
        assert exc_info.value.code.name == "A001"
