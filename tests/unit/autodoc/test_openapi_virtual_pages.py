"""
Integration-style unit test for OpenAPI virtual page generation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.autodoc.virtual_orchestrator import VirtualAutodocOrchestrator


def _make_mock_site(tmp_path: Path, spec_path: Path) -> MagicMock:
    """Create a minimal mock site configured for OpenAPI autodoc."""
    site = MagicMock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.baseurl = "/"
    site.config = {
        "autodoc": {
            "openapi": {
                "enabled": True,
                # Use absolute path to avoid cwd sensitivity
                "spec_file": str(spec_path),
            }
        }
    }
    site.theme = "default"
    site.theme_config = {}
    site.menu = {"main": []}
    site.menu_localized = {}
    site._section_registry = {}
    site._section_url_registry = {}
    return site


def test_openapi_virtual_pages_generated(tmp_path: Path) -> None:
    """Ensure OpenAPI extractor emits overview, schema, and endpoint pages."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """openapi: 3.1.0
info:
  title: Demo API
  version: "1.0.0"
paths:
  /users:
    get:
      tags: [users]
      summary: List users
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        email:
          type: string
""",
        encoding="utf-8",
    )

    site = _make_mock_site(tmp_path, spec_path)
    orchestrator = VirtualAutodocOrchestrator(site)

    pages, sections, result = orchestrator.generate()

    # Three elements expected: overview, one schema, one endpoint
    element_types = {p.metadata.get("element_type") for p in pages}
    url_paths = {p.metadata.get("_autodoc_url_path") for p in pages}

    assert "openapi_overview" in element_types
    assert "openapi_schema" in element_types
    assert "openapi_endpoint" in element_types

    # OpenAPI prefix is auto-derived from spec title "Demo API" -> "api/demo"
    assert "api/demo/overview" in url_paths
    assert "api/demo/schemas/User" in url_paths
    assert "api/demo/endpoints/get-users" in url_paths

    # Root section should be returned (only root sections are returned by generate())
    # The orchestrator returns aggregating parent sections (e.g., "api") when
    # OpenAPI prefix is "api/demo" - the "api" section aggregates "api/demo".
    section_names = [s.name for s in sections]
    assert "api" in section_names  # Aggregating parent section

    # The "demo" section (derived from "Demo API") should be a subsection of "api"
    api_section = next((s for s in sections if s.name == "api"), None)
    assert api_section is not None
    api_subsection_names = [s.name for s in api_section.subsections]
    assert "demo" in api_subsection_names  # Demo section under api

    # Verify nested structure: api -> demo -> schemas/users
    demo_section = next((s for s in api_section.subsections if s.name == "demo"), None)
    assert demo_section is not None
    demo_subsection_names = [s.name for s in demo_section.subsections]
    assert "schemas" in demo_subsection_names  # Schemas subsection
    assert "users" in demo_subsection_names  # Tag section for "users"

    # Result is returned (even if pages rendered later)
    assert result is not None


def test_openapi_spec_file_is_resolved_relative_to_site_root(tmp_path: Path, monkeypatch) -> None:
    """
    Ensure spec_file is resolved relative to site.root_path, not the current working directory.

    This matches how the example site config is written (e.g. spec_file: "api/openapi.yaml")
    and prevents missing OpenAPI autodocs in public/CI builds that run from the repo root.
    """
    site_root = tmp_path / "site"
    api_dir = site_root / "api"
    api_dir.mkdir(parents=True)
    spec_path = api_dir / "openapi.yaml"
    spec_path.write_text(
        """openapi: 3.1.0
info:
  title: Demo API
  version: "1.0.0"
paths:
  /users:
    get:
      tags: [users]
      summary: List users
      responses:
        "200":
          description: ok
""",
        encoding="utf-8",
    )

    # Ensure CWD is NOT the site root.
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    site = MagicMock()
    site.root_path = site_root
    site.output_dir = tmp_path / "public"
    site.baseurl = "/"
    site.config = {"autodoc": {"openapi": {"enabled": True, "spec_file": "api/openapi.yaml"}}}
    site.theme = "default"
    site.theme_config = {}
    site.menu = {"main": []}
    site.menu_localized = {}
    site._section_registry = {}
    site._section_url_registry = {}

    orchestrator = VirtualAutodocOrchestrator(site)
    pages, _sections, _result = orchestrator.generate()

    url_paths = {p.metadata.get("_autodoc_url_path") for p in pages}
    assert "api/demo/overview" in url_paths
