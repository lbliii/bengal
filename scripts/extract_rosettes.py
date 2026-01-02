#!/usr/bin/env python3
"""Extract rosettes from Bengal to standalone package.

This script:
1. Copies all rosettes source files to the standalone repo
2. Transforms imports from bengal.rendering.rosettes → rosettes
3. Removes Bengal-specific error handling, uses standard LookupError
4. Copies and transforms tests
5. Copies non-Python fixtures as-is

Usage:
    python scripts/extract_rosettes.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

BENGAL_ROOT = Path("/Users/llane/Documents/github/python/bengal")
ROSETTES_ROOT = Path("/Users/llane/Documents/github/python/rosettes")

# Import transformations (order matters - more specific first)
IMPORT_TRANSFORMS: list[tuple[str, str]] = [
    # Full module paths
    (r"from bengal\.rendering\.rosettes\.", "from rosettes."),
    (r"import bengal\.rendering\.rosettes\.", "import rosettes."),
    # Partial references
    (r"bengal\.rendering\.rosettes\.", "rosettes."),
]


def transform_registry(content: str) -> str:
    """Transform _registry.py - remove Bengal error, fix module paths."""
    # Remove the Bengal error import (lazy import in _normalize_name)
    content = re.sub(
        r"\n    # Lazy import to avoid pulling in heavy Bengal error infrastructure at module load\n"
        r"    # This import is only triggered when an unsupported language is requested \(rare path\)\n"
        r"    from bengal\.errors import BengalRenderingError, ErrorCode\n",
        "",
        content,
    )

    # Replace BengalRenderingError with LookupError
    content = re.sub(
        r"raise BengalRenderingError\(\s*"
        r"f\"Unknown language: \{name!r\}\. Supported: \{_SORTED_LANGUAGES\}\",\s*"
        r"code=ErrorCode\.R011,\s*"
        r"suggestion=[^)]+\)",
        'raise LookupError(f"Unknown language: {name!r}. Supported: {_SORTED_LANGUAGES}")',
        content,
        flags=re.DOTALL,
    )

    # Update docstrings mentioning BengalRenderingError
    content = content.replace(
        "BengalRenderingError: If the language is not supported (R011).",
        "LookupError: If the language is not supported.",
    )

    # Fix module paths in LexerSpec entries
    content = content.replace(
        '"bengal.rendering.rosettes.lexers.',
        '"rosettes.lexers.',
    )

    # Remove performance note about Bengal imports
    content = re.sub(
        r"\nPerformance Note:\n    This module avoids importing bengal\.errors.*?unsupported languages\.\n",
        "",
        content,
        flags=re.DOTALL,
    )

    return content


def transform_themes_init(content: str) -> str:
    """Transform themes/__init__.py - remove Bengal error handling."""
    # Remove TYPE_CHECKING import of Bengal errors
    content = re.sub(
        r"\n    from bengal\.errors import BengalRenderingError, ErrorCode\n",
        "",
        content,
    )

    # Remove the lazy runtime import and replace error
    content = re.sub(
        r"        # Lazy import to avoid pulling in heavy Bengal error infrastructure at module load\n"
        r"        from bengal\.errors import BengalRenderingError, ErrorCode\n\n"
        r"        available = ",
        "        available = ",
        content,
    )

    # Replace BengalRenderingError with LookupError
    content = re.sub(
        r"raise BengalRenderingError\(\s*"
        r"f\"Unknown syntax theme: \{name!r\}\. Available: \{available\}\",\s*"
        r"code=ErrorCode\.R013,\s*"
        r"suggestion=[^)]+\)",
        'raise LookupError(f"Unknown syntax theme: {name!r}. Available: {available}")',
        content,
        flags=re.DOTALL,
    )

    # Update docstrings mentioning BengalRenderingError
    content = content.replace(
        "BengalRenderingError: If the palette is not registered (R013).",
        "LookupError: If the palette is not registered.",
    )

    # Remove performance note
    content = re.sub(
        r"\nPerformance Note:\n    This module avoids importing bengal\.errors.*?\(rare path\)\.\n",
        "",
        content,
        flags=re.DOTALL,
    )

    # Fix Quick Start example
    content = content.replace(
        "from bengal.rendering.rosettes.themes",
        "from rosettes.themes",
    )

    return content


def transform_main_init(content: str) -> str:
    """Transform __init__.py - update docstring examples."""
    # Already uses rosettes in examples, but fix any bengal references
    content = content.replace(
        "from bengal.rendering.rosettes",
        "from rosettes",
    )
    return content


def transform_file(content: str, rel_path: str) -> str:
    """Apply all transformations to file content."""
    # Apply standard import transforms
    for pattern, replacement in IMPORT_TRANSFORMS:
        content = re.sub(pattern, replacement, content)

    # Apply file-specific transforms
    rel_str = str(rel_path)

    if rel_str == "_registry.py":
        content = transform_registry(content)
    elif rel_str == "themes/__init__.py":
        content = transform_themes_init(content)
    elif rel_str == "__init__.py":
        content = transform_main_init(content)

    return content


def copy_source_files() -> int:
    """Copy and transform source files."""
    src_dir = ROSETTES_ROOT / "src" / "rosettes"
    src_dir.mkdir(parents=True, exist_ok=True)

    source_src = BENGAL_ROOT / "bengal" / "rendering" / "rosettes"
    count = 0

    for py_file in source_src.rglob("*.py"):
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue

        rel_path = py_file.relative_to(source_src)
        dest_path = src_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        content = py_file.read_text()
        content = transform_file(content, str(rel_path))
        dest_path.write_text(content)
        print(f"  ✓ src/rosettes/{rel_path}")
        count += 1

    # Copy py.typed marker
    py_typed_src = source_src / "py.typed"
    if py_typed_src.exists():
        shutil.copy(py_typed_src, src_dir / "py.typed")
        print("  ✓ src/rosettes/py.typed")

    return count


def copy_test_files() -> int:
    """Copy and transform test files."""
    test_dir = ROSETTES_ROOT / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)

    source_tests = BENGAL_ROOT / "tests" / "unit" / "rendering" / "rosettes"
    count = 0

    for py_file in source_tests.rglob("*.py"):
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue

        rel_path = py_file.relative_to(source_tests)
        dest_path = test_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        content = py_file.read_text()
        content = transform_file(content, str(rel_path))
        dest_path.write_text(content)
        print(f"  ✓ tests/{rel_path}")
        count += 1

    return count


def copy_fixtures() -> None:
    """Copy test fixtures (non-Python files, no transformation needed)."""
    fixtures_src = BENGAL_ROOT / "tests" / "unit" / "rendering" / "rosettes" / "fixtures"
    fixtures_dest = ROSETTES_ROOT / "tests" / "fixtures"

    if fixtures_src.exists():
        if fixtures_dest.exists():
            shutil.rmtree(fixtures_dest)
        shutil.copytree(fixtures_src, fixtures_dest)
        print("  ✓ tests/fixtures/ (copied as-is)")


def main() -> None:
    """Main extraction entry point."""
    print("=" * 60)
    print("Extracting Rosettes to standalone package")
    print("=" * 60)
    print(f"\nSource: {BENGAL_ROOT}")
    print(f"Target: {ROSETTES_ROOT}")
    print()

    # 1. Copy source files
    print("📦 Copying source files...")
    src_count = copy_source_files()
    print(f"   → {src_count} source files copied\n")

    # 2. Copy test files
    print("🧪 Copying test files...")
    test_count = copy_test_files()
    print(f"   → {test_count} test files copied\n")

    # 3. Copy fixtures
    print("📁 Copying fixtures...")
    copy_fixtures()
    print()

    # Summary
    print("=" * 60)
    print(f"✅ Extracted rosettes to {ROSETTES_ROOT}")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. cd /Users/llane/Documents/github/python/rosettes")
    print("  2. uv sync")
    print("  3. pytest")
    print("  4. pyright src/")


if __name__ == "__main__":
    main()
