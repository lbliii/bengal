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
import itertools
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path


def extract_imports(file_path: Path) -> Iterator[tuple[str, str, bool]]:
    """
    Extract import statements from a Python file.

    Yields:
        Tuples of (importing_module, imported_module, is_deferred)
        is_deferred is True if import is inside TYPE_CHECKING block or inside a function
        (both are "safe" from circular import issues at module load time)
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

    # Collect all TYPE_CHECKING block node IDs
    type_checking_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                # Mark all child nodes as TYPE_CHECKING
                for child in ast.walk(node):
                    type_checking_nodes.add(id(child))

    # Collect all function/method body node IDs (lazy imports)
    function_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Mark all child nodes as inside function
            for child in ast.walk(node):
                function_nodes.add(id(child))

    # Extract imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("bengal."):
                    is_deferred = id(node) in type_checking_nodes or id(node) in function_nodes
                    yield (module_name, alias.name, is_deferred)
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("bengal."):
            is_deferred = id(node) in type_checking_nodes or id(node) in function_nodes
            yield (module_name, node.module, is_deferred)


def find_cycles(
    edges: dict[str, set[str]], deferred_edges: dict[str, set[str]]
) -> list[tuple[list[str], bool]]:
    """
    Find all cycles in the import graph using DFS.

    Args:
        edges: All import edges
        deferred_edges: Edges that are deferred (TYPE_CHECKING or lazy imports inside functions)

    Returns:
        List of (cycle_path, is_deferred_only) tuples
        is_deferred_only is True if ALL edges in the cycle are deferred (safe at runtime)
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
                cycle = [*path[cycle_start:], neighbor]
                # Check if all edges in cycle are deferred (TYPE_CHECKING or lazy imports)
                cycle_edges = list(itertools.pairwise(cycle))
                is_deferred_only = all(
                    dst in deferred_edges.get(src, set()) for src, dst in cycle_edges
                )
                cycles.append((cycle, is_deferred_only))

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
    deferred_edges: dict[str, set[str]] = defaultdict(set)  # TYPE_CHECKING + lazy imports

    root = Path(args.path)
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        for importer, imported, is_deferred in extract_imports(py_file):
            edges[importer].add(imported)
            if is_deferred:
                deferred_edges[importer].add(imported)

    # Find cycles
    cycles = find_cycles(edges, deferred_edges)

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
                for _i, mod in enumerate(cycle[:-1]):
                    print(f"    {mod}")
                    print("      ↓ imports")
                print(f"    {cycle[-1]} (back to start)")
            else:
                print(f"  • {' → '.join(cycle)}")

    if tc_cycles:
        print(f"\n⚠️  Found {len(tc_cycles)} deferred-only cycle(s) (safe):")
        for cycle, _ in tc_cycles:
            if args.format == "detailed":
                print(f"\n  Cycle ({len(cycle) - 1} modules, deferred imports only):")
                for mod in cycle[:-1]:
                    print(f"    {mod}")
            else:
                print(f"  • {' → '.join(cycle)} (deferred)")

    return 1 if real_cycles else 0


if __name__ == "__main__":
    sys.exit(main())
