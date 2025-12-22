"""Integration tests for product template and JSON-LD structured data.

Tests product template functionality:
- Product data loading from YAML
- JSON-LD structured data generation
- Product page rendering
- Template scaffolding

Phase 2 of RFC: User Scenario Coverage - Extended Validation
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-product")
class TestProductTemplate:
    """Test product template functionality."""

    def test_product_data_loaded(self, site) -> None:
        """Product data from YAML should be accessible."""
        data = site.data.get("products", {})
        products = data.get("products", [])

        assert len(products) >= 1, "Should have at least 1 product in data"

    def test_product_data_structure(self, site) -> None:
        """Product data should have proper structure."""
        data = site.data.get("products", {})
        products = data.get("products", [])

        if products:
            product = products[0]
            assert product.get("sku"), "Product should have SKU"
            assert product.get("name"), "Product should have name"
            assert product.get("price") is not None, "Product should have price"

    def test_product_pages_discovered(self, site) -> None:
        """Product pages should be discovered."""
        product_pages = [
            p
            for p in site.pages
            if getattr(p, "type", None) == "product" or "product" in str(p.source_path).lower()
        ]

        assert len(product_pages) >= 1, "Should have at least 1 product page"

    def test_product_builds_successfully(self, site, build_site) -> None:
        """Product site should build without errors."""
        build_site()

        output = site.output_dir
        assert (output / "index.html").exists(), "Home page should be generated"
        assert (output / "products" / "index.html").exists(), "Products index should be generated"

    def test_product_page_rendered(self, site, build_site) -> None:
        """Individual product pages should be rendered."""
        build_site()

        output = site.output_dir
        product_page = output / "products" / "product-1" / "index.html"

        assert product_page.exists(), f"Product page should exist at {product_page}"


@pytest.mark.bengal(testroot="test-product")
class TestProductJSONLD:
    """Test JSON-LD structured data for products."""

    def test_product_page_has_structured_data_frontmatter(self, site) -> None:
        """Product pages with structured_data: true should be identified."""
        pages_with_structured_data = []
        for page in site.pages:
            if page.metadata.get("structured_data") is True:
                pages_with_structured_data.append(page)

        assert len(pages_with_structured_data) >= 1, (
            "At least 1 page should have structured_data: true"
        )

    def test_product_page_has_price(self, site) -> None:
        """Product pages should have price frontmatter."""
        product_pages = [p for p in site.pages if getattr(p, "type", None) == "product"]

        if product_pages:
            page = product_pages[0]
            assert hasattr(page, "price") or page.metadata.get("price"), (
                "Product page should have price"
            )

    def test_jsonld_partial_exists(self) -> None:
        """JSON-LD partial should exist in theme."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        partial_path = themes_dir / "templates" / "partials" / "product-jsonld.html"

        assert partial_path.exists(), f"Product JSON-LD partial should exist at {partial_path}"

    def test_jsonld_partial_content(self) -> None:
        """JSON-LD partial should contain schema.org Product markup."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        partial_path = themes_dir / "templates" / "partials" / "product-jsonld.html"

        content = partial_path.read_text()

        # Check for key schema.org Product elements
        assert "application/ld+json" in content, "Should have application/ld+json script type"
        assert "@context" in content, "Should have @context"
        assert "schema.org" in content, "Should reference schema.org"
        assert '"@type": "Product"' in content or "@type" in content, "Should have Product @type"
        assert "offers" in content.lower(), "Should have Offer"


class TestProductTemplateRegistration:
    """Test product template is registered and scaffolds correctly."""

    def test_product_template_registered(self) -> None:
        """Product template should be registered."""
        from bengal.cli.templates.registry import list_templates

        templates = list_templates()
        template_ids = [t[0] for t in templates]

        assert "product" in template_ids, "product template should be registered"

    def test_product_template_has_description(self) -> None:
        """Product template should have description."""
        from bengal.cli.templates.registry import get_template

        template = get_template("product")
        assert template is not None, "Product template should exist"
        assert template.description, "Product template should have description"

    def test_product_template_has_files(self) -> None:
        """Product template should have template files."""
        from bengal.cli.templates.registry import get_template

        template = get_template("product")
        assert template is not None, "Product template should exist"
        assert len(template.files) > 0, "Product template should have files"

    def test_product_template_files_structure(self) -> None:
        """Product template should have expected file structure."""
        from bengal.cli.templates.registry import get_template

        template = get_template("product")
        assert template is not None, "Product template should exist"

        file_paths = [f.relative_path for f in template.files]

        # Check for key files
        assert any("_index.md" in p for p in file_paths), "Should have index page"
        assert any("products" in p for p in file_paths), "Should have products section"


class TestProductData:
    """Test product data file structure."""

    def test_product_data_file_exists(self) -> None:
        """Product data YAML file should exist in template."""
        from pathlib import Path

        template_dir = (
            Path(__file__).parent.parent.parent / "bengal" / "cli" / "templates" / "product"
        )
        data_file = template_dir / "data" / "products.yaml"

        assert data_file.exists(), f"Products data file should exist at {data_file}"

    def test_product_data_file_valid(self) -> None:
        """Product data YAML should be valid."""
        from pathlib import Path

        import yaml

        template_dir = (
            Path(__file__).parent.parent.parent / "bengal" / "cli" / "templates" / "product"
        )
        data_file = template_dir / "data" / "products.yaml"

        with open(data_file) as f:
            data = yaml.safe_load(f)

        assert "products" in data, "Data should have products key"
        assert len(data["products"]) >= 1, "Should have at least 1 product"
