"""
Configuration utilities for autodoc.

Provides functions for normalizing and processing autodoc configuration.

Functions:
- normalize_autodoc_config: Normalize github repo/branch for template consumption

"""

from __future__ import annotations

from typing import Any


def normalize_autodoc_config(site_config: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize github repo/branch for autodoc template consumption.

    Mirrors RenderingPipeline._normalize_config for the subset we need
    inside the autodoc orchestrator (owner/repo → https URL, default branch).

    Args:
        site_config: Site configuration dict

    Returns:
        Normalized autodoc config with github_repo and github_branch

    Example:
            >>> config = {"github_repo": "owner/repo"}
            >>> normalize_autodoc_config(config)
        {"github_repo": "https://github.com/owner/repo", "github_branch": "main"}

    """
    base = {}
    if isinstance(site_config, dict):
        base.update(site_config)
    autodoc_cfg = base.get("autodoc", {}) or {}

    github_repo = base.get("github_repo") or autodoc_cfg.get("github_repo", "")
    if github_repo and not github_repo.startswith(("http://", "https://")):
        github_repo = f"https://github.com/{github_repo}"

    github_branch = base.get("github_branch") or autodoc_cfg.get("github_branch", "main")

    normalized = dict(autodoc_cfg)
    normalized["github_repo"] = github_repo
    normalized["github_branch"] = github_branch
    return normalized
