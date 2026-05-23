"""Audit direct writes in generated-output and cache-adjacent Bengal code."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED_DIRS = (
    ROOT / "bengal" / "assets",
    ROOT / "bengal" / "cache",
    ROOT / "bengal" / "orchestration",
    ROOT / "bengal" / "postprocess",
    ROOT / "bengal" / "rendering",
)
DIRECT_WRITE_METHODS = {"write_bytes", "write_text"}
APPROVED_DIRECT_WRITES = {
    (
        "bengal/orchestration/incremental/orchestrator.py",
        "_write_output",
        "write_text",
    ): "test bridge placeholder output; migrate before using for shipped output",
    (
        "bengal/rendering/pipeline/write_behind.py",
        "_atomic_write_fast",
        "write_text",
    ): "temp-file write followed by atomic replace",
    (
        "bengal/rendering/external_refs/resolver.py",
        "_fetch",
        "write_text",
    ): "external-reference cache write; tracked for atomic-write migration",
}


@dataclass(frozen=True, slots=True)
class DirectWriteFinding:
    """One direct write call found in a scanned module."""

    path: str
    line: int
    function: str
    method: str
    receiver: str

    @property
    def approval_key(self) -> tuple[str, str, str]:
        return (self.path, self.function, self.method)


class _DirectWriteVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.function_stack: list[str] = []
        self.findings: list[DirectWriteFinding] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in DIRECT_WRITE_METHODS:
            self.findings.append(
                DirectWriteFinding(
                    path=self.path,
                    line=node.lineno,
                    function=self.function_stack[-1] if self.function_stack else "<module>",
                    method=node.func.attr,
                    receiver=ast.unparse(node.func.value),
                )
            )
        self.generic_visit(node)


def scan_file(path: Path, *, root: Path = ROOT) -> tuple[DirectWriteFinding, ...]:
    """Return direct write findings for one Python source file."""
    relative = path.relative_to(root).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    visitor = _DirectWriteVisitor(relative)
    visitor.visit(tree)
    return tuple(visitor.findings)


def iter_scanned_files(root: Path = ROOT) -> tuple[Path, ...]:
    """Return Python files covered by the output-write audit."""
    files: list[Path] = []
    for directory in SCANNED_DIRS:
        if directory.exists():
            files.extend(sorted(directory.rglob("*.py")))
    return tuple(files)


def scan_direct_writes(root: Path = ROOT) -> tuple[DirectWriteFinding, ...]:
    """Return all direct write findings in scanned directories."""
    findings: list[DirectWriteFinding] = []
    for path in iter_scanned_files(root):
        findings.extend(scan_file(path, root=root))
    return tuple(findings)


def unapproved_direct_writes(
    findings: tuple[DirectWriteFinding, ...],
) -> tuple[DirectWriteFinding, ...]:
    """Return findings that are not in the explicit approval ledger."""
    return tuple(
        finding for finding in findings if finding.approval_key not in APPROVED_DIRECT_WRITES
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-approved",
        action="store_true",
        help="Print approved direct writes as audit context.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    findings = scan_direct_writes()
    if args.list_approved:
        for finding in findings:
            reason = APPROVED_DIRECT_WRITES.get(finding.approval_key, "UNAPPROVED")
            print(
                f"{finding.path}:{finding.line}: "
                f"{finding.function} {finding.receiver}.{finding.method} - {reason}"
            )
        return 0

    unapproved = unapproved_direct_writes(findings)
    for finding in unapproved:
        print(
            f"{finding.path}:{finding.line}: direct {finding.method} in "
            f"{finding.function}; use atomic_write_* or add an audited approval"
        )
    return 1 if unapproved else 0


if __name__ == "__main__":
    raise SystemExit(main())
