import ast
from pathlib import Path
from typing import TypeGuard

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
    "tests/core/test_page_bundles.py",
    "tests/unit/analysis/test_analysis_optimization.py",
    "tests/unit/analysis/test_graph_analysis.py",
    "tests/unit/analysis/test_graph_builder_parallel.py",
    "tests/unit/analysis/test_graph_features.py",
    "tests/unit/analysis/test_knowledge_graph.py",
    "tests/integration/test_autodoc_navigation.py",
    "tests/unit/autodoc/test_resilience.py",
    "tests/unit/autodoc/test_virtual_page_rendering.py",
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
    "tests/unit/rendering/test_type_based_templates.py",
    "tests/unit/rendering/utils/test_rendering_safe_access.py",
    "tests/unit/rendering/utils/test_rendering_url.py",
    "tests/themes/test_default_theme_kida.py",
    "tests/unit/core/test_site_caching.py",
    "tests/unit/core/test_site_lifecycle.py",
    "tests/unit/discovery/test_surgical_discovery.py",
    "tests/unit/cache/test_query_index.py",
    "tests/unit/cache/test_query_index_registry.py",
    "tests/unit/core/test_page_urls_in_sections.py",
    "tests/unit/core/test_cascade.py",
    "tests/unit/core/test_cascade_snapshot.py",
    "tests/unit/core/test_content_signals_visibility.py",
    "tests/unit/core/test_ergonomic_helpers.py",
    "tests/unit/core/test_href_property.py",
    "tests/unit/core/test_navigation.py",
    "tests/unit/core/test_page_navigation_weight_order.py",
    "tests/unit/core/test_section_hashability.py",
    "tests/unit/core/test_section_index_collision.py",
    "tests/unit/core/test_section_page_types.py",
    "tests/unit/core/test_section_sorting.py",
    "tests/unit/core/test_section_versioning.py",
    "tests/unit/core/test_site_visibility_filtering.py",
    "tests/unit/health/validators/test_connectivity.py",
    "tests/unit/health/validators/test_navigation_validator.py",
    "tests/unit/health/validators/test_taxonomy.py",
    "tests/unit/orchestration/incremental/test_shadow_mode.py",
    "tests/unit/orchestration/incremental/test_track_dependencies.py",
    "tests/unit/orchestration/test_content_type_detection.py",
    "tests/unit/orchestration/test_incremental_orchestrator.py",
    "tests/unit/orchestration/test_related_posts.py",
    "tests/unit/orchestration/test_render_orchestrator.py",
    "tests/unit/orchestration/test_section_orchestrator.py",
    "tests/unit/orchestration/test_taxonomy_incremental.py",
    "tests/unit/orchestration/test_taxonomy_orchestrator.py",
    "tests/unit/postprocess/test_redirects.py",
    "tests/unit/template_functions/test_taxonomies_baseurl.py",
    "tests/unit/test_nav_tree.py",
    "tests/unit/utils/test_page_initializer.py",
    "tests/integration/core/test_page_frontmatter.py",
    "tests/integration/test_hashable_page_deduplication.py",
    "tests/unit/core/test_component_model.py",
    "tests/unit/core/test_computed_functions.py",
    "tests/unit/core/test_page_hashability.py",
    "tests/unit/core/test_page_metadata_helpers.py",
    "tests/unit/core/test_page_record_migration.py",
    "tests/unit/core/test_page_url_cache_clearing.py",
    "tests/unit/core/test_page_visibility.py",
)


def _calls_page_constructor(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id == "Page"
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id == "Page" and node.func.attr == "create_virtual"
    return False


def _imports_core_page_class(node: ast.AST) -> TypeGuard[ast.ImportFrom]:
    if not isinstance(node, ast.ImportFrom) or node.module != "bengal.core.page":
        return False
    return any(alias.name == "Page" for alias in node.names)


def _imports_core_page_package_root(node: ast.AST) -> TypeGuard[ast.ImportFrom]:
    return isinstance(node, ast.ImportFrom) and node.module == "bengal.core.page"


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
        violations.extend(
            f"{relative_path}:{node.lineno}"
            for node in ast.walk(tree)
            if _imports_core_page_class(node)
        )

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


def test_non_compatibility_tests_do_not_import_page_class() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for path in sorted((repo_root / "tests").rglob("*.py")):
        relative_path = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations.extend(
            f"{relative_path}:{node.lineno}"
            for node in ast.walk(tree)
            if _imports_core_page_class(node)
        )

    assert violations == []


def test_no_code_imports_from_core_page_package_root() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []

    for root_name in ("bengal", "tests"):
        for path in sorted((repo_root / root_name).rglob("*.py")):
            relative_path = path.relative_to(repo_root).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            violations.extend(
                f"{relative_path}:{node.lineno}"
                for node in ast.walk(tree)
                if _imports_core_page_package_root(node)
            )

    assert violations == []
