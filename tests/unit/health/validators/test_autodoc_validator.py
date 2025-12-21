"""
Unit tests for AutodocValidator.

Tests that autodoc HTML page generation is validated correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.health.validators.autodoc import AutodocValidator


@pytest.fixture
def autodoc_validator() -> AutodocValidator:
    """Create an AutodocValidator instance."""
    return AutodocValidator()


@pytest.fixture
def minimal_site(tmp_path: Path):
    """Create a minimal site with autodoc config."""
    from bengal.core.site import Site

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n# Home")

    config_dir = tmp_path / "config" / "_default"
    config_dir.mkdir(parents=True)
    (config_dir / "site.yaml").write_text(
        """
site:
  title: Test Site
  baseurl: ""
"""
    )
    (config_dir / "autodoc.yaml").write_text(
        """
autodoc:
  python:
    enabled: true
    source_dirs:
      - ../mypackage
    output_prefix: api/mypackage
  cli:
    enabled: true
    app_path: mypackage.cli:app
    output_prefix: cli
"""
    )

    # Create output directory
    output_dir = tmp_path / "public"
    output_dir.mkdir()

    return Site.from_config(tmp_path)


class TestAutodocValidatorHTMLParity:
    """Tests for HTML/TXT parity checking."""

    def test_passes_when_html_and_txt_match(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """Validator passes when HTML and TXT counts match."""
        output_dir = minimal_site.output_dir

        # Create matching HTML and TXT files
        api_dir = output_dir / "api" / "mypackage" / "core"
        api_dir.mkdir(parents=True)
        (api_dir / "index.html").write_text("<!DOCTYPE html><html></html>")
        (api_dir / "index.txt").write_text("# core")

        results = autodoc_validator.validate(minimal_site)

        # Should have no errors related to parity
        parity_errors = [r for r in results if "no HTML" in r.message]
        assert len(parity_errors) == 0

    def test_fails_when_txt_has_no_html(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """Validator fails when TXT file has no corresponding HTML."""
        output_dir = minimal_site.output_dir

        # Create TXT without HTML
        api_dir = output_dir / "api" / "mypackage" / "core"
        api_dir.mkdir(parents=True)
        (api_dir / "index.txt").write_text("# core")
        # No index.html!

        results = autodoc_validator.validate(minimal_site)

        # Should have error about missing HTML
        assert any("no HTML" in r.message or "missing" in r.message.lower() for r in results)


class TestAutodocValidatorMissingHTML:
    """Tests for missing HTML detection."""

    def test_passes_when_all_dirs_have_html(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """Validator passes when all directories have index.html."""
        output_dir = minimal_site.output_dir

        # Create full structure
        for path in [
            "api/mypackage",
            "api/mypackage/core",
            "api/mypackage/core/page",
            "cli",
            "cli/build",
        ]:
            dir_path = output_dir / path
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / "index.html").write_text("<!DOCTYPE html><html></html>")

        results = autodoc_validator.validate(minimal_site)

        # Should have no errors about missing HTML
        missing_errors = [r for r in results if "missing" in r.message.lower()]
        assert len(missing_errors) == 0

    def test_fails_when_dir_missing_html(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """Validator fails when a directory is missing index.html."""
        output_dir = minimal_site.output_dir

        # Create structure with missing HTML
        api_dir = output_dir / "api" / "mypackage"
        api_dir.mkdir(parents=True)
        (api_dir / "index.html").write_text("<!DOCTYPE html><html></html>")

        # Subdirectory missing HTML
        core_dir = api_dir / "core"
        core_dir.mkdir()
        # No index.html in core!

        results = autodoc_validator.validate(minimal_site)

        # Should have error about missing HTML
        missing_errors = [r for r in results if "missing" in r.message.lower()]
        assert len(missing_errors) > 0


class TestAutodocValidatorPageTypes:
    """Tests for page type validation."""

    def test_passes_with_correct_page_type(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """Validator passes when page has correct data-type."""
        output_dir = minimal_site.output_dir

        # Create page with correct type
        api_dir = output_dir / "api" / "mypackage"
        api_dir.mkdir(parents=True)
        (api_dir / "index.html").write_text(
            '<!DOCTYPE html><html><body data-type="autodoc-python"></body></html>'
        )

        results = autodoc_validator.validate(minimal_site)

        # Should have no type mismatch warnings
        type_warnings = [r for r in results if "wrong type" in r.message.lower()]
        assert len(type_warnings) == 0

    def test_warns_with_wrong_page_type(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """Validator warns when page has wrong data-type."""
        output_dir = minimal_site.output_dir

        # Create page with wrong type
        api_dir = output_dir / "api" / "mypackage"
        api_dir.mkdir(parents=True)
        (api_dir / "index.html").write_text(
            '<!DOCTYPE html><html><body data-type="autodoc-cli"></body></html>'
        )

        results = autodoc_validator.validate(minimal_site)

        # Should have type mismatch warning
        type_warnings = [r for r in results if "wrong type" in r.message.lower()]
        assert len(type_warnings) > 0

    def test_cli_pages_expect_autodoc_cli(
        self, autodoc_validator: AutodocValidator, minimal_site
    ) -> None:
        """CLI pages should have data-type='autodoc-cli'."""
        output_dir = minimal_site.output_dir

        # Create CLI page with correct type
        cli_dir = output_dir / "cli" / "build"
        cli_dir.mkdir(parents=True)
        (cli_dir / "index.html").write_text(
            '<!DOCTYPE html><html><body data-type="autodoc-cli"></body></html>'
        )

        results = autodoc_validator.validate(minimal_site)

        # Should have no type mismatch warnings for CLI
        cli_warnings = [
            r for r in results if "cli" in r.message.lower() and "wrong type" in r.message.lower()
        ]
        assert len(cli_warnings) == 0


class TestAutodocValidatorStats:
    """Tests for validator stats/observability."""

    def test_populates_last_stats(self, autodoc_validator: AutodocValidator, minimal_site) -> None:
        """Validator populates last_stats after validation."""
        output_dir = minimal_site.output_dir

        # Create minimal structure
        api_dir = output_dir / "api" / "mypackage"
        api_dir.mkdir(parents=True)
        (api_dir / "index.html").write_text("<!DOCTYPE html><html></html>")

        autodoc_validator.validate(minimal_site)

        assert autodoc_validator.last_stats is not None
        assert "html_parity" in autodoc_validator.last_stats.sub_timings
        assert "missing_html" in autodoc_validator.last_stats.sub_timings
        assert "page_types" in autodoc_validator.last_stats.sub_timings


class TestAutodocValidatorDisabled:
    """Tests when autodoc is disabled."""

    def test_returns_empty_when_no_autodoc_config(
        self, autodoc_validator: AutodocValidator, tmp_path: Path
    ) -> None:
        """Validator returns empty results when autodoc not configured."""
        from bengal.core.site import Site

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("---\ntitle: Home\n---\n")

        config_dir = tmp_path / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "site.yaml").write_text("site:\n  title: Test\n")
        # No autodoc.yaml!

        site = Site.from_config(tmp_path)
        results = autodoc_validator.validate(site)

        assert results == []
