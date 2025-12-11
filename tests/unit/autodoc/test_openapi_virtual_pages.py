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

    assert "api/overview" in url_paths
    assert "api/schemas/User" in url_paths
    assert "api/endpoints/get-users" in url_paths

    # Sections should include the API root and schemas/tag sections
    section_keys = set(sections.keys())
    assert "api" in section_keys
    assert "api/schemas" in section_keys
    # Tag section created for "users"
    assert "api/tags/users" in section_keys

    # Result is returned (even if pages rendered later)
    assert result is not None
