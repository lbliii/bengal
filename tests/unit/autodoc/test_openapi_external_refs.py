"""Tests for local OpenAPI $ref resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock

from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


def _write_openapi_with_external_schema(tmp_path: Path) -> tuple[Path, Path]:
    spec_path = tmp_path / "openapi.yaml"
    schemas_path = tmp_path / "schemas.yaml"

    spec_path.write_text(
        """openapi: 3.1.0
info:
  title: Demo API
  version: "1.0.0"
paths:
  /users:
    get:
      tags: [users]
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                $ref: "./schemas.yaml#/User"
components:
  schemas:
    User:
      $ref: "./schemas.yaml#/User"
""",
        encoding="utf-8",
    )
    schemas_path.write_text(
        """User:
  type: object
  description: A user from a shared schema file.
  properties:
    id:
      type: string
    profile:
      $ref: "./schemas.yaml#/Profile"
Profile:
  type: object
  properties:
    display_name:
      type: string
""",
        encoding="utf-8",
    )
    return spec_path, schemas_path


def _make_site(tmp_path: Path, spec_path: Path) -> MagicMock:
    site = MagicMock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.baseurl = "/"
    site.config = {
        "autodoc": {
            "openapi": {
                "enabled": True,
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


def test_resolves_file_relative_schema_refs_and_tracks_sources(tmp_path: Path) -> None:
    spec_path, schemas_path = _write_openapi_with_external_schema(tmp_path)

    elements = OpenAPIExtractor().extract(spec_path)
    user_schema = next(element for element in elements if element.name == "User")

    assert user_schema.description == "A user from a shared schema file."
    assert user_schema.metadata["properties"]["id"]["type"] == "string"
    assert (
        user_schema.metadata["properties"]["profile"]["properties"]["display_name"]["type"]
        == "string"
    )
    assert set(user_schema.metadata["source_dependencies"]) == {
        str(spec_path.resolve()),
        str(schemas_path.resolve()),
    }


def test_unresolved_file_refs_are_preserved_with_partial_extraction(tmp_path: Path) -> None:
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """openapi: 3.1.0
info:
  title: Demo API
  version: "1.0.0"
paths: {}
components:
  schemas:
    Missing:
      $ref: "./missing.yaml#/Missing"
""",
        encoding="utf-8",
    )

    elements = OpenAPIExtractor().extract(spec_path)
    missing_schema = next(element for element in elements if element.name == "Missing")

    assert missing_schema.metadata["raw_schema"] == {"$ref": "./missing.yaml#/Missing"}
    assert missing_schema.metadata["source_dependencies"] == (str(spec_path.resolve()),)


def test_virtual_openapi_pages_depend_on_external_ref_files(tmp_path: Path) -> None:
    spec_path, schemas_path = _write_openapi_with_external_schema(tmp_path)
    site = _make_site(tmp_path, spec_path)

    _pages, _sections, result = VirtualAutodocOrchestrator(site).generate()

    assert str(spec_path) in result.autodoc_dependencies
    assert str(schemas_path.resolve()) in result.autodoc_dependencies
    assert result.autodoc_dependencies[str(schemas_path.resolve())]
