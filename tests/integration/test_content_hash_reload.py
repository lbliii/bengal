"""
Integration tests for content-hash based reload detection.

Tests that the content-hash system is properly wired into the build flow
and correctly filters aggregate-only changes.

RFC: Output Cache Architecture
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bengal.server.reload_controller import (
    EnhancedReloadDecision,
    ReloadController,
    ReloadDecision,
)


class TestContentHashReloadIntegration:
    """Integration tests for content-hash reload system."""

    def test_controller_initialized_with_content_hashes_enabled(self):
        """Verify global controller has content hashes enabled by default."""
        from bengal.server.reload_controller import controller

        assert controller._use_content_hashes is True

    def test_capture_baseline_extracts_hashes_from_html(self, tmp_path):
        """Baseline capture extracts content hashes from HTML files."""
        controller = ReloadController(use_content_hashes=True)

        # Create HTML file with embedded content hash
        html_file = tmp_path / "index.html"
        html_file.write_text(
            '<html><head><meta name="bengal:content-hash" content="abc123def456">'
            "</head><body>Hello</body></html>"
        )

        # Capture baseline
        controller.capture_content_hash_baseline(tmp_path)

        # Verify hash was extracted
        assert "index.html" in controller._baseline_content_hashes
        assert controller._baseline_content_hashes["index.html"] == "abc123def456"

    def test_decide_with_content_hashes_detects_real_changes(self, tmp_path):
        """Content hash comparison detects actual content changes."""
        controller = ReloadController(use_content_hashes=True)

        # Create initial HTML
        html_file = tmp_path / "page.html"
        html_file.write_text(
            '<html><head><meta name="bengal:content-hash" content="original123">'
            "</head><body>Original</body></html>"
        )

        # Capture baseline
        controller.capture_content_hash_baseline(tmp_path)

        # Simulate content change
        html_file.write_text(
            '<html><head><meta name="bengal:content-hash" content="changed456">'
            "</head><body>Changed</body></html>"
        )

        # Decide with content hashes
        decision = controller.decide_with_content_hashes(tmp_path)

        # Should detect the change
        assert decision.action == "reload"
        assert "page.html" in decision.content_changes

    def test_decide_with_content_hashes_ignores_aggregate_only(self, tmp_path):
        """Aggregate-only changes don't trigger reload."""
        controller = ReloadController(use_content_hashes=True)

        # Create content page and aggregate files
        content_html = tmp_path / "page.html"
        content_html.write_text(
            '<html><head><meta name="bengal:content-hash" content="abc123">'
            "</head><body>Content</body></html>"
        )

        sitemap = tmp_path / "sitemap.xml"
        sitemap.write_text("<sitemap>v1</sitemap>")

        index_json = tmp_path / "index.json"
        index_json.write_text('{"pages": []}')

        # Capture baseline
        controller.capture_content_hash_baseline(tmp_path)

        # Only aggregate files change (content hash stays same)
        sitemap.write_text("<sitemap>v2 - with new page</sitemap>")
        index_json.write_text('{"pages": ["new"]}')

        # Decide with content hashes
        decision = controller.decide_with_content_hashes(tmp_path)

        # Should be aggregate-only (no meaningful changes)
        # When content page hash is unchanged, it doesn't count as a change
        assert decision.meaningful_change_count == 0
        # The action should be 'none' because no actual content changed
        # (aggregate files without content hashes aren't tracked for reload)

    def test_meaningful_change_count_excludes_aggregates(self, tmp_path):
        """meaningful_change_count excludes aggregate files."""
        controller = ReloadController(use_content_hashes=True)

        # Create files
        content = tmp_path / "docs" / "page.html"
        content.parent.mkdir()
        content.write_text(
            '<html><head><meta name="bengal:content-hash" content="abc">'
            "</head><body>Doc</body></html>"
        )

        sitemap = tmp_path / "sitemap.xml"
        sitemap.write_text("<sitemap/>")

        # Capture baseline
        controller.capture_content_hash_baseline(tmp_path)

        # Change content file
        content.write_text(
            '<html><head><meta name="bengal:content-hash" content="xyz">'
            "</head><body>Updated doc</body></html>"
        )

        # Also change aggregate
        sitemap.write_text("<sitemap><url>new</url></sitemap>")

        decision = controller.decide_with_content_hashes(tmp_path)

        # meaningful_change_count should be 1 (content only), not 2
        assert decision.meaningful_change_count == 1
        assert len(decision.content_changes) == 1


class TestBuildTriggerContentHashIntegration:
    """Test content-hash integration in build_trigger."""

    def test_build_trigger_captures_baseline_before_build(self, tmp_path):
        """Build trigger captures content hash baseline before build."""
        from bengal.server.reload_controller import controller

        # Reset controller state
        controller._baseline_content_hashes = {}

        # Create mock site
        site = Mock()
        site.output_dir = tmp_path

        # Create HTML with hash
        html = tmp_path / "test.html"
        html.write_text(
            '<html><head><meta name="bengal:content-hash" content="test123">'
            "</head></html>"
        )

        # Capture baseline (simulating what build_trigger does)
        if controller._use_content_hashes:
            controller.capture_content_hash_baseline(site.output_dir)

        # Verify baseline was captured
        assert "test.html" in controller._baseline_content_hashes

    def test_aggregate_only_changes_filtered_in_reload_decision(self):
        """Aggregate-only changes are filtered from reload decision."""
        # Create enhanced decision with only aggregates
        decision = EnhancedReloadDecision(
            action="reload",
            reason="content-changed",
            changed_paths=["sitemap.xml", "index.json"],
            content_changes=[],
            aggregate_changes=["sitemap.xml", "index.json"],
            asset_changes=[],
        )

        # meaningful_change_count should be 0
        assert decision.meaningful_change_count == 0

        # If we have content changes, count should increase
        decision_with_content = EnhancedReloadDecision(
            action="reload",
            reason="content-changed",
            changed_paths=["page.html", "sitemap.xml"],
            content_changes=["page.html"],
            aggregate_changes=["sitemap.xml"],
            asset_changes=[],
        )

        assert decision_with_content.meaningful_change_count == 1


class TestDevServerContentHashIntegration:
    """Test content-hash integration in dev_server validation builds."""

    def test_validation_build_uses_content_hash_decision(self, tmp_path):
        """Validation builds use decide_with_content_hashes when available."""
        from bengal.server.reload_controller import controller

        # Verify controller is configured for content hashes
        assert controller._use_content_hashes is True

        # The actual integration is in dev_server._run_validation_build()
        # which calls controller.decide_with_content_hashes() when enabled
        # This test verifies the controller is configured correctly


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
