#!/usr/bin/env python3
"""
Circular import detection for Bengal codebase.

Detects potential circular import patterns by analyzing import statements
in Python files. Reports cycles and their severity.

Usage:
    python scripts/check_cycles.py [--format=simple|detailed] [--path=bengal/]

Exit Codes:
    0: No cycles detected
    1: Cycles detected (with detailed report)

"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator


def extract_imports(file_path: Path) -> Iterator[tuple[str, str, bool]]:
    """
    Extract import statements from a Python file.

    Yields:
        Tuples of (importing_module, imported_module, is_type_checking)
        is_type_checking is True if import is inside TYPE_CHECKING block
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

    # Track if we're inside a TYPE_CHECKING block
    in_type_checking = False

    for node in ast.walk(tree):
        # Check for TYPE_CHECKING blocks
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                # Process imports inside this block
                for child in ast.walk(node):
                    if isinstance(child, ast.Import):
                        for alias in child.names:
                            if alias.name.startswith("bengal."):
                                yield (module_name, alias.name, True)
                    elif isinstance(child, ast.ImportFrom):
                        if child.module and child.module.startswith("bengal."):
                            yield (module_name, child.module, True)

        # Regular imports (not in TYPE_CHECKING)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("bengal."):
                    # Check if this node is inside TYPE_CHECKING (handled above)
                    yield (module_name, alias.name, False)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("bengal."):
                yield (module_name, node.module, False)


def find_cycles(
    edges: dict[str, set[str]], type_checking_edges: dict[str, set[str]]
) -> list[tuple[list[str], bool]]:
    """
    Find all cycles in the import graph using DFS.

    Returns:
        List of (cycle_path, is_type_checking_only) tuples
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in edges.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle - extract it
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                # Check if all edges in cycle are type-checking only
                cycle_edges = list(zip(cycle[:-1], cycle[1:]))
                is_tc_only = all(
                    dst in type_checking_edges.get(src, set())
                    for src, dst in cycle_edges
                )
                cycles.append((cycle, is_tc_only))

        path.pop()
        rec_stack.remove(node)

    for node in edges:
        if node not in visited:
            dfs(node)

    return cycles


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect circular imports")
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

    # Build import graph
    edges: dict[str, set[str]] = defaultdict(set)
    type_checking_edges: dict[str, set[str]] = defaultdict(set)

    root = Path(args.path)
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        for importer, imported, is_tc in extract_imports(py_file):
            edges[importer].add(imported)
            if is_tc:
                type_checking_edges[importer].add(imported)

    # Find cycles
    cycles = find_cycles(edges, type_checking_edges)

    # Deduplicate cycles (same cycle can be found starting from different nodes)
    seen_cycles: set[tuple[str, ...]] = set()
    unique_cycles = []
    for cycle, is_tc_only in cycles:
        # Normalize cycle by rotating to start with smallest element
        min_idx = cycle.index(min(cycle[:-1]))
        normalized = tuple(cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]])
        if normalized not in seen_cycles:
            seen_cycles.add(normalized)
            unique_cycles.append((list(normalized), is_tc_only))

    # Report results
    if not unique_cycles:
        print("✅ No circular imports detected")
        return 0

    # Separate real cycles from type-checking-only cycles
    real_cycles = [(c, tc) for c, tc in unique_cycles if not tc]
    tc_cycles = [(c, tc) for c, tc in unique_cycles if tc]

    if real_cycles:
        print(f"❌ Found {len(real_cycles)} circular import(s):")
        for cycle, _ in real_cycles:
            if args.format == "detailed":
                print(f"\n  Cycle ({len(cycle) - 1} modules):")
                for i, mod in enumerate(cycle[:-1]):
                    print(f"    {mod}")
                    print(f"      ↓ imports")
                print(f"    {cycle[-1]} (back to start)")
            else:
                print(f"  • {' → '.join(cycle)}")

    if tc_cycles:
        print(f"\n⚠️  Found {len(tc_cycles)} TYPE_CHECKING-only cycle(s) (safe):")
        for cycle, _ in tc_cycles:
            if args.format == "detailed":
                print(f"\n  Cycle ({len(cycle) - 1} modules, TYPE_CHECKING only):")
                for mod in cycle[:-1]:
                    print(f"    {mod}")
            else:
                print(f"  • {' → '.join(cycle)} (TYPE_CHECKING)")

    return 1 if real_cycles else 0


if __name__ == "__main__":
    sys.exit(main())
