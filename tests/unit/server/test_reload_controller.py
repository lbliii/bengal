import os
import time
from pathlib import Path

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


def test_ignore_globs_filters_changes(tmp_path: Path):
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0, ignored_globs=["index.json", "search/**"])

    # baseline
    ctl.decide_and_update(pub)

    # Create ignored file
    (pub / "index.json").write_text("{}")
    d1 = ctl.decide_and_update(pub)
    assert d1.action == "none"  # ignored by glob

    # Non-ignored CSS should still trigger css-only
    (pub / "assets").mkdir(exist_ok=True)
    (pub / "assets" / "style.css").write_text("body{color:red}")
    d2 = ctl.decide_and_update(pub)
    assert d2.action == "reload-css"
    assert "assets/style.css" in d2.changed_paths


def test_suspect_hashing_suppresses_after_cache(tmp_path: Path):
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0, hash_on_suspect=True, suspect_hash_limit=100)

    # baseline
    ctl.decide_and_update(pub)

    # First write (size changes): triggers reload-css (not a suspect since size changed from 0/absent)
    (pub / "assets").mkdir(exist_ok=True)
    css_path = pub / "assets" / "a.css"
    css_path.write_text("body{a:1}")
    d1 = ctl.decide_and_update(pub)
    assert d1.action == "reload-css"

    # Rewrite same content (same size, new mtime) - first suspect: cache populated, not yet suppressed
    time.sleep(0.01)
    os.utime(css_path, None)
    d2 = ctl.decide_and_update(pub)
    # Depending on cache warm-up, this may still be css reload on the first suspect
    assert d2.action in {"reload-css", "none"}

    # Rewrite same content again (same size, new mtime) - second suspect: should be suppressed now
    time.sleep(0.01)
    os.utime(css_path, None)
    d3 = ctl.decide_and_update(pub)
    assert d3.action == "none"


def test_decide_from_changed_paths_with_ignores_and_css_only(tmp_path: Path):
    ctl = ReloadController(min_notify_interval_ms=0, ignored_globs=["ignored/**"])

    # CSS-only when all are .css
    d_css = ctl.decide_from_changed_paths(["assets/a.css", "assets/b.css"])
    assert d_css.action == "reload-css"
    assert set(d_css.changed_paths) == {"assets/a.css", "assets/b.css"}

    # Mixed changes -> full reload
    d_full = ctl.decide_from_changed_paths(["index.html", "assets/a.css"])
    assert d_full.action == "reload"

    # Ignored paths are filtered
    d_ignored = ctl.decide_from_changed_paths(["ignored/x.css"])  # filtered to empty
    assert d_ignored.action == "none"
