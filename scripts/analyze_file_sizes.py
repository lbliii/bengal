#!/usr/bin/env python3
"""Analyze Python file sizes excluding docstrings."""

import ast
from pathlib import Path


def count_lines_excluding_docstrings(file_path: Path) -> tuple[int, int]:
    """
    Count lines excluding docstrings.
    Returns (total_lines, code_lines).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            total_lines = len(content.splitlines())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, 0

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        # If we can't parse it, just return total lines
        return total_lines, total_lines

    # Find all docstrings
    docstring_lines = set()

    def visit_node(node):
        """Recursively visit AST nodes to find docstrings."""
        # Check for docstrings in module, class, and function definitions
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)
        ) and ast.get_docstring(node):
            docstring = ast.get_docstring(node)
            # Find the line numbers of the docstring
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Expr)
                    and isinstance(child.value, ast.Str)
                    and hasattr(child, "lineno")
                ):
                    # This is a string literal - could be a docstring
                    # Count lines in the docstring
                    docstring_text = child.value.s
                    if docstring_text == docstring:
                        start_line = child.lineno
                        # Estimate end line (docstrings can span multiple lines)
                        end_line = start_line + docstring_text.count("\n")
                        for line_num in range(start_line, end_line + 1):
                            docstring_lines.add(line_num)

        # Also check for string literals that are docstrings (triple-quoted)
        for child in ast.walk(node):
            if isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant):
                if isinstance(child.value.value, str):
                    value = child.value.value
                    if (value.startswith('"""') or value.startswith("'''")) and hasattr(
                        child, "lineno"
                    ):
                        start_line = child.lineno
                        end_line = start_line + value.count("\n")
                        for line_num in range(start_line, end_line + 1):
                            docstring_lines.add(line_num)
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Str):
                # Python < 3.8 uses ast.Str
                value = child.value.s
                if (
                    isinstance(value, str)
                    and (value.startswith('"""') or value.startswith("'''"))
                    and hasattr(child, "lineno")
                ):
                    start_line = child.lineno
                    end_line = start_line + value.count("\n")
                    for line_num in range(start_line, end_line + 1):
                        docstring_lines.add(line_num)

    visit_node(tree)

    # Also manually check for triple-quoted strings in the source
    lines = content.splitlines()
    in_docstring = False
    docstring_delimiter = None

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check for triple-quoted strings
        if '"""' in stripped or "'''" in stripped:
            # Count occurrences
            triple_double = stripped.count('"""')
            triple_single = stripped.count("'''")

            if triple_double % 2 == 1:
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = '"""'
                elif docstring_delimiter == '"""':
                    in_docstring = False
                    docstring_delimiter = None

            if triple_single % 2 == 1:
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = "'''"
                elif docstring_delimiter == "'''":
                    in_docstring = False
                    docstring_delimiter = None

        if in_docstring:
            docstring_lines.add(i)

    code_lines = total_lines - len(docstring_lines)
    return total_lines, code_lines


def analyze_directory(root_dir: Path, min_lines: int = 500) -> list[tuple[Path, int, int]]:
    """Analyze all Python files in directory."""
    results = []

    for py_file in root_dir.rglob("*.py"):
        # Skip test files, __pycache__, and virtual environments
        if (
            "__pycache__" in str(py_file)
            or ".venv" in str(py_file)
            or "venv" in str(py_file)
            or "test_" in py_file.name
            or py_file.name.startswith("test_")
        ):
            continue

        total_lines, code_lines = count_lines_excluding_docstrings(py_file)

        if code_lines >= min_lines:
            results.append((py_file, total_lines, code_lines))

    # Sort by code lines descending
    results.sort(key=lambda x: x[2], reverse=True)
    return results


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    results = analyze_directory(root, min_lines=400)

    print(f"\n{'=' * 80}")
    print("Python files with 400+ lines of code (excluding docstrings)")
    print(f"{'=' * 80}\n")

    if not results:
        print("No files found exceeding the threshold.")
    else:
        print(f"{'File':<60} {'Total Lines':<15} {'Code Lines':<15}")
        print("-" * 90)

        for file_path, total_lines, code_lines in results:
            rel_path = file_path.relative_to(root)
            print(f"{str(rel_path):<60} {total_lines:<15} {code_lines:<15}")
