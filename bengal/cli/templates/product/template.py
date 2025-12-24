"""Product site template.

Provides a starter product/e-commerce site with product listings,
individual product pages, JSON-LD structured data, and supporting pages.

Exported objects:
- ``TEMPLATE``: the concrete :class:`~bengal.cli.templates.base.SiteTemplate`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..base import SiteTemplate, TemplateFile


def _load_template_file(relative_path: str) -> str:
    """Load and lightly render a page from the template's ``pages/`` dir.

    Replaces ``{{date}}`` placeholders with today's date (``YYYY-MM-DD``).

    Args:
        relative_path: Path inside this template's ``pages/`` directory.

    Returns:
        The file contents with simple substitutions applied.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / "pages" / relative_path

    with open(file_path) as f:
        content = f.read()

    # Replace template variables
    current_date = datetime.now().strftime("%Y-%m-%d")
    content = content.replace("{{date}}", current_date)

    return content


def _load_data_file(relative_path: str) -> str:
    """Load a data file from the template's ``data/`` dir.

    Args:
        relative_path: Path inside this template's ``data/`` directory.

    Returns:
        The file contents.
    """
    template_dir = Path(__file__).parent
    file_path = template_dir / "data" / relative_path

    with open(file_path) as f:
        return f.read()


def _create_product_template() -> SiteTemplate:
    """Construct the product template definition.

    Returns:
        A :class:`SiteTemplate` that scaffolds a product-focused site.
    """

    files = [
        # Content pages
        TemplateFile(
            relative_path="_index.md",
            content=_load_template_file("_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="products/_index.md",
            content=_load_template_file("products/_index.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="products/product-1.md",
            content=_load_template_file("products/product-1.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="products/product-2.md",
            content=_load_template_file("products/product-2.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="features.md",
            content=_load_template_file("features.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="pricing.md",
            content=_load_template_file("pricing.md"),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="contact.md",
            content=_load_template_file("contact.md"),
            target_dir="content",
        ),
        # Data files
        TemplateFile(
            relative_path="products.yaml",
            content=_load_data_file("products.yaml"),
            target_dir="data",
        ),
    ]

    return SiteTemplate(
        id="product",
        name="Product",
        description="A product-focused site with listings, features, and JSON-LD structured data",
        files=files,
        additional_dirs=["content/products", "data"],
        menu_sections=["products", "features", "pricing", "contact"],
    )


# Export the template
TEMPLATE = _create_product_template()
