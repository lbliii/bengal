import json
from pathlib import Path

from click.testing import CliRunner

from bengal.cli import main
from bengal.core.site import Site
from bengal.themes.swizzle import ModificationStatus, SwizzleManager


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_swizzle_copy_and_registry(tmp_path: Path):
    # Arrange theme template
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "Hello from theme")

    site = Site.from_config(tmp_path)
    site.theme = "child"

    mgr = SwizzleManager(site)

    # Act
    dest = mgr.swizzle("partials/demo.html")

    # Assert: file copied and registry written
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "Hello from theme"
    registry = tmp_path / ".bengal" / "themes" / "sources.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    recs = data.get("records", [])
    assert any(r.get("target") == "partials/demo.html" and r.get("theme") == "child" for r in recs)


def test_swizzle_update_skips_when_local_changed(tmp_path: Path):
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "v1")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    dest = mgr.swizzle("partials/demo.html")

    # Local edit
    _write(dest, "local edit")
    # Upstream change
    _write(theme_tpl, "v2")

    # Act
    summary = mgr.update()

    # Assert
    assert summary["skipped_changed"] >= 1
    assert dest.read_text(encoding="utf-8") == "local edit"


def test_swizzle_update_overwrites_when_local_unchanged(tmp_path: Path):
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "v1")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    dest = mgr.swizzle("partials/demo.html")

    # Upstream change
    _write(theme_tpl, "v2")

    # Act
    summary = mgr.update()

    # Assert
    assert summary["updated"] >= 1
    assert dest.read_text(encoding="utf-8") == "v2"


def test_swizzle_cli_invocation(tmp_path: Path):
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "from cli")

    # Create bengal.toml to configure the theme
    config_file = tmp_path / "bengal.toml"
    config_file.write_text('[site]\nname="test"\ntheme="child"\n', encoding="utf-8")

    runner = CliRunner()

    # Act
    result = runner.invoke(
        main,
        ["utils", "theme", "swizzle", "partials/demo.html", str(tmp_path)],
        catch_exceptions=False,
    )

    # Assert
    assert result.exit_code == 0
    dest = tmp_path / "templates" / "partials" / "demo.html"
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "from cli"


def test_modification_status_not_swizzled(tmp_path: Path):
    """Verify get_modification_status returns NOT_SWIZZLED for non-swizzled templates."""
    site = Site.from_config(tmp_path)
    mgr = SwizzleManager(site)

    status = mgr.get_modification_status("partials/nonexistent.html")

    assert status == ModificationStatus.NOT_SWIZZLED


def test_modification_status_unchanged(tmp_path: Path):
    """Verify get_modification_status returns UNCHANGED for unmodified swizzled templates."""
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "original content")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    mgr.swizzle("partials/demo.html")

    # Act
    status = mgr.get_modification_status("partials/demo.html")

    # Assert
    assert status == ModificationStatus.UNCHANGED


def test_modification_status_modified(tmp_path: Path):
    """Verify get_modification_status returns MODIFIED for locally modified templates."""
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "original content")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    dest = mgr.swizzle("partials/demo.html")

    # Modify the local file
    _write(dest, "modified content")

    # Act
    status = mgr.get_modification_status("partials/demo.html")

    # Assert
    assert status == ModificationStatus.MODIFIED


def test_modification_status_file_missing(tmp_path: Path):
    """Verify get_modification_status returns FILE_MISSING when swizzled file is deleted."""
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "original content")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    dest = mgr.swizzle("partials/demo.html")

    # Delete the local file
    dest.unlink()

    # Act
    status = mgr.get_modification_status("partials/demo.html")

    # Assert
    assert status == ModificationStatus.FILE_MISSING


def test_is_modified_convenience_method(tmp_path: Path):
    """Verify is_modified returns correct boolean values."""
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "original content")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    dest = mgr.swizzle("partials/demo.html")

    # Unchanged should return False
    assert mgr.is_modified("partials/demo.html") is False

    # Modified should return True
    _write(dest, "modified content")
    assert mgr.is_modified("partials/demo.html") is True

    # Not swizzled should return False
    assert mgr.is_modified("partials/nonexistent.html") is False


def test_update_returns_skipped_error_count(tmp_path: Path):
    """Verify update() returns skipped_error count in results."""
    # Arrange
    theme_tpl = tmp_path / "themes" / "child" / "templates" / "partials" / "demo.html"
    _write(theme_tpl, "v1")

    site = Site.from_config(tmp_path)
    site.theme = "child"
    mgr = SwizzleManager(site)
    mgr.swizzle("partials/demo.html")

    # Act - update with unchanged file
    summary = mgr.update()

    # Assert - skipped_error should be present in response
    assert "skipped_error" in summary
    assert isinstance(summary["skipped_error"], int)
