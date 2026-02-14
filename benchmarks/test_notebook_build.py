"""
Notebook build benchmarks for native .ipynb support.

Tracks cold build and incremental rebuild when notebooks are in the content tree.
Bengal parses .ipynb via Patitas (stdlib JSON, no nbformat).

Prerequisite: pip install -e . from project root (bengal CLI + deps must be available).

Run with:
    pytest benchmarks/test_notebook_build.py -v --benchmark-only

Related:
    - site/content/docs/content/authoring/notebooks/setup.md
"""

import json
import subprocess
import time
from pathlib import Path

import pytest


def _make_notebook(idx: int) -> dict:
    """Create minimal valid nbformat 4 notebook for index idx."""
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# Notebook {idx}\n",
                    "\n",
                    "This notebook contains markdown and code cells for benchmarking.\n",
                    "\n",
                    f"```python\nx = {idx}\n```\n",
                ],
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [f"def example_{idx}():\n    return {idx}\n"],
                "outputs": [],
                "execution_count": None,
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _bengal_build(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run bengal build (requires: pip install -e . from project root)."""
    return subprocess.run(
        ["bengal", "build", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def create_notebook_site(num_notebooks: int, tmp_path: Path) -> Path:
    """Create a site with N notebooks in content."""
    site_root = tmp_path / f"notebook_site_{num_notebooks}"
    site_root.mkdir(exist_ok=True)

    (site_root / "bengal.toml").write_text("""[site]
title = "Notebook Benchmark"
base_url = "https://example.com"

[build]
output_dir = "output"
parallel = true
""")

    content_dir = site_root / "content"
    content_dir.mkdir(exist_ok=True)

    for i in range(num_notebooks):
        nb_path = content_dir / f"notebook_{i:04d}.ipynb"
        nb_path.write_text(json.dumps(_make_notebook(i), indent=2))

    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Notebook Benchmark")

    return site_root


@pytest.fixture
def notebook_site_50(tmp_path):
    """50-notebook site (built once for incremental tests)."""
    site = create_notebook_site(50, tmp_path)
    _bengal_build(site)
    return site


@pytest.mark.benchmark
def test_notebook_cold_build_50(benchmark, tmp_path):
    """Cold build of 50 notebooks."""
    site = create_notebook_site(50, tmp_path)

    def build():
        _bengal_build(site)

    benchmark(build)


@pytest.mark.benchmark
def test_notebook_incremental_single_change(benchmark, notebook_site_50):
    """Incremental rebuild after editing one notebook."""
    nb_path = notebook_site_50 / "content" / "notebook_0025.ipynb"
    original = nb_path.read_text()

    def build():
        nb = json.loads(original)
        nb["metadata"]["benchmark_edit"] = time.time_ns()
        nb_path.write_text(json.dumps(nb, indent=2))
        _bengal_build(notebook_site_50, "--incremental")
        nb_path.write_text(original)

    benchmark(build)


@pytest.mark.benchmark
def test_notebook_mixed_site(benchmark, tmp_path):
    """Cold build of mixed content: 25 markdown + 25 notebooks."""
    site_root = tmp_path / "mixed_site"
    site_root.mkdir()
    (site_root / "bengal.toml").write_text("""[site]
title = "Mixed Content"
base_url = "https://example.com"

[build]
output_dir = "output"
parallel = true
""")
    content_dir = site_root / "content"
    content_dir.mkdir()

    for i in range(25):
        (content_dir / f"page{i:04d}.md").write_text(
            f"---\ntitle: Page {i}\n---\n# Page {i}\nContent."
        )
    for i in range(25):
        (content_dir / f"notebook_{i:04d}.ipynb").write_text(
            json.dumps(_make_notebook(i), indent=2)
        )
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Mixed")

    def build():
        _bengal_build(site_root)

    benchmark(build)
