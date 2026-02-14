#!/usr/bin/env python3
"""
Fix docstrings with 4-space indentation that render as code blocks.

This script finds and fixes docstrings where content is indented with 4 spaces,
which causes markdown renderers to treat them as code blocks. It removes the
indentation from text content while preserving code examples.
"""

import ast
import re
from pathlib import Path


def fix_docstring_content(docstring: str) -> str:
    """Fix indentation in docstring content."""
    if not docstring:
        return docstring

    lines = docstring.split("\n")
    fixed_lines = []
    in_code_block = False

    for line in lines:
        # Track code blocks (triple backticks)
        if "```" in line:
            in_code_block = not in_code_block
            fixed_lines.append(line)
            continue

        if in_code_block:
            fixed_lines.append(line)
            continue

        # Check if line starts with 4 spaces
        if line.startswith("    ") and line.strip():
            stripped = line[4:]  # Remove 4 spaces

            # Preserve indentation for code examples
            if stripped.strip().startswith(">>>") or stripped.strip().startswith("..."):
                fixed_lines.append(line)
                continue

            # Check if it's text content that should not be indented
            # Pattern: starts with capital letter, dash, or asterisk after 4 spaces
            if (
                re.match(r"^[A-Z]", stripped)
                or re.match(r"^-", stripped)
                or re.match(r"^\*", stripped)
            ):
                fixed_lines.append(stripped)
                continue

            # Check if it's a numbered list item
            if re.match(r"^\d+\.", stripped.strip()):
                fixed_lines.append(stripped)
                continue

            # For continuation lines in indented paragraphs, remove indentation
            # But preserve if it looks like code
            if re.match(r"^[a-z_][a-z0-9_()]*\s*[:=]", stripped) or stripped.strip().startswith(
                "'"
            ):
                # Looks like code, preserve indentation
                fixed_lines.append(line)
            else:
                # Text content, remove indentation
                fixed_lines.append(stripped)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def get_docstring_range(source_lines: list[str], node) -> tuple[int, int] | None:
    """Get the line range for a docstring node."""
    # Find the docstring node (first Expr with Constant string)
    if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            doc_node = node.body[0]
            start_line = doc_node.lineno - 1  # 0-indexed
        else:
            return None
    else:
        return None

    # Find the end of the docstring
    line = source_lines[start_line]

    # Determine quote type
    if '"""' in line:
        quote = '"""'
    elif "'''" in line:
        quote = "'''"
    else:
        return None

    # Count quotes in first line
    quote_count = line.count(quote)

    # If docstring is on single line (has both opening and closing quotes)
    if quote_count >= 2:
        return start_line, start_line

    # Multi-line docstring - find closing quote
    # Start counting from the line after start_line since we already counted start_line
    for i in range(start_line + 1, len(source_lines)):
        quote_count += source_lines[i].count(quote)
        if quote_count >= 2:
            return start_line, i

    return start_line, len(source_lines) - 1


def fix_file(file_path: Path) -> tuple[int, list[str]]:
    """Fix docstrings in a single file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        source_lines = content.split("\n")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return 0, ["Skipped (syntax error)"]

        changes_made = []
        docstrings_fixed = 0

        # Collect all docstrings that need fixing
        nodes_to_process = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node, clean=False)
                if docstring:
                    # Check if needs fixing
                    needs_fixing = False
                    for line in docstring.split("\n"):
                        if line.startswith("    ") and line.strip():
                            stripped = line[4:]
                            if (
                                not stripped.strip().startswith(">>>")
                                and not stripped.strip().startswith("...")
                                and (
                                    re.match(r"^[A-Z]", stripped)
                                    or re.match(r"^-", stripped)
                                    or re.match(r"^\*", stripped)
                                )
                            ):
                                needs_fixing = True
                                break

                    if needs_fixing:
                        doc_range = get_docstring_range(source_lines, node)
                        if doc_range:
                            start, end = doc_range
                            nodes_to_process.append((start, end, docstring))

        # Sort by line number (descending) to process from bottom up
        nodes_to_process.sort(key=lambda x: x[0], reverse=True)

        for start_line, end_line, original_docstring in nodes_to_process:
            # Fix the docstring content
            fixed_content = fix_docstring_content(original_docstring)

            if fixed_content != original_docstring:
                # Extract the actual docstring from source lines
                doc_lines = source_lines[start_line : end_line + 1]
                "\n".join(doc_lines)

                # Determine quote type and indentation
                first_line = doc_lines[0]
                match = re.match(r'^(\s*)(.*?)(["\']{3})(.*)', first_line)
                if not match:
                    continue

                indent = match.group(1)
                prefix = match.group(2)
                quote = match.group(3)
                match.group(4)

                # Check if single-line or multi-line
                if start_line == end_line:
                    # Single-line docstring
                    # Extract content between quotes
                    full_line = doc_lines[0]
                    # Find content between first and last quote
                    quote_pos = full_line.find(quote)
                    if quote_pos != -1:
                        after_first_quote = full_line[quote_pos + 3 :]
                        last_quote_pos = after_first_quote.rfind(quote)
                        if last_quote_pos != -1:
                            after_first_quote[:last_quote_pos]
                            # Replace with fixed content
                            new_line = f"{indent}{prefix}{quote}{fixed_content}{quote}"
                            source_lines[start_line] = new_line
                            docstrings_fixed += 1
                            changes_made.append(f"Fixed docstring at line {start_line + 1}")
                else:
                    # Multi-line docstring
                    fixed_lines = fixed_content.split("\n")

                    # Rebuild docstring
                    new_lines = [f"{indent}{prefix}{quote}{fixed_lines[0]}"]
                    new_lines.extend(f"{indent}{fline}" for fline in fixed_lines[1:])
                    new_lines.append(f"{indent}{quote}")

                    # Replace the range
                    source_lines[start_line : end_line + 1] = new_lines
                    docstrings_fixed += 1
                    changes_made.append(f"Fixed docstring at line {start_line + 1}")

        if docstrings_fixed > 0:
            # Write back
            new_content = "\n".join(source_lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return docstrings_fixed, changes_made

        return 0, []
    except Exception as e:
        return 0, [f"Error: {e}"]


def main():
    """Main entry point."""
    # Find all Python files
    python_files = list(Path("bengal").rglob("*.py")) + list(Path("tests").rglob("*.py"))

    total_fixed = 0
    files_fixed = 0

    for py_file in sorted(python_files):
        count, changes = fix_file(py_file)
        if count > 0:
            files_fixed += 1
            total_fixed += count
            print(f"{py_file}: Fixed {count} docstring(s)")
            for change in changes[:3]:  # Show first 3 changes
                print(f"  - {change}")
            if len(changes) > 3:
                print(f"  ... and {len(changes) - 3} more")

    print(f"\nSummary: Fixed {total_fixed} docstring(s) in {files_fixed} file(s)")


if __name__ == "__main__":
    main()
