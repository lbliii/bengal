import ast
from pathlib import Path

MIGRATED_PARSED_APPLICATION_FILES = (
    "bengal/content/discovery/content_discovery.py",
    "bengal/rendering/pipeline/autodoc_renderer.py",
    "bengal/rendering/pipeline/cache_checker.py",
    "bengal/rendering/template_functions/get_page.py",
    "bengal/snapshots/persistence.py",
)

PARSED_FIELD_NAMES = {
    "html_content",
    "toc",
    "_toc_items_cache",
    "_excerpt",
    "_meta_description",
    "_plain_text_cache",
}


def test_migrated_paths_apply_parsed_records_through_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for relative_path in MIGRATED_PARSED_APPLICATION_FILES:
        path = repo_root / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "page"
                and target.attr in PARSED_FIELD_NAMES
            )
        )

    assert violations == []
