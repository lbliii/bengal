"""
Golden file tests for Bengal output verification.

RFC: rfc-behavioral-test-hardening (Phase 2)

Golden tests verify that Bengal produces consistent, expected output.
Unlike unit tests that mock dependencies, these test ACTUAL behavior
by comparing real build output against known-good expected files.

Usage:
    # Run all golden tests
    pytest tests/integration/test_golden_output.py -v

    # Update golden files after intentional changes
    pytest tests/integration/test_golden_output.py --update-golden

    # Run specific scenario
    pytest tests/integration/test_golden_output.py -k simple_site
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Path to golden test scenarios
GOLDEN_DIR = Path(__file__).parent.parent / "golden"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden option to pytest."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden files with current output",
    )


def _normalize_html(html: str) -> str:
    """
    Normalize HTML for comparison, stripping volatile content.

    Removes:
    - Build timestamps
    - Content hashes in asset URLs
    - Excessive whitespace
    - Trailing newlines

    Args:
        html: Raw HTML content

    Returns:
        Normalized HTML string
    """
    # Remove build timestamps
    html = re.sub(r'data-build-time="[^"]*"', 'data-build-time=""', html)
    html = re.sub(r'data-build-timestamp="[^"]*"', 'data-build-timestamp=""', html)
    html = re.sub(r'data-generated="[^"]*"', 'data-generated=""', html)

    # Remove content hashes in asset URLs (e.g., main.a1b2c3d4.css -> main.HASH.css)
    html = re.sub(r"\.[a-f0-9]{8,}\.(css|js)", ".HASH.\\1", html)

    # Normalize line endings
    html = html.replace("\r\n", "\n")

    # Strip trailing whitespace from lines
    html = "\n".join(line.rstrip() for line in html.split("\n"))

    # Remove multiple blank lines (keep at most one)
    html = re.sub(r"\n{3,}", "\n\n", html)

    # Strip leading/trailing whitespace
    html = html.strip()

    return html


def _get_golden_scenarios() -> list[str]:
    """Get list of available golden test scenarios."""
    if not GOLDEN_DIR.exists():
        return []
    return [d.name for d in GOLDEN_DIR.iterdir() if d.is_dir() and (d / "input").exists()]


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    """Fixture to check if --update-golden flag was passed."""
    return request.config.getoption("--update-golden", default=False)


class TestGoldenOutput:
    """Golden file tests for Bengal build output."""

    @pytest.fixture
    def golden_site(
        self,
        tmp_path: Path,
        request: pytest.FixtureRequest,
    ) -> Generator[tuple[Path, Path, Path], None, None]:
        """
        Set up a golden test site.

        Copies input files to tmp_path, builds the site, and yields paths.

        Yields:
            Tuple of (site_dir, output_dir, expected_dir)
        """
        scenario = request.param
        golden_scenario_dir = GOLDEN_DIR / scenario
        input_dir = golden_scenario_dir / "input"
        expected_dir = golden_scenario_dir / "expected"

        # Copy input to temp directory
        site_dir = tmp_path / "site"
        shutil.copytree(input_dir, site_dir)

        # Build the site
        from bengal.core.site import Site
        from bengal.orchestration.build.options import BuildOptions

        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()

        options = BuildOptions(incremental=False, quiet=True)
        site.build(options=options)

        yield site_dir, site.output_dir, expected_dir

    @pytest.mark.parametrize(
        "golden_site",
        _get_golden_scenarios(),
        indirect=True,
    )
    def test_golden_output(
        self,
        golden_site: tuple[Path, Path, Path],
        update_golden: bool,
    ) -> None:
        """
        Verify build output matches expected golden files.

        For each file in expected/, compare against the actual build output.
        Use --update-golden to regenerate expected files.
        """
        _site_dir, output_dir, expected_dir = golden_site

        if update_golden:
            self._update_expected_files(output_dir, expected_dir)
            pytest.skip("Golden files updated")

        if not expected_dir.exists():
            pytest.skip(
                f"No expected/ directory for this scenario. Run with --update-golden to generate."
            )

        mismatches = []
        missing = []

        for expected_file in expected_dir.rglob("*"):
            if expected_file.is_dir():
                continue

            rel_path = expected_file.relative_to(expected_dir)
            actual_file = output_dir / rel_path

            if not actual_file.exists():
                missing.append(str(rel_path))
                continue

            # Normalize and compare
            expected_content = _normalize_html(expected_file.read_text(encoding="utf-8"))
            actual_content = _normalize_html(actual_file.read_text(encoding="utf-8"))

            if expected_content != actual_content:
                mismatches.append(
                    {
                        "file": str(rel_path),
                        "expected_preview": expected_content[:200],
                        "actual_preview": actual_content[:200],
                    }
                )

        # Report errors
        error_msg = []
        if missing:
            error_msg.append(f"Missing files: {missing}")
        if mismatches:
            error_msg.append(f"Mismatched files ({len(mismatches)}):")
            for m in mismatches[:3]:  # Show first 3
                error_msg.append(f"  - {m['file']}")
                error_msg.append(f"    Expected: {m['expected_preview'][:100]}...")
                error_msg.append(f"    Actual:   {m['actual_preview'][:100]}...")

        assert not missing and not mismatches, "\n".join(error_msg)

    def _update_expected_files(
        self,
        output_dir: Path,
        expected_dir: Path,
    ) -> None:
        """
        Update expected files from current output.

        Args:
            output_dir: Path to build output
            expected_dir: Path to expected directory
        """
        # Create expected directory if needed
        expected_dir.mkdir(parents=True, exist_ok=True)

        # Copy HTML files (the main output we care about)
        for html_file in output_dir.rglob("*.html"):
            rel_path = html_file.relative_to(output_dir)
            target_file = expected_dir / rel_path

            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Normalize before saving
            content = _normalize_html(html_file.read_text(encoding="utf-8"))
            target_file.write_text(content, encoding="utf-8")

        print(f"Updated golden files in {expected_dir}")


class TestGoldenInfrastructure:
    """Tests for the golden file infrastructure itself."""

    def test_normalize_removes_timestamps(self) -> None:
        """Normalization removes build timestamps."""
        html = '<div data-build-time="2024-01-01T00:00:00">Content</div>'
        normalized = _normalize_html(html)
        assert 'data-build-time=""' in normalized
        assert "2024-01-01" not in normalized

    def test_normalize_removes_hashes(self) -> None:
        """Normalization removes content hashes."""
        html = '<link href="main.a1b2c3d4.css">'
        normalized = _normalize_html(html)
        assert "main.HASH.css" in normalized
        assert "a1b2c3d4" not in normalized

    def test_normalize_preserves_structure(self) -> None:
        """Normalization preserves HTML structure."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Hello</h1>
        </body>
        </html>
        """
        normalized = _normalize_html(html)
        assert "<title>Test</title>" in normalized
        assert "<h1>Hello</h1>" in normalized

    def test_golden_scenarios_exist(self) -> None:
        """At least one golden scenario exists."""
        scenarios = _get_golden_scenarios()
        assert len(scenarios) >= 1, (
            f"No golden scenarios found in {GOLDEN_DIR}. "
            f"Create tests/golden/simple_site/input/ directory."
        )
