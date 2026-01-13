"""
Lint rule to ensure all BengalError raises include error codes.

This test scans the codebase for `raise Bengal*Error(...)` statements
and verifies they include the `code=` parameter.

Exemptions:
- `bengal/errors/` directory (contains examples in docstrings)
- Test files (may intentionally test error behavior)
- Analysis modules (already have 100% coverage)

Usage:
pytest tests/lint/test_error_codes.py -v

See Also:
- bengal/errors/codes.py: Error code definitions

"""

from __future__ import annotations

import re
from pathlib import Path

# Project root
BENGAL_ROOT = Path(__file__).parent.parent.parent / "bengal"

# Directories exempted from enforcement
EXEMPT_DIRS = {
    "errors",  # Examples in docstrings
    "tests",  # Test files may intentionally omit codes
    "analysis",  # Already has 100% coverage
}


def find_bengal_error_raises(file_path: Path) -> list[tuple[int, str]]:
    """
    Find all BengalError raises in a Python file.
    
    Returns list of (line_number, line_content) tuples for raises
    that don't include code= parameter.
        
    """
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = content.split("\n")

    # Pattern to match raise statements
    raise_pattern = re.compile(r"raise\s+Bengal\w+Error\s*\(")

    i = 0
    while i < len(lines):
        line = lines[i]

        if raise_pattern.search(line):
            # Collect the full raise statement (may span multiple lines)
            statement_lines = [line]
            paren_count = line.count("(") - line.count(")")

            j = i + 1
            while paren_count > 0 and j < len(lines):
                statement_lines.append(lines[j])
                paren_count += lines[j].count("(") - lines[j].count(")")
                j += 1

            full_statement = "\n".join(statement_lines)

            # Check if code= is present
            if "code=" not in full_statement and "code =" not in full_statement:
                violations.append((i + 1, line.strip()))

            i = j
        else:
            i += 1

    return violations


def test_all_bengal_errors_have_codes() -> None:
    """
    Ensure all BengalError raises include code= parameter.
    
    This test enforces that all BengalError exceptions should include error codes for:
    - User-friendly CLI output
    - Documentation links
    - Searchability and debugging
        
    """
    violations: list[str] = []

    for py_file in BENGAL_ROOT.rglob("*.py"):
        # Skip exempted directories
        if any(exempt in py_file.parts for exempt in EXEMPT_DIRS):
            continue

        # Find violations in this file
        file_violations = find_bengal_error_raises(py_file)

        for line_num, line_content in file_violations:
            rel_path = py_file.relative_to(BENGAL_ROOT.parent)
            violations.append(f"{rel_path}:{line_num}: {line_content[:60]}...")

    if violations:
        msg = f"Found {len(violations)} BengalError raise(s) missing code= parameter:\n\n"
        msg += "\n".join(f"  • {v}" for v in violations[:20])  # Show first 20
        if len(violations) > 20:
            msg += f"\n  ... and {len(violations) - 20} more"
        msg += "\n\nAdd error codes like: code=ErrorCode.C001"
        msg += "\nSee bengal/errors/codes.py for available codes."

        raise AssertionError(msg)


def test_error_code_coverage_report() -> None:
    """
    Generate a report of error code coverage across the codebase.
    
    This is an informational test that doesn't fail but prints statistics
    about error code usage.
        
    """
    from bengal.errors.codes import ErrorCode

    total_raises = 0
    raises_with_codes = 0
    code_usage: dict[str, int] = {code.name: 0 for code in ErrorCode}

    for py_file in BENGAL_ROOT.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Count raises
        raise_pattern = re.compile(r"raise\s+Bengal\w+Error\s*\(")
        raises = raise_pattern.findall(content)
        total_raises += len(raises)

        # Count raises with code=
        code_pattern = re.compile(r"raise\s+Bengal\w+Error\s*\([^)]*code\s*=")
        raises_with_codes += len(code_pattern.findall(content))

        # Count specific code usage
        for code in ErrorCode:
            if code.name in content:
                code_usage[code.name] += 1

    # Generate report
    if total_raises > 0:
        coverage = (raises_with_codes / total_raises) * 100
        print("\n📊 Error Code Coverage Report")
        print(f"   Total BengalError raises: {total_raises}")
        print(f"   Raises with code=: {raises_with_codes}")
        print(f"   Coverage: {coverage:.1f}%")

        # Most used codes
        used_codes = {k: v for k, v in code_usage.items() if v > 0}
        if used_codes:
            print("\n   Top used codes:")
            for code, count in sorted(used_codes.items(), key=lambda x: -x[1])[:5]:
                print(f"     {code}: {count} uses")

        # Unused codes
        unused = [k for k, v in code_usage.items() if v == 0]
        if unused:
            print(f"\n   Unused codes: {len(unused)}")


if __name__ == "__main__":
    # Run as script for quick check
    print("Checking BengalError raises for missing error codes...")
    try:
        test_all_bengal_errors_have_codes()
        print("✓ All BengalError raises include error codes!")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)
