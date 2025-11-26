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
        # tests/integration/test_autodoc_openapi.py -> tests/fixtures/openapi/messy_api.yaml
        fixture_path = Path(__file__).parent.parent / "fixtures" / "openapi" / "messy_api.yaml"
        
        if not fixture_path.exists():
            # Fallback for different test runner execution paths
            fixture_path = Path("tests/fixtures/openapi/messy_api.yaml")
            
        assert fixture_path.exists(), f"Fixture not found at {fixture_path}"

        # Configure extractor
        extractor = OpenAPIExtractor()
        print(f"DEBUG: Extractor module: {extractor.__module__}")
        import inspect
        print(f"DEBUG: Extractor file: {inspect.getfile(OpenAPIExtractor)}")

        # Extract elements
        elements = extractor.extract(fixture_path)
        
        # Verify extraction
        assert len(elements) > 0
        
        # Check for specific known elements from the messy spec
        endpoints = [e for e in elements if e.element_type == "openapi_endpoint"]
        schemas = [e for e in elements if e.element_type == "openapi_schema"]
        overview = [e for e in elements if e.element_type == "openapi_overview"]
        
        assert len(overview) == 1
        assert overview[0].name == "Legacy Enterprise Sprawl API"
        
        # We expect 5 endpoints in the spec
        # /users GET, /users POST, /user/getDetails GET, /reports/upload POST, /iam/... GET, /webhooks/subscribe POST
        # Wait, /webhooks/subscribe defines a callback, but the main op is POST /webhooks/subscribe
        # So 6 endpoints?
        # Let's check the spec I wrote.
        # 1. GET /users
        # 2. POST /users
        # 3. GET /user/getDetails
        # 4. POST /reports/upload
        # 5. GET /iam/...
        # 6. POST /webhooks/subscribe
        assert len(endpoints) == 6
        
        # Check schemas
        # Error, PaymentMethod, CreditCard, BankAccount, PayPal, OrgChartNode, LegacyConfigBlob
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
        
        # Check for endpoint files (structure defined in extractor.get_output_path)
        # Users tag
        assert (output_dir / "endpoints" / "Users" / "get_users.md").exists()
        assert (output_dir / "endpoints" / "Users" / "create_user.md").exists() # inferred name? or explicit opId?
        # POST /users has no opId, so fallback: post_users
        if (output_dir / "endpoints" / "Users" / "post_users.md").exists():
             pass 
        
        # Reports tag (uploadReport opId)
        assert (output_dir / "endpoints" / "Reports" / "uploadReport.md").exists()
        
        # Check for schema files
        assert (output_dir / "schemas" / "LegacyConfigBlob.md").exists()
        assert (output_dir / "schemas" / "PaymentMethod.md").exists()

