from unittest.mock import patch

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
        self.output_dir = root_path
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
        patch("bengal.server.build_handler.controller") as mock_controller,
        patch("bengal.server.build_handler.send_reload_payload", fake_send_reload),
        patch("bengal.server.build_handler.BengalRequestHandler"),
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
        patch("bengal.server.build_handler.controller") as mock_controller,
        patch("bengal.server.build_handler.send_reload_payload", fake_send_reload),
        patch("bengal.server.build_handler.BengalRequestHandler"),
    ):
        mock_controller.decide_and_update.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=["style.css", "page.html"]
        )
        handler._trigger_build()

    assert called.get("action") == "reload"
