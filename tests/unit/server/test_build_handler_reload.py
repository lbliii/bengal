from unittest.mock import MagicMock, patch

from bengal.server.build_handler import BuildHandler
from bengal.server.reload_controller import ReloadDecision


class DummyStats:
    def __init__(self):
        self.total_pages = 1
        self.build_time_ms = 1
        self.incremental = True
        self.parallel = True
        self.skipped = False
        # Optional attribute used by BuildHandler when present
        self.changed_outputs = None


class DummySite:
    def __init__(self, root_path):
        self.root_path = root_path
        self.output_dir = root_path / "public"  # Separate output directory
        self.pages = []
        self.sections = []
        self.assets = []
        self.config = {}
        self.theme = None

    def build(self, *args, **kwargs):
        return DummyStats()

    def invalidate_regular_pages_cache(self):
        pass

    def reset_ephemeral_state(self):
        pass


def _make_handler(tmp_path):
    site = DummySite(tmp_path)
    handler = BuildHandler(site, host="localhost", port=5173)
    return handler


def test_css_only_triggers_css_reload(tmp_path, monkeypatch):
    handler = _make_handler(tmp_path)
    handler.pending_changes = {str(tmp_path / "assets" / "style.css")}

    called = {}

    def fake_send_reload(action, reason, changed_paths):
        called["action"] = action
        called["reason"] = reason

    # Silence display/printing via the symbols actually used by BuildHandler
    monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
    monkeypatch.setattr("bengal.server.build_handler.show_building_indicator", lambda *a, **k: None)

    # Mock the reload controller to return CSS-only decision
    with (
        patch("bengal.server.reload_controller.controller") as mock_controller,
        patch("bengal.server.live_reload.send_reload_payload", fake_send_reload),
        patch("bengal.server.request_handler.BengalRequestHandler"),
    ):
        mock_controller.decide_and_update.return_value = ReloadDecision(
            action="reload-css", reason="css-only", changed_paths=["style.css"]
        )
        handler._trigger_build()

    assert called.get("action") == "reload-css"


def test_mixed_changes_trigger_full_reload(tmp_path, monkeypatch):
    handler = _make_handler(tmp_path)
    handler.pending_changes = {
        str(tmp_path / "assets" / "style.css"),
        str(tmp_path / "content" / "page.md"),
    }

    called = {}

    def fake_send_reload(action, reason, changed_paths):
        called["action"] = action
        called["reason"] = reason

    # Silence display/printing via the symbols actually used by BuildHandler
    monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
    monkeypatch.setattr("bengal.server.build_handler.show_building_indicator", lambda *a, **k: None)

    # Mock the reload controller to return full reload decision
    with (
        patch("bengal.server.reload_controller.controller") as mock_controller,
        patch("bengal.server.live_reload.send_reload_payload", fake_send_reload),
        patch("bengal.server.request_handler.BengalRequestHandler"),
    ):
        mock_controller.decide_and_update.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=["style.css", "page.html"]
        )
        handler._trigger_build()

    assert called.get("action") == "reload"


def test_prefers_changed_outputs_over_snapshot_diff(tmp_path, monkeypatch):
    handler = _make_handler(tmp_path)

    # Prepare DummySite.build to return stats with changed_outputs
    stats = DummyStats()
    stats.changed_outputs = ["assets/style.css"]

    def fake_build(*args, **kwargs):
        return stats

    handler.site.build = fake_build

    # Capture payload and track which controller API was called
    called = {"api": None}

    def fake_send_reload(action, reason, changed_paths):
        called["action"] = action
        called["reason"] = reason
        called["changed_paths"] = list(changed_paths)

    monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
    monkeypatch.setattr("bengal.server.build_handler.show_building_indicator", lambda *a, **k: None)

    with (
        # Patch controller at the import site (build_handler module)
        patch("bengal.server.build_handler.controller") as mock_controller,
        patch("bengal.server.live_reload.send_reload_payload", fake_send_reload),
        patch("bengal.server.request_handler.BengalRequestHandler"),
    ):
        # decide_from_changed_paths should be used, not decide_and_update
        def _decide_from_changed_paths(paths):
            called["api"] = "decide_from_changed_paths"
            return ReloadDecision(action="reload-css", reason="css-only", changed_paths=paths)

        mock_controller.decide_from_changed_paths.side_effect = _decide_from_changed_paths
        # Make decide_and_update obvious if called erroneously
        mock_controller.decide_and_update.return_value = ReloadDecision(
            action="reload",
            reason="snapshot",
            changed_paths=["should-not-be-used"],
        )

        handler._trigger_build()

    # Assert builder-provided path was used and CSS-only classification occurred
    assert called.get("api") == "decide_from_changed_paths"
    assert called.get("action") == "reload-css"
    assert called.get("changed_paths") == ["assets/style.css"]


def test_on_created_triggers_rebuild(tmp_path):
    """Test that file creation events trigger rebuilds."""
    handler = _make_handler(tmp_path)

    # Create a test file
    test_file = tmp_path / "content" / "new-page.md"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    # Mock the event
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(test_file)

    # Call the handler
    handler.on_created(event)

    # Verify the file was added to pending changes
    assert str(test_file) in handler.pending_changes
    assert handler.debounce_timer is not None


def test_on_deleted_triggers_rebuild(tmp_path):
    """Test that file deletion events trigger rebuilds."""
    handler = _make_handler(tmp_path)

    # Mock the event for a deleted file
    test_file = tmp_path / "content" / "deleted-page.md"
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(test_file)

    # Call the handler
    handler.on_deleted(event)

    # Verify the file was added to pending changes
    assert str(test_file) in handler.pending_changes
    assert handler.debounce_timer is not None


def test_on_moved_triggers_rebuild(tmp_path):
    """Test that file move/rename events trigger rebuilds."""
    handler = _make_handler(tmp_path)

    # Mock the event for a moved file
    old_path = tmp_path / "content" / "old-name.md"
    new_path = tmp_path / "content" / "new-name.md"
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(old_path)
    event.dest_path = str(new_path)

    # Call the handler
    handler.on_moved(event)

    # Verify both paths were added to pending changes
    assert str(old_path) in handler.pending_changes
    assert str(new_path) in handler.pending_changes
    assert handler.debounce_timer is not None


def test_ignores_output_directory_on_create(tmp_path):
    """Test that files created in the output directory are ignored."""
    handler = _make_handler(tmp_path)

    # Mock the event for a file in the output directory
    output_file = tmp_path / "public" / "index.html"
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(output_file)

    # Call the handler
    handler.on_created(event)

    # Verify the file was NOT added to pending changes
    assert str(output_file) not in handler.pending_changes
    assert handler.debounce_timer is None


def test_ignores_temp_files_on_create(tmp_path):
    """Test that temp files are ignored on creation."""
    handler = _make_handler(tmp_path)

    # Mock the event for a temp file
    temp_file = tmp_path / "content" / "page.md.swp"
    event = MagicMock()
    event.is_directory = False
    event.src_path = str(temp_file)

    # Call the handler
    handler.on_created(event)

    # Verify the file was NOT added to pending changes
    assert str(temp_file) not in handler.pending_changes
    assert handler.debounce_timer is None


class TestRebuildStrategy:
    """Test the rebuild strategy logic (full vs incremental)."""

    def test_content_file_change_allows_incremental_build(self, tmp_path, monkeypatch):
        """Content file (.md) modifications allow incremental builds for faster dev rebuilds.

        Since incremental build support, content modifications without nav-affecting
        frontmatter keys use incremental mode for faster dev server performance.
        """
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "content" / "page.md")}
        handler.pending_event_types = {"modified"}

        build_kwargs = {}

        def capture_build(*args, **kwargs):
            build_kwargs.update(kwargs)
            return DummyStats()

        handler.site.build = capture_build

        # Silence display/printing
        monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller") as mock_controller,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_controller.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="content-changed", changed_paths=[]
            )
            handler._trigger_build()

        # Content modifications (without nav-affecting frontmatter) allow incremental builds
        assert build_kwargs.get("incremental") is True

    def test_css_only_change_allows_incremental_build(self, tmp_path, monkeypatch):
        """CSS-only changes should allow incremental builds."""
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "assets" / "style.css")}
        handler.pending_event_types = {"modified"}

        build_kwargs = {}

        def capture_build(*args, **kwargs):
            build_kwargs.update(kwargs)
            return DummyStats()

        handler.site.build = capture_build

        # Silence display/printing
        monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller") as mock_controller,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_controller.decide_and_update.return_value = ReloadDecision(
                action="reload-css", reason="css-only", changed_paths=[]
            )
            handler._trigger_build()

        # CSS-only changes should allow incremental builds
        assert build_kwargs.get("incremental") is True

    def test_created_file_triggers_full_rebuild(self, tmp_path, monkeypatch):
        """File creation should trigger full rebuild (structural change)."""
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "content" / "new-page.md")}
        handler.pending_event_types = {"created"}

        build_kwargs = {}

        def capture_build(*args, **kwargs):
            build_kwargs.update(kwargs)
            return DummyStats()

        handler.site.build = capture_build

        # Silence display/printing
        monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller") as mock_controller,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_controller.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="content-changed", changed_paths=[]
            )
            handler._trigger_build()

        # Created files should trigger full rebuild
        assert build_kwargs.get("incremental") is False

    def test_deleted_file_triggers_full_rebuild(self, tmp_path, monkeypatch):
        """File deletion should trigger full rebuild (structural change)."""
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "content" / "deleted-page.md")}
        handler.pending_event_types = {"deleted"}

        build_kwargs = {}

        def capture_build(*args, **kwargs):
            build_kwargs.update(kwargs)
            return DummyStats()

        handler.site.build = capture_build

        # Silence display/printing
        monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller") as mock_controller,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_controller.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="content-changed", changed_paths=[]
            )
            handler._trigger_build()

        # Deleted files should trigger full rebuild
        assert build_kwargs.get("incremental") is False

    def test_js_only_change_allows_incremental_build(self, tmp_path, monkeypatch):
        """JavaScript-only changes should allow incremental builds."""
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "assets" / "script.js")}
        handler.pending_event_types = {"modified"}

        build_kwargs = {}

        def capture_build(*args, **kwargs):
            build_kwargs.update(kwargs)
            return DummyStats()

        handler.site.build = capture_build

        # Silence display/printing
        monkeypatch.setattr("bengal.server.build_handler.display_build_stats", lambda *a, **k: None)
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller") as mock_controller,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_controller.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="js-changed", changed_paths=[]
            )
            handler._trigger_build()

        # JS-only changes should allow incremental builds
        assert build_kwargs.get("incremental") is True

    def test_markdown_extension_allows_incremental_build(self, tmp_path, monkeypatch):
        """Both .md and .markdown modifications allow incremental builds.

        Content file modifications without nav-affecting frontmatter keys
        use incremental mode for faster dev server performance.
        """
        for ext in [".md", ".markdown"]:
            handler = _make_handler(tmp_path)
            handler.pending_changes = {str(tmp_path / "content" / f"page{ext}")}
            handler.pending_event_types = {"modified"}

            build_kwargs = {}

            def make_capture(target):
                def capture_build(*args, **kwargs):
                    target.update(kwargs)
                    return DummyStats()

                return capture_build

            handler.site.build = make_capture(build_kwargs)

            # Silence display/printing
            monkeypatch.setattr(
                "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
            )
            monkeypatch.setattr(
                "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
            )

            with (
                patch("bengal.server.reload_controller.controller") as mock_controller,
                patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
            ):
                from bengal.server.reload_controller import ReloadDecision

                mock_controller.decide_and_update.return_value = ReloadDecision(
                    action="reload", reason="content-changed", changed_paths=[]
                )
                handler._trigger_build()

            assert build_kwargs.get("incremental") is True, (
                f"Extension {ext} should allow incremental build for content modifications"
            )
