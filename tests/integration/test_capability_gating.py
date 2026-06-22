"""
Integration tests for per-page capability gating (#571).

When capabilities are enabled site-wide, vendor assets should only appear
on pages that actually use the feature.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path


class TestPerPageCapabilityGating:
    def test_katex_only_on_pages_with_math(self, tmp_path: Path) -> None:
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "bengal.toml").write_text("""
[site]
title = "Capability Gating Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"
features = ["content.math"]

[capabilities]
katex = true
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Welcome — no math on this page.
""")

        (content_dir / "math.md").write_text("""---
title: Math Page
---
The equation $E = mc^2$ is famous.
""")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        home_html = (site_dir / "public" / "index.html").read_text()
        math_html = (site_dir / "public" / "math" / "index.html").read_text()

        assert "vendor/katex.min" not in home_html
        assert "enhancements/math" not in home_html

        assert "vendor/katex.min" in math_html
        assert "enhancements/math" in math_html
        assert 'class="math"' in math_html

    def test_mermaid_only_on_pages_with_diagrams(self, tmp_path: Path) -> None:
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "bengal.toml").write_text("""
[site]
title = "Mermaid Gating Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"

[capabilities]
mermaid = true
iconify = true
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
No diagrams here.
""")

        (content_dir / "diagram.md").write_text("""---
title: Diagram
---
```mermaid
graph TD
  A --> B
```
""")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        home_html = (site_dir / "public" / "index.html").read_text()
        diagram_html = (site_dir / "public" / "diagram" / "index.html").read_text()

        assert "vendor/mermaid.min" not in home_html
        assert 'class="mermaid"' not in home_html

        assert 'class="mermaid"' in diagram_html
        assert "vendor/mermaid.min" in diagram_html
