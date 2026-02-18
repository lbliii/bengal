"""
Dependency graph report for Bengal's internal Python imports.

This script builds an import graph for the in-repo `bengal.*` modules by parsing
Python source files with `ast` (no runtime importing). It then reports:
    - strongly connected components (SCCs)
    - largest SCC size
    - top fan-in / fan-out modules

The goal is to provide a repeatable "before/after" signal for refactors that
reduce import-cycle pressure and coupling.

Usage:
    python scripts/dep_graph_report.py

Notes:
    - This is a best-effort static import extractor. Dynamic imports and runtime
      import patterns are intentionally ignored.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GraphReport:
    """Computed graph report."""

    module_count: int
    edge_count: int
    scc_count: int
    nontrivial_scc_count: int
    largest_scc: tuple[str, ...]
    fan_out: tuple[tuple[str, int], ...]
    fan_in: tuple[tuple[str, int], ...]


def _iter_python_files(package_root: Path) -> Iterable[Path]:
    for path in package_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _module_name_for_path(package_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(package_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]  # strip ".py"
    return ".".join(["bengal", *parts])


def _resolve_relative_module(
    current_module: str, relative_module: str | None, level: int
) -> str | None:
    """
    Resolve `from ...foo import bar` imports.

    Args:
        current_module: Fully-qualified module name, e.g. "bengal.core.section"
        relative_module: The explicit module in the import (can be None)
        level: Number of leading dots in the import

    Returns:
        Fully qualified module name, or None if it cannot be resolved.
    """
    if level <= 0:
        return relative_module

    current_parts = current_module.split(".")
    if current_parts[-1] == "__init__":
        current_parts = current_parts[:-1]

    # Convert module to package context
    base_parts = current_parts[:-1]  # drop the module itself
    if level > len(base_parts):
        return None
    base = base_parts[: len(base_parts) - (level - 1)]

    if relative_module:
        return ".".join([*base, relative_module])
    return ".".join(base)


def _extract_imports(module_name: str, file_path: Path) -> set[str]:
    """
    Extract imported modules for a given file.

    Only returns `bengal.*` imports (internal to the repo).
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except OSError, SyntaxError:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "bengal" or name.startswith("bengal."):
                    imports.add(name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_relative_module(
                current_module=module_name,
                relative_module=node.module,
                level=node.level,
            )
            if not resolved:
                continue
            if resolved == "bengal" or resolved.startswith("bengal."):
                imports.add(resolved)
    return imports


def _tarjan_scc(graph: dict[str, set[str]]) -> list[list[str]]:
    """
    Tarjan SCC algorithm.

    Returns SCCs as list of lists; each SCC is a list of node names.
    """
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, set()):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in sorted(graph):
        if v not in indices:
            strongconnect(v)

    return sccs


def build_report(repo_root: Path) -> GraphReport:
    # This repo is often used in a multi-root workspace where the *workspace*
    # root is one level above the Bengal repo directory.
    #
    # Handle both layouts:
    #   - repo root: <...>/bengal/            -> package_root: <...>/bengal/bengal/
    #   - workspace root: <...>/python/       -> package_root: <...>/python/bengal/bengal/
    candidates = [
        repo_root / "bengal",
        repo_root / "bengal" / "bengal",
    ]
    package_root = next((p for p in candidates if (p / "__init__.py").exists()), None)
    if package_root is None:
        raise FileNotFoundError(
            "Could not find package root. Tried:\n" + "\n".join(f"  - {p}" for p in candidates)
        )

    nodes: set[str] = set()
    graph: dict[str, set[str]] = {}

    for file_path in _iter_python_files(package_root):
        mod = _module_name_for_path(package_root=package_root, file_path=file_path)
        nodes.add(mod)

    for file_path in _iter_python_files(package_root):
        mod = _module_name_for_path(package_root=package_root, file_path=file_path)
        deps = _extract_imports(module_name=mod, file_path=file_path)

        # Keep only internal deps that correspond to known modules or packages.
        internal: set[str] = set()
        for dep in deps:
            if dep in nodes:
                internal.add(dep)
                continue
            # If dep is a package import (e.g. bengal.core) and we have bengal.core.__init__
            init_name = f"{dep}.__init__"
            if init_name in nodes:
                internal.add(init_name)

        graph[mod] = internal

    # Ensure every node exists as a key
    for n in nodes:
        graph.setdefault(n, set())

    edge_count = sum(len(v) for v in graph.values())

    sccs = _tarjan_scc(graph)
    nontrivial = [sorted(scc) for scc in sccs if len(scc) > 1]
    nontrivial.sort(key=len, reverse=True)
    largest = tuple(nontrivial[0]) if nontrivial else ()

    fan_out_counts = sorted(
        ((m, len(deps)) for m, deps in graph.items()), key=lambda x: x[1], reverse=True
    )
    reverse: dict[str, set[str]] = defaultdict(set)
    for src, deps in graph.items():
        for dst in deps:
            reverse[dst].add(src)
    fan_in_counts = sorted(
        ((m, len(reverse.get(m, set()))) for m in nodes), key=lambda x: x[1], reverse=True
    )

    return GraphReport(
        module_count=len(nodes),
        edge_count=edge_count,
        scc_count=len(sccs),
        nontrivial_scc_count=len(nontrivial),
        largest_scc=largest,
        fan_out=tuple(fan_out_counts[:20]),
        fan_in=tuple(fan_in_counts[:20]),
    )


def _format_table(items: Iterable[tuple[str, int]], label: str) -> str:
    lines = [label]
    for name, count in items:
        lines.append(f"  - {count:>4}  {name}")
    return "\n".join(lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_report(repo_root=repo_root)

    print("Bengal dependency graph report")
    print("=============================")
    print(f"modules: {report.module_count}")
    print(f"edges:   {report.edge_count}")
    print()
    print(f"SCCs: {report.scc_count} (non-trivial: {report.nontrivial_scc_count})")
    if report.largest_scc:
        print(f"largest SCC size: {len(report.largest_scc)}")
        for mod in report.largest_scc:
            print(f"  - {mod}")
    else:
        print("largest SCC size: 0")
    print()
    print(_format_table(report.fan_out, "Top fan-out (outgoing deps)"))
    print()
    print(_format_table(report.fan_in, "Top fan-in (incoming deps)"))


if __name__ == "__main__":
    main()
