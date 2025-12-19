"""
Python-specific metadata dataclasses for autodoc system.

Provides typed metadata for:
- Modules (PythonModuleMetadata)
- Classes (PythonClassMetadata)
- Functions/Methods (PythonFunctionMetadata)
- Attributes (PythonAttributeMetadata)
- Aliases (PythonAliasMetadata)
- Parsed docstrings (ParsedDocstring)
- Parameters (ParameterInfo)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ParameterInfo:
    """
    Single function parameter information.

    Attributes:
        name: Parameter name
        type_hint: Type annotation as string (e.g., "str | None")
        default: Default value as string (e.g., "None", "'default'")
        kind: Parameter kind (positional, keyword, var_positional, var_keyword)
        description: Description from docstring

    Example:
        >>> param = ParameterInfo(name="path", type_hint="Path", default="None")
        >>> param.name
        'path'
    """

    name: str
    type_hint: str | None = None
    default: str | None = None
    kind: Literal[
        "positional", "keyword", "var_positional", "var_keyword", "positional_or_keyword"
    ] = "positional_or_keyword"
    description: str | None = None


@dataclass(frozen=True, slots=True)
class RaisesInfo:
    """
    Exception information from docstring.

    Attributes:
        type_name: Exception type name
        description: Description of when raised
    """

    type_name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class ParsedDocstring:
    """
    Parsed docstring information.

    Attributes:
        summary: One-line summary
        description: Full description (may include summary)
        params: Parameter documentation
        returns: Return value description
        raises: Exception documentation
        examples: Code examples

    Example:
        >>> doc = ParsedDocstring(summary="Build the site.", returns="None")
        >>> doc.summary
        'Build the site.'
    """

    summary: str = ""
    description: str = ""
    params: tuple[ParameterInfo, ...] = ()
    returns: str | None = None
    raises: tuple[RaisesInfo, ...] = ()
    examples: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PythonModuleMetadata:
    """
    Metadata specific to Python modules.

    Attributes:
        file_path: Path to source file
        is_package: Whether this is a package (__init__.py)
        has_all: Whether module defines __all__
        all_exports: Contents of __all__ if present

    Example:
        >>> meta = PythonModuleMetadata(file_path="bengal/core/__init__.py", is_package=True)
        >>> meta.is_package
        True
    """

    file_path: str
    is_package: bool = False
    has_all: bool = False
    all_exports: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PythonClassMetadata:
    """
    Metadata specific to Python classes.

    Attributes:
        bases: Base class names
        decorators: Decorator names
        is_exception: Whether class inherits from Exception/BaseException
        is_dataclass: Whether class has @dataclass decorator
        is_abstract: Whether class inherits from ABC
        is_mixin: Whether class name ends with "Mixin"
        parsed_doc: Parsed docstring

    Example:
        >>> meta = PythonClassMetadata(bases=("Page", "Cacheable"), is_dataclass=True)
        >>> meta.is_dataclass
        True
    """

    bases: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()
    is_exception: bool = False
    is_dataclass: bool = False
    is_abstract: bool = False
    is_mixin: bool = False
    parsed_doc: ParsedDocstring | None = None


@dataclass(frozen=True, slots=True)
class PythonFunctionMetadata:
    """
    Metadata specific to Python functions/methods.

    Attributes:
        signature: Full signature string (e.g., "def build(self, force: bool = False) -> None")
        parameters: Parameter information
        return_type: Return type annotation as string
        is_async: Whether function is async
        is_classmethod: Whether function has @classmethod decorator
        is_staticmethod: Whether function has @staticmethod decorator
        is_property: Whether function has @property decorator
        is_generator: Whether function uses yield
        decorators: Decorator names
        parsed_doc: Parsed docstring

    Example:
        >>> meta = PythonFunctionMetadata(signature="def build()", is_async=False)
        >>> meta.signature
        'def build()'
    """

    signature: str = ""
    parameters: tuple[ParameterInfo, ...] = ()
    return_type: str | None = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    is_generator: bool = False
    decorators: tuple[str, ...] = ()
    parsed_doc: ParsedDocstring | None = None


@dataclass(frozen=True, slots=True)
class PythonAttributeMetadata:
    """
    Metadata specific to Python attributes/class variables.

    Attributes:
        annotation: Type annotation as string
        is_class_var: Whether this is a class variable
        default_value: Default value as string

    Example:
        >>> meta = PythonAttributeMetadata(annotation="str", is_class_var=True)
        >>> meta.annotation
        'str'
    """

    annotation: str | None = None
    is_class_var: bool = False
    default_value: str | None = None


@dataclass(frozen=True, slots=True)
class PythonAliasMetadata:
    """
    Metadata for import aliases.

    Attributes:
        alias_of: Qualified name of the aliased entity
        alias_kind: Type of alias (assignment or import)

    Example:
        >>> meta = PythonAliasMetadata(alias_of="bengal.core.site.Site", alias_kind="assignment")
        >>> meta.alias_of
        'bengal.core.site.Site'
    """

    alias_of: str
    alias_kind: Literal["assignment", "import"] = "assignment"
