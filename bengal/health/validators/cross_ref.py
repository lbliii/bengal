"""
Cross-reference validator for validating semantic references in content.

Validates that code references, configuration mentions, and other semantic
links in documentation actually exist and are current.

Key Features:
    - Validate function/class references against source code
    - Validate configuration option references
    - Find broken anchor links to headings
    - Detect stale version references

Related Modules:
    - bengal.health.base: BaseValidator interface
    - bengal.health.report: CheckResult for reporting

See Also:
    - bengal/health/validators/links.py: URL link validation
    - bengal/debug/base.py: Debug tool infrastructure
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus

if TYPE_CHECKING:
    from bengal.core.site import Site


@dataclass
class CodeReference:
    """
    A reference to code in documentation content.

    Attributes:
        ref_type: Type of reference (function, class, config, variable)
        name: The referenced name
        module: Optional module path
        raw: Raw matched text
        line: Line number in content
        file_path: Path to the content file
    """

    ref_type: str  # function, class, config, variable, anchor
    name: str
    module: str | None = None
    raw: str = ""
    line: int = 0
    file_path: str = ""

    def __str__(self) -> str:
        if self.module:
            return f"{self.module}.{self.name}"
        return self.name


@dataclass
class CodeIndex:
    """
    Index of code symbols for validation.

    Attributes:
        functions: Set of function names
        classes: Set of class names
        constants: Set of constant names
        config_options: Set of configuration option names
        modules: Set of module paths
    """

    functions: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)
    constants: set[str] = field(default_factory=set)
    config_options: set[str] = field(default_factory=set)
    modules: set[str] = field(default_factory=set)

    @classmethod
    def from_directory(cls, source_dir: Path) -> CodeIndex:
        """
        Build code index from a source directory.

        Parses Python files to extract function, class, and constant names.

        Args:
            source_dir: Directory containing Python source code

        Returns:
            CodeIndex with discovered symbols
        """
        index = cls()

        if not source_dir.exists():
            return index

        for py_file in source_dir.rglob("*.py"):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        # Include all functions, mark private ones
                        index.functions.add(node.name)
                    elif isinstance(node, ast.ClassDef):
                        index.classes.add(node.name)
                    elif isinstance(node, ast.Assign):
                        # Check for module-level constants (UPPER_CASE)
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id.isupper():
                                index.constants.add(target.id)

                # Track module path
                rel_path = py_file.relative_to(source_dir)
                module_path = ".".join(rel_path.with_suffix("").parts)
                index.modules.add(module_path)

            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        return index

    def contains(self, ref: CodeReference) -> bool:
        """Check if a reference exists in the index."""
        if ref.ref_type == "function":
            return ref.name in self.functions
        elif ref.ref_type == "class":
            return ref.name in self.classes
        elif ref.ref_type == "config":
            return ref.name in self.config_options
        elif ref.ref_type == "constant":
            return ref.name in self.constants
        return False


class CrossReferenceValidator(BaseValidator):
    """
    Validates semantic cross-references in documentation.

    Checks that code references (functions, classes, config options) in
    documentation actually exist in the source code.

    Creation:
        health_check.register(CrossReferenceValidator(source_dirs=[Path("src")]))

    Attributes:
        source_dirs: Directories to search for source code
        code_index: Index of discovered code symbols
        config_options: Known configuration option names
        current_version: Current product version for version checks
        deprecated_versions: List of deprecated version strings
    """

    name = "cross_references"
    description = "Validates code and config references in documentation"

    def __init__(
        self,
        source_dirs: list[Path] | None = None,
        config_options: set[str] | None = None,
        current_version: str | None = None,
        deprecated_versions: list[str] | None = None,
    ):
        """
        Initialize cross-reference validator.

        Args:
            source_dirs: Directories containing source code to index
            config_options: Known configuration option names
            current_version: Current product version
            deprecated_versions: List of deprecated versions to flag
        """
        super().__init__()
        self.source_dirs = source_dirs or []
        self.config_options = config_options or set()
        self.current_version = current_version
        self.deprecated_versions = deprecated_versions or []
        self.code_index: CodeIndex | None = None

    def validate(self, site: Site, build_context: Any | None = None) -> list[CheckResult]:
        """
        Validate cross-references in all site pages.

        Args:
            site: Site to validate
            build_context: Optional BuildContext (not used by this validator)

        Returns:
            List of CheckResults for invalid references
        """
        results: list[CheckResult] = []

        # Build code index if we have source directories
        if self.source_dirs:
            self.code_index = CodeIndex()
            for source_dir in self.source_dirs:
                index = CodeIndex.from_directory(source_dir)
                self.code_index.functions.update(index.functions)
                self.code_index.classes.update(index.classes)
                self.code_index.constants.update(index.constants)
                self.code_index.modules.update(index.modules)

            # Add config options to index
            self.code_index.config_options.update(self.config_options)

        # Validate each page
        for page in site.pages:
            page_results = self._validate_page(page)
            results.extend(page_results)

        return results

    def _validate_page(self, page: Any) -> list[CheckResult]:
        """Validate references in a single page."""
        results: list[CheckResult] = []
        content = getattr(page, "content", "") or ""
        page_path = str(getattr(page, "source_path", "unknown"))

        # Extract references
        refs = self._extract_references(content, page_path)

        # Validate each reference
        for ref in refs:
            result = self._validate_reference(ref)
            if result:
                results.append(result)

        # Validate version references
        if self.deprecated_versions:
            version_results = self._validate_versions(content, page_path)
            results.extend(version_results)

        # Validate anchor links
        anchor_results = self._validate_anchors(page)
        results.extend(anchor_results)

        return results

    def _extract_references(self, content: str, file_path: str) -> list[CodeReference]:
        """
        Extract code references from content.

        Looks for:
        - `function_name()` - function calls in backticks
        - `ClassName` - CamelCase names in backticks (classes)
        - `config_option` - snake_case names in backticks (config)
        - `CONSTANT_NAME` - UPPER_CASE names in backticks (constants)

        Args:
            content: Page content to search
            file_path: Path to the content file

        Returns:
            List of CodeReference objects
        """
        refs: list[CodeReference] = []

        # Function calls: `function_name()`
        for match in re.finditer(r"`([a-z_][a-z0-9_]*)\(\)`", content):
            line = content[: match.start()].count("\n") + 1
            refs.append(
                CodeReference(
                    ref_type="function",
                    name=match.group(1),
                    raw=match.group(0),
                    line=line,
                    file_path=file_path,
                )
            )

        # Classes: `CamelCase` (but not all caps)
        for match in re.finditer(r"`([A-Z][a-zA-Z0-9]+[a-z][a-zA-Z0-9]*)`", content):
            name = match.group(1)
            # Skip if it looks like a constant (has consecutive caps)
            if not re.search(r"[A-Z]{2,}", name):
                line = content[: match.start()].count("\n") + 1
                refs.append(
                    CodeReference(
                        ref_type="class",
                        name=name,
                        raw=match.group(0),
                        line=line,
                        file_path=file_path,
                    )
                )

        # Config options: `snake_case` (not function calls)
        for match in re.finditer(r"`([a-z][a-z0-9_]*[a-z0-9])`(?!\()", content):
            name = match.group(1)
            # Skip common words that aren't config
            if name not in {"true", "false", "null", "none", "self", "cls"}:
                line = content[: match.start()].count("\n") + 1
                refs.append(
                    CodeReference(
                        ref_type="config",
                        name=name,
                        raw=match.group(0),
                        line=line,
                        file_path=file_path,
                    )
                )

        # Constants: `UPPER_CASE`
        for match in re.finditer(r"`([A-Z][A-Z0-9_]+)`", content):
            line = content[: match.start()].count("\n") + 1
            refs.append(
                CodeReference(
                    ref_type="constant",
                    name=match.group(1),
                    raw=match.group(0),
                    line=line,
                    file_path=file_path,
                )
            )

        return refs

    def _validate_reference(self, ref: CodeReference) -> CheckResult | None:
        """
        Validate a single code reference.

        Args:
            ref: Reference to validate

        Returns:
            CheckResult if invalid, None if valid
        """
        if not self.code_index:
            return None

        # Check if reference exists
        if not self.code_index.contains(ref):
            # Determine severity based on reference type
            if ref.ref_type == "function":
                severity = CheckStatus.ERROR
                message = f"Function '{ref.name}()' not found in source code"
                suggestion = "Verify function name or check if it was renamed/removed"
            elif ref.ref_type == "class":
                severity = CheckStatus.ERROR
                message = f"Class '{ref.name}' not found in source code"
                suggestion = "Verify class name or check if it was renamed/removed"
            elif ref.ref_type == "config":
                # Config references are warnings (might be external)
                severity = CheckStatus.WARNING
                message = f"Config option '{ref.name}' not found in known options"
                suggestion = "Verify option name or add to known config options"
            else:
                severity = CheckStatus.INFO
                message = f"Reference '{ref.name}' could not be validated"
                suggestion = None

            return CheckResult(
                status=severity,
                validator=self.name,
                message=message,
                recommendation=suggestion,
                metadata={
                    "reference": ref.raw,
                    "type": ref.ref_type,
                    "file_path": ref.file_path,
                    "line": ref.line,
                },
            )

        return None

    def _validate_versions(self, content: str, file_path: str) -> list[CheckResult]:
        """
        Validate version references in content.

        Args:
            content: Page content
            file_path: Path to content file

        Returns:
            List of CheckResults for deprecated versions
        """
        results: list[CheckResult] = []

        # Match version patterns: v1.0, 1.0.0, etc.
        version_pattern = re.compile(r"\bv?(\d+\.\d+(?:\.\d+)?)\b")

        for match in version_pattern.finditer(content):
            version = match.group(1)
            if version in self.deprecated_versions:
                line = content[: match.start()].count("\n") + 1
                results.append(
                    CheckResult(
                        status=CheckStatus.WARNING,
                        validator=self.name,
                        message=f"References deprecated version '{version}'",
                        file_path=file_path,
                        line=line,
                        suggestion=f"Update to current version '{self.current_version}'"
                        if self.current_version
                        else "Update to current version",
                        metadata={"found_version": version},
                    )
                )

        return results

    def _validate_anchors(self, page: Any) -> list[CheckResult]:
        """
        Validate anchor links to headings.

        Args:
            page: Page to validate

        Returns:
            List of CheckResults for broken anchors
        """
        results: list[CheckResult] = []
        content = getattr(page, "content", "") or ""
        page_path = str(getattr(page, "source_path", "unknown"))

        # Extract headings to build valid anchors
        heading_pattern = re.compile(r"^#+\s+(.+)$", re.MULTILINE)
        valid_anchors: set[str] = set()

        for match in heading_pattern.finditer(content):
            heading_text = match.group(1)
            # Generate anchor (simplified slug)
            anchor = re.sub(r"[^\w\s-]", "", heading_text.lower())
            anchor = re.sub(r"[\s_]+", "-", anchor).strip("-")
            valid_anchors.add(anchor)

        # Find internal anchor links
        anchor_link_pattern = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")

        for match in anchor_link_pattern.finditer(content):
            anchor = match.group(2)
            if anchor not in valid_anchors:
                line = content[: match.start()].count("\n") + 1
                results.append(
                    CheckResult(
                        status=CheckStatus.WARNING,
                        validator=self.name,
                        message=f"Anchor link '#{anchor}' points to non-existent heading",
                        recommendation="Check heading exists or fix anchor name",
                        metadata={
                            "anchor": anchor,
                            "valid_anchors": list(valid_anchors)[:5],
                            "file_path": page_path,
                            "line": line,
                        },
                    )
                )

        return results


def create_cross_ref_validator(
    site_root: Path,
    source_dir: str = "bengal",
    config_options: set[str] | None = None,
) -> CrossReferenceValidator:
    """
    Factory function to create a configured CrossReferenceValidator.

    Args:
        site_root: Root path of the site
        source_dir: Name of source code directory
        config_options: Optional set of known config option names

    Returns:
        Configured CrossReferenceValidator
    """
    source_path = site_root / source_dir
    source_dirs = [source_path] if source_path.exists() else []

    return CrossReferenceValidator(
        source_dirs=source_dirs,
        config_options=config_options or set(),
    )
