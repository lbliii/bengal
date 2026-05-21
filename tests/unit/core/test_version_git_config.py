"""Tests for Git-backed versioning configuration parsing."""

from __future__ import annotations

from bengal.core.version import VersionConfig


def test_git_latest_and_previous_config_parse_from_dict() -> None:
    config = VersionConfig.from_config(
        {
            "versioning": {
                "enabled": True,
                "mode": "git",
                "sections": ["docs"],
                "git": {
                    "latest": {
                        "branch": "main",
                        "id": "main",
                        "label": "Latest",
                    },
                    "previous": {
                        "source": "tags",
                        "count": 3,
                        "pattern": "v*",
                        "strip_prefix": "v",
                        "sort": "semver-desc",
                        "include_prereleases": False,
                    },
                    "cache_worktrees": True,
                    "parallel_builds": 2,
                },
                "aliases": {"latest": "main"},
            }
        }
    )

    assert config.is_git_mode
    assert config.git_config is not None
    assert config.git_config.latest is not None
    assert config.git_config.latest.branch == "main"
    assert config.git_config.latest.id == "main"
    assert config.git_config.latest.label == "Latest"
    assert config.git_config.previous is not None
    assert config.git_config.previous.source == "tags"
    assert config.git_config.previous.count == 3
    assert config.git_config.previous.pattern == "v*"
    assert config.git_config.previous.strip_prefix == "v"
    assert config.git_config.previous.sort == "semver-desc"
    assert config.git_config.previous.include_prereleases is False


def test_git_latest_config_accepts_branch_shorthand() -> None:
    config = VersionConfig.from_config(
        {
            "versioning": {
                "enabled": True,
                "mode": "git",
                "git": {
                    "latest": "develop",
                    "previous": {"count": 2},
                },
            }
        }
    )

    assert config.git_config is not None
    assert config.git_config.latest is not None
    assert config.git_config.latest.branch == "develop"
    assert config.git_config.latest.id == ""
    assert config.git_config.previous is not None
    assert config.git_config.previous.source == "tags"
    assert config.git_config.previous.count == 2
    assert config.git_config.previous.pattern == "v*"
