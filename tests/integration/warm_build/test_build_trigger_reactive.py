"""Integration tests for BuildTrigger reactive path and ReactiveContentHandler.

RFC: Reactive Dev Sequel (Phase 3 + 5)
- First trigger_build: full build, seeds content hash cache
- Second trigger_build (content-only edit): uses reactive path, skips site.build()
- handle_content_change: writes updated HTML to disk
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger
from bengal.server.reactive import ReactiveContentHandler
from tests.integration.warm_build.conftest import WarmBuildTestSite


class TestBuildTriggerReactivePath:
    """Integration tests for BuildTrigger reactive path after initial build."""

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor (warm builds use site.build directly)."""
        return MagicMock()

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_trigger_build_uses_reactive_path_after_first_build(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        warm_build_site: WarmBuildTestSite,
        mock_executor: MagicMock,
    ) -> None:
        """Second trigger_build uses reactive path and does not call site.build().

        Flow:
        1. First trigger_build: full build, seeds content hash cache
        2. Edit content file (body only)
        3. Second trigger_build: reactive path, site.build() not called
        """
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # Ensure site exists and has content
        site = warm_build_site.site
        content_path = warm_build_site.site_dir / "content" / "_index.md"
        assert content_path.exists()

        # Wrap site.build to count calls
        original_build = site.build
        build_calls: list[object] = []

        def tracking_build(*args: object, **kwargs: object) -> object:
            build_calls.append(1)
            return original_build(*args, **kwargs)

        with patch.object(site, "build", side_effect=tracking_build):
            trigger = BuildTrigger(site=site, executor=mock_executor)

            # First trigger: full build (no cache yet)
            trigger.trigger_build(
                changed_paths={content_path},
                event_types={"modified"},
            )
            assert len(build_calls) == 1

            # Content-only edit (frontmatter unchanged)
            warm_build_site.modify_file(
                "content/_index.md",
                """---
title: Home
---

# Welcome

This is the home page with updated body.
""",
            )

            # Second trigger: should use reactive path, no site.build()
            trigger.trigger_build(
                changed_paths={content_path},
                event_types={"modified"},
            )
            assert len(build_calls) == 1, "Reactive path should skip site.build()"


class TestReactiveContentHandlerIntegration:
    """Integration tests for ReactiveContentHandler writing output to disk."""

    def test_handle_content_change_writes_updated_html(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """handle_content_change writes updated HTML to disk after content edit."""
        # Initial build
        warm_build_site.full_build()
        warm_build_site.assert_output_exists("index.html")

        # Verify original content
        warm_build_site.assert_output_contains("index.html", "This is the home page")

        # Edit content (body only)
        updated_body = "Reactive update: new body content"
        warm_build_site.modify_file(
            "content/_index.md",
            f"""---
title: Home
---

# Welcome

{updated_body}
""",
        )

        # Call handler (no RenderingPipeline mock)
        handler = ReactiveContentHandler(
            warm_build_site.site, warm_build_site.output_dir
        )
        content_path = warm_build_site.site_dir / "content" / "_index.md"
        result = handler.handle_content_change(content_path)

        assert result is not None
        assert result.exists()

        # Updated HTML written to disk
        warm_build_site.assert_output_contains("index.html", updated_body)
