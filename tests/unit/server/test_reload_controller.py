import os
import time
from pathlib import Path

from bengal.core.output import OutputRecord, OutputType
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


# ============================================================================
# Tests for decide_from_outputs (typed OutputRecord-based decision making)
# ============================================================================


def test_decide_from_outputs_empty():
    """Empty outputs list returns no-reload decision."""
    ctl = ReloadController(min_notify_interval_ms=0)
    decision = ctl.decide_from_outputs([])

    assert decision.action == "none"
    assert decision.reason == "no-outputs"
    assert decision.changed_paths == []


def test_decide_from_outputs_css_only():
    """All CSS outputs trigger CSS-only reload."""
    ctl = ReloadController(min_notify_interval_ms=0)

    outputs = [
        OutputRecord(Path("assets/style.css"), OutputType.CSS, "asset"),
        OutputRecord(Path("assets/theme.css"), OutputType.CSS, "asset"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload-css"
    assert decision.reason == "css-only"
    assert set(decision.changed_paths) == {"assets/style.css", "assets/theme.css"}


def test_decide_from_outputs_mixed_types_triggers_full_reload():
    """Mixed output types (CSS + HTML) trigger full reload."""
    ctl = ReloadController(min_notify_interval_ms=0)

    outputs = [
        OutputRecord(Path("assets/style.css"), OutputType.CSS, "asset"),
        OutputRecord(Path("index.html"), OutputType.HTML, "render"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload"
    assert decision.reason == "content-changed"
    assert "assets/style.css" in decision.changed_paths
    assert "index.html" in decision.changed_paths


def test_decide_from_outputs_html_only_triggers_full_reload():
    """HTML outputs trigger full reload."""
    ctl = ReloadController(min_notify_interval_ms=0)

    outputs = [
        OutputRecord(Path("index.html"), OutputType.HTML, "render"),
        OutputRecord(Path("about.html"), OutputType.HTML, "render"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload"
    assert decision.reason == "content-changed"


def test_decide_from_outputs_with_ignore_globs():
    """Outputs matching ignore globs are filtered."""
    ctl = ReloadController(min_notify_interval_ms=0, ignored_globs=["search/**"])

    outputs = [
        OutputRecord(Path("search/index.json"), OutputType.JSON, "postprocess"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "none"
    assert decision.reason == "all-ignored"


def test_decide_from_outputs_partial_ignore():
    """Some outputs ignored, others remain."""
    ctl = ReloadController(min_notify_interval_ms=0, ignored_globs=["search/**"])

    outputs = [
        OutputRecord(Path("search/index.json"), OutputType.JSON, "postprocess"),
        OutputRecord(Path("assets/style.css"), OutputType.CSS, "asset"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload-css"
    assert decision.changed_paths == ["assets/style.css"]


def test_decide_from_outputs_throttling():
    """Rapid calls within throttle window return 'none'."""
    ctl = ReloadController(min_notify_interval_ms=1000)

    outputs = [OutputRecord(Path("assets/style.css"), OutputType.CSS, "asset")]

    # First call should trigger reload
    d1 = ctl.decide_from_outputs(outputs)
    assert d1.action == "reload-css"

    # Immediate second call should be throttled
    d2 = ctl.decide_from_outputs(outputs)
    assert d2.action == "none"
    assert d2.reason == "throttled"


def test_decide_from_outputs_all_output_types():
    """Test all OutputType values trigger full reload when mixed."""
    ctl = ReloadController(min_notify_interval_ms=0)

    # Various output types
    outputs = [
        OutputRecord(Path("index.html"), OutputType.HTML, "render"),
        OutputRecord(Path("assets/app.js"), OutputType.JS, "asset"),
        OutputRecord(Path("images/logo.png"), OutputType.IMAGE, "asset"),
        OutputRecord(Path("fonts/custom.woff2"), OutputType.FONT, "asset"),
        OutputRecord(Path("data/api.json"), OutputType.JSON, "postprocess"),
        OutputRecord(Path("sitemap.xml"), OutputType.XML, "postprocess"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload"
    assert decision.reason == "content-changed"
    assert len(decision.changed_paths) == 6


def test_decide_from_outputs_js_only_triggers_full_reload():
    """JS-only outputs trigger full reload (not CSS hot reload)."""
    ctl = ReloadController(min_notify_interval_ms=0)

    outputs = [
        OutputRecord(Path("assets/app.js"), OutputType.JS, "asset"),
        OutputRecord(Path("assets/vendor.js"), OutputType.JS, "asset"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload"
    assert decision.reason == "content-changed"


def test_decide_from_outputs_xml_sitemap():
    """XML outputs (sitemap) trigger full reload."""
    ctl = ReloadController(min_notify_interval_ms=0)

    outputs = [
        OutputRecord(Path("sitemap.xml"), OutputType.XML, "postprocess"),
    ]
    decision = ctl.decide_from_outputs(outputs)

    assert decision.action == "reload"
    assert decision.reason == "content-changed"


def test_decide_from_outputs_reload_hint_none_returns_none():
    """reload_hint='none' short-circuits to action='none' even with non-empty outputs."""
    ctl = ReloadController(min_notify_interval_ms=0)

    outputs = [
        OutputRecord(Path("index.html"), OutputType.HTML, "render"),
        OutputRecord(Path("assets/style.css"), OutputType.CSS, "asset"),
    ]
    decision = ctl.decide_from_outputs(outputs, reload_hint="none")

    assert decision.action == "none"
    assert decision.reason == "reload-hint-none"
    assert decision.changed_paths == []


def test_decide_from_outputs_other_hints_do_not_override_typed_outputs():
    """Other reload_hint values (css-only, full) do not override typed output classification."""
    ctl = ReloadController(min_notify_interval_ms=0)

    # HTML outputs should trigger full reload regardless of hint
    html_outputs = [
        OutputRecord(Path("index.html"), OutputType.HTML, "render"),
    ]
    d_full = ctl.decide_from_outputs(html_outputs, reload_hint="css-only")
    assert d_full.action == "reload"
    assert d_full.reason == "content-changed"

    # CSS-only outputs with css-only hint still get reload-css
    css_outputs = [
        OutputRecord(Path("assets/style.css"), OutputType.CSS, "asset"),
    ]
    d_css = ctl.decide_from_outputs(css_outputs, reload_hint="full")
    assert d_css.action == "reload-css"
    assert d_css.reason == "css-only"


# ============================================================================
# Tests for content hash baseline (CSS file capture fix)
# ============================================================================


def test_capture_content_hash_baseline_includes_css_files(tmp_path: Path):
    """
    BUG FIX: CSS files must be captured in baseline for accurate CSS-only detection.

    Previously, capture_content_hash_baseline() only captured .html files,
    but _check_css_changes_hashed() compared CSS files against the baseline.
    This caused ALL CSS files to be reported as changed every time.
    """
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0, use_content_hashes=True)

    # Create initial files
    (pub / "assets").mkdir()
    (pub / "assets" / "style.css").write_text("body{color:red}")
    (pub / "index.html").write_text("<html></html>")

    # Capture baseline
    ctl.capture_content_hash_baseline(pub)

    # Verify CSS file is in baseline
    assert "assets/style.css" in ctl._baseline_content_hashes
    assert "index.html" in ctl._baseline_content_hashes


def test_css_only_detection_with_content_hashes_no_spurious_reload(tmp_path: Path):
    """
    Verify CSS-only detection doesn't trigger spurious reloads when CSS is unchanged.
    """
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0, use_content_hashes=True)

    # Create initial files
    (pub / "assets").mkdir()
    (pub / "assets" / "style.css").write_text("body{color:red}")
    (pub / "index.html").write_text("<html></html>")

    # Capture baseline (simulates pre-build state)
    ctl.capture_content_hash_baseline(pub)

    # No changes made - should detect no changes
    decision = ctl.decide_with_content_hashes(pub)

    assert decision.action == "none"
    assert decision.reason == "no-changes"


def test_css_only_change_detected_with_content_hashes(tmp_path: Path):
    """
    CSS-only changes should trigger reload-css when using content hashes.
    """
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0, use_content_hashes=True)

    # Create initial files
    (pub / "assets").mkdir()
    (pub / "assets" / "style.css").write_text("body{color:red}")
    (pub / "index.html").write_text("<html></html>")

    # Capture baseline
    ctl.capture_content_hash_baseline(pub)

    # Change only CSS
    (pub / "assets" / "style.css").write_text("body{color:blue}")

    # Should detect CSS-only change
    decision = ctl.decide_with_content_hashes(pub)

    assert decision.action == "reload-css"
    assert "assets/style.css" in decision.asset_changes


def test_content_hash_baseline_empty_on_missing_directory(tmp_path: Path):
    """Baseline capture handles missing directory gracefully."""
    ctl = ReloadController(min_notify_interval_ms=0, use_content_hashes=True)

    # Non-existent directory
    missing_dir = tmp_path / "does_not_exist"

    # Should not raise, just result in empty baseline
    ctl.capture_content_hash_baseline(missing_dir)

    assert ctl._baseline_content_hashes == {}


def test_multiple_css_files_in_baseline(tmp_path: Path):
    """All CSS files should be captured in baseline."""
    pub = tmp_path
    ctl = ReloadController(min_notify_interval_ms=0, use_content_hashes=True)

    # Create multiple CSS files in different directories
    (pub / "assets").mkdir()
    (pub / "assets" / "style.css").write_text("body{}")
    (pub / "assets" / "theme.css").write_text("h1{}")
    (pub / "assets" / "nested").mkdir()
    (pub / "assets" / "nested" / "components.css").write_text("div{}")

    ctl.capture_content_hash_baseline(pub)

    assert "assets/style.css" in ctl._baseline_content_hashes
    assert "assets/theme.css" in ctl._baseline_content_hashes
    assert "assets/nested/components.css" in ctl._baseline_content_hashes
