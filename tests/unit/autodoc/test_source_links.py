from pathlib import Path

from bengal.autodoc.virtual_orchestrator import (
    _format_source_file_for_display,
    _normalize_autodoc_config,
)


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

    # Falls back to parent of root (tmp_path) for relative link
    assert result == "external/file.py"


def test_normalizes_autodoc_config_with_defaults() -> None:
    site_cfg = {
        "autodoc": {
            "github_repo": "lbliii/bengal",
        },
    }

    normalized = _normalize_autodoc_config(site_cfg)

    assert normalized["github_repo"] == "https://github.com/lbliii/bengal"
    assert normalized["github_branch"] == "main"
