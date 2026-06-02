"""
Integration-style unit test for OpenAPI virtual page generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock

from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


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
    site.registry = Mock()
    site.registry.epoch = 0
    site.registry.register_section = Mock()
    site.registry.get_section = Mock(return_value=None)
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

    # Overview doesn't get a separate page - root section index IS the overview.
    # consolidate defaults to False, so each endpoint becomes its own page.
    element_types = {p.metadata.get("element_type") for p in pages}
    url_paths = {p.metadata.get("_autodoc_url_path") for p in pages}

    # Overview element exists but doesn't get a page
    assert "openapi_overview" not in element_types
    assert "openapi_schema" in element_types
    # With consolidate=False (default), endpoints get their own pages
    assert "openapi_endpoint" in element_types

    # OpenAPI prefix is auto-derived from spec title "Demo API" -> "api/demo"
    # Overview is handled by section index, not a separate page
    assert "api/demo/overview" not in url_paths
    assert "api/demo/schemas/User" in url_paths
    # Endpoints get individual pages grouped under their tag section
    assert "api/demo/tags/users/get-users" in url_paths

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


def test_openapi_untagged_endpoint_nests_under_default_tag(tmp_path: Path) -> None:
    """An endpoint with no tags must nest under the synthetic ``tags/default``
    section so its page URL agrees with its section placement (the URL path,
    ``find_parent_section``, and ``section_builders`` must all use the same key).
    """
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """openapi: 3.1.0
info:
  title: Demo API
  version: "1.0.0"
paths:
  /health:
    get:
      summary: Health check
      responses:
        "200":
          description: ok
""",
        encoding="utf-8",
    )

    site = _make_mock_site(tmp_path, spec_path)
    pages, _sections, _result = VirtualAutodocOrchestrator(site).generate()

    url_paths = {p.metadata.get("_autodoc_url_path") for p in pages}
    # Untagged endpoint nests under tags/default (NOT the old /endpoints/ scheme),
    # matching the default tag section section_builders creates for it.
    assert "api/demo/tags/default/get-health" in url_paths
    assert not any(u and u.startswith("api/demo/endpoints/") for u in url_paths)


def _find_section(sections: object, name: str):
    """Depth-first search for a section by name within a section tree."""
    for section in sections or []:
        if getattr(section, "name", None) == name:
            return section
        found = _find_section(getattr(section, "subsections", []), name)
        if found is not None:
            return found
    return None


def test_openapi_multi_tag_endpoint_cross_listed_with_single_page(tmp_path: Path) -> None:
    """A multi-tag endpoint gets ONE canonical page (under its first tag) but is
    cross-listed under EVERY tag section — including a secondary tag that also owns
    its own first-tag endpoint. Regression for the endpoints_filter precedence bug
    where page-backed and metadata endpoints were mutually exclusive.
    """
    from bengal.rendering.template_functions.openapi import endpoints_filter

    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """openapi: 3.1.0
info:
  title: Demo API
  version: "1.0.0"
paths:
  /billing/usage:
    get:
      tags: [billing]
      summary: Usage
      responses:
        "200":
          description: ok
  /users/{id}/billing:
    get:
      tags: [users, billing]
      summary: User billing
      responses:
        "200":
          description: ok
""",
        encoding="utf-8",
    )

    site = _make_mock_site(tmp_path, spec_path)
    pages, sections, _result = VirtualAutodocOrchestrator(site).generate()

    # Exactly one page per endpoint — the multi-tag endpoint is NOT duplicated, and
    # its single canonical page lives under its FIRST tag ("users").
    endpoint_pages = [p for p in pages if p.metadata.get("element_type") == "openapi_endpoint"]
    assert len(endpoint_pages) == 2
    multi = [
        p
        for p in endpoint_pages
        if (p.metadata.get("_autodoc_url_path") or "").startswith("api/demo/tags/users/")
    ]
    assert len(multi) == 1

    # The "billing" tag section owns /billing/usage (first tag) AND must cross-list
    # /users/{id}/billing (whose first tag is "users") — the union, not just one.
    billing = _find_section(sections, "billing")
    assert billing is not None
    billing_paths = {ev.path for ev in endpoints_filter(billing)}
    assert "/billing/usage" in billing_paths
    assert "/users/{id}/billing" in billing_paths


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
    site.registry = Mock()
    site.registry.epoch = 0
    site.registry.register_section = Mock()
    site.registry.get_section = Mock(return_value=None)

    orchestrator = VirtualAutodocOrchestrator(site)
    pages, _sections, _result = orchestrator.generate()

    url_paths = {p.metadata.get("_autodoc_url_path") for p in pages}
    # Overview is handled by section index, not a separate page
    assert "api/demo/overview" not in url_paths
