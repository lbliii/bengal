import json
from pathlib import Path

from click.testing import CliRunner

from bengal.cli import main
from bengal.core.site import Site
from bengal.utils.swizzle import SwizzleManager


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def test_swizzle_copy_and_registry(tmp_path: Path):
    # Arrange theme template
    theme_tpl = tmp_path / 'themes' / 'child' / 'templates' / 'partials' / 'demo.html'
    _write(theme_tpl, 'Hello from theme')

    site = Site.from_config(tmp_path)
    site.theme = 'child'

    mgr = SwizzleManager(site)

    # Act
    dest = mgr.swizzle('partials/demo.html')

    # Assert: file copied and registry written
    assert dest.exists()
    assert dest.read_text(encoding='utf-8') == 'Hello from theme'
    registry = tmp_path / '.bengal' / 'themes' / 'sources.json'
    data = json.loads(registry.read_text(encoding='utf-8'))
    recs = data.get('records', [])
    assert any(r.get('target') == 'partials/demo.html' and r.get('theme') == 'child' for r in recs)


def test_swizzle_update_skips_when_local_changed(tmp_path: Path):
    # Arrange
    theme_tpl = tmp_path / 'themes' / 'child' / 'templates' / 'partials' / 'demo.html'
    _write(theme_tpl, 'v1')

    site = Site.from_config(tmp_path)
    site.theme = 'child'
    mgr = SwizzleManager(site)
    dest = mgr.swizzle('partials/demo.html')

    # Local edit
    _write(dest, 'local edit')
    # Upstream change
    _write(theme_tpl, 'v2')

    # Act
    summary = mgr.update()

    # Assert
    assert summary['skipped_changed'] >= 1
    assert dest.read_text(encoding='utf-8') == 'local edit'


def test_swizzle_update_overwrites_when_local_unchanged(tmp_path: Path):
    # Arrange
    theme_tpl = tmp_path / 'themes' / 'child' / 'templates' / 'partials' / 'demo.html'
    _write(theme_tpl, 'v1')

    site = Site.from_config(tmp_path)
    site.theme = 'child'
    mgr = SwizzleManager(site)
    dest = mgr.swizzle('partials/demo.html')

    # Upstream change
    _write(theme_tpl, 'v2')

    # Act
    summary = mgr.update()

    # Assert
    assert summary['updated'] >= 1
    assert dest.read_text(encoding='utf-8') == 'v2'


def test_swizzle_cli_invocation(tmp_path: Path):
    # Arrange
    theme_tpl = tmp_path / 'themes' / 'child' / 'templates' / 'partials' / 'demo.html'
    _write(theme_tpl, 'from cli')

    runner = CliRunner()

    # Act
    result = runner.invoke(main, ['theme', 'swizzle', 'partials/demo.html', str(tmp_path)], catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    dest = tmp_path / 'templates' / 'partials' / 'demo.html'
    assert dest.exists()
    assert dest.read_text(encoding='utf-8') == 'from cli'


