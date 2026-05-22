"""Font output writes use the shared atomic writer."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal import fonts as fonts_module

if TYPE_CHECKING:
    from pathlib import Path


def test_rewrite_font_urls_uses_atomic_write(tmp_path: Path, monkeypatch) -> None:
    css_path = tmp_path / "fonts.css"
    css_path.write_text("@font-face { src: url('fonts/inter-400.woff2'); }", encoding="utf-8")
    writes: list[tuple[Path, str]] = []

    def fake_atomic_write_text(path: Path, content: str, **kwargs) -> None:
        writes.append((path, content))
        path.write_text(content, encoding=kwargs.get("encoding", "utf-8"))

    monkeypatch.setattr(fonts_module, "atomic_write_text", fake_atomic_write_text)

    updated = fonts_module.rewrite_font_urls_with_fingerprints(
        css_path,
        {
            "assets": {
                "fonts/inter-400.woff2": {
                    "output_path": "assets/fonts/inter-400.abc123.woff2",
                }
            }
        },
    )

    assert updated is True
    assert writes == [(css_path, "@font-face { src: url('fonts/inter-400.abc123.woff2'); }")]


def test_font_helper_process_uses_atomic_write_for_fonts_css(
    tmp_path: Path,
    monkeypatch,
) -> None:
    helper = fonts_module.FontHelper({"primary": "Inter:400"})
    helper.downloader = SimpleNamespace(download_font=lambda **kwargs: ["variant"])
    helper.generator = SimpleNamespace(generate=lambda variants: "/* fonts */\n")
    writes: list[tuple[Path, str]] = []

    class FakeCli:
        icons = SimpleNamespace(tree_end="tree")

        def section(self, message: str) -> None:
            pass

        def detail(self, message: str, **kwargs) -> None:
            pass

    def fake_atomic_write_text(path: Path, content: str, **kwargs) -> None:
        writes.append((path, content))
        path.write_text(content, encoding=kwargs.get("encoding", "utf-8"))

    monkeypatch.setattr("bengal.output.get_cli_output", lambda: FakeCli())
    monkeypatch.setattr(fonts_module, "atomic_write_text", fake_atomic_write_text)

    css_path = helper.process(tmp_path)

    assert css_path == tmp_path / "fonts.css"
    assert writes == [(tmp_path / "fonts.css", "/* fonts */\n")]


def test_font_helper_process_skips_atomic_write_when_css_is_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "fonts.css").write_text("/* fonts */\n", encoding="utf-8")
    helper = fonts_module.FontHelper({"primary": "Inter:400"})
    helper.downloader = SimpleNamespace(download_font=lambda **kwargs: ["variant"])
    helper.generator = SimpleNamespace(generate=lambda variants: "/* fonts */\n")

    class FakeCli:
        icons = SimpleNamespace(tree_end="tree")

        def section(self, message: str) -> None:
            pass

        def detail(self, message: str, **kwargs) -> None:
            pass

    def fail_atomic_write_text(path: Path, content: str, **kwargs) -> None:
        raise AssertionError("unchanged fonts.css should not be rewritten")

    monkeypatch.setattr("bengal.output.get_cli_output", lambda: FakeCli())
    monkeypatch.setattr(fonts_module, "atomic_write_text", fail_atomic_write_text)

    assert helper.process(tmp_path) == tmp_path / "fonts.css"
