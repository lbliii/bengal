import ast
from pathlib import Path

PRODUCTION_PAGE_BOUNDARY_FILES = (
    "bengal/content/discovery/content_discovery.py",
    "bengal/content/discovery/page_factory.py",
    "bengal/autodoc/orchestration/index_pages.py",
    "bengal/autodoc/orchestration/page_builders.py",
    "bengal/orchestration/section.py",
    "bengal/orchestration/utils/virtual_pages.py",
)

PAGE_CONSTRUCTION_ADAPTER_FILES = {
    "bengal/content/discovery/page_adapter.py",
}


def _calls_page_constructor(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id == "Page"
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id == "Page" and node.func.attr == "create_virtual"
    return False


def test_production_page_creation_goes_through_source_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for relative_path in PRODUCTION_PAGE_BOUNDARY_FILES:
        path = repo_root / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _calls_page_constructor(node)
        )

    assert violations == []


def test_production_page_construction_stays_in_source_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for path in sorted((repo_root / "bengal").rglob("*.py")):
        relative_path = path.relative_to(repo_root).as_posix()
        if relative_path in PAGE_CONSTRUCTION_ADAPTER_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _calls_page_constructor(node)
        )

    assert violations == []
