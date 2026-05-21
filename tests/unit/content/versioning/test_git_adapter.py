"""Unit tests for Git version worktree management."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from bengal.content.versioning.git_adapter import GitVersionAdapter
from bengal.core.version import GitLatestConfig, GitPreviousConfig, GitVersionConfig

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


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-b", "main")
    _run_git(repo, "config", "user.email", "bengal-test@example.test")
    _run_git(repo, "config", "user.name", "Bengal Test")
    _run_git(repo, "config", "commit.gpgsign", "false")
    _write(repo / "content" / "docs" / "guide.md", "# main\n")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "main docs")
    _run_git(repo, "checkout", "-b", "release/v1")
    _write(repo / "content" / "docs" / "guide.md", "# v1\n")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "v1 docs")
    _run_git(repo, "checkout", "main")
    return repo


def test_reuses_cached_worktree_at_expected_commit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    adapter = GitVersionAdapter(repo, GitVersionConfig())

    first = adapter.get_or_create_worktree("v1", "release/v1")
    sentinel = first.path / "sentinel.txt"
    sentinel.write_text("kept", encoding="utf-8")

    second = adapter.get_or_create_worktree("v1", "release/v1")

    assert second.path == first.path
    assert sentinel.read_text(encoding="utf-8") == "kept"


def test_detects_ref_at_current_checkout(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    adapter = GitVersionAdapter(repo, GitVersionConfig())

    assert adapter.is_ref_current_checkout("main") is True
    assert adapter.is_ref_current_checkout("release/v1") is False


def test_discovers_latest_branch_and_previous_semver_tags(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _run_git(repo, "checkout", "main")

    for version in ("0.3.0", "0.3.1", "0.3.2", "0.4.0-rc.1"):
        _write(repo / "content" / "docs" / "guide.md", f"# {version}\n")
        _run_git(repo, "add", "content/docs/guide.md")
        _run_git(repo, "commit", "-m", f"{version} docs")
        _run_git(repo, "tag", f"v{version}")

    adapter = GitVersionAdapter(
        repo,
        GitVersionConfig(
            latest=GitLatestConfig(branch="main", id="main", label="Latest"),
            previous=GitPreviousConfig(count=2, pattern="v*", strip_prefix="v"),
        ),
    )

    versions = adapter.discover_versions()

    assert [version.id for version in versions] == ["main", "0.3.2", "0.3.1"]
    assert versions[0].latest is True
    assert versions[0].source == "git:main"
    assert versions[1].source == "git:v0.3.2"


def test_previous_tags_can_include_prereleases(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _run_git(repo, "checkout", "main")

    for version in ("0.3.0", "0.4.0-rc.1"):
        _write(repo / "content" / "docs" / "guide.md", f"# {version}\n")
        _run_git(repo, "add", "content/docs/guide.md")
        _run_git(repo, "commit", "-m", f"{version} docs")
        _run_git(repo, "tag", f"v{version}")

    adapter = GitVersionAdapter(
        repo,
        GitVersionConfig(
            latest=GitLatestConfig(branch="main", id="main"),
            previous=GitPreviousConfig(
                count=1,
                pattern="v*",
                strip_prefix="v",
                include_prereleases=True,
            ),
        ),
    )

    versions = adapter.discover_versions()

    assert [version.id for version in versions] == ["main", "0.4.0-rc.1"]
