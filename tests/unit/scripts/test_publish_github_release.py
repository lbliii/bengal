"""Tests for ``scripts/publish_github_release.py``.

These are #130-style *discriminating* tests: each assertion is designed to go
red if the original greedy-grep bug — or its title-formatting consequence — is
reintroduced. The headline guard is that a release title derived from a real
release page must never contain a towncrier category word (``Added``,
``Changed``, ``Security``, ...), because that is exactly what the old
``grep '^name ='`` pipeline leaked into the title.
"""

from __future__ import annotations

import pytest

from scripts.publish_github_release import (
    build_title,
    read_version_from_pyproject,
    resolve_theme,
    split_frontmatter,
    strip_frontmatter,
    theme_from_description,
)

# A pyproject.toml that reproduces the exact shape that broke the old grep:
# the [project] name/version, PLUS six [[tool.towncrier.type]] blocks each with
# their own `name = "..."` line. `grep '^name ='` matched all seven.
PYPROJECT_WITH_TOWNCRIER = """\
[project]
name = "bengal"
version = "0.4.1"
description = "Python static site generator"

[[tool.towncrier.type]]
directory = "added"
name = "Added"
showcontent = true

[[tool.towncrier.type]]
directory = "changed"
name = "Changed"
showcontent = true

[[tool.towncrier.type]]
directory = "deprecated"
name = "Deprecated"
showcontent = true

[[tool.towncrier.type]]
directory = "removed"
name = "Removed"
showcontent = true

[[tool.towncrier.type]]
directory = "fixed"
name = "Fixed"
showcontent = true

[[tool.towncrier.type]]
directory = "security"
name = "Security"
showcontent = true
"""

# A release page mirroring site/content/releases/0.4.1.md: frontmatter whose
# `description:` opens with a theme clause, then an em-dash, then details.
SAMPLE_RELEASE_PAGE = """\
---
title: Bengal 0.4.1
description: A focused correctness patch — valid JSON-LD on every doc page and more.
date: 2026-06-15
draft: false
tags: [release, changelog, patch]
category: changelog
---

# Bengal 0.4.1

**Key theme:** Stop shipping wrong output.

## What's fixed

- Valid JSON-LD on every doc page (#442).
"""

TOWNCRIER_CATEGORIES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")


class TestVersionResolution:
    def test_reads_project_version_not_towncrier_names(self):
        """Version must come from [project].version, ignoring [[tool.towncrier.type]] names.

        Proves the greedy-grep class of bug cannot recur: even with six
        `name = "..."` lines present, only the [project] table is consulted.
        """
        assert read_version_from_pyproject(PYPROJECT_WITH_TOWNCRIER) == "0.4.1"

    def test_returns_none_without_project_version(self):
        assert read_version_from_pyproject('[tool.foo]\nname = "x"\n') is None

    def test_returns_none_on_invalid_toml(self):
        assert read_version_from_pyproject("this is = = not toml [[[") is None


class TestThemeAndTitle:
    def test_theme_from_description_truncates_at_em_dash(self):
        desc = "A focused correctness patch — valid JSON-LD on every doc page and more."
        assert theme_from_description(desc) == "A focused correctness patch"

    def test_theme_none_when_no_description(self):
        assert theme_from_description(None) is None

    def test_explicit_theme_wins_over_frontmatter(self):
        frontmatter, _ = split_frontmatter(SAMPLE_RELEASE_PAGE)
        assert resolve_theme("Custom theme", frontmatter) == "Custom theme"

    def test_resolve_theme_falls_back_to_description(self):
        frontmatter, _ = split_frontmatter(SAMPLE_RELEASE_PAGE)
        assert resolve_theme(None, frontmatter) == "A focused correctness patch"

    def test_title_from_page_is_version_em_dash_theme(self):
        """The headline #130 guard: title = `vX.Y.Z — <first clause>`."""
        frontmatter, _ = split_frontmatter(SAMPLE_RELEASE_PAGE)
        theme = resolve_theme(None, frontmatter)
        title = build_title("0.4.1", theme)
        assert title == "v0.4.1 — A focused correctness patch"

    def test_title_never_contains_towncrier_category_words(self):
        """Discriminating guard against the original greedy-grep title bug.

        The old title was `bengal Added Changed Deprecated Removed Fixed
        Security 0.4.1`. A correct title built from the release page must contain
        none of those category words.
        """
        frontmatter, _ = split_frontmatter(SAMPLE_RELEASE_PAGE)
        theme = resolve_theme(None, frontmatter)
        title = build_title("0.4.1", theme)
        for category in TOWNCRIER_CATEGORIES:
            assert category not in title, f"title leaked towncrier category {category!r}: {title!r}"

    def test_title_without_theme_is_bare_version(self):
        assert build_title("0.5.0", None) == "v0.5.0"


class TestFrontmatterStripping:
    def test_split_returns_body_after_second_fence(self):
        frontmatter, body = split_frontmatter(SAMPLE_RELEASE_PAGE)
        assert "title: Bengal 0.4.1" in frontmatter
        assert body.lstrip().startswith("# Bengal 0.4.1")
        assert "---" not in frontmatter  # the fences themselves are excluded

    def test_strip_frontmatter_keeps_h1_and_body(self):
        body = strip_frontmatter(SAMPLE_RELEASE_PAGE)
        assert body.startswith("# Bengal 0.4.1")
        assert "description:" not in body  # frontmatter gone
        assert "(#442)" in body  # body content preserved

    def test_no_frontmatter_returns_text_unchanged(self):
        text = "# Just a heading\n\nbody text\n"
        frontmatter, body = split_frontmatter(text)
        assert frontmatter == ""
        assert body == text


class TestOldBehaviorWouldFail:
    """Simulate the old greedy-grep behavior and prove the guard catches it.

    This documents the RED side of the #130 invert-check: if title derivation
    ever collapsed back to the grep-greedy form, the category-word guard above
    would fail. Here we assert that the *simulated* bad title indeed trips it.
    """

    @staticmethod
    def _greedy_grep_title(pyproject: str, version: str) -> str:
        """Reproduce the buggy `grep '^name =' | --title "$PROJECT $VERSION"`."""
        names = [
            line.split("=", 1)[1].strip().strip('"')
            for line in pyproject.splitlines()
            if line.startswith("name = ")
        ]
        project = " ".join(names)
        return f"{project} {version}"

    def test_simulated_old_title_leaks_categories(self):
        bad = self._greedy_grep_title(PYPROJECT_WITH_TOWNCRIER, "0.4.1")
        assert bad == "bengal Added Changed Deprecated Removed Fixed Security 0.4.1"
        # The exact failure the new code prevents:
        leaked = [c for c in TOWNCRIER_CATEGORIES if c in bad]
        assert leaked == list(TOWNCRIER_CATEGORIES)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
