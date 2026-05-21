"""Integration tests for Git-backed versioned documentation builds."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from tests._testing.cli import run_cli

if TYPE_CHECKING:
    from pathlib import Path


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_site(site_root: Path) -> None:
    _write(
        site_root / "bengal.toml",
        """
[site]
title = "Git Versioned Test"
baseurl = "/"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"

[markdown]
parser = "patitas"
""",
    )
    _write(
        site_root / "config" / "_default" / "versioning.yaml",
        """
versioning:
  enabled: true
  mode: git
  sections:
    - docs
  git:
    branches:
      - name: main
        latest: true
      - pattern: "release/*"
        strip_prefix: "release/"
    default_branch: main
    cache_worktrees: true
    parallel_builds: 2
  aliases:
    latest: main
""",
    )
    _write(site_root / "content" / "index.md", "---\ntitle: Home\n---\n# Home\n")
    _write(site_root / "content" / "docs" / "_index.md", "---\ntitle: Docs\n---\n# Docs\n")


def _write_auto_tag_versioning(site_root: Path, *, count: int = 2) -> None:
    _write(
        site_root / "config" / "_default" / "versioning.yaml",
        f"""
versioning:
  enabled: true
  mode: git
  sections:
    - docs
  git:
    latest:
      branch: main
      id: main
      label: Latest
    previous:
      source: tags
      count: {count}
      pattern: "v*"
      strip_prefix: "v"
      sort: semver-desc
      include_prereleases: false
    default_branch: main
    cache_worktrees: true
    parallel_builds: 2
  aliases:
    latest: main
""",
    )


def _write_disabled_versioning(site_root: Path) -> None:
    _write(
        site_root / "config" / "_default" / "versioning.yaml",
        """
versioning:
  enabled: false
""",
    )


def _write_docs_page(site_root: Path, version_label: str) -> None:
    _write(
        site_root / "content" / "docs" / "guide.md",
        f"""---
title: Guide {version_label}
---
# Guide {version_label}

This page belongs to {version_label}.
""",
    )


def _make_git_versioned_site(tmp_path: Path) -> Path:
    site_root = tmp_path / "git-versioned-site"
    site_root.mkdir()
    _write_site(site_root)
    _write_docs_page(site_root, "main")

    _run_git(site_root, "init", "-b", "main")
    _run_git(site_root, "config", "user.email", "bengal-test@example.test")
    _run_git(site_root, "config", "user.name", "Bengal Test")
    _run_git(site_root, "config", "commit.gpgsign", "false")
    _run_git(site_root, "add", ".")
    _run_git(site_root, "commit", "-m", "main docs")

    for version in ("v2", "v1"):
        _run_git(site_root, "checkout", "-b", f"release/{version}")
        _write_docs_page(site_root, version)
        _write(
            site_root / "config" / "_default" / "versioning.yaml",
            """
versioning:
  enabled: false
""",
        )
        _run_git(site_root, "add", "content/docs/guide.md")
        _run_git(site_root, "add", "config/_default/versioning.yaml")
        _run_git(site_root, "commit", "-m", f"{version} docs")

    _run_git(site_root, "checkout", "main")
    return site_root


def _make_git_tag_versioned_site(tmp_path: Path) -> Path:
    site_root = tmp_path / "git-tag-versioned-site"
    site_root.mkdir()
    _write_site(site_root)
    _write_auto_tag_versioning(site_root)
    _write_docs_page(site_root, "0.3.0")

    _run_git(site_root, "init", "-b", "main")
    _run_git(site_root, "config", "user.email", "bengal-test@example.test")
    _run_git(site_root, "config", "user.name", "Bengal Test")
    _run_git(site_root, "config", "commit.gpgsign", "false")
    _run_git(site_root, "add", ".")
    _run_git(site_root, "commit", "-m", "0.3.0 docs")
    _run_git(site_root, "tag", "v0.3.0")

    for version in ("0.3.1", "0.3.2", "0.4.0-rc.1"):
        _write_docs_page(site_root, version)
        _write_disabled_versioning(site_root)
        _run_git(site_root, "add", "content/docs/guide.md")
        _run_git(site_root, "add", "config/_default/versioning.yaml")
        _run_git(site_root, "commit", "-m", f"{version} docs")
        _run_git(site_root, "tag", f"v{version}")

    _write_docs_page(site_root, "main")
    _write_auto_tag_versioning(site_root)
    _run_git(site_root, "add", "content/docs/guide.md")
    _run_git(site_root, "add", "config/_default/versioning.yaml")
    _run_git(site_root, "commit", "-m", "main docs")

    return site_root


def test_git_all_versions_build_outputs_canonical_version_paths(tmp_path: Path) -> None:
    site_root = _make_git_versioned_site(tmp_path)

    result = run_cli(["build", "--all-versions", "--quiet"], cwd=str(site_root), timeout=120)

    result.assert_ok()
    public = site_root / "public"
    assert (public / "docs" / "guide" / "index.html").exists()
    assert (public / "docs" / "v2" / "guide" / "index.html").exists()
    assert (public / "docs" / "v1" / "guide" / "index.html").exists()
    assert (public / "versions.json").exists()


def test_git_auto_previous_tags_build_latest_and_recent_tag_paths(tmp_path: Path) -> None:
    site_root = _make_git_tag_versioned_site(tmp_path)

    result = run_cli(["build", "--all-versions", "--quiet"], cwd=str(site_root), timeout=120)

    result.assert_ok()
    public = site_root / "public"
    assert (public / "docs" / "guide" / "index.html").exists()
    assert (public / "docs" / "0.3.2" / "guide" / "index.html").exists()
    assert (public / "docs" / "0.3.1" / "guide" / "index.html").exists()
    assert not (public / "docs" / "0.3.0" / "guide" / "index.html").exists()
    assert not (public / "docs" / "0.4.0-rc.1" / "guide" / "index.html").exists()
    versions_json = (public / "versions.json").read_text(encoding="utf-8")
    assert '"version": "main"' in versions_json
    assert '"version": "0.3.2"' in versions_json
    assert '"version": "0.3.1"' in versions_json
    assert '"version": "0.3.0"' not in versions_json
    assert '"version": "0.4.0-rc.1"' not in versions_json


def test_git_all_versions_prunes_unselected_version_outputs(tmp_path: Path) -> None:
    site_root = _make_git_tag_versioned_site(tmp_path)
    _write_auto_tag_versioning(site_root, count=3)

    first = run_cli(["build", "--all-versions", "--quiet"], cwd=str(site_root), timeout=120)
    first.assert_ok()
    public = site_root / "public"
    assert (public / "docs" / "0.3.0" / "guide" / "index.html").exists()

    _write_auto_tag_versioning(site_root, count=2)
    second = run_cli(["build", "--all-versions", "--quiet"], cwd=str(site_root), timeout=120)

    second.assert_ok()
    assert (public / "docs" / "0.3.2" / "guide" / "index.html").exists()
    assert (public / "docs" / "0.3.1" / "guide" / "index.html").exists()
    assert not (public / "docs" / "0.3.0").exists()


def test_git_specific_version_build_outputs_only_requested_version(tmp_path: Path) -> None:
    site_root = _make_git_versioned_site(tmp_path)

    result = run_cli(
        ["build", "--build-version", "v2", "--quiet"],
        cwd=str(site_root),
        timeout=120,
    )

    result.assert_ok()
    public = site_root / "public"
    assert (public / "docs" / "v2" / "guide" / "index.html").exists()
    assert not (public / "docs" / "v1" / "guide" / "index.html").exists()


def test_git_version_diff_uses_configured_content_dir(tmp_path: Path) -> None:
    site_root = _make_git_versioned_site(tmp_path)

    result = run_cli(
        [
            "version",
            "diff",
            "--old-version",
            "main",
            "--new-version",
            "release/v2",
            "--git",
            "--output",
            "json",
        ],
        cwd=str(site_root),
        timeout=60,
    )

    result.assert_ok()
    assert "content/docs/guide.md" in result.stdout
