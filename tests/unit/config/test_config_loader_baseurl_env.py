from pathlib import Path

import pytest

from bengal.config.loader import ConfigLoader


def write_min_config(dir_path: Path, baseurl: str | None = None) -> Path:
    cfg = dir_path / "bengal.toml"
    site_section = ["[site]", 'title = "Test Site"']
    if baseurl is not None:
        site_section.append(f'baseurl = "{baseurl}"')
    cfg.write_text("\n".join(site_section) + "\n", encoding="utf-8")
    return cfg


def test_env_explicit_bengal_baseurl_overrides_when_config_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    write_min_config(tmp_path, baseurl="")
    monkeypatch.setenv("BENGAL_BASEURL", "https://example.com/sub")

    loader = ConfigLoader(tmp_path)
    config = loader.load()

    assert config.get("baseurl") == "https://example.com/sub"


def test_netlify_url_used_when_config_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    write_min_config(tmp_path, baseurl="")
    # Ensure BENGAL_BASEURL isn't set from test matrix
    monkeypatch.delenv("BENGAL_BASEURL", raising=False)
    monkeypatch.delenv("BENGAL_BASE_URL", raising=False)
    monkeypatch.setenv("NETLIFY", "true")
    monkeypatch.setenv("URL", "https://docs.example.com")

    loader = ConfigLoader(tmp_path)
    config = loader.load()

    assert config.get("baseurl") == "https://docs.example.com"


def test_netlify_preview_deploy_prime_url_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    write_min_config(tmp_path, baseurl="")
    # Ensure BENGAL_BASEURL isn't set from test matrix
    monkeypatch.delenv("BENGAL_BASEURL", raising=False)
    monkeypatch.delenv("BENGAL_BASE_URL", raising=False)
    monkeypatch.setenv("NETLIFY", "true")
    # No URL, only DEPLOY_PRIME_URL
    monkeypatch.delenv("URL", raising=False)
    monkeypatch.setenv("DEPLOY_PRIME_URL", "https://deploy-preview--site.netlify.app")

    loader = ConfigLoader(tmp_path)
    config = loader.load()

    assert config.get("baseurl") == "https://deploy-preview--site.netlify.app"


def test_vercel_url_with_protocol_added_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    write_min_config(tmp_path, baseurl="")
    # Ensure BENGAL_BASEURL isn't set from test matrix
    monkeypatch.delenv("BENGAL_BASEURL", raising=False)
    monkeypatch.delenv("BENGAL_BASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_URL", "my-docs.vercel.app")

    loader = ConfigLoader(tmp_path)
    config = loader.load()

    assert config.get("baseurl") == "https://my-docs.vercel.app"


def test_github_pages_owner_repo_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    write_min_config(tmp_path, baseurl="")
    # Ensure BENGAL_BASEURL isn't set from test matrix
    monkeypatch.delenv("BENGAL_BASEURL", raising=False)
    monkeypatch.delenv("BENGAL_BASE_URL", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner123/repo456")

    loader = ConfigLoader(tmp_path)
    config = loader.load()

    assert config.get("baseurl") == "https://owner123.github.io/repo456"


def test_explicit_config_baseurl_not_overridden_by_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    write_min_config(tmp_path, baseurl="https://explicit.example.com")
    monkeypatch.setenv("BENGAL_BASEURL", "https://should-not-apply.example.com")

    loader = ConfigLoader(tmp_path)
    config = loader.load()

    assert config.get("baseurl") == "https://explicit.example.com"
