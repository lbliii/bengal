"""Regression tests for bengal-syntax-highlighter packaging (#448)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "bengal-syntax-highlighter"


@pytest.mark.parametrize(
    "relative_path",
    [
        "package.json",
        "language-configuration.json",
        "syntaxes/kida.tmLanguage.json",
    ],
)
def test_packaged_files_exist(relative_path: str) -> None:
    assert (_PACKAGE_ROOT / relative_path).is_file()


def test_kida_grammar_does_not_hijack_html() -> None:
    grammar = json.loads((_PACKAGE_ROOT / "syntaxes/kida.tmLanguage.json").read_text())
    assert "html" not in grammar.get("fileTypes", [])


def test_package_json_references_language_configuration() -> None:
    package = json.loads((_PACKAGE_ROOT / "package.json").read_text())
    languages = package["contributes"]["languages"]
    kida = next(lang for lang in languages if lang["id"] == "kida")
    config_path = _PACKAGE_ROOT / kida["configuration"].removeprefix("./")
    assert config_path.is_file()
