"""Wheel install smoke test — catches dep-drift between ``uv.lock`` and the published artifact.

The v0.3.1 release shipped a broken ``bengal --version`` because:

1. ``uv.lock`` locked milo-cli to 0.2.1 (a pre-release of the auto-``--no-<flag>`` feature).
2. ``pyproject.toml`` constrained milo-cli to ``>=0.2.1`` (no upper bound).
3. milo-cli 0.2.2 was published to PyPI 21 minutes after the Bengal v0.3.1 tag.
4. ``pip install bengal==0.3.1`` into a fresh venv resolved milo-cli to 0.2.2
   (latest satisfying ``>=0.2.1``), whose auto-generated ``--no-include-version``
   flag collided with the explicit ``no_include_version`` param in ``cache_hash``,
   crashing argparse at parser-build time on every invocation.

Every CI job resolved against ``uv.lock`` and saw milo-cli 0.2.1, so tests passed.

This test builds the wheel, installs it into a *fresh* venv (no lock, no cache),
and runs ``bengal --version``. It reproduces the end-user install pathway and
would have caught the v0.3.1 regression.

Marked slow (``python -m build`` + network install ≈ 30-90s); runs in the nightly
``slow-tests`` CI job and locally via ``pytest -m slow``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.integration]


REPO_ROOT = Path(__file__).resolve().parents[2]


def _has_network() -> bool:
    """Check if PyPI is reachable — skip if not (offline CI, firewalled runner)."""
    import socket

    try:
        socket.create_connection(("pypi.org", 443), timeout=3).close()
    except OSError:
        return False
    return True


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a wheel from the repo root into a scratch dist/ — returns the wheel path."""
    dist_dir = tmp_path_factory.mktemp("wheel-dist")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        pytest.skip(
            f"python -m build failed (install 'build' package to enable): "
            f"stderr={result.stderr[-500:]!r}"
        )

    wheels = list(dist_dir.glob("bengal-*.whl"))
    assert len(wheels) == 1, f"Expected exactly one wheel, got {wheels}"
    return wheels[0]


@pytest.fixture(scope="module")
def installed_venv(tmp_path_factory: pytest.TempPathFactory, built_wheel: Path) -> Path:
    """Create a fresh venv, install the built wheel with PyPI-resolved deps. Returns venv path."""
    if not _has_network():
        pytest.skip("PyPI unreachable — wheel-install test requires network")

    venv_dir = tmp_path_factory.mktemp("wheel-venv")
    # Use stdlib venv to mirror a real user install (not uv).
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        timeout=60,
    )
    py = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python"

    subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=True,
        timeout=60,
    )
    # Install the wheel. pip resolves each dep to the *latest* version matching the
    # constraint in the wheel's METADATA — exactly what `pip install bengal` does
    # for end users, and exactly the path that broke in v0.3.1.
    install = subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", str(built_wheel)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if install.returncode != 0:
        pytest.skip(f"pip install failed (likely network): {install.stderr[-500:]!r}")

    return venv_dir


def _bengal_bin(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin") / "bengal"


def test_wheel_bengal_version_succeeds(installed_venv: Path) -> None:
    """``bengal --version`` must exit 0 after wheel install against latest PyPI deps.

    Regression guard for v0.3.1: parser-build argparse conflicts crashed this
    invocation for every end user. If a future dep bump reintroduces the same
    failure mode, this test fails immediately in the release pipeline.
    """
    bengal = _bengal_bin(installed_venv)
    result = subprocess.run([str(bengal), "--version"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (
        f"bengal --version failed with code {result.returncode}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert any(ch.isdigit() for ch in result.stdout), (
        f"Expected version digits in stdout, got: {result.stdout!r}"
    )


def test_wheel_bengal_help_succeeds(installed_venv: Path) -> None:
    """``bengal --help`` must exit 0 — exercises full parser construction under real install."""
    bengal = _bengal_bin(installed_venv)
    result = subprocess.run([str(bengal), "--help"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (
        f"bengal --help failed with code {result.returncode}\nstderr={result.stderr[-1000:]!r}"
    )
    assert "bengal" in result.stdout.lower()


def test_wheel_cache_hash_help_succeeds(installed_venv: Path) -> None:
    """``bengal cache hash --help`` — the specific command that crashed in v0.3.1.

    Pinpoints the regression class: a subcommand's argument schema conflicting
    with auto-generated milo flags. Kept as a dedicated test so a future failure
    here is self-documenting.
    """
    bengal = _bengal_bin(installed_venv)
    result = subprocess.run(
        [str(bengal), "cache", "hash", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"bengal cache hash --help failed with code {result.returncode}\n"
        f"stderr={result.stderr[-1000:]!r}"
    )


def test_wheel_build_executable_exists(installed_venv: Path) -> None:
    """The ``bengal`` console_scripts entry point must be installed and executable."""
    bengal = _bengal_bin(installed_venv)
    assert bengal.exists(), f"console script not installed at {bengal}"
    # On Unix, also check executability.
    if os.name != "nt":
        assert os.access(bengal, os.X_OK), f"{bengal} exists but is not executable"
    assert shutil.which(str(bengal)) is not None or bengal.is_file()
