"""E2E test fixtures.

Provides fixtures that run `bengal build` on a test root, then allow
inspecting output HTML/assets as a real user would.

Plan: plan-production-maturity.md Phase 0A
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def e2e_rootdir() -> Path:
    """Path to tests/roots/ directory (session-scoped)."""
    return Path(__file__).parent.parent / "roots"


@pytest.fixture
def e2e_site_dir(tmp_path: Path, e2e_rootdir: Path) -> Callable[..., Path]:
    """Factory to prepare a site directory from a test root for E2E builds.

    Copies the root to tmp_path, excluding build artifacts (.bengal, public).
    Returns the path to the prepared site directory.
    """

    def _prepare(testroot: str) -> Path:
        root_path = e2e_rootdir / testroot
        if not root_path.exists():
            available = [p.name for p in e2e_rootdir.iterdir() if p.is_dir()]
            raise ValueError(f"Test root '{testroot}' not found. Available: {', '.join(available)}")
        site_dir = tmp_path / "e2e_site"
        site_dir.mkdir(exist_ok=True)
        for item in root_path.iterdir():
            if item.name in (".bengal", "public"):
                continue
            dst = site_dir / item.name
            if item.is_file():
                shutil.copy2(item, dst)
            elif item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
        return site_dir

    return _prepare


@pytest.fixture
def bengal_build(
    e2e_site_dir: Callable[..., Path],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run `bengal build` in a site directory (CLI invocation, real user path).

    Returns the subprocess result. Use e2e_site_dir to prepare the site first.
    """

    def _build(site_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = ["bengal", "build", *args]
        return subprocess.run(
            cmd,
            cwd=site_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

    return _build


@pytest.fixture
def built_site(
    e2e_site_dir: Callable[..., Path],
    bengal_build: Callable[..., subprocess.CompletedProcess[str]],
) -> Callable[..., tuple[Path, Path, subprocess.CompletedProcess[str]]]:
    """Prepare a site from a test root, run `bengal build`, return (site_dir, output_dir, result).

    Usage:
        def test_something(built_site):
            site_dir, output_dir, result = built_site("test-basic")
            assert result.returncode == 0
            assert (output_dir / "index.html").exists()
    """

    def _build(
        testroot: str, *build_args: str
    ) -> tuple[Path, Path, subprocess.CompletedProcess[str]]:
        site_dir = e2e_site_dir(testroot)
        result = bengal_build(site_dir, *build_args)
        output_dir = site_dir / "public"
        return site_dir, output_dir, result

    return _build
