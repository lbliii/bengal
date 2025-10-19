"""
Custom pytest markers for Bengal test suite.

Provides @pytest.mark.bengal marker that works with site_factory fixture
to automatically set up test sites from test roots.

Usage:
    @pytest.mark.bengal(testroot="test-basic")
    def test_something(site):
        # 'site' will be automatically created from test-basic root
        assert site.pages

    @pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/custom"})
    def test_with_overrides(site):
        # 'site' will have custom baseurl
        assert site.config["site"]["baseurl"] == "/custom"
"""

import pytest


def pytest_configure(config):
    """Register the bengal marker."""
    config.addinivalue_line(
        "markers",
        "bengal(testroot, confoverrides): "
        "Mark test to use Bengal test root infrastructure. "
        "Requires 'site' fixture parameter in test function.",
    )


def pytest_generate_tests(metafunc):
    """
    Hook to provide 'site' fixture for tests marked with @pytest.mark.bengal.

    This is called during test collection for each test function.
    If the test has the bengal marker, we ensure the site fixture is available.
    """
    bengal_marker = metafunc.definition.get_closest_marker("bengal")

    if bengal_marker and "site" in metafunc.fixturenames:
        # Extract marker parameters
        testroot = bengal_marker.kwargs.get("testroot")
        confoverrides = bengal_marker.kwargs.get("confoverrides")

        if not testroot:
            raise ValueError(
                f"@pytest.mark.bengal requires 'testroot' parameter. "
                f"Test: {metafunc.function.__name__}"
            )

        # Store marker params as attributes on the test
        # The site fixture in conftest.py will read these
        metafunc.definition._bengal_testroot = testroot
        metafunc.definition._bengal_confoverrides = confoverrides


@pytest.fixture
def site(request, site_factory):
    """
    Provide 'site' fixture for tests marked with @pytest.mark.bengal.

    This fixture reads the marker parameters and uses site_factory
    to create the appropriate Site instance.

    Note: This is automatically available for all tests, but only
    does something when the test has @pytest.mark.bengal.
    """
    # Check if test has bengal marker data
    bengal_marker = request.node.get_closest_marker("bengal")

    if bengal_marker:
        testroot = bengal_marker.kwargs.get("testroot")
        confoverrides = bengal_marker.kwargs.get("confoverrides")

        if not testroot:
            raise ValueError(
                f"@pytest.mark.bengal requires 'testroot' parameter. "
                f"Test: {request.node.nodeid}"
            )

        return site_factory(testroot, confoverrides=confoverrides)

    # If no bengal marker, this fixture doesn't apply
    # (test should be using site_factory directly or another approach)
    raise pytest.UsageError(
        f"Test {request.node.nodeid} uses 'site' fixture but has no @pytest.mark.bengal marker. "
        "Either add the marker or use site_factory directly."
    )
