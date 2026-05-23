"""Validate the PR Performance Evidence section."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

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


def missing_evidence_fields(body: str, *, allow_template: bool = False) -> tuple[str, ...]:
    """Return missing evidence fields, or an empty tuple when the section is valid."""
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
    payload = json.loads(path.read_text(encoding="utf-8"))
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    body = (
        body_from_github_event(args.github_event)
        if args.github_event is not None
        else args.body_file.read_text(encoding="utf-8")
    )
    missing = missing_evidence_fields(body, allow_template=args.allow_template)
    for field in missing:
        print(f"Missing Performance Evidence field: {field}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
