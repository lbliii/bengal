"""
Tests for autodoc view dataclasses and filters (MemberView, CommandView, OptionView).

These views normalize access to Python and CLI autodoc data for theme developers,
providing a consistent API regardless of how data is stored in DocElements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bengal.rendering.template_functions.autodoc import (
    CommandView,
    MemberView,
    OptionView,
    ParamView,
    commands_filter,
    members_filter,
    options_filter,
)

# =============================================================================
# Mock Classes
# =============================================================================


@dataclass
class MockParameterInfo:
    """Mock ParameterInfo for testing."""

    name: str
    type_hint: str | None = None
    default: str | None = None
    kind: str = "positional_or_keyword"
    description: str | None = None


@dataclass
class MockParsedDocstring:
    """Mock ParsedDocstring for testing."""

    summary: str = ""
    description: str = ""
    returns: str | None = None


@dataclass
class MockPythonFunctionMetadata:
    """Mock PythonFunctionMetadata for testing."""

    signature: str = ""
    parameters: tuple[MockParameterInfo, ...] = ()
    return_type: str | None = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    is_generator: bool = False
    decorators: tuple[str, ...] = ()
    parsed_doc: MockParsedDocstring | None = None


@dataclass
class MockCLIOptionMetadata:
    """Mock CLIOptionMetadata for testing."""

    name: str = ""
    param_type: str = "option"
    type_name: str = "STRING"
    required: bool = False
    default: Any = None
    multiple: bool = False
    is_flag: bool = False
    opts: tuple[str, ...] = ()
    envvar: str | None = None
    help_text: str = ""


@dataclass
class MockCLICommandMetadata:
    """Mock CLICommandMetadata for testing."""

    callback: str | None = None
    option_count: int = 0
    argument_count: int = 0
    is_group: bool = False
    is_hidden: bool = False


@dataclass
class MockDocElement:
    """Mock DocElement for testing."""

    name: str
    description: str = ""
    element_type: str = "function"
    typed_metadata: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list[Any] = field(default_factory=list)
    href: str | None = None


# =============================================================================
# Tests for ParamView
# =============================================================================


class TestParamView:
    """Tests for ParamView dataclass."""

    def test_from_dict(self) -> None:
        """Creates ParamView from parameter dict."""
        param_dict = {
            "name": "path",
            "type": "Path",
            "default": "None",
            "required": False,
            "description": "The file path",
            "kind": "positional_or_keyword",
        }

        view = ParamView.from_dict(param_dict)

        assert view.name == "path"
        assert view.type == "Path"
        assert view.default == "None"
        assert view.required is False
        assert view.description == "The file path"

    def test_from_dict_with_missing_fields(self) -> None:
        """Handles missing fields with defaults."""
        view = ParamView.from_dict({"name": "x"})

        assert view.name == "x"
        assert view.type == ""
        assert view.default is None
        assert view.required is False


# =============================================================================
# Tests for MemberView
# =============================================================================


class TestMemberViewFromDocElement:
    """Tests for MemberView.from_doc_element()."""

    def test_extracts_from_typed_metadata(self) -> None:
        """Extracts member data from typed_metadata."""
        meta = MockPythonFunctionMetadata(
            signature="def process(data: str) -> bool",
            parameters=(
                MockParameterInfo(name="self"),
                MockParameterInfo(name="data", type_hint="str", description="Input data"),
            ),
            return_type="bool",
            is_async=True,
            is_classmethod=True,
            decorators=("classmethod",),
            parsed_doc=MockParsedDocstring(returns="True if successful"),
        )
        element = MockDocElement(
            name="process",
            description="Process the data",
            typed_metadata=meta,
            href="/api/module/Class/process/",
        )

        view = MemberView.from_doc_element(element)

        assert view.name == "process"
        assert view.signature == "def process(data: str) -> bool"
        assert view.description == "Process the data"
        assert view.return_type == "bool"
        assert view.return_description == "True if successful"
        assert view.is_async is True
        assert view.is_classmethod is True
        assert view.href == "/api/module/Class/process/"
        assert len(view.params) == 1  # self excluded
        assert view.params[0].name == "data"

    def test_extracts_from_metadata_dict(self) -> None:
        """Falls back to metadata dict when typed_metadata unavailable."""
        element = MockDocElement(
            name="helper",
            description="A helper function",
            metadata={
                "signature": "def helper(x: int) -> str",
                "return_type": "str",
                "is_async": False,
                "is_property": True,
            },
        )

        view = MemberView.from_doc_element(element)

        assert view.name == "helper"
        assert view.signature == "def helper(x: int) -> str"
        assert view.return_type == "str"
        assert view.is_property is True

    def test_detects_private_members(self) -> None:
        """Correctly identifies private members."""
        element = MockDocElement(name="_internal")
        view = MemberView.from_doc_element(element)
        assert view.is_private is True

        element2 = MockDocElement(name="public")
        view2 = MemberView.from_doc_element(element2)
        assert view2.is_private is False

    def test_detects_deprecated(self) -> None:
        """Detects deprecated from decorators."""
        meta = MockPythonFunctionMetadata(decorators=("deprecated",))
        element = MockDocElement(name="old_func", typed_metadata=meta)

        view = MemberView.from_doc_element(element)

        assert view.is_deprecated is True

    def test_href_fallback_to_anchor(self) -> None:
        """Falls back to anchor when no href."""
        element = MockDocElement(name="method", href=None)

        view = MemberView.from_doc_element(element)

        assert view.href == "#method"

    def test_excludes_self_and_cls_params(self) -> None:
        """Excludes self and cls from params."""
        meta = MockPythonFunctionMetadata(
            parameters=(
                MockParameterInfo(name="self"),
                MockParameterInfo(name="cls"),
                MockParameterInfo(name="value"),
            )
        )
        element = MockDocElement(name="method", typed_metadata=meta)

        view = MemberView.from_doc_element(element)

        assert len(view.params) == 1
        assert view.params[0].name == "value"


# =============================================================================
# Tests for OptionView
# =============================================================================


class TestOptionViewFromDocElement:
    """Tests for OptionView.from_doc_element()."""

    def test_extracts_from_typed_metadata(self) -> None:
        """Extracts option data from typed_metadata."""
        meta = MockCLIOptionMetadata(
            name="verbose",
            param_type="option",
            type_name="BOOL",
            is_flag=True,
            opts=("-v", "--verbose"),
            help_text="Enable verbose output",
            envvar="VERBOSE",
        )
        element = MockDocElement(
            name="verbose",
            element_type="option",
            typed_metadata=meta,
        )

        view = OptionView.from_doc_element(element)

        assert view.name == "verbose"
        assert view.flags == ("-v", "--verbose")
        assert view.flags_str == "-v, --verbose"
        assert view.type == "BOOL"
        assert view.is_flag is True
        assert view.is_argument is False
        assert view.description == "Enable verbose output"
        assert view.envvar == "VERBOSE"

    def test_identifies_arguments(self) -> None:
        """Correctly identifies arguments vs options."""
        meta = MockCLIOptionMetadata(
            name="source",
            param_type="argument",
            type_name="PATH",
            required=True,
        )
        element = MockDocElement(name="source", typed_metadata=meta)

        view = OptionView.from_doc_element(element)

        assert view.is_argument is True
        assert view.required is True

    def test_extracts_from_metadata_dict(self) -> None:
        """Falls back to metadata dict when typed_metadata unavailable."""
        element = MockDocElement(
            name="output",
            description="Output path",
            metadata={
                "opts": ("-o", "--output"),
                "type_name": "PATH",
                "required": True,
            },
        )

        view = OptionView.from_doc_element(element)

        assert view.name == "output"
        assert view.flags == ("-o", "--output")
        assert view.required is True


# =============================================================================
# Tests for CommandView
# =============================================================================


class TestCommandViewFromDocElement:
    """Tests for CommandView.from_doc_element()."""

    def test_extracts_from_typed_metadata(self) -> None:
        """Extracts command data from typed_metadata."""
        meta = MockCLICommandMetadata(
            is_group=True,
            is_hidden=False,
            option_count=3,
            argument_count=1,
        )
        element = MockDocElement(
            name="build",
            description="Build the site",
            element_type="command-group",
            typed_metadata=meta,
            href="/cli/build/",
            metadata={"usage": "bengal build [OPTIONS]"},
        )

        view = CommandView.from_doc_element(element)

        assert view.name == "build"
        assert view.description == "Build the site"
        assert view.is_group is True
        assert view.is_hidden is False
        assert view.href == "/cli/build/"
        assert view.usage == "bengal build [OPTIONS]"

    def test_counts_children(self) -> None:
        """Counts options, arguments, and subcommands from children."""
        element = MockDocElement(
            name="cli",
            children=[
                MockDocElement(name="verbose", element_type="option"),
                MockDocElement(name="quiet", element_type="option"),
                MockDocElement(name="source", element_type="argument"),
                MockDocElement(name="build", element_type="command"),
                MockDocElement(name="serve", element_type="command"),
            ],
            typed_metadata=MockCLICommandMetadata(is_group=True),
        )

        view = CommandView.from_doc_element(element)

        assert view.option_count == 2
        assert view.argument_count == 1
        assert view.subcommand_count == 2

    def test_extracts_from_metadata_dict(self) -> None:
        """Falls back to metadata dict when typed_metadata unavailable."""
        element = MockDocElement(
            name="serve",
            description="Start dev server",
            metadata={"is_hidden": True},
        )

        view = CommandView.from_doc_element(element)

        assert view.name == "serve"
        assert view.is_hidden is True


# =============================================================================
# Tests for members_filter
# =============================================================================


class TestMembersFilter:
    """Tests for members_filter()."""

    def test_returns_empty_for_none(self) -> None:
        """Returns empty list for None element."""
        result = members_filter(None)
        assert result == []

    def test_returns_empty_for_no_children(self) -> None:
        """Returns empty list for element without children."""
        element = MockDocElement(name="empty")
        result = members_filter(element)
        assert result == []

    def test_filters_to_member_types(self) -> None:
        """Returns only method, function, and property children."""
        element = MockDocElement(
            name="MyClass",
            children=[
                MockDocElement(name="method1", element_type="method"),
                MockDocElement(name="func1", element_type="function"),
                MockDocElement(name="prop1", element_type="property"),
                MockDocElement(name="attr1", element_type="attribute"),  # Excluded
                MockDocElement(name="nested", element_type="class"),  # Excluded
            ],
        )

        result = members_filter(element)

        assert len(result) == 3
        assert all(isinstance(m, MemberView) for m in result)
        names = [m.name for m in result]
        assert "method1" in names
        assert "func1" in names
        assert "prop1" in names
        assert "attr1" not in names

    def test_member_views_have_correct_properties(self) -> None:
        """Returned MemberViews have expected properties."""
        meta = MockPythonFunctionMetadata(
            signature="def greet(name: str) -> str",
            return_type="str",
            is_async=True,
        )
        element = MockDocElement(
            name="MyClass",
            children=[
                MockDocElement(
                    name="greet",
                    description="Say hello",
                    element_type="method",
                    typed_metadata=meta,
                    href="/api/MyClass/greet/",
                )
            ],
        )

        result = members_filter(element)

        assert len(result) == 1
        m = result[0]
        assert m.name == "greet"
        assert m.is_async is True
        assert m.return_type == "str"
        assert m.href == "/api/MyClass/greet/"


# =============================================================================
# Tests for commands_filter
# =============================================================================


class TestCommandsFilter:
    """Tests for commands_filter()."""

    def test_returns_empty_for_none(self) -> None:
        """Returns empty list for None element."""
        result = commands_filter(None)
        assert result == []

    def test_filters_to_command_types(self) -> None:
        """Returns only command and command-group children."""
        element = MockDocElement(
            name="cli",
            children=[
                MockDocElement(name="build", element_type="command"),
                MockDocElement(name="serve", element_type="command"),
                MockDocElement(name="assets", element_type="command-group"),
                MockDocElement(name="verbose", element_type="option"),  # Excluded
            ],
        )

        result = commands_filter(element)

        assert len(result) == 3
        assert all(isinstance(c, CommandView) for c in result)
        names = [c.name for c in result]
        assert "build" in names
        assert "serve" in names
        assert "assets" in names
        assert "verbose" not in names


# =============================================================================
# Tests for options_filter
# =============================================================================


class TestOptionsFilter:
    """Tests for options_filter()."""

    def test_returns_empty_for_none(self) -> None:
        """Returns empty list for None element."""
        result = options_filter(None)
        assert result == []

    def test_filters_to_option_types(self) -> None:
        """Returns only option and argument children."""
        element = MockDocElement(
            name="build",
            children=[
                MockDocElement(name="verbose", element_type="option"),
                MockDocElement(name="source", element_type="argument"),
                MockDocElement(name="subcommand", element_type="command"),  # Excluded
            ],
        )

        result = options_filter(element)

        assert len(result) == 2
        assert all(isinstance(o, OptionView) for o in result)

    def test_sorts_options_before_arguments(self) -> None:
        """Options come before arguments in result."""
        element = MockDocElement(
            name="build",
            children=[
                MockDocElement(
                    name="source",
                    element_type="argument",
                    typed_metadata=MockCLIOptionMetadata(param_type="argument"),
                ),
                MockDocElement(
                    name="verbose",
                    element_type="option",
                    typed_metadata=MockCLIOptionMetadata(param_type="option"),
                ),
                MockDocElement(
                    name="dest",
                    element_type="argument",
                    typed_metadata=MockCLIOptionMetadata(param_type="argument"),
                ),
            ],
        )

        result = options_filter(element)

        assert len(result) == 3
        # Options first (is_argument=False), then arguments sorted by name
        assert result[0].is_argument is False
        assert result[0].name == "verbose"
        assert result[1].is_argument is True
        assert result[2].is_argument is True


# =============================================================================
# Integration Tests
# =============================================================================


class TestFilterIntegration:
    """Integration tests for filter usage patterns."""

    def test_members_with_public_private_split(self) -> None:
        """Can split members into public and private."""
        element = MockDocElement(
            name="MyClass",
            children=[
                MockDocElement(name="public_method", element_type="method"),
                MockDocElement(name="_private_method", element_type="method"),
                MockDocElement(name="__dunder__", element_type="method"),
            ],
        )

        members = members_filter(element)
        public = [m for m in members if not m.is_private]
        private = [m for m in members if m.is_private]

        assert len(public) == 1
        assert public[0].name == "public_method"
        assert len(private) == 2

    def test_options_with_required_filtering(self) -> None:
        """Can filter options by required status."""
        element = MockDocElement(
            name="command",
            children=[
                MockDocElement(
                    name="required_opt",
                    element_type="option",
                    typed_metadata=MockCLIOptionMetadata(required=True),
                ),
                MockDocElement(
                    name="optional_opt",
                    element_type="option",
                    typed_metadata=MockCLIOptionMetadata(required=False),
                ),
            ],
        )

        options = options_filter(element)
        required = [o for o in options if o.required]
        optional = [o for o in options if not o.required]

        assert len(required) == 1
        assert len(optional) == 1

    def test_commands_with_group_detection(self) -> None:
        """Can identify command groups."""
        element = MockDocElement(
            name="cli",
            children=[
                MockDocElement(
                    name="build",
                    element_type="command",
                    typed_metadata=MockCLICommandMetadata(is_group=False),
                ),
                MockDocElement(
                    name="assets",
                    element_type="command-group",
                    typed_metadata=MockCLICommandMetadata(is_group=True),
                ),
            ],
        )

        commands = commands_filter(element)
        groups = [c for c in commands if c.is_group]
        simple = [c for c in commands if not c.is_group]

        assert len(groups) == 1
        assert groups[0].name == "assets"
        assert len(simple) == 1
        assert simple[0].name == "build"
