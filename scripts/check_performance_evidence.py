"""Validate the PR Performance Evidence section."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

PERFORMANCE_SECTION = "Performance Evidence"
REQUIRED_FIELDS = (
    "Benchmark matrix row",
    "Command",
    "Python build",
    "Machine/OS",
    "Baseline commit or saved result",
    "Current commit or saved result",
    "Artifact path",
    "Interpretation",
)
DOC_ONLY_PREFIXES = ("site/", "docs/", "plan/", "skills/", ".context/")
DOC_ONLY_FILENAMES = frozenset({"LICENSE"})


def extract_section(body: str, heading: str = PERFORMANCE_SECTION) -> str:
    """Return a Markdown section body by level-two heading."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$"
        r"(?P<section>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    return match.group("section").strip() if match else ""


def field_values(section: str) -> dict[str, str]:
    """Return field values from the Performance Evidence checklist."""
    values: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        pattern = re.compile(
            rf"^[ \t]*-[ \t]*{re.escape(field)}:[ \t]*(?P<value>.*)$",
            re.MULTILINE,
        )
        match = pattern.search(section)
        if match:
            values[field] = match.group("value").strip()
    return values


def is_docs_only_file(path: str) -> bool:
    """Return whether a changed file is documentation/planning-only."""
    normalized = path.strip().replace("\\", "/")
    if not normalized:
        return True
    return (
        normalized.startswith(DOC_ONLY_PREFIXES)
        or normalized.endswith(".md")
        or normalized in DOC_ONLY_FILENAMES
    )


def has_performance_sensitive_changes(changed_files: Iterable[str]) -> bool:
    """Return whether changed files require performance evidence."""
    paths = tuple(path for path in changed_files if path.strip())
    if not paths:
        return True
    return any(not is_docs_only_file(path) for path in paths)


def changed_files_from_file(path: Path) -> tuple[str, ...]:
    """Read changed file paths from a newline-delimited file."""
    return tuple(
        line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def payload_from_github_event(path: Path) -> dict[str, object]:
    """Read a GitHub event payload."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _github_api_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bengal-performance-evidence-check",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def changed_files_from_github_event(path: Path) -> tuple[str, ...] | None:
    """Fetch changed files for a pull-request event payload."""
    payload = payload_from_github_event(path)
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    pull_request_url = pull_request.get("url")
    if not isinstance(pull_request_url, str):
        return None

    filenames: list[str] = []
    for page in range(1, 100):
        files_url = f"{pull_request_url}/files?per_page=100&page={page}"
        try:
            page_payload = _github_api_json(files_url)
        except OSError:
            return None
        except json.JSONDecodeError:
            return None
        if not isinstance(page_payload, list):
            return None
        filenames.extend(
            item["filename"]
            for item in page_payload
            if isinstance(item, dict) and isinstance(item.get("filename"), str)
        )
        if len(page_payload) < 100:
            return tuple(filenames)
    return tuple(filenames)


def missing_evidence_fields(
    body: str,
    *,
    allow_template: bool = False,
    changed_files: Iterable[str] | None = None,
) -> tuple[str, ...]:
    """Return missing evidence fields, or an empty tuple when the section is valid."""
    if changed_files is not None and not has_performance_sensitive_changes(changed_files):
        return ()
    section = extract_section(body)
    if not section:
        return (PERFORMANCE_SECTION,)
    values = field_values(section)
    if allow_template:
        return tuple(field for field in REQUIRED_FIELDS if field not in values)
    if any(value.lower() == "not applicable" for value in values.values()):
        return ()

    return tuple(field for field in REQUIRED_FIELDS if not values.get(field))


def body_from_github_event(path: Path) -> str:
    """Read a pull-request body from a GitHub event payload."""
    payload = payload_from_github_event(path)
    pull_request = payload.get("pull_request", {})
    body = pull_request.get("body") or ""
    if not isinstance(body, str):
        return ""
    return body


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--body-file", type=Path, help="Markdown file containing a PR body")
    source.add_argument("--github-event", type=Path, help="GitHub event JSON payload")
    parser.add_argument(
        "--allow-template",
        action="store_true",
        help="Only require that the Performance Evidence fields are present.",
    )
    parser.add_argument(
        "--changed-files-file",
        type=Path,
        help=(
            "Newline-delimited changed files. When all files are docs/plans, "
            "Performance Evidence is not required."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    body = (
        body_from_github_event(args.github_event)
        if args.github_event is not None
        else args.body_file.read_text(encoding="utf-8")
    )
    changed_files = (
        changed_files_from_file(args.changed_files_file)
        if args.changed_files_file is not None
        else changed_files_from_github_event(args.github_event)
        if args.github_event is not None
        else None
    )
    missing = missing_evidence_fields(
        body,
        allow_template=args.allow_template,
        changed_files=changed_files,
    )
    for field in missing:
        print(f"Missing Performance Evidence field: {field}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
