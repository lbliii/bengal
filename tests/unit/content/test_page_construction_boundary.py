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

MIGRATED_TEST_PAGE_CONSTRUCTION_FILES = (
    "tests/unit/analysis/test_analysis_optimization.py",
    "tests/unit/analysis/test_graph_analysis.py",
    "tests/unit/analysis/test_graph_builder_parallel.py",
    "tests/unit/analysis/test_graph_features.py",
    "tests/unit/analysis/test_knowledge_graph.py",
    "tests/unit/rendering/test_crossref.py",
    "tests/unit/rendering/test_crossref_baseurl.py",
    "tests/unit/rendering/test_i18n_template_functions.py",
    "tests/unit/rendering/test_output_format_html.py",
    "tests/unit/rendering/test_page_content.py",
    "tests/unit/rendering/test_page_operations.py",
    "tests/unit/rendering/test_page_urls.py",
    "tests/unit/rendering/test_pipeline_reporter_output.py",
    "tests/unit/rendering/test_renderer_index_conflict.py",
    "tests/unit/rendering/test_renderer_template_selection.py",
    "tests/unit/rendering/test_renderer_tag_context.py",
    "tests/unit/rendering/test_section_ergonomics.py",
    "tests/unit/rendering/test_section_urls.py",
    "tests/unit/rendering/test_template_url_access.py",
    "tests/unit/rendering/utils/test_rendering_url.py",
    "tests/unit/core/test_site_caching.py",
    "tests/unit/core/test_site_lifecycle.py",
    "tests/unit/cache/test_query_index.py",
    "tests/unit/cache/test_query_index_registry.py",
    "tests/unit/health/validators/test_connectivity.py",
    "tests/unit/health/validators/test_navigation_validator.py",
    "tests/unit/health/validators/test_taxonomy.py",
    "tests/unit/template_functions/test_taxonomies_baseurl.py",
)


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


def test_production_page_imports_stay_in_source_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for path in sorted((repo_root / "bengal").rglob("*.py")):
        relative_path = path.relative_to(repo_root).as_posix()
        if relative_path in PAGE_CONSTRUCTION_ADAPTER_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "bengal.core.page":
                continue
            if any(alias.name == "Page" for alias in node.names):
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []


def test_migrated_tests_build_pages_through_source_adapter() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for relative_path in MIGRATED_TEST_PAGE_CONSTRUCTION_FILES:
        path = repo_root / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _calls_page_constructor(node)
        )

    assert violations == []
