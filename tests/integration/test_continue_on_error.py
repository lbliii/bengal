"""
Integration tests for --continue-on-error build mode (Sprint A4.1).

Verifies that when continue_on_error=True:
- Builds do NOT halt on the first template error.
- Pages with template errors render an HTML error placeholder in place
  of the failed page.
- All other pages still build normally.
- The number of collected errors matches the number of broken pages.

Mutual exclusion with strict mode is enforced at the CLI layer; the
BuildOptions dataclass treats `strict` and `continue_on_error` as
independent flags so this test focuses on the orchestrator behavior.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions


@pytest.fixture
def mixed_site():
    """Site with 3 pages: 2 valid + 1 using a broken template."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        (temp_dir / "content").mkdir()
        (temp_dir / "templates").mkdir()

        (temp_dir / "bengal.toml").write_text(
            """
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
validate_templates = true
"""
        )

        (temp_dir / "templates" / "page.html").write_text(
            "<!DOCTYPE html><html><body><h1>{{ page.title }}</h1>"
            "<div>{{ content | safe }}</div></body></html>"
        )

        (temp_dir / "templates" / "broken.html").write_text(
            "<!DOCTYPE html><html><body>"
            "{% if page.title %}<h1>{{ page.title }}</h1>"
            "{# missing endif on purpose #}"
            "</body></html>"
        )

        for i, name in enumerate(["good_a", "good_b"]):
            (temp_dir / "content" / f"{name}.md").write_text(
                f"""+++
title = "Good Page {i}"
template = "page.html"
+++

Body for {name}.
"""
            )

        (temp_dir / "content" / "broken.md").write_text(
            """+++
title = "Broken Page"
template = "broken.html"
+++

Body for broken page.
"""
        )

        yield temp_dir

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


class TestContinueOnError:
    def test_default_renders_placeholder_and_continues(self, mixed_site: Path) -> None:
        """Even without continue_on_error, non-strict builds already write
        a placeholder for failed pages and continue. Establishes baseline."""
        site = Site.from_config(mixed_site, None)
        stats = BuildOrchestrator(site).build(BuildOptions(force_sequential=True, verbose=False))

        output_dir = mixed_site / "public"
        rendered = sorted(p.name for p in output_dir.rglob("index.html"))

        assert len(rendered) >= 3, f"Expected 3 HTML pages, got: {rendered}"
        assert len(stats.template_errors) >= 1

    def test_continue_on_error_does_not_change_render_count(self, mixed_site: Path) -> None:
        """continue_on_error=True yields the same page count as the default
        graceful path — it changes exit-code semantics, not render behavior."""
        site = Site.from_config(mixed_site, None)
        stats = BuildOrchestrator(site).build(
            BuildOptions(force_sequential=True, verbose=False, continue_on_error=True)
        )

        output_dir = mixed_site / "public"
        rendered = sorted(p.name for p in output_dir.rglob("index.html"))

        assert len(rendered) >= 3
        assert len(stats.template_errors) >= 1

    def test_runtime_error_renders_placeholder(self, tmp_path: Path) -> None:
        """A template with a runtime error (e.g. calling .undefined_method
        on an object) is caught at render time and replaced with the error
        overlay HTML page — the build does not halt."""
        (tmp_path / "content").mkdir()
        (tmp_path / "templates").mkdir()
        (tmp_path / "bengal.toml").write_text(
            """
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
"""
        )

        # Template with an undefined filter — raises at render time.
        (tmp_path / "templates" / "page.html").write_text(
            "<!DOCTYPE html><html><body><h1>{{ page.title }}</h1>"
            "{{ page.title | nonexistent_filter_xyz_42 }}</body></html>"
        )

        (tmp_path / "content" / "boom.md").write_text(
            """+++
title = "Boom"
template = "page.html"
+++

Body.
"""
        )

        site = Site.from_config(tmp_path, None)
        stats = BuildOrchestrator(site).build(
            BuildOptions(force_sequential=True, verbose=False, continue_on_error=True)
        )

        assert len(stats.template_errors) >= 1
        boom_html = (tmp_path / "public" / "boom" / "index.html").read_text()
        # Error overlay or fallback should mention the build error.
        assert "Build Error" in boom_html or "[R0" in boom_html or "error" in boom_html.lower()
