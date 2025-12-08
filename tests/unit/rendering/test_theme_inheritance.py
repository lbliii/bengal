from __future__ import annotations


from pathlib import Path

from bengal.core.theme import Theme
from bengal.rendering.template_engine import TemplateEngine


class DummySite:
    def __init__(self, root_path: Path, theme: str = "default") -> None:
        self.root_path = root_path
        self.theme = theme
        self.config = {}
        self.output_dir = root_path / "public"  # Required by TemplateEngine for bytecode cache

    @property
    def theme_config(self) -> Theme:
        """Return a default Theme for testing."""
        return Theme(name=self.theme)


def write_theme(root: Path, name: str, extends: str | None, with_template: bool = False) -> None:
    tdir = root / "themes" / name
    (tdir / "templates").mkdir(parents=True, exist_ok=True)
    if extends is not None:
        (tdir / "theme.toml").write_text(
            f'name = "{name}"\nextends = "{extends}"\n', encoding="utf-8"
        )
    if with_template:
        (tdir / "templates" / "marker.html").write_text(f"{name}", encoding="utf-8")


def test_theme_chain_child_overrides_parent(tmp_path: Path):
    # Arrange: parent theme defines a template; child extends parent and defines its own
    write_theme(tmp_path, "parent", extends=None, with_template=True)
    write_theme(tmp_path, "child", extends="parent", with_template=True)

    site = DummySite(tmp_path, theme="child")
    engine = TemplateEngine(site)

    # Act: resolve template dirs (child first, then parent, default fallback)
    dirs = [str(d) for d in engine.template_dirs]

    # Assert: child templates dir appears before parent
    child_dir = str(tmp_path / "themes" / "child" / "templates")
    parent_dir = str(tmp_path / "themes" / "parent" / "templates")
    assert child_dir in dirs and parent_dir in dirs
    assert dirs.index(child_dir) < dirs.index(parent_dir)
