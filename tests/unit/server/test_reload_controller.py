from pathlib import Path
import time

from bengal.server.reload_controller import ReloadController


def test_decisions_none_css_full(tmp_path: Path):
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0)

    # baseline
    d0 = ctl.decide_and_update(pub)
    assert d0.action == "none"

    # css only
    (pub / "assets").mkdir()
    (pub / "assets" / "a.css").write_text("body{a:1}")
    d1 = ctl.decide_and_update(pub)
    assert d1.action == "reload-css"
    assert "assets/a.css" in d1.changed_paths

    # html change -> full reload
    (pub / "x.html").write_text("<html></html>")
    d2 = ctl.decide_and_update(pub)
    assert d2.action == "reload"


def test_throttle_monotonic(tmp_path: Path, monkeypatch):
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=1000)
    ctl.decide_and_update(pub)
    (pub / "a.css").write_text("x")
    d1 = ctl.decide_and_update(pub)
    assert d1.action == "reload-css"
    # immediate second change throttled
    (pub / "b.css").write_text("y")
    d2 = ctl.decide_and_update(pub)
    assert d2.action == "none"

