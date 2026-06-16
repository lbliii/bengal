"""Packaging integrity checks for the VS Code syntax-highlighter extension."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HIGHLIGHTER_ROOT = REPO_ROOT / "bengal-syntax-highlighter"
PACKAGE_JSON = HIGHLIGHTER_ROOT / "package.json"
KIDA_GRAMMAR = HIGHLIGHTER_ROOT / "syntaxes" / "kida.tmLanguage.json"


def _package_json_paths() -> list[Path]:
    data = json.loads(PACKAGE_JSON.read_text())
    paths: list[Path] = []

    for language in data.get("contributes", {}).get("languages", []):
        config = language.get("configuration")
        if config:
            paths.append(HIGHLIGHTER_ROOT / config.lstrip("./"))

    for grammar in data.get("contributes", {}).get("grammars", []):
        grammar_path = grammar.get("path")
        if grammar_path:
            paths.append(HIGHLIGHTER_ROOT / grammar_path.lstrip("./"))

    return paths


class TestSyntaxHighlighterPackage:
    def test_package_json_declared_files_exist(self) -> None:
        missing = [path for path in _package_json_paths() if not path.is_file()]
        assert not missing, f"Missing syntax-highlighter files: {missing}"

    def test_kida_grammar_does_not_hijack_html_file_type(self) -> None:
        data = json.loads(KIDA_GRAMMAR.read_text())
        file_types = data.get("fileTypes", [])
        assert "html" not in file_types, (
            "Kida primary grammar must not register .html — use text.html injection instead"
        )
