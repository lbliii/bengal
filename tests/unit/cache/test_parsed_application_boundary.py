import ast
from pathlib import Path

MIGRATED_PARSED_APPLICATION_FILES = (
    "bengal/content/discovery/content_discovery.py",
    "bengal/rendering/pipeline/autodoc_renderer.py",
    "bengal/rendering/pipeline/cache_checker.py",
    "bengal/rendering/page_content.py",
    "bengal/rendering/page_operations.py",
    "bengal/rendering/template_functions/get_page.py",
    "bengal/orchestration/streaming.py",
    "bengal/snapshots/persistence.py",
)

PARSED_MUTATION_ADAPTER_FILES = {
    "bengal/cache/parsed_output.py",
}

PARSED_FIELD_NAMES = {
    "html_content",
    "toc",
    "_toc_items_cache",
    "_excerpt",
    "_meta_description",
    "_plain_text_cache",
    "links",
}


def _iter_parsed_field_assignments(tree: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        targets: list[ast.expr]
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            targets = [node.target]
        else:
            continue

        lines.extend(
            target.lineno
            for target in targets
            if isinstance(target, ast.Attribute) and target.attr in PARSED_FIELD_NAMES
        )
    return lines


def _iter_page_field_assignments(tree: ast.AST) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "page"
            and target.attr in PARSED_FIELD_NAMES
        )
    ]


def test_migrated_paths_apply_parsed_records_through_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for relative_path in MIGRATED_PARSED_APPLICATION_FILES:
        path = repo_root / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{lineno}" for lineno in _iter_page_field_assignments(tree)
        )

    assert violations == []


def test_production_parsed_field_writes_stay_in_cache_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for path in sorted((repo_root / "bengal").rglob("*.py")):
        relative_path = path.relative_to(repo_root).as_posix()
        if relative_path in PARSED_MUTATION_ADAPTER_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{lineno}" for lineno in _iter_page_field_assignments(tree)
        )

    assert violations == []


def test_test_parsed_field_writes_stay_allowlisted() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for path in sorted((repo_root / "tests").rglob("*.py")):
        relative_path = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{lineno}" for lineno in _iter_parsed_field_assignments(tree)
        )

    assert violations == []
