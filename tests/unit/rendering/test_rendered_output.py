from pathlib import Path
from types import SimpleNamespace

from bengal.rendering.rendered_output import get_rendered_html


def test_render_pipeline_does_not_dual_write_rendered_html() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    checked_files = (
        repo_root / "bengal/rendering/pipeline/core.py",
        repo_root / "bengal/rendering/pipeline/cache_checker.py",
        repo_root / "bengal/rendering/pipeline/autodoc_renderer.py",
    )

    for path in checked_files:
        assert "page.rendered_html =" not in path.read_text(encoding="utf-8")


def test_get_rendered_html_prefers_existing_page_value(tmp_path):
    output_path = tmp_path / "public" / "index.html"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("<html>from disk</html>", encoding="utf-8")

    page = SimpleNamespace(rendered_html="<html>from page</html>", output_path=output_path)

    assert get_rendered_html(page) == "<html>from page</html>"


def test_get_rendered_html_reads_written_output_when_page_value_missing(tmp_path):
    output_path = tmp_path / "public" / "index.html"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("<html>from disk</html>", encoding="utf-8")

    page = SimpleNamespace(rendered_html="", output_path=output_path)

    assert get_rendered_html(page) == "<html>from disk</html>"


def test_get_rendered_html_returns_empty_for_missing_output(tmp_path):
    page = SimpleNamespace(rendered_html="", output_path=tmp_path / "missing.html")

    assert get_rendered_html(page) == ""
