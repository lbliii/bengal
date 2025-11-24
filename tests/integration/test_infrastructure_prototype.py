"""
Prototype test to validate Phase 1 infrastructure.

This test demonstrates and validates the new testing utilities:
- @pytest.mark.bengal marker
- site_factory fixture
- Test roots
- build_site helper
"""

import pytest


class TestInfrastructurePrototype:
    """Prototype tests using Phase 1 infrastructure."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_basic_root_with_marker(self, site, build_site):
        """Test using @pytest.mark.bengal with test-basic root."""
        # Site should be pre-configured from test-basic root
        assert site is not None
        # Use site.title property (config is nested: config["site"]["title"])
        assert site.title == "Test Site"

        # Build the site
        build_site()

        # Verify basic assertions
        assert len(site.pages) == 1
        assert (site.output_dir / "index.html").exists()

    @pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/custom"})
    def test_config_overrides(self, site):
        """Test config overrides with @pytest.mark.bengal."""
        # Override should be applied
        assert site.baseurl == "/custom"
        # Original test-baseurl had baseurl="/site"
        assert site.title == "Baseurl Test Site"

    def test_site_factory_direct(self, site_factory):
        """Test using site_factory directly without marker."""
        # Create site from test-taxonomy root
        site = site_factory("test-taxonomy")

        assert site is not None
        assert site.title == "Taxonomy Test Site"
        # Note: 3 content pages, but build() generates additional tag list pages
        assert len(site.pages) == 3  # post1, post2, post3

    def test_site_factory_with_overrides(self, site_factory):
        """Test site_factory with config overrides."""
        site = site_factory("test-basic", confoverrides={"site.title": "Overridden Title"})

        assert site.title == "Overridden Title"

    @pytest.mark.bengal(testroot="test-taxonomy")
    def test_taxonomy_root(self, site, build_site):
        """Test taxonomy root builds tags correctly."""
        # Before build: 3 content pages
        assert len(site.pages) == 3

        build_site()

        # After build: 3 content pages + 3 generated tag pages = 6 total
        # (tags/index, tags/python/index, tags/testing/index)
        assert len(site.pages) == 6

        # Tag pages should be generated
        assert (site.output_dir / "tags").exists()
        assert (site.output_dir / "tags" / "python" / "index.html").exists()
        assert (site.output_dir / "tags" / "testing" / "index.html").exists()


class TestCLIUtilities:
    """Test CLI utilities."""

    def test_cli_import(self):
        """Test that CLI utilities can be imported."""
        from tests._testing.cli import run_cli, strip_ansi

        assert callable(run_cli)
        # Test ANSI stripping with actual escape codes
        assert strip_ansi("\x1b[31mRed\x1b[0m") == "Red"

    def test_cli_result_assertions(self):
        """Test CLIResult assertion methods."""
        from tests._testing.cli import CLIResult

        # Success case
        result = CLIResult(returncode=0, stdout="output", stderr="")
        result.assert_ok()  # Should not raise
        result.assert_stdout_contains("output")

        # Failure case
        result_fail = CLIResult(returncode=1, stdout="", stderr="error")
        result_fail.assert_fail_with()  # Should not raise
        result_fail.assert_stderr_contains("error")


class TestNormalizeUtilities:
    """Test normalization utilities."""

    def test_normalize_html(self):
        """Test HTML normalization."""
        from tests._testing.normalize import normalize_html

        html = '<link href="/assets/css/style.abc123def.css" />'
        normalized = normalize_html(html)

        # Hash should be replaced
        assert ".HASH." in normalized
        assert "abc123def" not in normalized

    def test_normalize_json(self):
        """Test JSON normalization."""
        from tests._testing.normalize import normalize_json

        data = {
            "z_key": "value",
            "a_key": "value",
            "build_time": "2024-01-01",  # Should be stripped
        }

        normalized = normalize_json(data)

        # Should be sorted
        keys = list(normalized.keys())
        assert keys == ["a_key", "z_key"]

        # Volatile key should be removed
        assert "build_time" not in normalized


class TestRootdir:
    """Test rootdir fixture."""

    def test_rootdir_exists(self, rootdir):
        """Test that rootdir fixture works."""
        assert rootdir.exists()
        assert rootdir.name == "roots"

        # Should contain our test roots
        roots = [p.name for p in rootdir.iterdir() if p.is_dir()]
        assert "test-basic" in roots
        assert "test-baseurl" in roots
        assert "test-taxonomy" in roots
        assert "test-templates" in roots
        assert "test-assets" in roots
