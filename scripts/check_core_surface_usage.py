"""Guard internal usage of core compatibility surfaces marked for retirement."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOT = ROOT / "bengal"
IGNORED_PATHS = {
    "bengal/core/section/__init__.py",
}
RETIRED_COMPAT_ATTRS = {
    "content_pages": "Use bengal.rendering.section_ergonomics.content_pages() inside Bengal.",
}


@dataclass(frozen=True, slots=True)
class CoreSurfaceUsage:
    """One internal compatibility-surface usage."""

    path: str
    line: int
    attr: str
    suggestion: str


class _CoreSurfaceVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.usages: list[CoreSurfaceUsage] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in RETIRED_COMPAT_ATTRS:
            self.usages.append(
                CoreSurfaceUsage(
                    path=self.path,
                    line=node.lineno,
                    attr=node.attr,
                    suggestion=RETIRED_COMPAT_ATTRS[node.attr],
                )
            )
        self.generic_visit(node)


def scan_file(path: Path, *, root: Path = ROOT) -> tuple[CoreSurfaceUsage, ...]:
    """Return retired core-surface usage in one source file."""
    relative = path.relative_to(root).as_posix()
    if relative in IGNORED_PATHS:
        return ()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    visitor = _CoreSurfaceVisitor(relative)
    visitor.visit(tree)
    return tuple(visitor.usages)


def scan_core_surface_usage(root: Path = ROOT) -> tuple[CoreSurfaceUsage, ...]:
    """Return retired core-surface usage in Bengal production code."""
    usages: list[CoreSurfaceUsage] = []
    for path in sorted((root / "bengal").rglob("*.py")):
        usages.extend(scan_file(path, root=root))
    return tuple(usages)


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: list[str] | None = None) -> int:
    _build_parser().parse_args(argv)
    usages = scan_core_surface_usage()
    for usage in usages:
        print(f"{usage.path}:{usage.line}: .{usage.attr} - {usage.suggestion}")
    return 1 if usages else 0


if __name__ == "__main__":
    raise SystemExit(main())
