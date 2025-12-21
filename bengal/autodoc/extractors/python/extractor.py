"""
Python API documentation extractor.

Extracts documentation from Python source files via AST parsing.
No imports required - fast and reliable.

This is the main extractor class that coordinates the extraction process
using utilities from sibling modules.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, override

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.docstring_parser import parse_docstring
from bengal.autodoc.extractors.python.aliases import detect_aliases, extract_all_exports
from bengal.autodoc.extractors.python.inheritance import (
    should_include_inherited,
    synthesize_inherited_members,
)
from bengal.autodoc.extractors.python.module_info import (
    get_output_path,
    get_relative_source_path,
    infer_module_name,
)
from bengal.autodoc.extractors.python.signature import (
    annotation_to_string,
    build_signature,
    expr_to_string,
    extract_arguments,
    has_yield,
)
from bengal.autodoc.extractors.python.skip_logic import (
    should_skip,
    should_skip_shadowed_module,
)
from bengal.autodoc.models import (
    PythonAliasMetadata,
    PythonAttributeMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
    PythonModuleMetadata,
)
from bengal.autodoc.models.python import ParameterInfo, ParsedDocstring, RaisesInfo
from bengal.autodoc.utils import (
    auto_detect_prefix_map,
    get_python_function_is_property,
    sanitize_text,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class PythonExtractor(Extractor):
    """
    Extract Python API documentation via AST parsing.

    Features:
    - No imports (AST-only) - fast and reliable
    - Extracts modules, classes, functions, methods
    - Type hint support
    - Docstring extraction
    - Signature building
    - Alias detection
    - Inherited member synthesis

    Performance:
    - ~0.1-0.5s per file
    - No dependencies loaded
    - No side effects
    """

    def __init__(
        self, exclude_patterns: list[str] | None = None, config: dict[str, Any] | None = None
    ):
        """
        Initialize extractor.

        Args:
            exclude_patterns: Glob patterns to exclude (e.g., "*/tests/*")
            config: Configuration dict with include_inherited, exclude_patterns, etc.
        """
        self.config = config or {}

        # Read exclude_patterns from parameter, config, or use defaults
        if exclude_patterns is not None:
            self.exclude_patterns = exclude_patterns
        elif "exclude_patterns" in self.config:
            self.exclude_patterns = self.config["exclude_patterns"]
        else:
            self.exclude_patterns = [
                "*/tests/*",
                "*/test_*.py",
                "*/__pycache__/*",
            ]

        self.class_index: dict[str, DocElement] = {}
        self._source_root: Path | None = None  # Track source root for module name resolution

        # Initialize grouping configuration
        self._grouping_config = self._init_grouping()

    def _init_grouping(self) -> dict[str, Any]:
        """
        Initialize grouping configuration.

        Returns:
            Grouping config dict with mode and prefix_map
        """
        grouping = self.config.get("grouping", {})
        mode = grouping.get("mode", "off")

        # Mode "off" - return early
        if mode == "off":
            return {"mode": "off", "prefix_map": {}}

        # Mode "auto" - detect from source directories
        if mode == "auto":
            source_dirs = [Path(d) for d in self.config.get("source_dirs", ["."])]
            strip_prefix = self.config.get("strip_prefix", "")
            prefix_map = auto_detect_prefix_map(source_dirs, strip_prefix)
            return {"mode": "auto", "prefix_map": prefix_map}

        # Mode "explicit" - use provided prefix_map
        if mode == "explicit":
            prefix_map = grouping.get("prefix_map", {})
            return {"mode": "explicit", "prefix_map": prefix_map}

        # Unknown mode - log warning and use off
        print(f"⚠️  Warning: Unknown grouping mode: {mode}, using 'off'")
        return {"mode": "off", "prefix_map": {}}

    @override
    def extract(self, source: Path) -> list[DocElement]:
        """
        Extract documentation from Python source.

        Args:
            source: Directory or file path

        Returns:
            List of DocElement objects
        """
        # Store source root for module name resolution (must be absolute)
        # Always use the source parameter since it's already resolved by the caller
        if source.is_file():
            self._source_root = source.parent.resolve()
        else:
            self._source_root = source.resolve()

        if source.is_file():
            return self._extract_file(source)
        elif source.is_dir():
            return self._extract_directory(source)
        else:
            from bengal.errors import BengalDiscoveryError

            raise BengalDiscoveryError(
                f"Source must be a file or directory: {source}",
                file_path=source if isinstance(source, Path) else None,
                suggestion="Provide a valid file or directory path for autodoc extraction",
            )

    def _extract_directory(self, directory: Path) -> list[DocElement]:
        """Extract from all Python files in directory."""
        elements = []

        # First pass: extract all elements
        for py_file in directory.rglob("*.py"):
            if should_skip(py_file, self.exclude_patterns):
                continue

            # Skip module files shadowed by package directories
            # e.g., skip template_functions.py when template_functions/ exists
            if should_skip_shadowed_module(py_file):
                continue

            try:
                file_elements = self._extract_file(py_file)
                elements.extend(file_elements)
            except SyntaxError as e:
                logger.warning(
                    f"Syntax error in {py_file.relative_to(directory) if py_file.is_relative_to(directory) else py_file}\n"
                    f"  Line {e.lineno}: {e.msg}\n"
                    f"  Tip: Fix the syntax error or add to exclude patterns"
                )
            except Exception as e:
                import traceback

                # Get the actual location where error occurred
                tb = traceback.extract_tb(e.__traceback__)
                if tb:
                    last_frame = tb[-1]
                    error_location = (
                        f"{last_frame.filename}:{last_frame.lineno} in {last_frame.name}"
                    )
                else:
                    error_location = "unknown location"

                logger.warning(
                    f"Failed to extract {py_file.relative_to(directory) if py_file.is_relative_to(directory) else py_file}\n"
                    f"  Error: {type(e).__name__}: {e}\n"
                    f"  Location: {error_location}\n"
                    f"  Tip: This may be a bug in the extractor - report if persistent"
                )

        # Second pass: build class index
        for element in elements:
            if element.element_type == "module":
                for child in element.children:
                    if child.element_type == "class":
                        self.class_index[child.qualified_name] = child

        # Third pass: synthesize inherited members if enabled
        if should_include_inherited(self.config):
            for element in elements:
                if element.element_type == "module":
                    for child in element.children:
                        if child.element_type == "class":
                            synthesize_inherited_members(child, self.class_index, self.config)

        return elements

    def _extract_file(self, file_path: Path) -> list[DocElement]:
        """Extract documentation from a single Python file."""
        source = file_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            raise

        # Extract module-level documentation
        module_element = self._extract_module(tree, file_path, source)

        if not module_element:
            return []

        # Build class index from this module
        for child in module_element.children:
            if child.element_type == "class":
                self.class_index[child.qualified_name] = child

        # Synthesize inherited members if enabled
        if should_include_inherited(self.config):
            for child in module_element.children:
                if child.element_type == "class":
                    synthesize_inherited_members(child, self.class_index, self.config)

        return [module_element]

    def _extract_module(self, tree: ast.Module, file_path: Path, source: str) -> DocElement | None:
        """Extract module documentation."""
        module_name = infer_module_name(file_path, self._source_root)
        docstring = ast.get_docstring(tree)

        # Extract top-level classes and functions
        children = []
        defined_names = set()

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_elem = self._extract_class(node, file_path, module_name)
                if class_elem:
                    children.append(class_elem)
                    defined_names.add(node.name)

            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func_elem = self._extract_function(node, file_path)
                if func_elem:
                    # Update qualified_name to include module for consistency
                    func_elem.qualified_name = f"{module_name}.{func_elem.name}"
                    children.append(func_elem)
                    defined_names.add(node.name)

        # Detect aliases after extracting all definitions
        aliases = detect_aliases(tree, module_name, defined_names, expr_to_string)

        # Create DocElements for aliases
        for alias_name, canonical_name in aliases.items():
            # Find the line number of the alias assignment
            line_number = 1
            for node in tree.body:
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == alias_name
                ):
                    line_number = node.lineno
                    break

            # Build typed metadata for alias
            typed_meta = PythonAliasMetadata(
                alias_of=canonical_name,
                alias_kind="assignment",
            )

            alias_elem = DocElement(
                name=alias_name,
                qualified_name=f"{module_name}.{alias_name}",
                description=f"Alias of `{canonical_name}`",
                element_type="alias",
                source_file=get_relative_source_path(file_path, self._source_root),
                line_number=line_number,
                metadata={
                    "alias_of": canonical_name,
                    "alias_kind": "assignment",
                },
                typed_metadata=typed_meta,
            )
            children.append(alias_elem)

            # Track this alias in the canonical element's metadata
            canonical_simple = canonical_name.split(".")[-1]
            for child in children:
                if child.name == canonical_simple and child.element_type != "alias":
                    if "aliases" not in child.metadata:
                        child.metadata["aliases"] = []
                    child.metadata["aliases"].append(alias_name)

        # Only create module element if it has docstring or children
        if not docstring and not children:
            return None

        # Use just the last component for display name (e.g., "cli" instead of "autodoc.extractors.cli")
        display_name = module_name.split(".")[-1] if "." in module_name else module_name

        # Check if this is a package (__init__.py)
        is_package = file_path.name == "__init__.py"

        # Extract __all__ exports
        all_exports = extract_all_exports(tree)

        # Build typed metadata
        typed_meta = PythonModuleMetadata(
            file_path=str(file_path),
            is_package=is_package,
            has_all=all_exports is not None,
            all_exports=tuple(all_exports) if all_exports else (),
        )

        return DocElement(
            name=display_name,
            qualified_name=module_name,
            description=sanitize_text(docstring),
            element_type="module",
            source_file=get_relative_source_path(file_path, self._source_root),
            line_number=1,
            metadata={
                "file_path": str(file_path),
                "has_all": all_exports,
            },
            typed_metadata=typed_meta,
            children=children,
        )

    def _extract_class(
        self, node: ast.ClassDef, file_path: Path, parent_name: str = ""
    ) -> DocElement | None:
        """Extract class documentation."""
        qualified_name = f"{parent_name}.{node.name}" if parent_name else node.name
        docstring = ast.get_docstring(node)

        # Parse docstring
        parsed_doc = parse_docstring(docstring) if docstring else None

        # Extract base classes
        bases = []
        for base in node.bases:
            bases.append(expr_to_string(base))

        # Extract decorators
        decorators = [expr_to_string(d) for d in node.decorator_list]

        # Extract methods and properties
        methods = []
        properties = []
        class_vars = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                method = self._extract_function(item, file_path, qualified_name)
                if method:
                    # Check if it's a property using typed accessor
                    if get_python_function_is_property(method):
                        properties.append(method)
                    else:
                        methods.append(method)

            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Class variable with type annotation
                annotation_str = annotation_to_string(item.annotation)
                typed_attr_meta = PythonAttributeMetadata(
                    annotation=annotation_str,
                    is_class_var=True,
                    default_value=expr_to_string(item.value) if item.value else None,
                )
                var_elem = DocElement(
                    name=item.target.id,
                    qualified_name=f"{qualified_name}.{item.target.id}",
                    description="",
                    element_type="attribute",
                    source_file=get_relative_source_path(file_path, self._source_root),
                    line_number=item.lineno,
                    metadata={
                        "annotation": annotation_str,
                    },
                    typed_metadata=typed_attr_meta,
                )
                class_vars.append(var_elem)

        # Merge docstring attributes with code-discovered attributes
        if parsed_doc and parsed_doc.attributes:
            # Create a dict of code attributes by name for easy lookup
            code_attrs_by_name = {attr.name: attr for attr in class_vars}

            # For each docstring attribute, either enrich existing or create new
            for attr_name, attr_desc in parsed_doc.attributes.items():
                if attr_name in code_attrs_by_name:
                    # Enrich existing code attribute with docstring description
                    code_attrs_by_name[attr_name].description = attr_desc
                else:
                    # Create attribute element from docstring only
                    typed_attr_meta = PythonAttributeMetadata(
                        annotation=None,
                        is_class_var=False,  # Unknown from docstring only
                    )
                    var_elem = DocElement(
                        name=attr_name,
                        qualified_name=f"{qualified_name}.{attr_name}",
                        description=attr_desc,
                        element_type="attribute",
                        source_file=get_relative_source_path(file_path, self._source_root),
                        line_number=node.lineno,
                        metadata={
                            "annotation": None,
                        },
                        typed_metadata=typed_attr_meta,
                    )
                    class_vars.append(var_elem)

        # Combine children
        children = properties + methods + class_vars

        # Use parsed description if available
        raw_description = parsed_doc.description if parsed_doc else docstring
        description = sanitize_text(raw_description)

        # Detect exception, dataclass, abstract, mixin
        is_exception = any(b in ("Exception", "BaseException") for b in bases) or any(
            "Exception" in b for b in bases
        )
        is_dataclass = "dataclass" in decorators or any("dataclass" in d for d in decorators)
        is_abstract = any("ABC" in base for base in bases)
        is_mixin = node.name.endswith("Mixin")

        # Build typed metadata
        typed_meta = PythonClassMetadata(
            bases=tuple(bases),
            decorators=tuple(decorators),
            is_exception=is_exception,
            is_dataclass=is_dataclass,
            is_abstract=is_abstract,
            is_mixin=is_mixin,
            parsed_doc=self._to_parsed_docstring(parsed_doc) if parsed_doc else None,
        )

        return DocElement(
            name=node.name,
            qualified_name=qualified_name,
            description=description,
            element_type="class",
            source_file=get_relative_source_path(file_path, self._source_root),
            line_number=node.lineno,
            metadata={
                "bases": bases,
                "decorators": decorators,
                "is_dataclass": is_dataclass,
                "is_abstract": is_abstract,
                "is_mixin": is_mixin,
                "parsed_doc": parsed_doc.to_dict() if parsed_doc else {},
            },
            typed_metadata=typed_meta,
            children=children,
            examples=parsed_doc.examples if parsed_doc else [],
            see_also=parsed_doc.see_also if parsed_doc else [],
            deprecated=parsed_doc.deprecated if parsed_doc else None,
        )

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path, parent_name: str = ""
    ) -> DocElement | None:
        """Extract function/method documentation."""
        qualified_name = f"{parent_name}.{node.name}" if parent_name else node.name
        docstring = ast.get_docstring(node)

        # Skip private functions unless they have docstrings
        if node.name.startswith("_") and not node.name.startswith("__") and not docstring:
            return None

        # Parse docstring
        parsed_doc = parse_docstring(docstring) if docstring else None

        # Build signature
        signature = build_signature(node)

        # Extract decorators
        decorators = [expr_to_string(d) for d in node.decorator_list]

        # Extract arguments
        args = extract_arguments(node)

        # Extract return annotation
        returns = annotation_to_string(node.returns) if node.returns else None

        # Determine function type
        is_property = any("property" in d for d in decorators)
        is_classmethod = any("classmethod" in d for d in decorators)
        is_staticmethod = any("staticmethod" in d for d in decorators)
        is_async = isinstance(node, ast.AsyncFunctionDef)

        element_type = "method" if parent_name else "function"

        # Filter out self/cls for methods (but not for staticmethods)
        # Remove first argument (self for regular methods, cls for classmethods)
        if (
            element_type == "method"
            and not is_staticmethod
            and args
            and args[0]["name"] in ("self", "cls")
        ):
            args = args[1:]

        # Merge parsed docstring args with signature args
        merged_args = args  # Start with signature args
        if parsed_doc and parsed_doc.args:
            # Add descriptions from parsed docstring
            for arg in merged_args:
                if arg["name"] in parsed_doc.args:
                    arg["docstring"] = parsed_doc.args[arg["name"]]

        # Use parsed description if available
        raw_description = parsed_doc.description if parsed_doc else docstring
        description = sanitize_text(raw_description)

        # Detect generator (simple heuristic - check for yield in body)
        is_generator = has_yield(node)

        # Build typed metadata with ParameterInfo objects
        typed_params = tuple(self._to_parameter_info(arg) for arg in merged_args)
        typed_meta = PythonFunctionMetadata(
            signature=signature,
            parameters=typed_params,
            return_type=returns,
            is_async=is_async,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_property=is_property,
            is_generator=is_generator,
            decorators=tuple(decorators),
            parsed_doc=self._to_parsed_docstring(parsed_doc) if parsed_doc else None,
        )

        return DocElement(
            name=node.name,
            qualified_name=qualified_name,
            description=description,
            element_type=element_type,
            source_file=get_relative_source_path(file_path, self._source_root),
            line_number=node.lineno,
            metadata={
                "signature": signature,
                "args": merged_args,
                "returns": returns,
                "decorators": decorators,
                "is_async": is_async,
                "is_property": is_property,
                "is_classmethod": is_classmethod,
                "is_staticmethod": is_staticmethod,
                "parsed_doc": parsed_doc.to_dict() if parsed_doc else {},
            },
            typed_metadata=typed_meta,
            examples=parsed_doc.examples if parsed_doc else [],
            see_also=parsed_doc.see_also if parsed_doc else [],
            deprecated=parsed_doc.deprecated if parsed_doc else None,
        )

    def _to_parsed_docstring(self, parsed: Any) -> ParsedDocstring | None:
        """
        Convert ParsedDoc to frozen ParsedDocstring.

        Args:
            parsed: ParsedDoc from docstring_parser

        Returns:
            ParsedDocstring dataclass or None
        """
        if not parsed:
            return None

        # Build parameter info from parsed docstring
        params: list[ParameterInfo] = []
        if hasattr(parsed, "args") and parsed.args:
            for name, desc in parsed.args.items():
                params.append(
                    ParameterInfo(
                        name=name,
                        description=desc,
                    )
                )

        # Build raises info (parsed.raises is a list of dicts, not a dict)
        raises: list[RaisesInfo] = []
        if hasattr(parsed, "raises") and parsed.raises:
            for raise_item in parsed.raises:
                if isinstance(raise_item, dict):
                    raises.append(
                        RaisesInfo(
                            type_name=raise_item.get("type", ""),
                            description=raise_item.get("description", ""),
                        )
                    )

        return ParsedDocstring(
            summary=getattr(parsed, "summary", "") or "",
            description=getattr(parsed, "description", "") or "",
            params=tuple(params),
            returns=getattr(parsed, "returns", None),
            raises=tuple(raises),
            examples=tuple(getattr(parsed, "examples", []) or []),
        )

    def _to_parameter_info(self, arg: dict[str, Any]) -> ParameterInfo:
        """
        Convert arg dict to ParameterInfo.

        Args:
            arg: Dict with name, annotation, default, docstring

        Returns:
            ParameterInfo dataclass
        """
        return ParameterInfo(
            name=arg.get("name", ""),
            type_hint=arg.get("annotation"),
            default=arg.get("default"),
            description=arg.get("docstring"),
        )

    def _should_skip(self, path: Path) -> bool:
        """
        Check if file should be skipped during extraction.

        This is a thin wrapper around skip_logic.should_skip for backward compatibility.

        Args:
            path: Path to check

        Returns:
            True if path should be skipped
        """
        return should_skip(path, self.exclude_patterns)

    def _infer_module_name(self, file_path: Path) -> str:
        """
        Infer module name from file path relative to source root.

        This is a thin wrapper around module_info.infer_module_name for backward compatibility.

        Args:
            file_path: Path to the Python file

        Returns:
            Qualified module name (e.g., "bengal.cli.commands.build")
        """
        return infer_module_name(file_path, self._source_root)

    @override
    def get_output_path(self, element: DocElement) -> Path | None:
        """
        Get output path for element.

        Packages (modules from __init__.py) generate _index.md files to act as
        section indexes. With grouping enabled, modules are organized under
        group directories based on package hierarchy or explicit configuration.

        Returns:
            Path object for output location, or None if element should be skipped
        """
        return get_output_path(element, self.config, self._grouping_config)
