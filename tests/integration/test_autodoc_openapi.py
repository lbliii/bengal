"""Integration tests for OpenAPI autodoc generation."""

from __future__ import annotations

from pathlib import Path

from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.autodoc.generator import DocumentationGenerator


class TestOpenAPIAutodocIntegration:
    """Integration tests for OpenAPI documentation generation."""

    def test_generate_messy_api_docs(self, tmp_path):
        """Test generating docs from a complex/messy OpenAPI spec."""
        # Locate the fixture
        fixture_path = Path(__file__).parent.parent / "fixtures" / "openapi" / "messy_api.yaml"
        
        if not fixture_path.exists():
            # Fallback for different test runner execution paths
            fixture_path = Path("tests/fixtures/openapi/messy_api.yaml")
            
        assert fixture_path.exists(), f"Fixture not found at {fixture_path}"

        # Configure extractor
        extractor = OpenAPIExtractor()

        # Extract elements
        elements = extractor.extract(fixture_path)
        
        # Verify extraction
        assert len(elements) > 0
        
        # Check for specific known elements from the messy spec
        # Updated types: endpoint, schema, api_overview
        endpoints = [e for e in elements if e.element_type == "endpoint"]
        schemas = [e for e in elements if e.element_type == "schema"]
        overview = [e for e in elements if e.element_type == "api_overview"]
        
        assert len(overview) == 1
        assert overview[0].name == "Legacy Enterprise Sprawl API"
        
        # We expect 6 endpoints in the spec
        assert len(endpoints) == 6
        
        # Check schemas
        assert len(schemas) >= 7

        # Generate docs
        output_dir = tmp_path / "api-openapi"
        config = {
            "openapi": {
                "enabled": True,
                "spec_file": str(fixture_path)
            }
        }
        
        generator = DocumentationGenerator(extractor, config)
        generated_files = generator.generate_all(elements, output_dir, parallel=False)

        # Verify generated files exist
        assert (output_dir / "index.md").exists()
        
        # Check for endpoint files
        # Users tag
        assert (output_dir / "endpoints" / "Users" / "get_users.md").exists()
        assert (output_dir / "endpoints" / "Users" / "post_users.md").exists()
        
        # Reports tag (uploadReport opId)
        assert (output_dir / "endpoints" / "Reports" / "uploadReport.md").exists()
        
        # Check for schema files
        assert (output_dir / "schemas" / "LegacyConfigBlob.md").exists()
        assert (output_dir / "schemas" / "PaymentMethod.md").exists()
