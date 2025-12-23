import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.utils.file_io import write_text_file

logger = logging.getLogger(__name__)


def pytest_configure(config: pytest.Config) -> None:
    """Configure Hypothesis and scaling knobs for CI speed vs nightly depth.

    Environment-controlled profiles:
    - BENGAL_CI_FAST=1: reduce Hypothesis examples and scale of long tests.
    """
    if os.environ.get("BENGAL_CI_FAST") == "1":
        try:
            from hypothesis import settings

            settings.register_profile("ci-fast", max_examples=10, deadline=None)
            settings.load_profile("ci-fast")
        except Exception:
            # Hypothesis not installed; nothing to do
            pass


"""
Global pytest configuration and fixtures.

This file provides:
- Shared fixtures for all tests
- Pytest hooks for better debugging
- Automatic test output capture
- Testing infrastructure plugins
- Progress reporting for long-running tests
"""

# ============================================================================
# TESTING INFRASTRUCTURE
# ============================================================================

# Register Phase 1 testing plugins
pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers"]


# ============================================================================
# TEST PROGRESS REPORTING
# ============================================================================


@pytest.fixture
def test_progress(request):
    """
    Progress reporter for long-running tests.

    Provides visual feedback during test execution. Enabled when running
    pytest with -v/--verbose flag.

    Usage:
        def test_long_operation(test_progress):
            # Simple status updates
            test_progress.status("Starting...")

            # Timed operations
            with test_progress.timed("Building site"):
                site.build()

            # Progress tracking for loops
            with test_progress.phase("Processing pages", total=100) as update:
                for i, page in enumerate(pages):
                    process(page)
                    update(i + 1, page.title)

            # Step-by-step progress
            test_progress.step(1, 3, "Discovering content")
            test_progress.step(2, 3, "Rendering pages")
            test_progress.step(3, 3, "Writing output")

    Args:
        request: pytest request fixture (auto-injected)

    Returns:
        TestProgressReporter instance
    """
    from tests._testing.progress import TestProgressReporter

    # Check if pytest is running in verbose mode
    verbose = request.config.getoption("verbose", 0) > 0

    # Get test name for prefix
    test_name = request.node.name

    return TestProgressReporter(verbose=verbose, prefix=test_name)


# ============================================================================
# COLLECTION HOOKS
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items to:
    1. Filter out non-test functions
    2. Configure xdist scheduling for parallel-unsafe tests

    This prevents pytest from collecting functions like test_draft() from
    bengal/rendering/template_tests.py which are Jinja2 template tests,
    not pytest tests.

    For xdist: Tests marked with 'serial' or 'parallel_unsafe' are assigned
    to the same worker to prevent "node down" errors from nested multiprocessing.
    """
    # Filter out items that are collected from outside the tests directory
    filtered_items = []
    tests_dir = Path(__file__).parent  # /path/to/tests/

    for item in items:
        fspath = Path(str(item.fspath))
        # Only keep items where the file is under the tests directory
        try:
            fspath.relative_to(tests_dir)
            filtered_items.append(item)

            # Mark parallel-unsafe tests for xdist
            # Tests with these markers should run on the same worker sequentially
            if any(marker in item.keywords for marker in ["serial", "parallel_unsafe"]):
                # Add xdist marker to schedule these tests on same worker
                item.add_marker(pytest.mark.xdist_group(name="serial_group"))
        except ValueError:
            # File is not relative to tests_dir, skip it
            pass

    items[:] = filtered_items


# ============================================================================
# AUTO-SAVE TEST OUTPUT FOR AI DEBUGGING
# ============================================================================


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Save detailed failure information automatically.

    This hook captures test failures and saves them to .pytest_cache/
    so AI assistants can read full details without re-running tests.
    """
    outcome = yield
    report = outcome.get_result()

    # Only save on failure
    if report.when == "call" and report.failed:
        cache_dir = Path(".pytest_cache")
        cache_dir.mkdir(exist_ok=True)

        # Create detailed failure report
        failure_file = cache_dir / "last_failure.txt"

        with open(failure_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("PYTEST FAILURE DETAILS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Test: {item.nodeid}\n")
            f.write(f"Location: {item.location}\n")
            f.write("\n")

            # Full error details
            if report.longrepr:
                f.write("FAILURE DETAILS:\n")
                f.write("-" * 80 + "\n")
                f.write(str(report.longrepr))
                f.write("\n\n")

            # Captured output
            if hasattr(report, "capstdout") and report.capstdout:
                f.write("CAPTURED STDOUT:\n")
                f.write("-" * 80 + "\n")
                f.write(report.capstdout)
                f.write("\n\n")

            if hasattr(report, "capstderr") and report.capstderr:
                f.write("CAPTURED STDERR:\n")
                f.write("-" * 80 + "\n")
                f.write(report.capstderr)
                f.write("\n\n")


# ============================================================================
# EXISTING FIXTURES (preserved)
# ============================================================================


@pytest.fixture(scope="session")
def sample_config_immutable():
    """
    Session-scoped config fixture for read-only tests.

    Performance: Created ONCE per test session.
    Use this when tests only READ config and don't modify it.

    WARNING: Do NOT modify this config in tests! Use sample_config() instead.
    """
    return {
        "site": {"title": "Test Site", "baseurl": "https://example.com"},
        "build": {"output_dir": "public", "content_dir": "content"},
    }


@pytest.fixture(scope="class")
def class_tmp_site(tmp_path_factory):
    """
    Class-scoped temporary site for tests that share setup.

    Performance: Created ONCE per test class.
    Use this when multiple tests in a class can share the same site structure.

    Example:
        class TestSiteFeatures:
            def test_feature_a(self, class_tmp_site):
                # All tests in this class share the same site

            def test_feature_b(self, class_tmp_site):
                # Reuses the same site from test_feature_a

    Note: If tests modify the site, use tmp_site() instead.
    """
    return tmp_path_factory.mktemp("class_site")


@pytest.fixture
def tmp_site(tmp_path):
    """
    Function-scoped temporary site for tests that modify state.

    Performance: Created FRESH for each test.
    Use this when tests need isolated, clean state.

    Note: This is SLOWER than class_tmp_site because it creates
    a new site for every test. Use class_tmp_site when possible.
    """
    return tmp_path


@pytest.fixture
def sample_config():
    """
    Function-scoped config fixture for tests that modify config.

    Performance: Created FRESH for each test.
    Each test gets its own copy, safe to modify.

    Example:
        def test_config_modification(sample_config):
            sample_config["site"]["title"] = "Modified"  # Safe!
    """
    return {
        "site": {"title": "Test Site", "baseurl": "https://example.com"},
        "build": {"output_dir": "public", "content_dir": "content"},
    }


@pytest.fixture(autouse=True)
def reset_bengal_state(request):
    """
    Reset all stateful singletons/caches between tests for test isolation.

    This fixture runs automatically for every test (autouse=True) and ensures:
    - Rich console is reset (prevents Live display conflicts)
    - Logger state is cleared (prevents file handle leaks)
    - Theme cache is cleared (ensures fresh theme discovery)
    - Parser cache is cleared (ensures fresh parsers with current directives)

    Tests can skip the logger reset by adding the @pytest.mark.preserve_loggers
    marker. This is useful for tests that verify logged events across builds.

    Future expansions:
    - PageProxyCache (if added as singleton)
    - TaxonomyIndex caching state
    - Template engine instances/bytecode cache
    - Asset dependency map state
    """
    # Setup: Clear parser cache before test to get fresh parsers with latest directives
    try:
        from bengal.rendering.pipeline.thread_local import reset_parser_cache

        reset_parser_cache()
    except ImportError:
        logger.debug("Parser cache reset skipped: reset_parser_cache not available")

    # Setup: Force reload directives factory to pick up any new directives
    # This is needed because directive imports happen at module load time
    try:
        import importlib

        import bengal.directives.factory

        importlib.reload(bengal.directives.factory)
    except ImportError:
        logger.debug("Directives factory reload skipped: module not available")
    except AttributeError as e:
        logger.debug("Directives factory reload failed: %s", e)

    yield

    # Teardown: Reset all stateful components after each test

    # 1. Reset Rich console
    try:
        from bengal.utils.rich_console import reset_console

        reset_console()
    except ImportError:
        logger.debug("Rich console reset skipped: reset_console not available")

    # 2. Reset logger state (close file handles, clear registry)
    # Skip for tests that manage their own logger state (marked with preserve_loggers)
    if not request.node.get_closest_marker("preserve_loggers"):
        try:
            from bengal.utils.logger import reset_loggers

            reset_loggers()
        except ImportError:
            logger.debug("Logger reset skipped: reset_loggers not available")

    # 3. Clear theme cache (forces fresh discovery)
    try:
        from bengal.core.theme import clear_theme_cache

        clear_theme_cache()
    except ImportError:
        logger.debug("Theme cache clear skipped: clear_theme_cache not available")

    # 4. Clear created directories cache (ensures fresh directory tracking per test)
    try:
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()
    except ImportError:
        logger.debug("Created dirs cache clear skipped: get_created_dirs not available")


@pytest.fixture(scope="class")
def shared_site_class(request, tmp_path_factory):
    """
    Class-scoped temporary site for tests that can share setup.

    Creates a basic site with sample content and builds it once per class.
    Tests can modify if needed, but prefer tmp_site for heavy changes.

    Yields: Site object
    """
    site_dir = tmp_path_factory.mktemp("shared_site")

    # Write config
    config_path = site_dir / "bengal.toml"
    write_text_file(
        str(config_path),
        """[site]
title = "Test Shared Site"
baseurl = "/"

[build]
output_dir = "public"
parallel = true
incremental = false
""",
    )

    # Create sample content (10 pages)
    content_dir = site_dir / "content"
    content_dir.mkdir()

    for i in range(10):
        page_path = content_dir / f"page_{i}.md"
        write_text_file(
            str(page_path),
            f"""---
title: "Page {i}"
---
Content for page {i}.""",
        )

    # Create site and build
    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()
    _build_stats = site.build(parallel=False)  # Sequential for consistency

    # Yield site, with optional param to copy for modification
    if hasattr(request, "param") and request.param == "modifiable":
        # For tests that need a copy
        mod_site_dir = tmp_path_factory.mktemp("modifiable_site")
        shutil.copytree(site_dir, mod_site_dir)
        mod_config_path = mod_site_dir / "bengal.toml"
        mod_site = Site.from_config(mod_site_dir, config_path=mod_config_path)
        mod_site.discover_content()
        mod_site.discover_assets()
        yield mod_site
    else:
        yield site

    # Teardown: Clean output
    output_dir = site_dir / "public"
    if output_dir.exists():
        shutil.rmtree(output_dir)
