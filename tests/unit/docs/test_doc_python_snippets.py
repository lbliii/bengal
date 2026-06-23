"""CI guard: imports in extension-guide docs must resolve.

The extension guides under ``site/content/docs/build-sites/extend/`` teach third
parties how to write against Bengal's public APIs. If a guide imports a
module or symbol that does not exist, every example silently breaks for the
reader (issue #388 — the custom-directives guide imported a nonexistent
``bengal.directives`` package).

This test extracts every fenced ``python`` code block from the guides and
executes only its ``import`` statements, asserting they resolve against the
installed package. An ``ImportError`` is a test failure.

We execute the import lines (not whole snippets) because the prose snippets
intentionally show fragments that reference names defined in other blocks
(e.g. a class defined earlier). The load-bearing accuracy claim is that the
*first-party import paths* are real, which is exactly what regressed in #388,
so we only assert imports rooted at ``bengal`` or ``patitas`` (Bengal's own
public surface). Illustrative placeholder imports for user code (e.g.
``from your_directives import AlertDirective``) are skipped.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# tests/unit/docs/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOCS_DIR = _REPO_ROOT / "site" / "content" / "docs" / "build-sites" / "extend"

# Guides whose python snippets must import real symbols.
_GUIDES = (
    _DOCS_DIR / "custom-directives.md",
    _DOCS_DIR / "_index.md",
)

_FENCE_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _python_blocks(markdown: str) -> list[str]:
    """Return the source of every fenced ```python block."""
    return _FENCE_RE.findall(markdown)


def _import_lines(block: str) -> list[str]:
    """Extract the (possibly multi-line) import statements from a block.

    Uses the AST so parenthesized multi-line imports are captured whole.
    Returns the exact source segments for each ``import`` / ``from ...
    import`` statement.
    """
    try:
        tree = ast.parse(block)
    except SyntaxError:
        # Fragment blocks (e.g. a bare method body) are not standalone
        # modules; they carry no top-level imports to check.
        return []

    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            segment = ast.get_source_segment(block, node)
            if segment is not None:
                imports.append(segment)
    return imports


# Roots of Bengal's own public surface. Only imports rooted here are asserted
# to resolve; placeholder user-code imports (your_directives, etc.) are skipped.
_FIRST_PARTY_ROOTS = ("bengal", "patitas")


def _is_first_party(stmt: str) -> bool:
    """True if the import statement targets a Bengal/Patitas module."""
    try:
        tree = ast.parse(stmt)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in _FIRST_PARTY_ROOTS:
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in _FIRST_PARTY_ROOTS:
                    return True
    return False


def _iter_doc_imports() -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for guide in _GUIDES:
        assert guide.is_file(), f"missing guide: {guide}"
        markdown = guide.read_text(encoding="utf-8")
        for block in _python_blocks(markdown):
            cases.extend(
                (guide.name, stmt) for stmt in _import_lines(block) if _is_first_party(stmt)
            )
    return cases


_DOC_IMPORTS = _iter_doc_imports()


def test_guides_contain_python_imports() -> None:
    """Sanity: the extractor actually found import statements to guard.

    A green suite is meaningless if the regex silently matched nothing
    (the #130 vacuous-assertion lesson).
    """
    assert _DOC_IMPORTS, "no python imports extracted from extension guides"
    # The custom-directives guide must import from the real public path.
    joined = " ".join(stmt for _, stmt in _DOC_IMPORTS)
    assert "bengal.parsing.backends.patitas.directives" in joined


def test_no_nonexistent_directives_module() -> None:
    """No guide may import the nonexistent ``bengal.directives`` package."""
    for name, stmt in _DOC_IMPORTS:
        assert "from bengal.directives import" not in stmt, (
            f"{name} imports nonexistent bengal.directives: {stmt!r}"
        )
        assert "import bengal.directives" not in stmt, (
            f"{name} imports nonexistent bengal.directives: {stmt!r}"
        )


@pytest.mark.parametrize(
    ("guide_name", "import_stmt"),
    _DOC_IMPORTS,
    ids=[f"{name}:{stmt.splitlines()[0][:60]}" for name, stmt in _DOC_IMPORTS],
)
def test_doc_import_resolves(guide_name: str, import_stmt: str) -> None:
    """Each import statement in the guides must execute without ImportError."""
    try:
        exec(compile(import_stmt, f"<{guide_name}>", "exec"), {})  # noqa: S102 - executing doc imports is the test
    except ImportError as exc:  # pragma: no cover - failure path
        pytest.fail(f"{guide_name}: import failed to resolve:\n{import_stmt}\n  -> {exc}")
