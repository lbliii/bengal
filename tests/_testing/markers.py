"""
Custom pytest markers for Bengal test suite.

Provides:
- @pytest.mark.bengal: Works with site_factory fixture to set up test sites
- @pytest.mark.needs_hardening: Mark tests that need behavioral assertion refactoring

Usage:
    @pytest.mark.bengal(testroot="test-basic")
    def test_something(site):
        # 'site' will be automatically created from test-basic root
        assert site.pages

    @pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/custom"})
    def test_with_overrides(site):
        # 'site' will have custom baseurl
        assert site.baseurl == "/custom"

    @pytest.mark.needs_hardening
    def test_uses_mocks():
        # TODO: Replace mock verification with behavioral assertions
        ...

RFC: rfc-behavioral-test-hardening
"""

import shutil
import tomllib

import pytest
import tomli_w

from bengal.orchestration.build.options import BuildOptions


def pytest_configure(config):
    """Register custom markers."""
    # Bengal test root marker
    config.addinivalue_line(
        "markers",
        "bengal(testroot, confoverrides): "
        "Mark test to use Bengal test root infrastructure. "
        "Requires 'site' fixture parameter in test function.",
    )

    # Test hardening marker (RFC: rfc-behavioral-test-hardening)
    config.addinivalue_line(
        "markers",
        "needs_hardening: "
        "Mark test as needing refactoring from mock-based to behavioral assertions. "
        "Track progress with: pytest --collect-only -m needs_hardening | wc -l",
    )


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
                f"@pytest.mark.bengal requires 'testroot' parameter. Test: {request.node.nodeid}"
            )

        return site_factory(testroot, confoverrides=confoverrides)

    # If no bengal marker, this fixture doesn't apply
    # (test should be using site_factory directly or another approach)
    raise pytest.UsageError(
        f"Test {request.node.nodeid} uses 'site' fixture but has no @pytest.mark.bengal marker. "
        "Either add the marker or use site_factory directly."
    )


@pytest.fixture(scope="class")
def built_site(request, tmp_path_factory, rootdir):
    """
    Class-scoped built site for read-only integration tests.

    Creates, discovers, and builds the site ONCE per test class.
    Use this instead of site + build_site() for tests that only read output.

    Tests using this fixture must NOT modify the site or its files.

    """
    from bengal.core.site import Site

    bengal_marker = request.node.get_closest_marker("bengal")
    if not bengal_marker:
        raise pytest.UsageError(
            f"Test {request.node.nodeid} uses 'built_site' fixture but has no "
            "@pytest.mark.bengal marker."
        )

    testroot = bengal_marker.kwargs.get("testroot")
    confoverrides = bengal_marker.kwargs.get("confoverrides")

    if not testroot:
        raise ValueError(
            f"@pytest.mark.bengal requires 'testroot' parameter. Test: {request.node.nodeid}"
        )

    root_path = rootdir / testroot
    if not root_path.exists():
        available = [p.name for p in rootdir.iterdir() if p.is_dir()]
        raise ValueError(
            f"Test root '{testroot}' not found. Available roots: {', '.join(available)}"
        )

    site_dir = tmp_path_factory.mktemp(f"built_{testroot}")

    # Check if skeleton manifest exists
    skeleton_manifest = root_path / "skeleton.yaml"
    if skeleton_manifest.exists():
        from bengal.cli.skeleton.hydrator import Hydrator
        from bengal.cli.skeleton.schema import Skeleton

        skeleton = Skeleton.from_yaml(skeleton_manifest.read_text())
        content_dir = site_dir / "content"
        content_dir.mkdir()

        hydrator = Hydrator(content_dir, dry_run=False, force=True)
        hydrator.apply(skeleton)

        for item in root_path.iterdir():
            if item.name not in ("skeleton.yaml", "content"):
                if item.is_file():
                    shutil.copy2(item, site_dir / item.name)
                elif item.is_dir() and item.name != "public":
                    shutil.copytree(item, site_dir / item.name, dirs_exist_ok=True)
    else:
        shutil.copytree(root_path, site_dir, dirs_exist_ok=True)

    # Apply config overrides
    if confoverrides:
        config_path = site_dir / "bengal.toml"
        if config_path.exists():
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            for key, value in confoverrides.items():
                if "." in key:
                    section, subkey = key.split(".", 1)
                    if section not in config:
                        config[section] = {}
                    config[section][subkey] = value
                else:
                    config[key] = value

            with open(config_path, "wb") as f:
                tomli_w.dump(config, f)

    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()
    site.build(BuildOptions(force_sequential=True))

    return site
