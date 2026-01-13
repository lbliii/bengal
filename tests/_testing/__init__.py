"""
Testing utilities for Bengal test suite.

This package provides shared fixtures, markers, mocks, and utilities to make
writing tests easier and more consistent.

Usage in conftest.py:
    pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers"]

Mock Objects:
from tests._testing.mocks import MockPage, MockSection, MockSite

    page = MockPage(title="Test", href="/test/")
    site = MockSite(pages=[page])

Progress Reporting:
For long-running tests, use the test_progress fixture:

    def test_long_running(test_progress):
        with test_progress.phase("Processing", total=100) as update:
            for i in range(100):
                do_work()
                update(i + 1)

"""

from tests._testing.mocks import (
    MockPage,
    MockSection,
    MockSite,
    create_mock_xref_index,
)
from tests._testing.progress import (
    TestProgressReporter,
    create_test_progress,
    progress_status,
    test_status,  # Deprecated, kept for backward compatibility
)

__version__ = "1.1.0"

__all__ = [
    # Mock objects
    "MockPage",
    "MockSection",
    "MockSite",
    "create_mock_xref_index",
    # Progress reporting
    "TestProgressReporter",
    "create_test_progress",
    "progress_status",
    "test_status",  # Deprecated
]
