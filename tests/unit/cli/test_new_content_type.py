"""Tests for `bengal new content-type` scaffold."""

from __future__ import annotations

import importlib.util
import sys
from typing import TYPE_CHECKING

import pytest

from bengal.cli.milo_commands.new import new_content_type
from bengal.content_types import get_strategy

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _quiet_cli() -> None:
    """Silence the global CLI singleton — tests don't want render output."""
    from bengal.output import get_cli_output

    get_cli_output(quiet=True, use_global=True)


def _import_generated(path: Path, mod_name: str) -> object:
    """Import a generated scaffold file by absolute path."""
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestNewContentTypeScaffold:
    def test_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = new_content_type(name="recipe")

        target = tmp_path / "content_types" / "recipe_strategy.py"
        assert target.exists(), result
        assert result["slug"] == "recipe"
        assert result["class_name"] == "RecipeStrategy"

    def test_generated_file_imports_and_registers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        new_content_type(name="case-study")

        target = tmp_path / "content_types" / "case_study_strategy.py"
        assert target.exists()

        try:
            module = _import_generated(target, "case_study_strategy")
            cls = vars(module)["CaseStudyStrategy"]
            assert cls.__name__ == "CaseStudyStrategy"

            # register_strategy ran at import time — should be in registry
            strategy = get_strategy("case-study")
            assert type(strategy).__name__ == "CaseStudyStrategy"
        finally:
            sys.modules.pop("case_study_strategy", None)

    def test_class_name_pascal_cased_from_hyphens(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = new_content_type(name="release-note")
        assert result["class_name"] == "ReleaseNoteStrategy"
        assert result["slug"] == "release-note"

        target = tmp_path / "content_types" / "release_note_strategy.py"
        assert "class ReleaseNoteStrategy" in target.read_text()

    def test_scaffold_includes_required_sections(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        new_content_type(name="recipe")
        body = (tmp_path / "content_types" / "recipe_strategy.py").read_text()

        assert "When to use:" in body
        assert "default_template" in body
        assert "def sort_pages" in body
        assert "register_strategy" in body
        assert "bengal/content_types/base.py" in body

    def test_rejects_existing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        new_content_type(name="recipe")
        with pytest.raises(SystemExit) as excinfo:
            new_content_type(name="recipe")
        assert excinfo.value.code == 1

    def test_rejects_non_alphanumeric_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            new_content_type(name="!!!")
        assert excinfo.value.code == 1
