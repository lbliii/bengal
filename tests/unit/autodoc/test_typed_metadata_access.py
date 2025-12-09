"""
Tests for typed metadata access helper functions.

Verifies that helpers correctly use typed_metadata when available and
fall back to untyped metadata dict when not.
"""

from bengal.autodoc.base import DocElement
from bengal.autodoc.models import (
    CLICommandMetadata,
    CLIGroupMetadata,
    OpenAPIEndpointMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
)
from bengal.autodoc.utils import (
    get_cli_command_callback,
    get_cli_command_option_count,
    get_cli_group_command_count,
    get_openapi_method,
    get_openapi_operation_id,
    get_openapi_path,
    get_openapi_tags,
    get_python_class_bases,
    get_python_class_decorators,
    get_python_class_is_dataclass,
    get_python_function_decorators,
    get_python_function_is_property,
    get_python_function_return_type,
    get_python_function_signature,
)

# =============================================================================
# Python Metadata Helpers
# =============================================================================


class TestGetPythonClassBases:
    """Tests for get_python_class_bases helper."""

    def test_from_typed_metadata(self):
        """Should return bases from typed_metadata when present."""
        meta = PythonClassMetadata(
            bases=("ABC", "Mixin"),
            decorators=(),
            is_dataclass=False,
            is_abstract=True,
        )
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={"bases": ["Different"]},  # Should be ignored
            typed_metadata=meta,
        )
        assert get_python_class_bases(elem) == ("ABC", "Mixin")

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={"bases": ["Base1", "Base2"]},
            typed_metadata=None,
        )
        assert get_python_class_bases(elem) == ("Base1", "Base2")

    def test_empty_default(self):
        """Should return empty tuple when no bases in either."""
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={},
            typed_metadata=None,
        )
        assert get_python_class_bases(elem) == ()


class TestGetPythonClassDecorators:
    """Tests for get_python_class_decorators helper."""

    def test_from_typed_metadata(self):
        """Should return decorators from typed_metadata when present."""
        meta = PythonClassMetadata(
            bases=(),
            decorators=("dataclass", "frozen"),
            is_dataclass=True,
            is_abstract=False,
        )
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            typed_metadata=meta,
        )
        assert get_python_class_decorators(elem) == ("dataclass", "frozen")

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={"decorators": ["singleton"]},
        )
        assert get_python_class_decorators(elem) == ("singleton",)


class TestGetPythonClassIsDataclass:
    """Tests for get_python_class_is_dataclass helper."""

    def test_from_typed_metadata_true(self):
        """Should return True when typed_metadata indicates dataclass."""
        meta = PythonClassMetadata(
            bases=(),
            decorators=("dataclass",),
            is_dataclass=True,
            is_abstract=False,
        )
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            typed_metadata=meta,
        )
        assert get_python_class_is_dataclass(elem) is True

    def test_from_typed_metadata_false(self):
        """Should return False when typed_metadata indicates not dataclass."""
        meta = PythonClassMetadata(
            bases=(),
            decorators=(),
            is_dataclass=False,
            is_abstract=False,
        )
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            typed_metadata=meta,
        )
        assert get_python_class_is_dataclass(elem) is False

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={"is_dataclass": True},
        )
        assert get_python_class_is_dataclass(elem) is True


class TestGetPythonFunctionDecorators:
    """Tests for get_python_function_decorators helper."""

    def test_from_typed_metadata(self):
        """Should return decorators from typed_metadata when present."""
        meta = PythonFunctionMetadata(
            signature="def example() -> None",
            parameters=(),
            return_type="None",
            is_async=False,
            is_property=False,
            is_classmethod=False,
            is_staticmethod=False,
            decorators=("override", "classmethod"),
        )
        elem = DocElement(
            name="example",
            qualified_name="module.example",
            description="Test function",
            element_type="function",
            typed_metadata=meta,
        )
        assert get_python_function_decorators(elem) == ("override", "classmethod")

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="example",
            qualified_name="module.example",
            description="Test function",
            element_type="function",
            metadata={"decorators": ["staticmethod"]},
        )
        assert get_python_function_decorators(elem) == ("staticmethod",)


class TestGetPythonFunctionIsProperty:
    """Tests for get_python_function_is_property helper."""

    def test_from_typed_metadata_true(self):
        """Should return True when typed_metadata indicates property."""
        meta = PythonFunctionMetadata(
            signature="def name(self) -> str",
            parameters=(),
            return_type="str",
            is_async=False,
            is_property=True,
            is_classmethod=False,
            is_staticmethod=False,
            decorators=("property",),
        )
        elem = DocElement(
            name="name",
            qualified_name="module.Class.name",
            description="Name property",
            element_type="method",
            typed_metadata=meta,
        )
        assert get_python_function_is_property(elem) is True

    def test_from_typed_metadata_false(self):
        """Should return False when typed_metadata indicates not property."""
        meta = PythonFunctionMetadata(
            signature="def build(self) -> None",
            parameters=(),
            return_type="None",
            is_async=False,
            is_property=False,
            is_classmethod=False,
            is_staticmethod=False,
            decorators=(),
        )
        elem = DocElement(
            name="build",
            qualified_name="module.Class.build",
            description="Build method",
            element_type="method",
            typed_metadata=meta,
        )
        assert get_python_function_is_property(elem) is False

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="name",
            qualified_name="module.Class.name",
            description="Name property",
            element_type="method",
            metadata={"is_property": True},
        )
        assert get_python_function_is_property(elem) is True


class TestGetPythonFunctionSignature:
    """Tests for get_python_function_signature helper."""

    def test_from_typed_metadata(self):
        """Should return signature from typed_metadata when present."""
        meta = PythonFunctionMetadata(
            signature="def build(force: bool = False) -> None",
            parameters=(),
            return_type="None",
            is_async=False,
            is_property=False,
            is_classmethod=False,
            is_staticmethod=False,
            decorators=(),
        )
        elem = DocElement(
            name="build",
            qualified_name="module.build",
            description="Build function",
            element_type="function",
            typed_metadata=meta,
        )
        assert get_python_function_signature(elem) == "def build(force: bool = False) -> None"

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="build",
            qualified_name="module.build",
            description="Build function",
            element_type="function",
            metadata={"signature": "def build() -> None"},
        )
        assert get_python_function_signature(elem) == "def build() -> None"


class TestGetPythonFunctionReturnType:
    """Tests for get_python_function_return_type helper."""

    def test_from_typed_metadata(self):
        """Should return return_type from typed_metadata when present."""
        meta = PythonFunctionMetadata(
            signature="def build() -> None",
            parameters=(),
            return_type="None",
            is_async=False,
            is_property=False,
            is_classmethod=False,
            is_staticmethod=False,
            decorators=(),
        )
        elem = DocElement(
            name="build",
            qualified_name="module.build",
            description="Build function",
            element_type="function",
            typed_metadata=meta,
        )
        assert get_python_function_return_type(elem) == "None"

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="build",
            qualified_name="module.build",
            description="Build function",
            element_type="function",
            metadata={"returns": "str"},
        )
        assert get_python_function_return_type(elem) == "str"


# =============================================================================
# CLI Metadata Helpers
# =============================================================================


class TestGetCliCommandCallback:
    """Tests for get_cli_command_callback helper."""

    def test_from_typed_metadata(self):
        """Should return callback from typed_metadata when present."""
        meta = CLICommandMetadata(
            callback="build_command",
            argument_count=0,
            option_count=3,
        )
        elem = DocElement(
            name="build",
            qualified_name="cli.build",
            description="Build command",
            element_type="command",
            typed_metadata=meta,
        )
        assert get_cli_command_callback(elem) == "build_command"

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="build",
            qualified_name="cli.build",
            description="Build command",
            element_type="command",
            metadata={"callback": "build_func"},
        )
        assert get_cli_command_callback(elem) == "build_func"


class TestGetCliCommandOptionCount:
    """Tests for get_cli_command_option_count helper."""

    def test_from_typed_metadata(self):
        """Should return option_count from typed_metadata when present."""
        meta = CLICommandMetadata(
            callback="serve_command",
            argument_count=1,
            option_count=5,
        )
        elem = DocElement(
            name="serve",
            qualified_name="cli.serve",
            description="Serve command",
            element_type="command",
            typed_metadata=meta,
        )
        assert get_cli_command_option_count(elem) == 5

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="serve",
            qualified_name="cli.serve",
            description="Serve command",
            element_type="command",
            metadata={"option_count": 3},
        )
        assert get_cli_command_option_count(elem) == 3


class TestGetCliGroupCommandCount:
    """Tests for get_cli_group_command_count helper."""

    def test_from_typed_metadata(self):
        """Should return command_count from typed_metadata when present."""
        meta = CLIGroupMetadata(
            callback="main_group",
            command_count=7,
        )
        elem = DocElement(
            name="bengal",
            qualified_name="cli.bengal",
            description="Main CLI group",
            element_type="command-group",
            typed_metadata=meta,
        )
        assert get_cli_group_command_count(elem) == 7

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="bengal",
            qualified_name="cli.bengal",
            description="Main CLI group",
            element_type="command-group",
            metadata={"command_count": 4},
        )
        assert get_cli_group_command_count(elem) == 4


# =============================================================================
# OpenAPI Metadata Helpers
# =============================================================================


class TestGetOpenapiTags:
    """Tests for get_openapi_tags helper."""

    def test_from_typed_metadata(self):
        """Should return tags from typed_metadata when present."""
        meta = OpenAPIEndpointMetadata(
            method="GET",
            path="/users",
            tags=("users", "admin"),
            operation_id="listUsers",
            summary="List all users",
        )
        elem = DocElement(
            name="GET /users",
            qualified_name="api.users.list",
            description="List users",
            element_type="openapi_endpoint",
            typed_metadata=meta,
        )
        assert get_openapi_tags(elem) == ("users", "admin")

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="GET /users",
            qualified_name="api.users.list",
            description="List users",
            element_type="openapi_endpoint",
            metadata={"tags": ["users"]},
        )
        assert get_openapi_tags(elem) == ("users",)

    def test_empty_default(self):
        """Should return empty tuple when no tags."""
        elem = DocElement(
            name="GET /status",
            qualified_name="api.status",
            description="Health check",
            element_type="openapi_endpoint",
            metadata={},
        )
        assert get_openapi_tags(elem) == ()


class TestGetOpenapiMethod:
    """Tests for get_openapi_method helper."""

    def test_from_typed_metadata(self):
        """Should return method from typed_metadata when present."""
        meta = OpenAPIEndpointMetadata(
            method="POST",
            path="/users",
            tags=(),
            operation_id=None,
            summary="Create user",
        )
        elem = DocElement(
            name="POST /users",
            qualified_name="api.users.create",
            description="Create user",
            element_type="openapi_endpoint",
            typed_metadata=meta,
        )
        assert get_openapi_method(elem) == "POST"

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="DELETE /users/{id}",
            qualified_name="api.users.delete",
            description="Delete user",
            element_type="openapi_endpoint",
            metadata={"method": "delete"},
        )
        # Should be uppercased
        assert get_openapi_method(elem) == "DELETE"


class TestGetOpenapiPath:
    """Tests for get_openapi_path helper."""

    def test_from_typed_metadata(self):
        """Should return path from typed_metadata when present."""
        meta = OpenAPIEndpointMetadata(
            method="GET",
            path="/users/{id}",
            tags=(),
            operation_id=None,
            summary="Get user",
        )
        elem = DocElement(
            name="GET /users/{id}",
            qualified_name="api.users.get",
            description="Get user by ID",
            element_type="openapi_endpoint",
            typed_metadata=meta,
        )
        assert get_openapi_path(elem) == "/users/{id}"

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="GET /items",
            qualified_name="api.items.list",
            description="List items",
            element_type="openapi_endpoint",
            metadata={"path": "/items"},
        )
        assert get_openapi_path(elem) == "/items"


class TestGetOpenapiOperationId:
    """Tests for get_openapi_operation_id helper."""

    def test_from_typed_metadata(self):
        """Should return operation_id from typed_metadata when present."""
        meta = OpenAPIEndpointMetadata(
            method="GET",
            path="/users",
            tags=(),
            operation_id="listAllUsers",
            summary="List users",
        )
        elem = DocElement(
            name="GET /users",
            qualified_name="api.users.list",
            description="List users",
            element_type="openapi_endpoint",
            typed_metadata=meta,
        )
        assert get_openapi_operation_id(elem) == "listAllUsers"

    def test_fallback_to_untyped(self):
        """Should fall back to metadata dict when typed_metadata is None."""
        elem = DocElement(
            name="GET /users",
            qualified_name="api.users.list",
            description="List users",
            element_type="openapi_endpoint",
            metadata={"operation_id": "getUsers"},
        )
        assert get_openapi_operation_id(elem) == "getUsers"

    def test_none_when_missing(self):
        """Should return None when operation_id not set."""
        elem = DocElement(
            name="GET /status",
            qualified_name="api.status",
            description="Health check",
            element_type="openapi_endpoint",
            metadata={},
        )
        assert get_openapi_operation_id(elem) is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestTypedMetadataPrecedence:
    """Test that typed_metadata always takes precedence over metadata dict."""

    def test_typed_metadata_wins_over_untyped(self):
        """When both present, typed_metadata should win."""
        meta = PythonClassMetadata(
            bases=("TypedBase",),
            decorators=("typed_decorator",),
            is_dataclass=True,
            is_abstract=False,
        )
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={
                "bases": ["UntypedBase"],
                "decorators": ["untyped_decorator"],
                "is_dataclass": False,
            },
            typed_metadata=meta,
        )

        # Typed metadata should win
        assert get_python_class_bases(elem) == ("TypedBase",)
        assert get_python_class_decorators(elem) == ("typed_decorator",)
        assert get_python_class_is_dataclass(elem) is True

    def test_fallback_when_typed_is_none(self):
        """When typed_metadata is None, fall back to metadata dict."""
        elem = DocElement(
            name="MyClass",
            qualified_name="module.MyClass",
            description="Test class",
            element_type="class",
            metadata={
                "bases": ["FallbackBase"],
                "decorators": ["fallback_decorator"],
                "is_dataclass": True,
            },
            typed_metadata=None,
        )

        # Should fall back to metadata dict
        assert get_python_class_bases(elem) == ("FallbackBase",)
        assert get_python_class_decorators(elem) == ("fallback_decorator",)
        assert get_python_class_is_dataclass(elem) is True

    def test_fallback_when_typed_wrong_type(self):
        """When typed_metadata is wrong type for helper, fall back to metadata dict."""
        # Function metadata but calling class helper
        meta = PythonFunctionMetadata(
            signature="def example() -> None",
            parameters=(),
            return_type="None",
            is_async=False,
            is_property=False,
            is_classmethod=False,
            is_staticmethod=False,
            decorators=(),
        )
        elem = DocElement(
            name="example",
            qualified_name="module.example",
            description="Test",
            element_type="function",
            metadata={"bases": ["ShouldBeReturned"]},
            typed_metadata=meta,
        )

        # Should fall back because typed_metadata is wrong type for class helper
        assert get_python_class_bases(elem) == ("ShouldBeReturned",)
