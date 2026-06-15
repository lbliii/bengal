#!/usr/bin/env python3
"""Lint changelog fragments and release pages for internal/meta leaks.

Enforces the highest-precision rules from ``docs/b-stack-changelog-strategy.md``:

  * No non-numeric ``(#slug)`` issue references — a reader cannot resolve a branch
    slug. (At the fragment level, issue-less fragments must be named
    ``+slug.<type>.md`` so Towncrier renders no reference at all.)
  * No internal coinage: ``Phase N``, ``Sprint``, ``saga``/saga-step codes
    (``S13.4a``), ``epic #N``, and ``plan/`` or ``benchmarks/`` file references.
  * No release-arc bookkeeping (``Nth patch off X``) or audit-process narration.

Fuzzy voice — signal-vs-noise, mechanism-vs-effect, counts, contributor-only
churn — stays a human/steward judgment. This lint blocks ONLY unambiguous
structural leaks, so it never nags about legitimate prose and is safe as a CI
gate. The narrow scope is deliberate.

Usage:
    python scripts/lint_changelog_voice.py              # fragments (the CI gate)
    python scripts/lint_changelog_voice.py --releases   # + site release pages
    python scripts/lint_changelog_voice.py --paths a.md b.md

Exit codes:
    0 - clean
    1 - leaks found
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAGMENT_DIR = REPO_ROOT / "changelog.d"
RELEASES_DIR = REPO_ROOT / "site" / "content" / "releases"

FRAGMENT_TYPES = {"added", "changed", "deprecated", "removed", "fixed", "security"}

# (compiled pattern, rule label, fix hint). Each is high-precision: it should not
# match legitimate user-facing prose. Patterns run line-by-line on text with
# fenced code blocks blanked out (see strip_code_fences).
BODY_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        # A parenthesized #token that is NOT a numeric issue and NOT a hex color:
        # require a hyphen or a non-hex letter (g-z) so (#FF9D00) / (#449) don't match.
        re.compile(r"\(`?#(?=[\w./-]*(?:-|[G-Zg-z]))[\w./-]+`?\)"),
        "non-numeric issue reference",
        "Cite a numeric issue like (#449), or drop it. Name issue-less fragments "
        "+slug.<type>.md so Towncrier renders no fake (#slug) reference.",
    ),
    (
        re.compile(r"\bphases?\s+\d", re.IGNORECASE),
        "internal phase coinage",
        "Drop the phase label; present the content directly.",
    ),
    (
        re.compile(r"\bsprint\b", re.IGNORECASE),
        "internal sprint coinage",
        "Drop sprint / process references.",
    ),
    (
        re.compile(r"\bsaga\b", re.IGNORECASE),
        "internal saga coinage",
        "Drop saga references.",
    ),
    (
        re.compile(r"\bepic\s+#?\d", re.IGNORECASE),
        "internal epic reference",
        "Drop the epic reference; describe the user-facing change.",
    ),
    (
        re.compile(r"\bS\d+\.\d+[a-z]?\b"),
        "saga-step code",
        "Drop the saga-step code (e.g. S13.4a).",
    ),
    (
        re.compile(r"\b(?:plan|benchmarks)/[\w./-]+\.(?:md|rst)\b"),
        "internal plan/benchmark file reference",
        "Don't reference internal plan or investigation files.",
    ),
    (
        re.compile(r"\brepo-wide audit\b", re.IGNORECASE),
        "process narration",
        "Describe what changed, not the audit that found it.",
    ),
    (
        re.compile(r"\bthe audit'?s\b", re.IGNORECASE),
        "process narration",
        "Describe what changed, not the audit process.",
    ),
    (
        re.compile(
            r"\b(?:first|second|third|fourth|fifth|sixth|\d+(?:st|nd|rd|th))\s+patch\s+off\b",
            re.IGNORECASE,
        ),
        "release-arc bookkeeping",
        "Drop the 'Nth patch off X' framing; state the release's character directly.",
    ),
]


class Finding(NamedTuple):
    path: Path
    line: int  # 0 == the filename itself, not a body line
    rule: str
    text: str
    hint: str


def strip_code_fences(text: str) -> str:
    """Blank out lines inside ``` fenced code blocks, preserving line numbers."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def scan_body(path: Path) -> list[Finding]:
    """Run every body rule line-by-line over a file's prose."""
    findings: list[Finding] = []
    text = strip_code_fences(path.read_text(encoding="utf-8"))
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, rule, hint in BODY_RULES:
            m = pattern.search(line)
            if m:
                findings.append(Finding(path, lineno, rule, m.group(0), hint))
    return findings


def fragment_type(path: Path) -> str | None:
    """Return the Towncrier type of a fragment file, or None if it isn't one."""
    name = path.name
    for ext in (".md", ".markdown"):
        if name.endswith(ext):
            stem = name[: -len(ext)]
            break
    else:
        return None
    parts = stem.split(".")
    if len(parts) < 2:
        return None
    ftype = parts[-1]
    return ftype if ftype in FRAGMENT_TYPES else None


def scan_fragment_filename(path: Path) -> Finding | None:
    """Flag a fragment whose issue token is non-numeric and lacks a leading '+'."""
    ftype = fragment_type(path)
    if ftype is None:
        return None
    stem = path.name.rsplit(".", 1)[0] if path.name.endswith(".md") else path.name
    issue = stem[: -(len(ftype) + 1)]  # drop ".<type>"
    if issue.startswith("+") or issue.isdigit():
        return None
    return Finding(
        path,
        0,
        "non-numeric fragment name",
        path.name,
        f"Rename to +{issue}.{ftype}.md (the leading '+' tells Towncrier there is "
        "no issue), or use a numeric issue number.",
    )


def collect_fragment_files() -> list[Path]:
    if not FRAGMENT_DIR.is_dir():
        return []
    return sorted(p for p in FRAGMENT_DIR.glob("*.md") if fragment_type(p) is not None)


def collect_release_files() -> list[Path]:
    if not RELEASES_DIR.is_dir():
        return []
    return sorted(p for p in RELEASES_DIR.glob("*.md") if p.stem != "_index")


def lint(paths: list[Path], *, check_fragment_names: bool) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if not path.is_file():
            print(f"warning: {path} not found, skipping", file=sys.stderr)
            continue
        if check_fragment_names:
            name_finding = scan_fragment_filename(path)
            if name_finding is not None:
                findings.append(name_finding)
        findings.extend(scan_body(path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--releases",
        action="store_true",
        help="Also lint site/content/releases/*.md (off by default to avoid "
        "failing on already-shipped pages; use at cut time).",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        type=Path,
        help="Lint exactly these files instead of the defaults.",
    )
    args = parser.parse_args()

    if args.paths:
        files = [p if p.is_absolute() else REPO_ROOT / p for p in args.paths]
        findings = lint(files, check_fragment_names=True)
        scanned = files
    else:
        files = collect_fragment_files()
        if args.releases:
            files = files + collect_release_files()
        findings = lint(files, check_fragment_names=True)
        scanned = files

    if not findings:
        n = len(scanned)
        print(f"changelog-lint: clean ({n} file{'s' if n != 1 else ''} scanned)")
        return 0

    by_path: dict[Path, list[Finding]] = {}
    for f in findings:
        by_path.setdefault(f.path, []).append(f)

    for path, items in by_path.items():
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            rel = path
        print(f"\n{rel}")
        for f in items:
            where = f"line {f.line}" if f.line else "filename"
            print(f"  {where}: [{f.rule}] {f.text!r}")
            print(f"      -> {f.hint}")

    print(
        f"\nchangelog-lint: {len(findings)} leak(s) in {len(by_path)} file(s). "
        "See docs/b-stack-changelog-strategy.md.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
