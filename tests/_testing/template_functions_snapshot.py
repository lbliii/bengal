"""Template function reference snapshot helpers (issue #623)."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GENERATED_DOC = (
    _REPO_ROOT
    / "site"
    / "content"
    / "docs"
    / "reference"
    / "template-functions"
    / "reference-generated.md"
)


def generated_doc_path() -> Path:
    return _GENERATED_DOC


def live_generated_markdown() -> str:
    from scripts.generate_template_functions_reference import generate

    return generate()


def write_generated_doc() -> Path:
    from scripts.generate_template_functions_reference import generate

    path = generated_doc_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate(), encoding="utf-8")
    return path
