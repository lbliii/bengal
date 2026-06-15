#!/usr/bin/env python
"""Create or update the GitHub release for a version from its site release page.

Why this exists
---------------
The GitHub release title used to be built in the Makefile from a shell pipeline:

    VERSION=$(grep '^version = ' pyproject.toml | sed ...)
    PROJECT=$(grep '^name = ' pyproject.toml | sed ...)
    gh release create vX.Y.Z --title "$PROJECT $VERSION" ...

``grep '^name = '`` is greedy: ``pyproject.toml`` carries six
``[[tool.towncrier.type]]`` blocks, each with its own ``name = "..."`` line
(``Added``, ``Changed``, ``Deprecated``, ``Removed``, ``Fixed``, ``Security``).
So ``PROJECT`` collapsed to ``bengal Added Changed Deprecated Removed Fixed
Security`` and the v0.4.1 release title rendered as
``bengal Added Changed Deprecated Removed Fixed Security 0.4.1``.

This script replaces that brittle extraction with a robust, tested helper:

  * The version is read from ``[project].version`` via ``tomllib`` (never grep).
  * The title is ``v{version} — {theme}`` (em-dash), with the theme taken from
    the release page's frontmatter ``description:`` (first clause before its
    own em-dash), matching the v0.4.0 convention
    ``v0.4.0 — documentation generation grows up``.
  * The release body is the page content with its YAML frontmatter stripped.

Usage
-----
    # Dry-run (default): print the computed title + body preview, create nothing.
    python scripts/publish_github_release.py --version 0.4.1

    # Actually create (or update, if it already exists) the GitHub release:
    python scripts/publish_github_release.py --version 0.4.1 --create

    # Override the resolved theme:
    python scripts/publish_github_release.py --theme "A focused correctness patch" --create

It does NOT push tags or call git — that stays in the Makefile target. It is
dependency-free (stdlib only).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EM_DASH = "—"


def read_version_from_pyproject(text: str) -> str | None:
    """Return ``[project].version`` from a pyproject.toml string, or None.

    Uses ``tomllib`` so unrelated ``name = "..."`` / ``version = "..."`` lines
    inside ``[[tool.towncrier.type]]`` (or any other table) cannot leak into the
    result — the greedy-grep class of bug cannot recur.
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    return version if isinstance(version, str) and version else None


def split_frontmatter(page_text: str) -> tuple[str, str]:
    """Split a release page into (frontmatter, body).

    Frontmatter is the block between the first two ``---`` lines. If the page
    does not open with a frontmatter block, the whole text is the body and the
    frontmatter is empty.
    """
    lines = page_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", page_text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            frontmatter = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            return frontmatter, body
    # No closing fence — treat the whole thing as body.
    return "", page_text


def strip_frontmatter(page_text: str) -> str:
    """Return the release page body with its YAML frontmatter removed.

    The ``# Bengal X.Y.Z`` H1 and everything after the frontmatter is kept as-is
    (matching the historical ``awk`` behavior).
    """
    _, body = split_frontmatter(page_text)
    return body.lstrip("\n")


def parse_frontmatter_field(frontmatter: str, field: str) -> str | None:
    """Return the value of a top-level ``field:`` line in YAML frontmatter.

    Only simple single-line scalar fields are needed here (``description:``).
    """
    prefix = f"{field}:"
    for line in frontmatter.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def theme_from_description(description: str | None) -> str | None:
    """Derive the release theme from a frontmatter ``description:`` value.

    The description follows the convention ``<theme> — <details...>``; the theme
    is the first clause, truncated at the first em-dash and stripped. Returns
    None if there is no usable theme.
    """
    if not description:
        return None
    theme = description.split(EM_DASH, 1)[0].strip()
    return theme or None


def build_title(version: str, theme: str | None) -> str:
    """Compose the release title as ``v{version} — {theme}`` (or ``v{version}``)."""
    if theme:
        return f"v{version} {EM_DASH} {theme}"
    return f"v{version}"


def resolve_theme(explicit: str | None, frontmatter: str) -> str | None:
    """Resolve the theme: explicit arg wins, else the description's first clause."""
    if explicit and explicit.strip():
        return explicit.strip()
    return theme_from_description(parse_frontmatter_field(frontmatter, "description"))


def _gh(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def release_exists(tag: str) -> bool:
    """True if a GitHub release already exists for ``tag`` (re-runnable support)."""
    return _gh(["gh", "release", "view", tag]).returncode == 0


def publish_release(tag: str, title: str, body: str) -> None:
    """Create the release, or edit it if it already exists. Notes come from a tempfile."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", prefix=f"{tag}-notes-", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(body)
        notes_path = fh.name
    try:
        verb = "edit" if release_exists(tag) else "create"
        result = _gh(["gh", "release", verb, tag, "--title", title, "--notes-file", notes_path])
        if result.returncode != 0:
            sys.exit(f"error: `gh release {verb} {tag}` failed:\n{result.stderr.strip()}")
        print(f"{'Updated' if verb == 'edit' else 'Created'} GitHub release {tag}: {title}")
    finally:
        Path(notes_path).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--version", help="Version to release (default: read [project].version from pyproject.toml)"
    )
    parser.add_argument("--theme", help="Override the release theme used in the title")
    parser.add_argument(
        "--notes", help="Path to the release page (default: site/content/releases/<version>.md)"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Actually create/update the GitHub release (default is a dry-run preview)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the computed title + body preview and create nothing (the default)",
    )
    args = parser.parse_args()

    pyproject = REPO_ROOT / "pyproject.toml"
    version = args.version
    if not version:
        if not pyproject.exists():
            sys.exit(f"error: {pyproject} not found and no --version given")
        version = read_version_from_pyproject(pyproject.read_text(encoding="utf-8"))
    if not version:
        sys.exit("error: could not resolve version; pass --version")

    notes_path = (
        Path(args.notes)
        if args.notes
        else REPO_ROOT / "site" / "content" / "releases" / f"{version}.md"
    )
    if not notes_path.exists():
        sys.exit(
            f"error: release page {notes_path} not found. "
            "Draft it first (`uv run poe release-notes --version "
            f"{version}`) or pass --notes."
        )

    page_text = notes_path.read_text(encoding="utf-8")
    frontmatter, _ = split_frontmatter(page_text)
    theme = resolve_theme(args.theme, frontmatter)
    title = build_title(version, theme)
    body = strip_frontmatter(page_text)
    tag = f"v{version}"

    if args.dry_run or not args.create:
        print(f"[dry-run] title: {title}")
        print(f"[dry-run] tag:   {tag}")
        print(f"[dry-run] notes: {notes_path}")
        print("[dry-run] body preview (first 15 lines):")
        for line in body.splitlines()[:15]:
            print(f"    {line}")
        print("\nRe-run with --create to publish the release.")
        return

    publish_release(tag, title, body)


if __name__ == "__main__":
    main()
