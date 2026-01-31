"""Product site template.

Provides a starter product/e-commerce site with product listings,
individual product pages, JSON-LD structured data, and supporting pages.

Exported objects:
- ``TEMPLATE``: the concrete :class:`~bengal.scaffolds.base.SiteTemplate`.
"""

from ..base import SiteTemplate, TemplateFile
from ..utils import load_template_file


def _create_product_template() -> SiteTemplate:
    """Construct the product template definition.

    Returns:
        A :class:`SiteTemplate` that scaffolds a product-focused site.

    """
    files = [
        # Content pages
        TemplateFile(
            relative_path="_index.md",
            content=load_template_file(__file__, "_index.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="products/_index.md",
            content=load_template_file(__file__, "products/_index.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="products/product-1.md",
            content=load_template_file(__file__, "products/product-1.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="products/product-2.md",
            content=load_template_file(__file__, "products/product-2.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="features.md",
            content=load_template_file(__file__, "features.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="pricing.md",
            content=load_template_file(__file__, "pricing.md", replace_date=True),
            target_dir="content",
        ),
        TemplateFile(
            relative_path="contact.md",
            content=load_template_file(__file__, "contact.md", replace_date=True),
            target_dir="content",
        ),
        # Data files
        TemplateFile(
            relative_path="products.yaml",
            content=load_template_file(__file__, "products.yaml", subdir="data"),
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
