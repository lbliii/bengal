"""
Global pytest configuration and fixtures.

This file provides:
- Shared fixtures for all tests
- Pytest hooks for better debugging
- Automatic test output capture
"""

from datetime import datetime
from pathlib import Path

import pytest

# ============================================================================
# COLLECTION HOOKS
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items to filter out non-test functions.

    This prevents pytest from collecting functions like test_draft() from
    bengal/rendering/template_tests.py which are Jinja2 template tests,
    not pytest tests.
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
