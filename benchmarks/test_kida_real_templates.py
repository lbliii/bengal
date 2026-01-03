"""Benchmark: Kida vs Jinja2 on REAL Bengal site/ templates.

This benchmark loads actual templates from bengal/themes/default/templates/
and tests them with realistic context data.

Run with:
    python benchmarks/test_kida_real_templates.py

Or with pytest:
    python -m pytest benchmarks/test_kida_real_templates.py -v
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

# Paths
BENGAL_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = BENGAL_ROOT / "bengal" / "themes" / "default" / "templates"


def create_mock_page() -> dict[str, Any]:
    """Create a mock page object matching Bengal's Page structure."""
    return {
        "title": "Getting Started with Bengal",
        "content": "<p>Welcome to Bengal documentation.</p>" * 10,
        "excerpt": "Learn how to get started with Bengal SSG.",
        "date": "2025-12-25",
        "draft": False,
        "tags": ["python", "ssg", "documentation", "tutorial"],
        "keywords": ["bengal", "static site generator", "python"],
        "_path": "/docs/get-started/",
        "href": "/docs/get-started/",
        "kind": "doc",
        "template": "doc/single.html",
        "robots_meta": "index, follow",
        "related_posts": [
            {
                "title": f"Related Post {i}",
                "href": f"/blog/post-{i}/",
                "date": "2025-12-20",
                "content": "Sample content",
                "excerpt": "A related post about Bengal.",
            }
            for i in range(5)
        ],
        "metadata": {
            "author": "Bengal Team",
            "css_class": "",
        },
    }


def create_mock_site() -> dict[str, Any]:
    """Create a mock site object matching Bengal's Site structure."""
    return {
        "title": "Bengal Documentation",
        "url": "https://bengal.dev",
        "description": "The modern static site generator for Python.",
        "pages": [
            {
                "title": f"Page {i}",
                "href": f"/page-{i}/",
                "draft": False,
                "kind": "doc",
                "date": "2025-12-25",
            }
            for i in range(100)
        ],
        "nav_version": "1.0.0",
        "build_badge": {
            "enabled": True,
            "version": "0.1.7",
        },
        "document_application": {
            "enabled": True,
            "navigation": {
                "view_transitions": True,
                "transition_style": "crossfade",
            },
            "speculation": {
                "enabled": True,
            },
            "features": {
                "speculation_rules": True,
            },
        },
        "link_previews": {
            "enabled": True,
        },
    }


def create_mock_config() -> dict[str, Any]:
    """Create a mock config object."""
    return {
        "title": "Bengal Documentation",
        "description": "The modern static site generator for Python.",
        "baseurl": "https://bengal.dev",
        "og_image": "/assets/og-image.png",
        "output_formats": {
            "per_page": ["html", "json"],
        },
    }


def create_mock_context() -> dict[str, Any]:
    """Create full template context matching Bengal's rendering."""
    page = create_mock_page()
    site = create_mock_site()
    config = create_mock_config()

    return {
        "page": page,
        "site": site,
        "config": config,
        "params": page.get("metadata", {}),
        "meta": page,
        "section": {"title": "Documentation", "pages": site["pages"][:10]},
        "content": page["content"],
        "toc": "<ul><li><a href='#intro'>Introduction</a></li><li><a href='#install'>Installation</a></li></ul>",
        "meta_desc": page.get("excerpt", config["description"]),
        # Template functions (simplified mocks)
        "current_lang": lambda: "en",
        "get_menu_lang": lambda name, lang: [
            {"title": "Docs", "href": "/docs/"},
            {"title": "Blog", "href": "/blog/"},
            {"title": "About", "href": "/about/"},
        ],
        "get_auto_nav": lambda: [],
        "canonical_url": lambda url: f"https://bengal.dev{url}",
        "og_image": lambda path, page=None: f"https://bengal.dev{path}" if path else "",
        "asset_url": lambda path: f"/assets/{path}",
        "icon": lambda name, **kwargs: f'<svg class="icon icon-{name}"></svg>',
    }


class TemplateTest:
    """Represents a template test case."""

    def __init__(self, name: str, path: Path, context: dict[str, Any] | None = None):
        self.name = name
        self.path = path
        self.context = context or create_mock_context()
        self.source = path.read_text() if path.exists() else ""


def get_test_templates() -> list[TemplateTest]:
    """Get list of templates to test."""
    templates = []

    # Key templates from Bengal's default theme
    template_files = [
        ("page.html", "Standard page template"),
        ("post.html", "Blog post template"),
        ("index.html", "List/index template"),
        ("home.html", "Homepage template"),
        ("search.html", "Search page"),
        ("tags.html", "Tags listing"),
        ("partials/header.html", "Header partial"),
        ("partials/footer.html", "Footer partial"),
        ("partials/navigation.html", "Navigation partial"),
        ("partials/sidebar.html", "Sidebar partial"),
        ("doc/single.html", "Documentation single page"),
        ("doc/list.html", "Documentation list"),
        ("blog/single.html", "Blog single post"),
        ("blog/list.html", "Blog list"),
    ]

    for filename, description in template_files:
        path = TEMPLATES_DIR / filename
        if path.exists():
            templates.append(
                TemplateTest(
                    name=f"{filename} ({description})",
                    path=path,
                )
            )

    return templates


def benchmark_single_template(
    template_source: str,
    context: dict[str, Any],
    iterations: int = 100,
) -> tuple[float, float, str, str]:
    """Benchmark a single template with both engines.

    Returns: (jinja_time, kida_time, jinja_output, kida_output)
    """
    from jinja2 import BaseLoader
    from jinja2 import Environment as JinjaEnv

    from bengal.rendering.kida import DictLoader
    from bengal.rendering.kida import Environment as KidaEnv

    # Custom loader that returns empty for missing templates
    class MockLoader(BaseLoader):
        def __init__(self, templates: dict[str, str]):
            self.templates = templates

        def get_source(self, environment, template):
            if template in self.templates:
                source = self.templates[template]
                return source, template, lambda: True
            # Return empty template for missing includes
            return "", template, lambda: True

    # Common templates needed for includes
    mock_templates = {
        "base.html": """<!DOCTYPE html>
<html>
<head><title>{% block title %}{% endblock %}</title></head>
<body>{% block content %}{% endblock %}</body>
</html>""",
        "partials/header.html": "<header>Header</header>",
        "partials/footer.html": "<footer>Footer</footer>",
        "partials/action-bar.html": "<div class='action-bar'>Action Bar</div>",
        "partials/blog-card.html": "<div class='card'>Card</div>",
        "partials/navigation-components.html": """
{% macro breadcrumbs(page=none) %}<nav>Breadcrumbs</nav>{% endmacro %}
{% macro page_navigation(page) %}<nav>Prev/Next</nav>{% endmacro %}
{% macro pagination(base_url, current_page, total_pages) %}<nav>Pagination</nav>{% endmacro %}
""",
        "partials/content-components.html": """
{% macro tag_list(tags) %}<span class='tags'>{{ tags | join(', ') if tags else '' }}</span>{% endmacro %}
{% macro random_posts(count=3) %}<div class='random'>Random</div>{% endmacro %}
{% macro content_tiles(title=none, children=none, subsections=none, related=none, related_title=none, variant="compact", group_by=none) %}<div class='tiles'>Tiles</div>{% endmacro %}
""",
    }
    mock_templates["_current"] = template_source

    # Setup Jinja2 (auto_reload=False for fair benchmark)
    jinja_env = JinjaEnv(loader=MockLoader(mock_templates), autoescape=True, auto_reload=False)
    # Add custom filters
    jinja_env.filters["safe"] = lambda x: x
    jinja_env.filters["date_iso"] = lambda x: x
    jinja_env.filters["time_ago"] = lambda x: "3 days ago"
    jinja_env.filters["meta_keywords"] = lambda tags, n: ", ".join(tags[:n]) if tags else ""
    jinja_env.filters["where_not"] = lambda items, attr, val: [
        i for i in (items or []) if i.get(attr) != val
    ]
    # Add tests
    jinja_env.tests["sameas"] = lambda a, b: a is b

    # Setup Kida (auto_reload=False for fair benchmark)
    kida_env = KidaEnv(loader=DictLoader(mock_templates), autoescape=True, auto_reload=False)

    try:
        jinja_template = jinja_env.get_template("_current")
    except Exception as e:
        return -1, -1, f"Jinja error: {e}", ""

    try:
        kida_template = kida_env.get_template("_current")
    except Exception as e:
        return -1, -1, "", f"Kida error: {e}"

    # Test render once to check for errors
    try:
        jinja_output = jinja_template.render(**context)
    except Exception as e:
        jinja_output = f"Jinja render error: {e}"

    try:
        kida_output = kida_template.render(**context)
    except Exception as e:
        kida_output = f"Kida render error: {e}"

    import contextlib

    # Warmup (more iterations to stabilize)
    for _ in range(50):
        with contextlib.suppress(Exception):
            jinja_template.render(**context)
        with contextlib.suppress(Exception):
            kida_template.render(**context)

    # Benchmark Jinja2 - RENDER only (template already compiled)
    start = time.perf_counter()
    for _ in range(iterations):
        with contextlib.suppress(Exception):
            jinja_template.render(**context)
    jinja_time = time.perf_counter() - start

    # Benchmark Kida - RENDER only (template already compiled)
    start = time.perf_counter()
    for _ in range(iterations):
        with contextlib.suppress(Exception):
            kida_template.render(**context)
    kida_time = time.perf_counter() - start

    return jinja_time, kida_time, jinja_output, kida_output


def run_real_template_benchmarks():
    """Run benchmarks on real Bengal templates."""
    print("=" * 90)
    print("Kida vs Jinja2: Real Bengal Template Benchmark")
    print("=" * 90)
    print(f"Templates directory: {TEMPLATES_DIR}")
    print()

    # Test simple standalone templates first
    print("=" * 90)
    print("PHASE 1: Simple Template Patterns (from real templates)")
    print("=" * 90)

    simple_patterns = {
        "Variable output": "{{ page.title }}",
        "Nested attribute": "{{ page.metadata.author }}",
        "Filter chain": "{{ page.title | upper | trim }}",
        "Conditional": "{% if page.draft %}Draft{% else %}Published{% endif %}",
        "Loop (tags)": "{% for tag in page.tags %}{{ tag }}{% endfor %}",
        "Loop (pages)": "{% for p in site.pages %}{{ p.title }}{% endfor %}",
        "Loop with if": "{% for p in site.pages %}{% if not p.draft %}{{ p.title }}{% endif %}{% endfor %}",
        "Function call": "{{ current_lang() }}",
        "Complex expr": "{{ 'Draft' if page.draft else page.title }}",
    }

    context = create_mock_context()
    results = []

    print(f"{'Pattern':40} | {'Jinja2':>12} | {'Kida':>12} | {'Speedup':>10}")
    print("-" * 90)

    for name, source in simple_patterns.items():
        jinja_time, kida_time, _, _ = benchmark_single_template(source, context, iterations=10000)

        if jinja_time > 0 and kida_time > 0:
            speedup = jinja_time / kida_time
            print(
                f"{name:40} | {jinja_time * 1000:10.2f}ms | {kida_time * 1000:10.2f}ms | {speedup:8.1f}x"
            )
            results.append((name, jinja_time, kida_time, speedup))
        else:
            print(f"{name:40} | ERROR")

    if results:
        total_jinja = sum(r[1] for r in results)
        total_kida = sum(r[2] for r in results)
        avg_speedup = total_jinja / total_kida if total_kida > 0 else 0
        wins = sum(1 for r in results if r[3] > 1.0)

        print("-" * 90)
        print(
            f"{'TOTAL':40} | {total_jinja * 1000:10.2f}ms | {total_kida * 1000:10.2f}ms | {avg_speedup:8.1f}x"
        )
        print()
        print(f"Kida wins: {wins}/{len(results)} patterns")
        print(f"Average speedup: {avg_speedup:.1f}x")

    # Phase 2: Real template files
    print()
    print("=" * 90)
    print("PHASE 2: Real Template Files")
    print("=" * 90)
    print()

    templates = get_test_templates()
    if not templates:
        print("No templates found in", TEMPLATES_DIR)
        return

    file_results = []

    for test in templates:
        if not test.source:
            print(f"SKIP: {test.name} (file not found)")
            continue

        # More iterations to amortize any remaining overhead
        iterations = 1000

        jinja_time, kida_time, jinja_out, kida_out = benchmark_single_template(
            test.source, test.context, iterations=iterations
        )

        if jinja_time > 0 and kida_time > 0:
            speedup = jinja_time / kida_time
            status = "✓" if speedup >= 1.0 else "✗"
            print(
                f"{status} {test.name[:50]:50} | {jinja_time * 1000:8.2f}ms | {kida_time * 1000:8.2f}ms | {speedup:6.1f}x"
            )
            file_results.append((test.name, jinja_time, kida_time, speedup))
        elif "error" in str(jinja_out).lower():
            print(f"! {test.name[:50]:50} | Jinja error: {jinja_out[:50]}")
        elif "error" in str(kida_out).lower():
            print(f"! {test.name[:50]:50} | Kida error: {kida_out[:50]}")
        else:
            print(f"? {test.name[:50]:50} | Unknown error")

    if file_results:
        print()
        total_jinja = sum(r[1] for r in file_results)
        total_kida = sum(r[2] for r in file_results)
        avg_speedup = total_jinja / total_kida if total_kida > 0 else 0
        wins = sum(1 for r in file_results if r[3] > 1.0)

        print("-" * 90)
        print(
            f"Real templates total: Jinja {total_jinja * 1000:.2f}ms, Kida {total_kida * 1000:.2f}ms = {avg_speedup:.1f}x"
        )
        print(f"Kida faster in: {wins}/{len(file_results)} templates")


def main():
    """Run the benchmark suite."""
    try:
        run_real_template_benchmarks()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure both jinja2 and bengal are installed.")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
