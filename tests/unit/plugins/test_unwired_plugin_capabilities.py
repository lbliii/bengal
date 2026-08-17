"""Guard: pending plugin capabilities stay registered but unwired.

``apply_plugin_content_sources`` is scaffolding on the frozen registry. A later
saga may wire it into discovery; until then, production must not call it.
Health validators and shortcodes have registry fields but no apply_* helpers.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BENGAL_DIR = REPO_ROOT / "bengal"
INTEGRATION_FILE = BENGAL_DIR / "plugins" / "integration.py"
UNWIRED_CONTENT_SOURCES = "apply_plugin_content_sources"
MISSING_APPLY_HELPERS = (
    "apply_plugin_health",
    "apply_plugin_health_validators",
    "apply_plugin_shortcode",
    "apply_plugin_shortcodes",
)


def _imported_or_called_names(tree: ast.AST) -> set[str]:
    """Names imported, referenced, or accessed as attributes in *tree*."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _function_def_names(tree: ast.AST) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


@pytest.fixture(scope="module")
def production_trees() -> list[tuple[Path, ast.AST]]:
    trees: list[tuple[Path, ast.AST]] = []
    for path in BENGAL_DIR.rglob("*.py"):
        if not path.is_file():
            continue
        trees.append((path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))))
    return trees


def test_content_source_apply_helper_exists_as_scaffolding(
    production_trees: list[tuple[Path, ast.AST]],
) -> None:
    integration = next(
        tree for path, tree in production_trees if path.resolve() == INTEGRATION_FILE.resolve()
    )
    assert UNWIRED_CONTENT_SOURCES in _function_def_names(integration)


def test_content_source_apply_helper_is_not_called_from_production(
    production_trees: list[tuple[Path, ast.AST]],
) -> None:
    violations = [
        path.relative_to(REPO_ROOT).as_posix()
        for path, tree in production_trees
        if path.resolve() != INTEGRATION_FILE.resolve()
        and UNWIRED_CONTENT_SOURCES in _imported_or_called_names(tree)
    ]
    assert violations == [], (
        f"{UNWIRED_CONTENT_SOURCES} must stay unwired; referenced outside "
        f"bengal/plugins/integration.py: {violations}"
    )


def test_pending_capabilities_have_no_apply_helpers_yet(
    production_trees: list[tuple[Path, ast.AST]],
) -> None:
    missing = set(MISSING_APPLY_HELPERS)
    defined = [
        f"{path.relative_to(REPO_ROOT).as_posix()}:{name}"
        for path, tree in production_trees
        for name in sorted(_function_def_names(tree) & missing)
    ]
    assert defined == [], (
        "health validators and shortcodes have registry fields but no apply_* "
        f"production injection yet; unexpected helpers: {defined}"
    )
