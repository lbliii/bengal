import json
from pathlib import Path

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator


def _write_site(tmp: Path, baseurl_line: str) -> Path:
    site_dir = tmp / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        f"""
[site]
title = "Test"
{baseurl_line}

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "index.md").write_text(
        """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
    )
    return site_dir


def test_build_with_path_baseurl(tmp_path: Path):
    site_dir = _write_site(tmp_path, 'baseurl = "/bengal"')
    site = Site.from_config(site_dir)
    orchestrator = BuildOrchestrator(site)
    orchestrator.build()

    # Assert assets and index.json present at root
    assert (site_dir / "public" / "assets").exists()
    index_path = site_dir / "public" / "index.json"
    assert index_path.exists()

    # Check home HTML contains baseurl-prefixed CSS link
    # Validate HTML contains baseurl-prefixed CSS
    html = (site_dir / "public" / "index.html").read_text(encoding="utf-8")
    assert 'href="/bengal/assets/css/style' in html

    # Validate index.json shape and baseurl
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "/bengal"
    assert isinstance(data.get("pages"), list)
    if data["pages"]:
        sample = data["pages"][0]
        assert "url" in sample and "uri" in sample


def test_build_with_env_absolute_baseurl(tmp_path: Path, monkeypatch):
    site_dir = _write_site(tmp_path, 'baseurl = ""')
    monkeypatch.setenv("BENGAL_BASEURL", "https://example.com/sub")

    site = Site.from_config(site_dir)
    orchestrator = BuildOrchestrator(site)
    orchestrator.build()

    # index.json written
    index_path = site_dir / "public" / "index.json"
    assert index_path.exists()
    html = (site_dir / "public" / "index.html").read_text(encoding="utf-8")
    assert 'href="https://example.com/sub/assets/css/style' in html

    # Validate index.json uses absolute baseurl
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "https://example.com/sub"
    assert isinstance(data.get("pages"), list)
    if data["pages"]:
        sample = data["pages"][0]
        assert sample["url"].startswith("https://example.com/sub/")
