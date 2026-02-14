"""
Testing utilities for Bengal test suite.

This package provides shared fixtures, markers, mocks, assertions, and utilities
to make writing tests easier and more consistent.

Usage in conftest.py:
    pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers"]

Mock Objects:
    from tests._testing.mocks import MockPage, MockSection, MockSite

    page = MockPage(title="Test", href="/test/")
    site = MockSite(pages=[page])

Behavioral Assertions (RFC: rfc-behavioral-test-hardening):
    from tests._testing.assertions import (
        assert_page_rendered,
        assert_build_idempotent,
        assert_all_pages_have_urls,
    )

    # Verify OUTCOMES, not implementation details
    site.build()
    assert_page_rendered(site.output_dir, "index.html", contains=["<h1>"])

Progress Reporting:
    For long-running tests, use the test_progress fixture:

    def test_long_running(test_progress):
        with test_progress.phase("Processing", total=100) as update:
            for i in range(100):
                do_work()
                update(i + 1)

"""

from tests._testing.assertions import (
    assert_all_pages_have_urls,
    assert_build_idempotent,
    assert_changed_file_rebuilt,
    assert_incremental_equivalent,
    assert_menu_structure,
    assert_no_broken_internal_links,
    assert_output_files_exist,
    assert_page_contains,
    assert_page_rendered,
    assert_pages_have_required_metadata,
    assert_taxonomy_pages_complete,
    assert_unchanged_files_not_rebuilt,
)
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

__version__ = "1.2.0"

__all__ = [
    # Mock objects
    "MockPage",
    "MockSection",
    "MockSite",
    # Progress reporting
    "TestProgressReporter",
    "assert_all_pages_have_urls",
    "assert_build_idempotent",
    "assert_changed_file_rebuilt",
    "assert_incremental_equivalent",
    "assert_menu_structure",
    "assert_no_broken_internal_links",
    "assert_output_files_exist",
    "assert_page_contains",
    # Behavioral assertions (Phase 1 of test hardening)
    "assert_page_rendered",
    "assert_pages_have_required_metadata",
    "assert_taxonomy_pages_complete",
    "assert_unchanged_files_not_rebuilt",
    "create_mock_xref_index",
    "create_test_progress",
    "progress_status",
    "test_status",  # Deprecated
]
