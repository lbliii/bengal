from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bengal.core.site import Site
from bengal.errors import BengalError
from bengal.utils.io.file_io import write_text_file

if TYPE_CHECKING:
    from _pytest.reports import TestReport
    from _pytest.terminal import TerminalReporter

logger = logging.getLogger(__name__)


def pytest_configure(config: pytest.Config) -> None:
    """Configure Hypothesis and scaling knobs for CI speed vs nightly depth.

    Environment-controlled profiles:
    - BENGAL_CI_FAST=1: reduce Hypothesis examples and scale of long tests.

    """
    # Enforce Python 3.14+ requirement (fail fast if wrong version)
    import sys

    if sys.version_info < (3, 14):  # noqa: UP036
        pytest.exit(
            f"ERROR: Python 3.14+ required, but found {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
            f"Current Python: {sys.executable}\n"
            f"Solution: Use 'uv run pytest' instead of 'pytest' to use the project's Python version.\n"
            f"Or run: make test",
            returncode=1,
        )

    # Check if free-threading build (warn if not, but don't fail)
    is_freethreading_build = "free-threading" in sys.version
    if not is_freethreading_build:
        import warnings

        warnings.warn(
            f"Warning: Not using free-threading build (3.14t). "
            f"Current: {sys.executable}\n"
            f"Expected: Python 3.14t free-threading build\n"
            f"Solution: Ensure .python-version contains '3.14t' and use 'uv run pytest'",
            UserWarning,
            stacklevel=2,
        )

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
pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers", "tests._testing.guards"]


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
    Save detailed failure information and extract Bengal error codes.

    This hook captures test failures and:
    1. Saves them to .pytest_cache/ for AI debugging
    2. Extracts Bengal error codes for the terminal summary

    """
    outcome = yield
    report = outcome.get_result()

    # Only process on failure during call phase
    if report.when == "call" and report.failed:
        # Extract Bengal error code if present
        if call.excinfo is not None:
            exc = call.excinfo.value
            if isinstance(exc, BengalError):
                # Store error code and suggestion on report for terminal summary
                code = getattr(exc, "code", None)
                if code is not None:
                    report.bengal_error_code = code.name
                    report.bengal_error_category = code.category
                else:
                    report.bengal_error_code = None
                    report.bengal_error_category = None
                report.bengal_suggestion = getattr(exc, "suggestion", None)
                report.bengal_error_type = type(exc).__name__
            else:
                # Non-Bengal exception
                report.bengal_error_code = None
                report.bengal_error_category = None
                report.bengal_suggestion = None
                report.bengal_error_type = type(exc).__name__

        # Save detailed failure report to cache
        cache_dir = Path(".pytest_cache")
        cache_dir.mkdir(exist_ok=True)

        failure_file = cache_dir / "last_failure.txt"

        with open(failure_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("PYTEST FAILURE DETAILS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Test: {item.nodeid}\n")
            f.write(f"Location: {item.location}\n")

            # Include Bengal error code if present
            if hasattr(report, "bengal_error_code") and report.bengal_error_code:
                f.write(f"Error Code: [{report.bengal_error_code}]\n")
                f.write(f"Category: {report.bengal_error_category}\n")
            if hasattr(report, "bengal_suggestion") and report.bengal_suggestion:
                f.write(f"Fix Hint: {report.bengal_suggestion}\n")

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


def pytest_terminal_summary(
    terminalreporter: TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    """
    Display Bengal error code summary for failed tests.

    Groups failures by error category and shows actionable fix hints.
    This makes CI output more parseable for debugging.

    """
    failed_reports: list[TestReport] = terminalreporter.stats.get("failed", [])
    if not failed_reports:
        return

    # Collect failures with Bengal error codes
    bengal_failures: list[tuple[str, str, str | None, str | None]] = []
    other_failures: list[tuple[str, str]] = []

    for report in failed_reports:
        code = getattr(report, "bengal_error_code", None)
        category = getattr(report, "bengal_error_category", None)
        suggestion = getattr(report, "bengal_suggestion", None)
        error_type = getattr(report, "bengal_error_type", "Exception")

        if code:
            bengal_failures.append((report.nodeid, code, category, suggestion))
        else:
            other_failures.append((report.nodeid, error_type))

    # Only show summary if there are failures
    if not bengal_failures and not other_failures:
        return

    terminalreporter.write_sep("=", "BENGAL ERROR SUMMARY", bold=True, yellow=True)

    # Group Bengal failures by category
    if bengal_failures:
        # Sort by category then code
        bengal_failures.sort(key=lambda x: (x[2] or "", x[1]))

        current_category = None
        for nodeid, code, category, suggestion in bengal_failures:
            if category != current_category:
                current_category = category
                terminalreporter.write_line("")
                terminalreporter.write_line(
                    f"  {category.upper() if category else 'UNKNOWN'} ERRORS:",
                    bold=True,
                )

            # Format: [R001] tests/unit/rendering/test_template.py::test_missing
            terminalreporter.write_line(f"  [{code}] {nodeid}", red=True)
            if suggestion:
                terminalreporter.write_line(f"         Fix: {suggestion}", cyan=True)

    # Show other (non-Bengal) failures
    if other_failures:
        terminalreporter.write_line("")
        terminalreporter.write_line("  OTHER ERRORS:", bold=True)
        for nodeid, error_type in other_failures:
            terminalreporter.write_line(f"  [----] {nodeid} ({error_type})", red=True)

    # Summary counts
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"  Total: {len(bengal_failures)} Bengal errors, {len(other_failures)} other errors",
        bold=True,
    )
    terminalreporter.write_sep("=", "", bold=True, yellow=True)


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
    - All registered caches are cleared (via cache registry system)
      - Global context cache (prevents memory leaks from Site object IDs)
      - Parser cache (ensures fresh parsers with current directives)
      - Created directories cache (fresh directory tracking per test)
      - Theme cache (ensures fresh theme discovery)

    Cache Registry System:
        Caches register themselves at module import time via
        bengal.utils.cache_registry.register_cache(). This ensures new caches
        are automatically included in test cleanup without manual updates.

    With the LazyLogger pattern, module-level logger references automatically
    refresh when reset_loggers() is called, eliminating orphaned logger issues.

    See: docs/cache-registry-system.md for details on the cache registry system.

    """
    # Setup: Clear all registered caches before test (ensures fresh state)
    # This is done before test to ensure clean state, and again after test for cleanup
    try:
        from bengal.utils.cache_registry import clear_all_caches

        clear_all_caches()
    except ImportError:
        # Fallback to manual cleanup if registry not available
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
        from bengal.utils.observability.rich_console import reset_console

        reset_console()
    except ImportError:
        logger.debug("Rich console reset skipped: reset_console not available")

    # 2. Reset logger state (close file handles, clear registry)
    # LazyLogger pattern ensures module-level references auto-refresh
    try:
        from bengal.utils.observability.logger import reset_loggers

        reset_loggers()
    except ImportError:
        logger.debug("Logger reset skipped: reset_loggers not available")

    # 3. Clear all registered caches (centralized cleanup prevents memory leaks)
    # This automatically clears: global_context_cache, parser_cache, created_dirs_cache
    # and any other caches that register themselves
    try:
        from bengal.utils.cache_registry import clear_all_caches

        clear_all_caches()
    except ImportError:
        logger.debug("Cache registry not available: skipping centralized cache cleanup")
        # Fallback to manual cleanup if registry not available
        try:
            from bengal.rendering.context import clear_global_context_cache
            from bengal.rendering.pipeline.thread_local import get_created_dirs, reset_parser_cache

            get_created_dirs().clear()
            reset_parser_cache()
            clear_global_context_cache()
        except ImportError:
            logger.debug("Manual cache cleanup skipped: modules not available")


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
