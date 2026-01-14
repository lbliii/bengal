#!/usr/bin/env python3
"""
Dependency layer enforcement for Bengal codebase.

Ensures that module dependencies flow in the correct direction according
to Bengal's layered architecture. Reports violations where lower layers
import from higher layers.

Architecture Layers (bottom to top):
    1. primitives (utils/primitives/) - Pure functions, no Bengal imports
    2. protocols (protocols/) - Interface definitions
    3. errors (errors/) - Error types
    4. core (core/) - Domain models (Page, Site, Section)
    5. infrastructure (cache/, assets/, discovery/) - Foundation services
    6. rendering (rendering/) - Template and content rendering
    7. orchestration (orchestration/) - Build coordination
    8. cli (cli/) - Command-line interface
    9. server (server/) - Development server

Rules:
    - Lower layers MUST NOT import from higher layers
    - Same-layer imports are allowed
    - protocols may be imported by any layer

Usage:
    python scripts/check_dependencies.py [--format=simple|detailed]

Exit Codes:
    0: No violations
    1: Dependency violations detected

"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator


# Define layer hierarchy (lower number = lower layer)
LAYER_ORDER = {
    "bengal.utils.primitives": 1,
    "bengal.protocols": 2,
    "bengal.errors": 3,
    "bengal.core": 4,
    "bengal.cache": 5,
    "bengal.assets": 5,
    "bengal.discovery": 5,
    "bengal.themes": 5,
    "bengal.utils": 5,  # Other utils (io, paths, concurrency, observability)
    "bengal.rendering": 6,
    "bengal.postprocess": 6,
    "bengal.analysis": 6,
    "bengal.orchestration": 7,
    "bengal.health": 7,
    "bengal.cli": 8,
    "bengal.server": 9,
}

# Acceptable cross-layer imports (documented exceptions)
# Format: (importer_prefix, imported_prefix) - if import matches, it's allowed
ALLOWED_VIOLATIONS: set[tuple[str, str]] = {
    # Logging is a cross-cutting concern - error modules need logging
    ("bengal.errors", "bengal.utils.observability.logger"),
    ("bengal.errors", "bengal.utils.observability.rich_console"),
    # Error aggregation needs error types from all modules (by design)
    ("bengal.errors.aggregation", "bengal.rendering.errors"),
    # CLI naturally imports server for coordination
    ("bengal.cli", "bengal.server"),
    # Core page needs utils for caching (cross-cutting concern)
    ("bengal.core", "bengal.utils.cache_registry"),
    ("bengal.core", "bengal.utils.lru_cache"),
    ("bengal.core", "bengal.utils.concurrency"),
    ("bengal.core", "bengal.utils.observability.logger"),
}


def get_layer(module: str) -> tuple[int, str]:
    """
    Get the layer number and name for a module.

    Returns:
        (layer_number, layer_name) or (0, "unknown") if not in hierarchy
    """
    # Sort by length (longest first) to match most specific prefix
    for prefix, layer in sorted(LAYER_ORDER.items(), key=lambda x: -len(x[0])):
        if module.startswith(prefix):
            return layer, prefix
    return 0, "unknown"


def extract_imports(file_path: Path) -> Iterator[tuple[str, str, int, bool]]:
    """
    Extract import statements from a Python file.

    Yields:
        Tuples of (importing_module, imported_module, line_number, is_type_checking)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return

    # Get the module path from file path
    parts = file_path.with_suffix("").parts
    if "bengal" in parts:
        idx = parts.index("bengal")
        module_name = ".".join(parts[idx:])
    else:
        return

    # First, collect line numbers that are inside TYPE_CHECKING blocks
    type_checking_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                # Mark all lines in this block as TYPE_CHECKING
                for child in ast.walk(node):
                    if hasattr(child, "lineno"):
                        type_checking_lines.add(child.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("bengal."):
                    is_tc = node.lineno in type_checking_lines
                    yield (module_name, alias.name, node.lineno, is_tc)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("bengal."):
                is_tc = node.lineno in type_checking_lines
                yield (module_name, node.module, node.lineno, is_tc)


def is_allowed_violation(importer: str, imported: str) -> bool:
    """
    Check if this import is in the allowed violations list.

    Args:
        importer: The importing module path
        imported: The imported module path

    Returns:
        True if this is an allowed (documented) exception
    """
    for allowed_importer, allowed_imported in ALLOWED_VIOLATIONS:
        if importer.startswith(allowed_importer) and imported.startswith(allowed_imported):
            return True
    return False


def check_violation(importer: str, imported: str) -> tuple[bool, str]:
    """
    Check if an import violates the layer hierarchy.

    Returns:
        (is_violation, violation_description)
    """
    importer_layer, importer_name = get_layer(importer)
    imported_layer, imported_name = get_layer(imported)

    # protocols can be imported from anywhere
    if imported_name == "bengal.protocols":
        return False, ""

    # Unknown layers are allowed (might be tests or scripts)
    if importer_layer == 0 or imported_layer == 0:
        return False, ""

    # Check if this is an allowed exception
    if is_allowed_violation(importer, imported):
        return False, ""

    # Violation: importing from a higher layer
    if imported_layer > importer_layer:
        return True, f"{importer_name} (layer {importer_layer}) → {imported_name} (layer {imported_layer})"

    return False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Check dependency layer violations")
    parser.add_argument(
        "--format",
        choices=["simple", "detailed"],
        default="simple",
        help="Output format",
    )
    parser.add_argument(
        "--path",
        default="bengal/",
        help="Path to analyze",
    )
    args = parser.parse_args()

    violations: list[tuple[str, str, int, str]] = []
    type_checking_skipped = 0

    root = Path(args.path)
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue

        for importer, imported, line, is_type_checking in extract_imports(py_file):
            # Skip TYPE_CHECKING imports - they don't create runtime violations
            if is_type_checking:
                type_checking_skipped += 1
                continue
            is_violation, desc = check_violation(importer, imported)
            if is_violation:
                violations.append((importer, imported, line, desc))

    if not violations:
        print("✅ No dependency layer violations detected")
        print(f"\n  Analyzed {len(list(root.rglob('*.py')))} Python files")
        return 0

    # Group violations by importer module
    by_module: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for importer, imported, line, desc in violations:
        by_module[importer].append((imported, line, desc))

    print(f"❌ Found {len(violations)} dependency layer violation(s):")

    if args.format == "detailed":
        for importer in sorted(by_module.keys()):
            print(f"\n  📁 {importer}:")
            for imported, line, desc in by_module[importer]:
                print(f"    Line {line}: imports {imported}")
                print(f"      ⚠️  {desc}")
    else:
        for importer, imported, line, desc in violations:
            print(f"  • {importer}:{line} → {imported}")
            print(f"    ({desc})")

    print(f"\n  📊 Summary:")
    print(f"    - Total violations: {len(violations)}")
    print(f"    - Modules affected: {len(by_module)}")
    print(f"\n  💡 Fix: Move imports to TYPE_CHECKING blocks, use protocols,")
    print(f"          or refactor to respect layer boundaries.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
