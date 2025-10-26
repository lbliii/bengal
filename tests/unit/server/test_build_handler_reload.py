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
