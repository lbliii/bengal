"""Unit tests for Git version worktree management."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from bengal.content.versioning.git_adapter import GitVersionAdapter
from bengal.core.version import GitVersionConfig

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
