"""External-theme build gate — exercises the REAL chirp-ui wheel end-to-end.

The synthetic provider-shape unit tests live in
``tests/unit/core/theme/test_providers.py`` and pin the *contract shape* with
mocked modules. They cannot catch a published wheel that quietly drops the
convention hooks, the ``chirp-theme`` entry point, or the library-asset
fingerprinting — every mock would keep passing. This module is the
integration-confidence layer: it installs the pinned ``chirp-ui`` wheel from
PyPI into a scratch venv (exactly like ``tests/integration/test_wheel_install.py``
installs the built Bengal wheel) and drives it through Bengal's
provider + theme-discovery + static-build path.

Marked slow (``pip install`` + a full themed build ≈ 30-90s); runs in the nightly
``slow-tests`` CI job and locally via ``pytest -m slow``. SKIPS — never fails —
when PyPI is unreachable, so the offline/firewalled PR fast-check stays green.

The pin is intentional and exact (``chirp-ui==0.9.0``): the gate moves only when
a human bumps ``CHIRP_UI_PIN``, which is precisely the version-governance signal
issue #362 asks for. Chirp-ui is a Pre-Alpha external dependency and is *not*
added to pyproject/uv.lock; the gate installs it into a throwaway venv.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.integration]


REPO_ROOT = Path(__file__).resolve().parents[2]

# Exact pin (not a floor): the gate only moves when a human bumps this constant,
# which is the #362 version-governance signal. The base wheel (no 'showcase'
# extra) is sufficient for provider + theme resolution and the static build;
# the showcase extra pulls bengal-chirp and a heavier/circular tree we don't need.
CHIRP_UI_PIN = "chirp-ui==0.9.0"

# Fingerprinted library-asset reference Bengal must emit for chirp-ui's contract
# assets (chirpui.<hex>.<js|css> namespaced under the chirp_ui asset prefix).
_LIBRARY_ASSET_RE = re.compile(r"/assets/chirp_ui/chirpui[\w-]*\.[0-9a-f]+\.(?:js|css)")


def _has_network() -> bool:
    """Check if PyPI is reachable — skip if not (offline CI, firewalled runner)."""
    import socket

    try:
        socket.create_connection(("pypi.org", 443), timeout=3).close()
    except OSError:
        return False
    return True


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python"


def _bengal_bin(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin") / "bengal"


@pytest.fixture(scope="module")
def chirp_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Fresh stdlib venv with editable Bengal + the pinned chirp-ui wheel.

    Mirrors ``test_wheel_install.installed_venv``: stdlib ``venv`` (not uv) to
    match a real user install, ``pytest.skip`` on any install failure so a
    network/PyPI hiccup never turns into a red build.
    """
    if not _has_network():
        pytest.skip("PyPI unreachable — external-theme build gate requires network")

    venv_dir = tmp_path_factory.mktemp("chirp-venv")
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        timeout=60,
    )
    py = _venv_python(venv_dir)

    subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=True,
        timeout=60,
    )
    # Editable install of the repo under test so the gate validates THIS Bengal's
    # provider/theme path against the published wheel.
    install_bengal = subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", "-e", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if install_bengal.returncode != 0:
        pytest.skip(f"editable Bengal install failed: {install_bengal.stderr[-500:]!r}")

    # Plain pin, NO 'showcase' extra (avoids the bengal-chirp / circular tree).
    install_chirp = subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", CHIRP_UI_PIN],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if install_chirp.returncode != 0:
        pytest.skip(
            f"pip install {CHIRP_UI_PIN} failed (likely network): {install_chirp.stderr[-500:]!r}"
        )

    return venv_dir


def _run_py(venv_dir: Path, snippet: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    """Run ``python -c <snippet>`` inside the installed venv and return the result."""
    return subprocess.run(
        [str(_venv_python(venv_dir)), "-c", snippet],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_provider_contract_resolves_real_wheel(chirp_venv: Path) -> None:
    """``resolve_provider('chirp_ui')`` against the real wheel exposes the full contract.

    Discriminating: if the wheel stops shipping the convention hooks
    (get_loader/static_path/register_filters/get_library_contract) or the
    contract assets, the corresponding ``OK ...`` line is never printed and the
    assertion fails. A macro template must load through the provider loader,
    proving template imports (the whole point of the library) still resolve.
    """
    snippet = (
        "from bengal.core.theme.providers import resolve_provider\n"
        "p = resolve_provider('chirp_ui')\n"
        "assert p.package == 'chirp_ui'\n"
        "assert p.loader is not None, 'no template loader'\n"
        "assert p.asset_root is not None and p.asset_root.exists(), 'asset_root missing'\n"
        "assert p.register_env is not None, 'no register_env hook'\n"
        "types = [a.asset_type for a in p.assets]\n"
        "assert sum(1 for t in types if t == 'css') >= 1, f'no css asset: {types}'\n"
        "assert sum(1 for t in types if t in ('js', 'javascript')) >= 1, f'no js asset: {types}'\n"
        "assert 'alpine' in p.runtime, f'runtime missing alpine: {p.runtime}'\n"
        # Real macro template must resolve through the provider loader.
        "src = p.loader.get_source('chirpui/card.html')\n"
        "assert src, 'chirpui/card.html did not resolve'\n"
        "print('OK provider')\n"
    )
    result = _run_py(chirp_venv, snippet)
    assert result.returncode == 0, (
        f"provider-contract probe failed\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "OK provider" in result.stdout


def test_theme_discovery_finds_chirp_theme(chirp_venv: Path) -> None:
    """``get_installed_themes()`` exposes 'chirp-theme' -> bengal_themes.chirp_theme.

    Discriminating: if the wheel drops the ``bengal.themes`` entry point or
    renames the package, the lookup is missing and the assertion fails. The
    theme.toml must resolve and declare ``chirp_ui`` in its libraries, proving
    the theme is wired to the library provider.
    """
    snippet = (
        "import tomllib\n"
        "from pathlib import Path\n"
        "import importlib\n"
        "from bengal.core.theme.registry import get_installed_themes\n"
        "themes = get_installed_themes()\n"
        "assert 'chirp-theme' in themes, f'chirp-theme not discovered: {sorted(themes)}'\n"
        "pkg = themes['chirp-theme'].package\n"
        "assert pkg == 'bengal_themes.chirp_theme', f'unexpected package: {pkg}'\n"
        "mod = importlib.import_module(pkg)\n"
        "toml_path = Path(mod.__file__).parent / 'theme.toml'\n"
        "assert toml_path.exists(), f'theme.toml missing at {toml_path}'\n"
        "data = tomllib.loads(toml_path.read_text(encoding='utf-8'))\n"
        "assert 'chirp_ui' in data.get('libraries', []), f'libraries: {data.get(\"libraries\")}'\n"
        "print('OK theme')\n"
    )
    result = _run_py(chirp_venv, snippet)
    assert result.returncode == 0, (
        f"theme-discovery probe failed\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "OK theme" in result.stdout


def test_kida_chirp_ui_version_skew(chirp_venv: Path) -> None:
    """The installed kida-templates must satisfy chirp-ui's requires-dist floor.

    #362 sub-task: "fail on kida/chirp-ui version mismatch" — there is no core
    gate for this today, so the test pins it. Reads chirp-ui's declared
    ``kida-templates>=X`` floor from its dist metadata and compares it against
    the actually-installed kida-templates version. Fails loudly if a future
    bump introduces skew (e.g. chirp-ui raises its floor above what is pinned).

    Discriminating: if the resolved environment ships a kida-templates below
    chirp-ui's floor, the version comparison fails with both versions reported.
    """
    snippet = (
        "from importlib import metadata\n"
        "from packaging.requirements import Requirement\n"
        "from packaging.version import Version\n"
        "reqs = metadata.requires('chirp-ui') or []\n"
        "kida_reqs = [Requirement(r) for r in reqs if Requirement(r).name == 'kida-templates']\n"
        "assert kida_reqs, f'chirp-ui no longer declares a kida-templates dep: {reqs}'\n"
        "installed = Version(metadata.version('kida-templates'))\n"
        "for req in kida_reqs:\n"
        "    assert req.specifier.contains(installed, prereleases=True), (\n"
        "        f'version skew: installed kida-templates {installed} does not satisfy '\n"
        "        f'chirp-ui floor {req.specifier}'\n"
        "    )\n"
        "print(f'OK skew installed={installed} req={[str(r.specifier) for r in kida_reqs]}')\n"
    )
    result = _run_py(chirp_venv, snippet)
    assert result.returncode == 0, (
        f"version-skew probe failed\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "OK skew" in result.stdout


def _write_chirp_site(root: Path) -> None:
    (root / "content").mkdir(parents=True)
    (root / "content" / "index.md").write_text("---\ntitle: Home\n---\n# Home\n", encoding="utf-8")
    (root / "bengal.toml").write_text(
        '[site]\ntitle = "Chirp Gate"\ntheme = "chirp-theme"\n', encoding="utf-8"
    )


def test_static_build_emits_fingerprinted_library_asset(chirp_venv: Path, tmp_path: Path) -> None:
    """A real themed ``bengal build`` emits a fingerprinted chirp-ui asset that exists on disk.

    This is the "returns 200" check done as on-disk existence (static output has
    no server): the rendered index.html must reference
    ``/assets/chirp_ui/chirpui.<hex>.<js|css>`` and the referenced file must
    exist under ``public/``.

    Discriminating: if library-asset fingerprinting breaks (no namespaced
    chirp_ui asset emitted, or the emitted href points at a file that was never
    written), the regex match or the on-disk ``exists()`` fails. The dev-server
    HTTP-200 variant across both dev+static is a documented follow-up (#362).
    """
    site_root = tmp_path / "chirp-site"
    _write_chirp_site(site_root)

    result = subprocess.run(
        [str(_bengal_bin(chirp_venv)), "build", "--source", str(site_root)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"bengal build (theme=chirp-theme) failed with code {result.returncode}\n"
        f"stdout={result.stdout[-1500:]!r}\nstderr={result.stderr[-1500:]!r}"
    )

    index_html = site_root / "public" / "index.html"
    assert index_html.exists(), f"index.html not written at {index_html}"
    html = index_html.read_text(encoding="utf-8")

    match = _LIBRARY_ASSET_RE.search(html)
    assert match is not None, (
        "rendered index.html has no fingerprinted /assets/chirp_ui/chirpui.<hex>.<js|css> "
        f"reference\nhtml (excerpt)={html[:2000]!r}"
    )

    # Parse the href out and stat the target under public/ (falsifiable: a
    # dangling reference fails here even though the regex matched).
    asset_url = match.group(0)
    asset_on_disk = site_root / "public" / asset_url.lstrip("/")
    assert asset_on_disk.exists(), (
        f"referenced library asset {asset_url} does not exist on disk at {asset_on_disk}"
    )
