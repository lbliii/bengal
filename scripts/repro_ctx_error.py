#!/usr/bin/env -S uv run python
"""Reproduce ctx scope error when endpoint extends explorer.

Run from bengal repo root:
  uv run python scripts/repro_ctx_error.py

Captures full traceback to identify root cause.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add bengal to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bengal.core.site import Site
from bengal.rendering.engines import create_engine


def main() -> None:
    site_path = Path(__file__).resolve().parent.parent / "tests" / "roots" / "test-basic"
    site = Site.from_config(site_path)
    engine = create_engine(site)

    # Load endpoint template (which extends explorer)
    env = engine.env

    # Load endpoint template
    template = env.get_template("autodoc/openapi/endpoint.html")

    # Minimal context for an endpoint page
    class MockElement:
        name = "getProducts"
        qualified_name = "products.getProducts"
        element_type = "openapi_endpoint"

        def __init__(self) -> None:
            self.metadata = {
                "method": "GET",
                "path": "/products",
                "parameters": [],
                "responses": {},
                "security": [],
            }
            self.typed_metadata = self.metadata

    class MockPage:
        title = "Get Products"
        _path = "/api/products"

        def __init__(self) -> None:
            self.metadata = {}
            self.section = None

    ctx = {
        "element": MockElement(),
        "page": MockPage(),
        "section": None,
        "config": {},
        "toc_items": [],
        "toc": "",
        "current_version": None,
        "is_latest_version": True,
        "params": {},
        "metadata": {},
        "content": "",
        "meta_desc": "",
        "reading_time": 0,
        "excerpt": "",
    }

    try:
        result = template.render(**ctx)
        print("SUCCESS:", len(result), "chars")
    except Exception as e:
        import traceback

        print("ERROR:", type(e).__name__, str(e))
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
