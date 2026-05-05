"""Integration tests for BuildTrigger reactive path and ReactiveContentHandler.

RFC: Reactive Dev Sequel (Phases 3, 5, 6, 7)
- First trigger_build: full build, seeds content hash cache
- Second trigger_build (content-only edit): uses reactive path, skips site.build()
- handle_content_change: writes updated HTML to disk
- fragment payload for instant DOM swap (content-only edits)
- Edge cases: dependent pages not updated
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger
from bengal.server.reactive import ReactiveContentHandler

if TYPE_CHECKING:
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
    @patch("bengal.server.build_trigger.get_cli_output")
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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_fragment_payload")
    def test_reactive_path_sends_fragment_payload(
        self,
        mock_send_fragment: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        warm_build_site: WarmBuildTestSite,
        mock_executor: MagicMock,
    ) -> None:
        """Reactive path sends fragment payload for instant DOM swap (mock SSE)."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        site = warm_build_site.site
        content_path = warm_build_site.site_dir / "content" / "_index.md"
        assert content_path.exists()

        with patch.object(site, "build", wraps=site.build):
            trigger = BuildTrigger(site=site, executor=mock_executor)

            # First trigger: full build
            trigger.trigger_build(
                changed_paths={content_path},
                event_types={"modified"},
            )

            # Content-only edit
            warm_build_site.modify_file(
                "content/_index.md",
                """---
title: Home
---

# Welcome

Updated body for fragment test.
""",
            )

            # Second trigger: reactive path should call send_fragment_payload
            trigger.trigger_build(
                changed_paths={content_path},
                event_types={"modified"},
            )

        mock_send_fragment.assert_called_once()
        call_kwargs = mock_send_fragment.call_args
        assert call_kwargs[0][0] == "#main-content"  # selector
        assert "Updated body for fragment test" in call_kwargs[0][1]  # html
        assert call_kwargs[0][2] == "/"  # permalink for _index.md


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
        handler = ReactiveContentHandler(warm_build_site.site, warm_build_site.output_dir)
        content_path = warm_build_site.site_dir / "content" / "_index.md"
        result = handler.handle_content_change(content_path)

        assert result is not None
        assert result.output_path.exists()
        assert result.rendered_html  # in-memory HTML available

        # Updated HTML written to disk
        warm_build_site.assert_output_contains("index.html", updated_body)

    def test_reactive_path_does_not_update_dependent_pages(
        self, site_with_nav: WarmBuildTestSite
    ) -> None:
        """Reactive path updates only the edited page; section index stays stale.

        Edge case (RFC Phase 7): When editing blog/post1.md, handle_content_change
        re-renders only post1. The blog section index (blog/index.html) lists
        post1 but is NOT re-rendered; it remains stale until full build.
        """
        site_dir = site_with_nav.site_dir
        output_dir = site_with_nav.output_dir

        # Full build
        site_with_nav.full_build()
        site_with_nav.assert_output_exists("blog/post1/index.html")
        site_with_nav.assert_output_exists("blog/index.html")

        # Capture section index content before edit (before post1 body change)
        post1_output = output_dir / "blog" / "post1" / "index.html"
        section_index_output = output_dir / "blog" / "index.html"
        section_index_mtime_before = section_index_output.stat().st_mtime

        # Edit post1 body only (content that affects post1 page)
        unique_content = "REACTIVE_EDGE_CASE_UNIQUE_STRING"
        post1_path = site_dir / "content" / "blog" / "post1.md"
        post1_path.write_text(f"""---
title: First Post
date: 2026-01-01
---

{unique_content}
""")

        # Reactive path: only processes post1
        handler = ReactiveContentHandler(site_with_nav.site, output_dir)
        result = handler.handle_content_change(post1_path)

        assert result is not None
        # Result may be relative or absolute; resolve for comparison
        assert result.output_path.resolve() == post1_output.resolve()

        # Post1 output updated with new content
        site_with_nav.assert_output_contains("blog/post1/index.html", unique_content)

        # Section index unchanged (mtime unchanged, content not updated)
        section_index_mtime_after = section_index_output.stat().st_mtime
        assert section_index_mtime_before == section_index_mtime_after, (
            "Section index should not be touched by reactive path"
        )
        # Section index does not contain the new post1 body (excerpt would be stale)
        section_html = section_index_output.read_text()
        assert unique_content not in section_html, (
            "Section index should not include post1 body; reactive path doesn't "
            "re-render dependent pages"
        )


class TestDevServerStyleFirstEdit:
    """First edit after DevServer-style init uses reactive path (bug fix).

    RFC: template-bugs-live-reload-issues
    DevServer does site.build() directly (not through BuildTrigger), then
    seeds content hash cache. First user edit must use reactive path.
    """

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.get_cli_output")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_fragment_payload")
    def test_first_edit_after_dev_server_init_uses_reactive_path(
        self,
        mock_send_fragment: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        warm_build_site: WarmBuildTestSite,
    ) -> None:
        """First edit uses reactive path when cache was seeded by DevServer.

        Simulates DevServer build-first flow:
        1. site.build() (not through BuildTrigger)
        2. build_trigger.seed_content_hash_cache(list(site.pages))
        3. User edits content (body only)
        4. trigger_build -> reactive path, send_fragment_payload
        """
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        site = warm_build_site.site
        content_path = warm_build_site.site_dir / "content" / "_index.md"
        assert content_path.exists()

        # DevServer-style: site.build() directly (not through BuildTrigger)
        warm_build_site.full_build()

        trigger = BuildTrigger(site=site, executor=MagicMock())
        # DevServer seeds cache after initial build
        trigger.seed_content_hash_cache(list(site.pages))

        # First user edit (content-only)
        warm_build_site.modify_file(
            "content/_index.md",
            """---
title: Home
---

# Welcome

First edit after server start.
""",
        )

        # First trigger_build should use reactive path (cache was seeded)
        trigger.trigger_build(
            changed_paths={content_path},
            event_types={"modified"},
        )

        mock_send_fragment.assert_called_once()
        assert "First edit after server start" in mock_send_fragment.call_args[0][1]
