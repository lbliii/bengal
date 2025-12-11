from pathlib import Path

from bengal.autodoc.virtual_orchestrator import _format_source_file_for_display


def test_formats_absolute_path_relative_to_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "bengal" / "cli" / "commands" / "assets.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.touch()

    result = _format_source_file_for_display(source, root)

    assert result == "bengal/cli/commands/assets.py"


def test_leaves_relative_paths_unchanged() -> None:
    source = Path("bengal/collections/__init__.py")
    root = Path("/home/runner/work/bengal/bengal")

    result = _format_source_file_for_display(source, root)

    assert result == "bengal/collections/__init__.py"


def test_falls_back_to_posix_absolute_when_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "external" / "file.py"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.touch()

    result = _format_source_file_for_display(outside, root)

    assert result == outside.as_posix()
