#!/usr/bin/env python
"""Draft a user-facing doc-site release page from the compiled changelog.

Why this exists
---------------
Bengal keeps two release artifacts with two audiences:

  * ``CHANGELOG.md`` — the precise engineering record (every change, in full
    detail). Compiled from ``changelog.d/`` fragments by Towncrier at cut time.
  * ``site/content/releases/<version>.md`` — the *distilled, user-facing* story
    (key theme, themed highlights with examples, condensed lists, upgrade notes).

The distillation is a release-time, top-down editorial act: the theme and the
highlight groupings only exist once you can see the whole release, so it cannot
be pushed back into per-fragment authoring. This script produces a *first draft*
of the release page from the compiled ``[version]`` section of ``CHANGELOG.md``
(plus an optional milestone issue list and the previous release page as a style
exemplar), which a human then edits before shipping.

It does NOT add the ``anthropic`` SDK to Bengal's dependencies. Generation is
opt-in: if ``anthropic`` is importable and a key is configured it calls Claude;
otherwise (or with ``--bundle``) it writes a ready-to-run prompt + context bundle
to ``.context/`` that you can paste into Claude Code or any Claude client. Bundle
mode is pure stdlib.

Usage
-----
    # Generate a draft directly (needs `uv pip install anthropic` + ANTHROPIC_API_KEY):
    uv run python scripts/draft_release_notes.py --version 0.4.0 \
        --theme "Documentation generation grows up"

    # No API key / no SDK — emit a prompt bundle to run by hand:
    uv run python scripts/draft_release_notes.py --version 0.4.0 --bundle

    # Pull closed issues for the milestone into the context (needs `gh`):
    uv run python scripts/draft_release_notes.py --version 0.4.0 --milestone v0.4.0

The default model is Claude Opus 4.8 (``claude-opus-4-8``); override with --model.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
You are drafting a user-facing release-notes page for Bengal, a Python static
site generator. You will be given the compiled CHANGELOG.md section for one
version (the precise engineering record), an optional list of closed issues, an
optional release theme, and a previous release page as a STYLE EXEMPLAR.

The reader is a USER of Bengal, not a maintainer of it. They did not sit in our
planning, do not run our tests, and will never read the CHANGELOG looking for the
audit that found a bug. They want one thing: what changed for me, and what do I
do about it. Your job is to distill the dense engineering record into that.

STRUCTURE (progressive disclosure — each layer reads on its own):
  1. YAML frontmatter (title, description, date, draft: false, lang: en, tags,
     keywords, category: changelog) matching the exemplar's frontmatter keys.
  2. An `# Bengal <version>` H1, then a `**Key theme:**` one-paragraph hook. A
     reader who reads only this paragraph should understand the release.
  3. A highlights section: 4-7 `###` subsections, each leading with what a USER
     can now do ("you can now ..."), with short code examples where they help.
     Group related changes into themes; do NOT list every fragment.
  4. CONDENSED `## Added` / `## Changed` / `## Fixed` / `## Removed` lists — a
     skim layer, one short bullet per USER-MEANINGFUL change. Compress hard.
  5. An `## Upgrading` section: the install command plus any action the user must
     take (migrations, default flips, removed imports, dependency bumps).

THE USER-FACING TEST — keep a change only if the user can OBSERVE it:
  - They type / import / call / unpack it (CLI command/flag, config key,
    frontmatter key, template function, public import path, factory parameter,
    documented return-tuple contract), OR
  - They see / grep / find it (build-output text, an emitted file, an error
    string, a fingerprinted filename, a surfaced health/error code), OR
  - They must act on it (migration, default flip, removed import, dependency bump).
  If a change answers NONE of these, it is internal: OMIT it entirely.
  This test also PROTECTS internal-looking detail that is genuinely user-facing
  (a real public API, a config key, an error string the user saw) — keep those.

NEVER INCLUDE (these are leaks — drop them, do not rephrase them):
  - Internal coinage: "Phase 2", "Phase 1A", "Sprint", "saga S13.4", "epic #350",
    RFC / plan-file names, branch slugs, codenames.
  - Process / journey narration: "a repo-wide audit", "surfaced after the cut",
    "discovered in CI", "the largest change in X's history", "Nth patch off Y".
  - Project bookkeeping: fix/file/line counts, ty-diagnostic floors, health-score
    percentages, test counts.
  - Contributor-only churn: test additions, guard tests, de-vacuumed assertions,
    CI gates, import-linter contracts, behavior-preserving refactors, dead-code
    removal, type/lint hygiene, and our own release/build tooling (gh-release,
    Towncrier, publish workflows). A user never runs any of it.
  - Untranslated mechanism: an internal class/module/log-key as the SUBJECT of a
    change. State the user-visible EFFECT instead (e.g. "incremental builds are
    faster and rebuild fewer pages", not "fingerprint fast paths are reused").
  - Off-by-default scaffolding with no caller (byte-identical default build).

TRANSLATION EXAMPLES (record -> release page):
  - "lazy Kida context is preserved, fingerprint fast paths are reused, version
    membership is memoized" -> "Incremental builds are faster and rebuild fewer
    pages."
  - "Removed the never-called `phase_cache_save` helper" -> OMIT.
  - "### i18n Gettext Workflow (Phase 1A)" -> "### i18n Gettext Workflow".
  - "unified the two `RebuildReasonCode`/`RebuildReason` definitions" -> "Rebuild
    reasons are now reported consistently."

ISSUE REFERENCES:
  - Cite a NUMERIC issue/PR like (#449) only when a reader would actually click it
    (track a limitation, see a repro, follow remaining work). Not a per-bullet
    reflex — drop it if it adds nothing for the reader.
  - NEVER emit a non-numeric token like (#some-branch-slug) or a plan-file path.

VOICE (one B-Stack voice across all repos):
  - Confident, plain, concrete, benefit-first, present tense.
  - No marketing fluff ("blazing", "massive", "seamless", "the largest ... ever")
    and no hedging ("should now", "we believe"). Say what is true, plainly.
  - Delight is clarity plus a little warmth, not exclamation points. The reader
    should finish a note knowing exactly what changed and why it's good.

THEME / KEY-THEME HOOK:
  - The theme describes WHAT THE RELEASE CONTAINS OR ENABLES for the user, not a
    verdict on the project's quality, maturity, or past behavior. Test: if a
    future release could plausibly need the same theme again, it's overclaiming.
  - Avoid maturity claims ("grows up", "production-ready"), virtue-achieved claims
    for perennial qualities ("Honest internals", "Rock solid"), confessions ("Stop
    shipping wrong output"), and release-to-release arcs ("Where 0.4.1 did X...").
  - Prefer a content/capability anchor: "Visible build failures and crash-safe
    writes" over "Honest internals"; for a patch, a plain repeatable theme like
    "Correctness and data-safety fixes" is fine. Honor an explicit --theme, but if
    it is a verdict-theme, reframe it to the concrete user-facing content.

HARD RULES:
  - Be accurate. Every claim must be supported by the changelog input. Do not
    invent features, numbers, flags, or issue numbers. You may quote a perf number
    that appears in the changelog; never fabricate one.
  - Output ONLY the markdown file content, starting at the `---` frontmatter.
    No preamble, no explanation, no surrounding code fences.
"""


def run(cmd: list[str]) -> str:
    """Run a command from the repo root, returning stdout (empty on failure)."""
    try:
        out = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        return out.stdout
    except subprocess.CalledProcessError, FileNotFoundError:
        return ""


def read_version_from_pyproject() -> str | None:
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*version\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    return None


def extract_changelog_section(changelog: Path, version: str) -> str:
    """Pull the `## [<version>] ...` block, up to the next `## [` heading."""
    if not changelog.exists():
        sys.exit(f"error: {changelog} not found")
    lines = changelog.read_text(encoding="utf-8").splitlines()
    # Match the heading for this version specifically (escape dots).
    start_re = re.compile(rf"^## \[{re.escape(version)}\]")
    next_re = re.compile(r"^## \[")
    collected: list[str] = []
    capturing = False
    for line in lines:
        if start_re.match(line):
            capturing = True
            collected.append(line)
            continue
        if capturing and next_re.match(line):
            break
        if capturing:
            collected.append(line)
    body = "\n".join(collected).strip()
    if not body:
        sys.exit(
            f"error: no '## [{version}]' section found in {changelog}. "
            "Run `uv run poe changelog` (or `towncrier build --version <v>`) first."
        )
    return body


def find_style_exemplar(releases_dir: Path, version: str) -> tuple[str, str] | None:
    """Return (name, text) of the highest-versioned release page that isn't `version`."""
    if not releases_dir.is_dir():
        return None

    def version_key(p: Path) -> tuple[int, ...]:
        return tuple(int(x) for x in re.findall(r"\d+", p.stem))

    candidates = sorted(
        (p for p in releases_dir.glob("*.md") if p.stem != version and p.stem != "_index"),
        key=version_key,
        reverse=True,
    )
    if not candidates:
        return None
    best = candidates[0]
    return best.name, best.read_text(encoding="utf-8")


def fetch_milestone_issues(milestone: str) -> str:
    """Best-effort: closed issues for a milestone, via gh. Empty string on failure."""
    out = run(
        [
            "gh",
            "issue",
            "list",
            "--milestone",
            milestone,
            "--state",
            "closed",
            "--limit",
            "100",
            "--json",
            "number,title",
            "--jq",
            r'.[] | "- #\(.number): \(.title)"',
        ]
    )
    return out.strip()


def build_user_prompt(
    version: str,
    theme: str | None,
    changelog_section: str,
    issues: str,
    exemplar: tuple[str, str] | None,
    date: str | None,
) -> str:
    parts: list[str] = [f"Draft the release page for **Bengal {version}**."]
    if date:
        parts.append(f"Release date (frontmatter `date:`): {date}")
    if theme:
        parts.append(f"Release theme / headline: {theme}")
    if exemplar:
        name, text = exemplar
        parts.append(
            f"STYLE EXEMPLAR — the previous release page `{name}`. Match its "
            f"frontmatter keys, section structure, and voice:\n\n{text}"
        )
    if issues:
        parts.append(f"Closed issues in this release (for context):\n\n{issues}")
    parts.append(
        "COMPILED CHANGELOG SECTION to distill (the engineering record — "
        f"compress into the user-facing page):\n\n{changelog_section}"
    )
    return "\n\n---\n\n".join(parts)


def strip_fences(text: str) -> str:
    """Remove a leading/trailing markdown code fence and any preamble before `---`."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text).strip()
    # Drop any chatter before the YAML frontmatter.
    idx = text.find("---")
    if idx > 0:
        text = text[idx:]
    return text.strip() + "\n"


def generate_with_claude(system: str, user_prompt: str, model: str) -> str | None:
    """Call Claude to produce the draft. Returns None if the SDK isn't available."""
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY / profile from env
        with client.messages.stream(
            model=model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError:
        print(
            "error: no Anthropic credentials (set ANTHROPIC_API_KEY). Falling back to --bundle.",
            file=sys.stderr,
        )
        return None
    text = "".join(b.text for b in message.content if b.type == "text")
    return strip_fences(text)


def write_bundle(version: str, system: str, user_prompt: str) -> Path:
    """Write a paste-ready prompt + context bundle for manual Claude use."""
    out = REPO_ROOT / ".context" / f"release-notes-{version}-prompt.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"# Release-notes draft prompt for Bengal {version}\n\n"
        "Paste the SYSTEM and USER blocks below into Claude (Opus 4.8 recommended) "
        "to draft `site/content/releases/" + version + ".md`, then edit before shipping.\n\n"
        "## SYSTEM\n\n```\n" + system + "\n```\n\n"
        "## USER\n\n```\n" + user_prompt + "\n```\n",
        encoding="utf-8",
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", help="Version to draft (default: read from pyproject.toml)")
    parser.add_argument("--theme", help="Release theme / headline hook")
    parser.add_argument("--date", help="Release date for frontmatter (e.g. 2026-06-12)")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to compiled changelog")
    parser.add_argument("--milestone", help="GitHub milestone to pull closed issues from (via gh)")
    parser.add_argument("--out", help="Output path (default: site/content/releases/<version>.md)")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--bundle", action="store_true", help="Emit a prompt bundle instead of calling the API"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite the output file if it exists"
    )
    args = parser.parse_args()

    version = args.version or read_version_from_pyproject()
    if not version:
        sys.exit("error: could not resolve version; pass --version")

    changelog = (
        (REPO_ROOT / args.changelog)
        if not Path(args.changelog).is_absolute()
        else Path(args.changelog)
    )
    changelog_section = extract_changelog_section(changelog, version)
    exemplar = find_style_exemplar(REPO_ROOT / "site" / "content" / "releases", version)
    issues = fetch_milestone_issues(args.milestone) if args.milestone else ""

    user_prompt = build_user_prompt(
        version, args.theme, changelog_section, issues, exemplar, args.date
    )

    if args.bundle:
        path = write_bundle(version, SYSTEM_PROMPT, user_prompt)
        print(f"Wrote prompt bundle: {path.relative_to(REPO_ROOT)}")
        return

    draft = generate_with_claude(SYSTEM_PROMPT, user_prompt, args.model)
    if draft is None:
        path = write_bundle(version, SYSTEM_PROMPT, user_prompt)
        print(
            "anthropic SDK or credentials unavailable — wrote a prompt bundle instead:\n"
            f"  {path.relative_to(REPO_ROOT)}\n"
            "Install with `uv pip install anthropic` and set ANTHROPIC_API_KEY to generate directly.",
            file=sys.stderr,
        )
        return

    out = (
        Path(args.out)
        if args.out
        else REPO_ROOT / "site" / "content" / "releases" / f"{version}.md"
    )
    if out.exists() and not args.force:
        sys.exit(
            f"error: {out} already exists. Re-run with --force to overwrite, "
            "or pass --out to write elsewhere."
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(draft, encoding="utf-8")
    print(f"Wrote release-page draft: {out.relative_to(REPO_ROOT)}")
    print("Review and edit before shipping — this is a first draft, not final copy.")


if __name__ == "__main__":
    main()
