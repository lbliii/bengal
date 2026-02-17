#!/usr/bin/env python3
"""Detect code smells in the bengal codebase.

This script analyzes Python source files for common code smell patterns:
- Long functions (>100 lines)
- God classes (>20 methods)
- Long parameter lists (>7 parameters)
- High import counts (>25 imports)
- Large files (>500 lines)

Usage:
    python scripts/detect_code_smells.py [--verbose] [--json] [path]

Examples:
    python scripts/detect_code_smells.py                    # Analyze bengal/
    python scripts/detect_code_smells.py --verbose          # Show all issues
    python scripts/detect_code_smells.py --json             # Output as JSON
    python scripts/detect_code_smells.py bengal/rendering/  # Analyze specific path

See RFC: rfc-code-smell-remediation.md for remediation strategies.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CodeSmellThresholds:
    """Configurable thresholds for code smell detection."""

    function_size: int = 100  # Lines per function
    class_methods: int = 20  # Methods per class
    parameters: int = 7  # Parameters per function
    imports: int = 25  # Imports per file
    file_size: int = 500  # Lines per file
    nesting_depth: int = 5  # Maximum nesting depth


@dataclass
class FunctionInfo:
    """Information about a function/method."""

    name: str
    line: int
    size: int
    params: int
    nesting_depth: int = 0


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    line: int
    size: int
    methods: int


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""

    path: Path
    line_count: int
    imports: int
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)


@dataclass
class CodeSmellIssue:
    """A detected code smell issue."""

    category: str  # LONG_FUNCTION, GOD_CLASS, MANY_PARAMS, etc.
    path: str
    line: int
    name: str
    value: int
    threshold: int

    def __str__(self) -> str:
        return f"{self.category}: {self.path}:{self.line} {self.name} ({self.value} > {self.threshold})"


class NestingDepthVisitor(ast.NodeVisitor):
    """Calculate maximum nesting depth of a function body."""

    def __init__(self) -> None:
        self.max_depth = 0
        self.current_depth = 0

    def _enter_block(self) -> None:
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)

    def _exit_block(self) -> None:
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_For(self, node: ast.For) -> None:
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_While(self, node: ast.While) -> None:
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_With(self, node: ast.With) -> None:
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_Try(self, node: ast.Try) -> None:
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_Match(self, node: ast.Match) -> None:
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()


def calculate_nesting_depth(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate the maximum nesting depth of a function."""
    visitor = NestingDepthVisitor()
    visitor.visit(node)
    return visitor.max_depth


def analyze_file(filepath: Path) -> FileAnalysis | None:
    """Analyze a single Python file for code smells.

    Args:
        filepath: Path to Python file

    Returns:
        FileAnalysis with function/class info, or None if parse fails
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return None

    lines = source.splitlines()
    line_count = len(lines)

    # Count imports
    import_count = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += len(node.names)

    result = FileAnalysis(
        path=filepath,
        line_count=line_count,
        imports=import_count,
    )

    # Analyze functions and classes
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            size = end - node.lineno + 1

            # Count non-self/cls parameters
            params = len([p for p in node.args.args if p.arg not in ("self", "cls")])

            # Calculate nesting depth
            nesting_depth = calculate_nesting_depth(node)

            result.functions.append(
                FunctionInfo(
                    name=node.name,
                    line=node.lineno,
                    size=size,
                    params=params,
                    nesting_depth=nesting_depth,
                )
            )
        elif isinstance(node, ast.ClassDef):
            methods = [
                n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            end = node.end_lineno or node.lineno

            result.classes.append(
                ClassInfo(
                    name=node.name,
                    line=node.lineno,
                    size=end - node.lineno + 1,
                    methods=len(methods),
                )
            )

    return result


def detect_smells(
    analysis: FileAnalysis,
    thresholds: CodeSmellThresholds,
) -> list[CodeSmellIssue]:
    """Detect code smells from file analysis.

    Args:
        analysis: Analysis result from analyze_file
        thresholds: Threshold configuration

    Returns:
        List of detected issues
    """
    issues: list[CodeSmellIssue] = []
    path_str = str(analysis.path)

    # Check file size
    if analysis.line_count > thresholds.file_size:
        issues.append(
            CodeSmellIssue(
                category="LARGE_FILE",
                path=path_str,
                line=1,
                name=analysis.path.name,
                value=analysis.line_count,
                threshold=thresholds.file_size,
            )
        )

    # Check import count
    if analysis.imports > thresholds.imports:
        issues.append(
            CodeSmellIssue(
                category="HIGH_IMPORTS",
                path=path_str,
                line=1,
                name=analysis.path.name,
                value=analysis.imports,
                threshold=thresholds.imports,
            )
        )

    # Check functions
    for func in analysis.functions:
        if func.size > thresholds.function_size:
            issues.append(
                CodeSmellIssue(
                    category="LONG_FUNCTION",
                    path=path_str,
                    line=func.line,
                    name=func.name,
                    value=func.size,
                    threshold=thresholds.function_size,
                )
            )

        if func.params > thresholds.parameters:
            issues.append(
                CodeSmellIssue(
                    category="MANY_PARAMS",
                    path=path_str,
                    line=func.line,
                    name=func.name,
                    value=func.params,
                    threshold=thresholds.parameters,
                )
            )

        if func.nesting_depth > thresholds.nesting_depth:
            issues.append(
                CodeSmellIssue(
                    category="DEEP_NESTING",
                    path=path_str,
                    line=func.line,
                    name=func.name,
                    value=func.nesting_depth,
                    threshold=thresholds.nesting_depth,
                )
            )

    # Check classes
    issues.extend(
        CodeSmellIssue(
            category="GOD_CLASS",
            path=path_str,
            line=cls.line,
            name=cls.name,
            value=cls.methods,
            threshold=thresholds.class_methods,
        )
        for cls in analysis.classes
        if cls.methods > thresholds.class_methods
    )

    return issues


def analyze_directory(
    root: Path,
    thresholds: CodeSmellThresholds,
) -> tuple[list[CodeSmellIssue], dict[str, int]]:
    """Analyze all Python files in a directory.

    Args:
        root: Directory to analyze
        thresholds: Threshold configuration

    Returns:
        Tuple of (issues list, category counts)
    """
    all_issues: list[CodeSmellIssue] = []
    category_counts: dict[str, int] = {
        "LONG_FUNCTION": 0,
        "GOD_CLASS": 0,
        "MANY_PARAMS": 0,
        "HIGH_IMPORTS": 0,
        "LARGE_FILE": 0,
        "DEEP_NESTING": 0,
    }

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip __pycache__ and hidden directories
        dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            filepath = Path(dirpath) / filename
            analysis = analyze_file(filepath)

            if analysis is None:
                continue

            issues = detect_smells(analysis, thresholds)
            all_issues.extend(issues)

            for issue in issues:
                category_counts[issue.category] += 1

    return all_issues, category_counts


def format_summary(
    issues: list[CodeSmellIssue],
    category_counts: dict[str, int],
) -> str:
    """Format a summary of detected issues.

    Args:
        issues: List of all issues
        category_counts: Count per category

    Returns:
        Formatted summary string
    """
    lines = [
        "=" * 60,
        "Code Smell Detection Report",
        "=" * 60,
        "",
        "Summary:",
    ]

    for category, count in sorted(category_counts.items()):
        if count > 0:
            lines.append(f"  {category}: {count}")

    lines.append(f"\nTotal Issues: {len(issues)}")
    lines.append("")

    if issues:
        lines.append("-" * 60)
        lines.append("Issues (sorted by category):")
        lines.append("-" * 60)

        lines.extend(
            str(issue) for issue in sorted(issues, key=lambda x: (x.category, x.path, x.line))
        )

    return "\n".join(lines)


def format_json(issues: list[CodeSmellIssue], category_counts: dict[str, int]) -> str:
    """Format issues as JSON.

    Args:
        issues: List of all issues
        category_counts: Count per category

    Returns:
        JSON string
    """
    data = {
        "summary": category_counts,
        "total_issues": len(issues),
        "issues": [
            {
                "category": issue.category,
                "path": issue.path,
                "line": issue.line,
                "name": issue.name,
                "value": issue.value,
                "threshold": issue.threshold,
            }
            for issue in issues
        ],
    }
    return json.dumps(data, indent=2)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 if issues found)
    """
    parser = argparse.ArgumentParser(
        description="Detect code smells in Python codebase",
        epilog="See RFC: rfc-code-smell-remediation.md for remediation strategies.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="bengal",
        help="Path to analyze (default: bengal)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--function-size",
        type=int,
        default=100,
        help="Max function size threshold (default: 100)",
    )
    parser.add_argument(
        "--class-methods",
        type=int,
        default=20,
        help="Max class methods threshold (default: 20)",
    )
    parser.add_argument(
        "--parameters",
        type=int,
        default=7,
        help="Max parameters threshold (default: 7)",
    )

    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"Error: Path does not exist: {root}", file=sys.stderr)
        return 1

    thresholds = CodeSmellThresholds(
        function_size=args.function_size,
        class_methods=args.class_methods,
        parameters=args.parameters,
    )

    issues, category_counts = analyze_directory(root, thresholds)

    if args.json:
        print(format_json(issues, category_counts))
    else:
        print(format_summary(issues, category_counts))

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
