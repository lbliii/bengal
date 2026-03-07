#!/usr/bin/env python3
"""
Generate cached benchmark scenario sites.

Creates pre-generated sites in benchmarks/scenarios/ for faster, more stable
benchmark runs. Benchmarks check for these first and fall back to temp generation.

Scenarios:
- minimal_100: 100 pages, no directives/code blocks/taxonomy
- minimal_1000: 1000 pages, minimal content
- directive_heavy_100: 100 pages, 5 directives per page

Run from project root:
    uv run python scripts/generate_benchmark_scenarios.py
"""

from __future__ import annotations

from pathlib import Path

PARAGRAPH = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam."
)

DIRECTIVE_BLOCK = """
:::note
This is an admonition block with some content for benchmarking.
:::
"""


def create_minimal_site(scenario_dir: Path, num_pages: int) -> None:
    """Create minimal site with no directives, code blocks, or taxonomy."""
    content_dir = scenario_dir / "content" / "posts"
    content_dir.mkdir(parents=True, exist_ok=True)
    (scenario_dir / "public").mkdir(exist_ok=True)

    for i in range(num_pages):
        content = f"""---
title: Post {i}
date: 2025-01-15
tags: []
---

# Post {i}

{PARAGRAPH}
"""
        (content_dir / f"post-{i}.md").write_text(content)

    (scenario_dir / "content" / "index.md").write_text("""---
title: Home
---

# Home

Welcome.
""")

    (scenario_dir / "bengal.toml").write_text("""
title = "Benchmark Scenario"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false
generate_sitemap = false
generate_rss = false
""")


def create_directive_heavy_site(
    scenario_dir: Path, num_pages: int, directives_per_page: int = 5
) -> None:
    """Create site with many directives per page."""
    content_dir = scenario_dir / "content" / "posts"
    content_dir.mkdir(parents=True, exist_ok=True)
    (scenario_dir / "public").mkdir(exist_ok=True)

    directive_blocks = DIRECTIVE_BLOCK * directives_per_page

    for i in range(num_pages):
        content = f"""---
title: Post {i}
date: 2025-01-15
tags: []
---

# Post {i}

{PARAGRAPH}
{directive_blocks}
"""
        (content_dir / f"post-{i}.md").write_text(content)

    (scenario_dir / "content" / "index.md").write_text("""---
title: Home
---

# Home

Welcome.
""")

    (scenario_dir / "bengal.toml").write_text("""
title = "Directive Heavy Benchmark"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false
generate_sitemap = false
generate_rss = false
""")


def create_content_complexity_site(
    scenario_dir: Path,
    num_pages: int,
    directives_per_page: int,
    code_blocks_per_page: int,
    taxonomy_terms_per_page: int,
) -> None:
    """Create site for content complexity benchmark."""
    content_dir = scenario_dir / "content" / "posts"
    content_dir.mkdir(parents=True, exist_ok=True)
    (scenario_dir / "public").mkdir(exist_ok=True)

    code_block = """
```python
def example():
    return "syntax highlighted code"
```
"""
    tags = [f"tag{i}" for i in range(max(taxonomy_terms_per_page, 1))]
    tags_str = str(tags[:taxonomy_terms_per_page]) if taxonomy_terms_per_page else "[]"

    directive_blocks = DIRECTIVE_BLOCK * directives_per_page
    code_blocks = code_block * code_blocks_per_page

    for i in range(num_pages):
        content = f"""---
title: Post {i}
date: 2025-01-15
tags: {tags_str}
---

# Post {i}

{PARAGRAPH}
{directive_blocks}
{code_blocks}
"""
        (content_dir / f"post-{i}.md").write_text(content)

    (scenario_dir / "content" / "index.md").write_text("""---
title: Home
---

# Home

Welcome.
""")

    (scenario_dir / "bengal.toml").write_text("""
title = "Content Complexity Benchmark"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false
generate_sitemap = false
generate_rss = false
""")


def main() -> None:
    """Generate all benchmark scenarios."""
    root = Path(__file__).resolve().parent.parent
    scenarios_dir = root / "benchmarks" / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    print("Generating benchmark scenarios...")

    minimal_100 = scenarios_dir / "minimal_100"
    minimal_100.mkdir(exist_ok=True)
    create_minimal_site(minimal_100, 100)
    print(f"  Created {minimal_100.relative_to(root)}")

    minimal_1000 = scenarios_dir / "minimal_1000"
    minimal_1000.mkdir(exist_ok=True)
    create_minimal_site(minimal_1000, 1000)
    print(f"  Created {minimal_1000.relative_to(root)}")

    directive_heavy_100 = scenarios_dir / "directive_heavy_100"
    directive_heavy_100.mkdir(exist_ok=True)
    create_directive_heavy_site(directive_heavy_100, 100, 5)
    print(f"  Created {directive_heavy_100.relative_to(root)}")

    # Content complexity scenarios (for benchmark_content_complexity.py)
    for d in [0, 2, 5, 10]:
        name = f"content_complexity_50_d{d}_c0_t0"
        scenario_dir = scenarios_dir / name
        scenario_dir.mkdir(exist_ok=True)
        create_content_complexity_site(scenario_dir, 50, d, 0, 0)
        print(f"  Created {scenario_dir.relative_to(root)}")

    for c in [0, 3, 10]:
        name = f"content_complexity_50_d0_c{c}_t0"
        scenario_dir = scenarios_dir / name
        scenario_dir.mkdir(exist_ok=True)
        create_content_complexity_site(scenario_dir, 50, 0, c, 0)
        print(f"  Created {scenario_dir.relative_to(root)}")

    for t in [0, 5, 20]:
        name = f"content_complexity_50_d0_c0_t{t}"
        scenario_dir = scenarios_dir / name
        scenario_dir.mkdir(exist_ok=True)
        create_content_complexity_site(scenario_dir, 50, 0, 0, t)
        print(f"  Created {scenario_dir.relative_to(root)}")

    print("Done.")


if __name__ == "__main__":
    main()
