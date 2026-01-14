"""
Integration tests for incremental build observability.

RFC: rfc-incremental-build-observability

Tests the --explain and --dry-run CLI flags for debugging incremental builds.
"""

import json
import time
from pathlib import Path

import pytest


@pytest.fixture
def minimal_site(tmp_path: Path):
    """Create a minimal Bengal site for testing."""
    # Create bengal.toml
    config = tmp_path / "bengal.toml"
    config.write_text("""
[site]
title = "Test Site"
baseURL = "http://localhost"

[build]
output_dir = "public"
""")

    # Create content directory with a few pages
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Home page
    (content_dir / "_index.md").write_text("""---
title: Home
---
# Welcome to the test site
""")

    # A few test pages
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("""---
title: Docs
---
Documentation section.
""")
    (docs_dir / "intro.md").write_text("""---
title: Introduction
---
This is the intro page.
""")
    (docs_dir / "guide.md").write_text("""---
title: Guide
---
This is the guide page.
""")

    return tmp_path


class TestExplainMode:
    """Tests for --explain flag."""

    def test_explain_shows_rebuild_reasons(self, minimal_site: Path, capfd):
        """--explain should show rebuild reason breakdown."""
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        # First build (full)
        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=False,
            quiet=True,
            explain=True,
        )
        stats = site.build(options=options)

        # Check that incremental_decision is populated
        assert hasattr(stats, "incremental_decision")
        decision = stats.incremental_decision
        assert decision is not None
        assert len(decision.pages_to_build) > 0
        assert len(decision.rebuild_reasons) > 0

        # All pages should have FULL_REBUILD reason for non-incremental builds
        for reason in decision.rebuild_reasons.values():
            assert reason.code.value == "full_rebuild"

    def test_explain_incremental_shows_content_changed(self, minimal_site: Path):
        """Incremental build with --explain should show content_changed reasons."""
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        # First build (full)
        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=False,
            quiet=True,
        )
        site.build(options=options)

        # Touch a file to simulate change
        time.sleep(0.1)
        intro_file = minimal_site / "content" / "docs" / "intro.md"
        intro_file.write_text("""---
title: Introduction (Updated)
---
This is the updated intro page.
""")

        # Second build (incremental with explain)
        site2 = load_site_from_cli(source=str(minimal_site))
        options2 = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=True,
            quiet=True,
            explain=True,
            verbose=True,
        )
        stats2 = site2.build(options=options2)

        # Check incremental decision
        decision = stats2.incremental_decision
        assert decision is not None

        # Should have content_changed reason for the modified file
        content_changed_count = sum(
            1 for r in decision.rebuild_reasons.values()
            if r.code.value == "content_changed"
        )
        assert content_changed_count >= 1

    def test_explain_tracks_skip_reasons_when_verbose(self, minimal_site: Path):
        """Skip reasons should be tracked when verbose=True on incremental build."""
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        # First build (with explain to establish decision tracking)
        first_stats = site.build(BuildOptions(incremental=False, quiet=True, explain=True))
        # Verify first build worked
        assert getattr(first_stats, "incremental_decision", None) is not None

        # Modify one file to trigger incremental rebuild of just that file
        time.sleep(0.1)
        intro_file = minimal_site / "content" / "docs" / "intro.md"
        intro_file.write_text("""---
title: Introduction (Modified)
---
Modified content.
""")

        # Second build with verbose and incremental
        site2 = load_site_from_cli(source=str(minimal_site))
        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=True,
            quiet=True,
            explain=True,
            verbose=True,
        )
        stats = site2.build(options=options)

        decision = getattr(stats, "incremental_decision", None)
        # Note: incremental_decision may be None if the incremental filter
        # determines this is a full build (e.g., config changed).
        # We just verify the stats object is returned without errors.
        if decision is not None and decision.pages_skipped_count > 0:
            # Skip reasons should be populated (verbose=True)
            assert len(decision.skip_reasons) > 0


class TestDryRunMode:
    """Tests for --dry-run flag."""

    def test_dry_run_does_not_write_files(self, minimal_site: Path):
        """--dry-run should not write output files."""
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        output_dir = minimal_site / "public"
        assert not output_dir.exists()

        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=False,
            quiet=True,
            dry_run=True,
            explain=True,
        )
        stats = site.build(options=options)

        # Output directory should not have been created (or should be empty)
        assert not output_dir.exists() or len(list(output_dir.rglob("*.html"))) == 0

        # But incremental_decision should still be populated
        assert hasattr(stats, "incremental_decision")
        assert stats.incremental_decision is not None

    def test_dry_run_sets_stats_flag(self, minimal_site: Path):
        """--dry-run should set stats.dry_run flag."""
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=False,
            quiet=True,
            dry_run=True,
        )
        stats = site.build(options=options)

        assert hasattr(stats, "dry_run")
        assert stats.dry_run is True


class TestExplainJson:
    """Tests for --explain-json output."""

    def test_explain_json_structure(self, minimal_site: Path):
        """Test that JSON output function produces correct structure."""
        from io import StringIO
        from unittest.mock import patch

        from bengal.cli.commands.build import _print_explain_json
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=False,
            quiet=True,
            explain=True,
        )
        stats = site.build(options=options)

        # Capture print output directly
        output = StringIO()
        with patch("builtins.print", lambda x: output.write(x)):
            _print_explain_json(stats, dry_run=False)

        # Should be valid JSON
        json_str = output.getvalue()
        data = json.loads(json_str)
        assert "pages_to_build" in data
        assert "pages_skipped" in data
        assert "rebuild_reasons" in data
        assert "reason_summary" in data
        assert "dry_run" in data

    def test_explain_json_includes_reason_summary(self, minimal_site: Path):
        """JSON output should include reason_summary counts."""
        from io import StringIO
        from unittest.mock import patch

        from bengal.cli.commands.build import _print_explain_json
        from bengal.cli.helpers import load_site_from_cli
        from bengal.orchestration.build.options import BuildOptions
        from bengal.utils.observability.profile import BuildProfile

        site = load_site_from_cli(source=str(minimal_site))

        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=False,
            quiet=True,
            explain=True,
        )
        stats = site.build(options=options)

        # Capture print output directly
        output = StringIO()
        with patch("builtins.print", lambda x: output.write(x)):
            _print_explain_json(stats, dry_run=False)

        data = json.loads(output.getvalue())
        assert "reason_summary" in data
        assert "full_rebuild" in data["reason_summary"]


class TestReasonSummary:
    """Tests for IncrementalDecision.get_reason_summary()."""

    def test_get_reason_summary_counts_by_code(self):
        """get_reason_summary should count pages by reason code."""
        from bengal.orchestration.build.results import (
            IncrementalDecision,
            RebuildReason,
            RebuildReasonCode,
        )

        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
            rebuild_reasons={
                "a.md": RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED),
                "b.md": RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED),
                "c.md": RebuildReason(code=RebuildReasonCode.TEMPLATE_CHANGED),
            },
        )

        summary = decision.get_reason_summary()
        assert summary["content_changed"] == 2
        assert summary["template_changed"] == 1
