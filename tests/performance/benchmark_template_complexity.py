"""
Benchmark template complexity impact on build performance.

Tests how complex Jinja2 templates affect build times, including:
- Many custom templates (50+)
- Deep template inheritance chains
- Heavy use of template functions
- Complex conditional logic
- Many includes/partials

This validates that Bengal handles real-world template complexity
without significant performance degradation.

Tests:
- Baseline: Minimal template (just content)
- Light: Basic template with functions
- Medium: Multiple templates with inheritance
- Heavy: Complex templates with many functions
- Extreme: 50+ templates with deep nesting

Expected Results:
- Light templates: < 10% overhead vs baseline
- Medium templates: 10-20% overhead
- Heavy templates: 20-40% overhead
- Extreme templates: < 100% overhead (not 2x slower)
"""

import shutil
import statistics
import time
from pathlib import Path
from tempfile import mkdtemp

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def create_test_site(template_complexity: str) -> Path:
    """
    Create test site with specified template complexity.
    
    Args:
        template_complexity: One of 'baseline', 'light', 'medium', 'heavy', 'extreme'
    
    Returns:
        Path to created site
        
    """
    site_root = Path(mkdtemp(prefix=f"bengal_template_{template_complexity}_"))

    content_dir = site_root / "content"
    templates_dir = site_root / "templates"

    content_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    # Configuration
    config = """
[site]
title = "Template Complexity Test"
baseurl = "https://example.com"

[build]
output_dir = "public"
incremental = false
parallel = true
"""
    (site_root / "bengal.toml").write_text(config)

    # Create 200 pages
    for i in range(200):
        section = f"section-{i // 40 + 1}"
        section_dir = content_dir / section
        section_dir.mkdir(exist_ok=True)

        if not (section_dir / "_index.md").exists():
            (section_dir / "_index.md").write_text(f"---\ntitle: {section}\n---\n")

        # Vary template assignment
        template_type = ["post", "article", "guide", "tutorial", "reference"][i % 5]

        page_content = f"""---
title: "Page {i + 1}"
type: {template_type}
date: 2025-01-{(i % 28) + 1:02d}
tags: ["python", "testing", "performance"]
author: "Test Author"
---

# Page {i + 1}

This is page {i + 1} for template complexity testing.

## Section 1

Content with **bold** and *italic* text.

```python
def example_{i}():
    return {i}
```

## Section 2

More content here with a list:

- Item 1
- Item 2
- Item 3

## Conclusion

End of page {i + 1}.
"""
        (section_dir / f"page-{i + 1:03d}.md").write_text(page_content)

    # Create templates based on complexity level
    if template_complexity == "baseline":
        _create_baseline_templates(templates_dir)
    elif template_complexity == "light":
        _create_light_templates(templates_dir)
    elif template_complexity == "medium":
        _create_medium_templates(templates_dir)
    elif template_complexity == "heavy":
        _create_heavy_templates(templates_dir)
    elif template_complexity == "extreme":
        _create_extreme_templates(templates_dir)

    return site_root


def _create_baseline_templates(templates_dir: Path):
    """Minimal templates - just output content."""
    base = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{ page.title }}</title>
</head>
<body>
  <main>{{ content }}</main>
</body>
</html>
"""
    (templates_dir / "base.html").write_text(base)


def _create_light_templates(templates_dir: Path):
    """Light templates with basic functions."""
    base = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{ page.title }} | {{ site.config.site.title }}</title>
</head>
<body>
  {% block content %}
  <main>
    <h1>{{ page.title }}</h1>
    <time>{{ page.date | date_format }}</time>
    {{ content }}
  </main>
  {% endblock %}
</body>
</html>
"""
    (templates_dir / "base.html").write_text(base)

    # Type-specific templates
    for template_type in ["post", "article", "guide", "tutorial", "reference"]:
        type_template = """{% extends "base.html" %}
{% block content %}
<article>
  <h1>{{ page.title }}</h1>
  <p class="meta">{{ page.date | date_format }} by {{ page.author }}</p>
  {{ content }}
</article>
{% endblock %}
"""
        (templates_dir / f"{template_type}.html").write_text(type_template)


def _create_medium_templates(templates_dir: Path):
    """Medium complexity with inheritance and functions."""
    base = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{ page.title }} | {{ site.config.site.title }}</title>
  {% block head %}{% endblock %}
</head>
<body>
  {% include "partials/header.html" %}
  {% block content %}{% endblock %}
  {% include "partials/footer.html" %}
</body>
</html>
"""
    (templates_dir / "base.html").write_text(base)

    # Partials
    partials_dir = templates_dir / "partials"
    partials_dir.mkdir()

    (partials_dir / "header.html").write_text("""
<header>
  <h1>{{ site.config.site.title }}</h1>
  <nav>
    {% for item in site.menu.main %}
    <a href="{{ item.url }}">{{ item.name }}</a>
    {% endfor %}
  </nav>
</header>
""")

    (partials_dir / "footer.html").write_text("""
<footer>
  <p>&copy; {{ now().year }} {{ site.config.site.title }}</p>
</footer>
""")

    # Type templates with more logic
    for template_type in ["post", "article", "guide", "tutorial", "reference"]:
        type_template = """{% extends "base.html" %}

{% block head %}
<meta name="description" content="{{ page.description | default(page.title) }}">
{% if page.tags %}
<meta name="keywords" content="{{ page.tags | join(', ') }}">
{% endif %}
{% endblock %}

{% block content %}
<article>
  <header>
    <h1>{{ page.title }}</h1>
    <div class="meta">
      <time>{{ page.date | date_format }}</time>
      {% if page.author %}by {{ page.author }}{% endif %}
    </div>
    {% if page.tags %}
    <div class="tags">
      {% for tag in page.tags %}
      <a href="/tags/{{ tag | slugify }}/">{{ tag }}</a>
      {% endfor %}
    </div>
    {% endif %}
  </header>

  <div class="content">
    {{ content }}
  </div>

  {% if page.next or page.prev %}
  <nav class="pagination">
    {% if page.prev %}
    <a href="{{ page.prev.permalink }}">← {{ page.prev.title }}</a>
    {% endif %}
    {% if page.next %}
    <a href="{{ page.next.permalink }}">{{ page.next.title }} →</a>
    {% endif %}
  </nav>
  {% endif %}
</article>
{% endblock %}
"""
        (templates_dir / f"{template_type}.html").write_text(type_template)


def _create_heavy_templates(templates_dir: Path):
    """Heavy templates with many functions and logic."""
    # Start with medium templates
    _create_medium_templates(templates_dir)

    # Override with heavier versions
    for template_type in ["post", "article", "guide", "tutorial", "reference"]:
        type_template = """{% extends "base.html" %}

{% block head %}
<meta name="description" content="{{ page.description | default(page.title | truncatewords(20)) }}">
<meta property="og:title" content="{{ page.title }}">
<meta property="og:description" content="{{ page.description | default(page.content | strip_html | truncatewords(30)) }}">
<meta property="og:url" content="{{ absolute_url(page.url) }}">
{% if page.image %}
<meta property="og:image" content="{{ absolute_url(page.image) }}">
{% endif %}
<meta name="keywords" content="{{ page.tags | default([]) | join(', ') }}">
<link rel="canonical" href="{{ absolute_url(page.url) }}">
{% endblock %}

{% block content %}
<article itemscope itemtype="http://schema.org/Article">
  <header>
    <h1 itemprop="headline">{{ page.title }}</h1>
    <div class="meta">
      <time itemprop="datePublished" datetime="{{ page.date | date_iso }}">
        {{ page.date | date_format }}
      </time>
      {% if page.author %}
      <span itemprop="author">by {{ page.author }}</span>
      {% endif %}
      <span class="reading-time">{{ page.content | reading_time }} min read</span>
    </div>
    {% if page.tags %}
    <div class="tags">
      {% for tag in page.tags %}
      <a href="{{ tag_url(tag) }}" rel="tag">{{ tag }}</a>
      {% endfor %}
    </div>
    {% endif %}
  </header>

  {% if page.toc and (page.toc | length) > 3 %}
  <aside class="toc">
    <h2>Table of Contents</h2>
    <ul>
    {% for item in page.toc %}
      <li><a href="#{{ item.id }}">{{ item.title }}</a></li>
    {% endfor %}
    </ul>
  </aside>
  {% endif %}

  <div class="content" itemprop="articleBody">
    {{ content }}
  </div>

  {% if page.tags %}
  {% set related = related_posts(page, limit=3) %}
  {% if related %}
  <aside class="related">
    <h2>Related Articles</h2>
    <ul>
    {% for post in related %}
      <li>
        <a href="{{ post.permalink }}">{{ post.title }}</a>
        <span>{{ post.date | date_format }}</span>
      </li>
    {% endfor %}
    </ul>
  </aside>
  {% endif %}
  {% endif %}

  <nav class="pagination">
    {% if page.prev_in_section %}
    <a href="{{ page.prev_in_section.permalink }}" rel="prev">
      ← {{ page.prev_in_section.title | truncatewords(5) }}
    </a>
    {% endif %}
    {% if page.next_in_section %}
    <a href="{{ page.next_in_section.permalink }}" rel="next">
      {{ page.next_in_section.title | truncatewords(5) }} →
    </a>
    {% endif %}
  </nav>
</article>
{% endblock %}
"""
        (templates_dir / f"{template_type}.html").write_text(type_template)


def _create_extreme_templates(templates_dir: Path):
    """Extreme complexity with many templates and deep nesting."""
    # Start with heavy templates
    _create_heavy_templates(templates_dir)

    # Add many specialized templates
    for i in range(50):
        specialized = f"""{{% extends "base.html" %}}

{{% block content %}}
<div class="specialized-{i}">
  {{% include "partials/specialized-{i}.html" %}}
  <h1>{{{{ page.title }}}}</h1>
  {{{{ content }}}}
</div>
{{% endblock %}}
"""
        (templates_dir / f"specialized-{i}.html").write_text(specialized)

        # Create corresponding partial
        partial = f"""
<div class="component-{i}">
  <p>Specialized component {i}</p>
  {{% if page.title %}}
  <span>{{{{ page.title | truncatewords(3) }}}}</span>
  {{% endif %}}
</div>
"""
        (templates_dir / "partials" / f"specialized-{i}.html").write_text(partial)


def benchmark_template_complexity(complexity: str, runs: int = 3) -> dict:
    """
    Benchmark build with specified template complexity.
    
    Args:
        complexity: Template complexity level
        runs: Number of runs to average
    
    Returns:
        Dict with timing results
        
    """
    print(f"\nBenchmarking {complexity.upper()} template complexity...")

    site_root = create_test_site(complexity)

    try:
        times = []

        for run in range(runs):
            # Clean cache between runs
            cache_file = site_root / "public" / ".bengal-cache.json"
            if cache_file.exists():
                cache_file.unlink()

            site = Site.from_config(site_root)

            start = time.perf_counter()
            _ = site.build(BuildOptions(incremental=False))
            elapsed = time.perf_counter() - start

            times.append(elapsed)
            print(f"  Run {run + 1}: {elapsed:.3f}s")

        avg_time = statistics.mean(times)
        pages_per_sec = 200 / avg_time

        return {
            "complexity": complexity,
            "avg_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "pages_per_sec": pages_per_sec,
            "times": times,
        }

    finally:
        shutil.rmtree(site_root)


def run_template_complexity_benchmarks():
    """Run full suite of template complexity benchmarks."""
    print("=" * 80)
    print("TEMPLATE COMPLEXITY BENCHMARKS")
    print("=" * 80)
    print()
    print("This benchmark measures how template complexity affects build performance.")
    print()
    print("Complexity Levels:")
    print("  - Baseline: Minimal template (just content)")
    print("  - Light:    Basic template with functions")
    print("  - Medium:   Multiple templates with inheritance")
    print("  - Heavy:    Complex templates with many functions")
    print("  - Extreme:  50+ templates with deep nesting")
    print()
    print("Testing with 200 pages per complexity level...")
    print()

    complexities = ["baseline", "light", "medium", "heavy", "extreme"]
    results = []

    for complexity in complexities:
        result = benchmark_template_complexity(complexity, runs=3)
        results.append(result)

    # Summary
    print(f"\n{'=' * 80}")
    print("RESULTS")
    print(f"{'=' * 80}")
    print()
    print(f"{'Complexity':<12} {'Avg Time':<12} {'Pages/sec':<12} {'Overhead':<12}")
    print("-" * 80)

    baseline_time = results[0]["avg_time"]

    for r in results:
        overhead_pct = ((r["avg_time"] - baseline_time) / baseline_time) * 100
        overhead_str = f"+{overhead_pct:.1f}%" if r["complexity"] != "baseline" else "—"

        print(
            f"{r['complexity']:<12} "
            f"{r['avg_time']:>8.3f}s    "
            f"{r['pages_per_sec']:>8.1f}    "
            f"{overhead_str:>10}"
        )

    # Validation
    print(f"\n{'=' * 80}")
    print("VALIDATION")
    print(f"{'=' * 80}")
    print()

    light_overhead = ((results[1]["avg_time"] - baseline_time) / baseline_time) * 100
    medium_overhead = ((results[2]["avg_time"] - baseline_time) / baseline_time) * 100
    heavy_overhead = ((results[3]["avg_time"] - baseline_time) / baseline_time) * 100
    extreme_overhead = ((results[4]["avg_time"] - baseline_time) / baseline_time) * 100

    checks = []

    if light_overhead < 10:
        checks.append(f"✅ Light templates: +{light_overhead:.1f}% overhead (target: <10%)")
    else:
        checks.append(f"⚠️  Light templates: +{light_overhead:.1f}% overhead (target: <10%)")

    if medium_overhead < 20:
        checks.append(f"✅ Medium templates: +{medium_overhead:.1f}% overhead (target: <20%)")
    else:
        checks.append(f"⚠️  Medium templates: +{medium_overhead:.1f}% overhead (target: <20%)")

    if heavy_overhead < 40:
        checks.append(f"✅ Heavy templates: +{heavy_overhead:.1f}% overhead (target: <40%)")
    else:
        checks.append(f"⚠️  Heavy templates: +{heavy_overhead:.1f}% overhead (target: <40%)")

    if extreme_overhead < 100:
        checks.append(f"✅ Extreme templates: +{extreme_overhead:.1f}% overhead (target: <100%)")
    else:
        checks.append(f"❌ Extreme templates: +{extreme_overhead:.1f}% overhead (target: <100%)")

    for check in checks:
        print(check)

    print()
    print("Key Findings:")
    print()

    if all("✅" in check for check in checks):
        print("✅ Template complexity has acceptable performance impact")
        print("   Bengal can handle complex real-world templates efficiently")
    else:
        print("⚠️  Template complexity causes significant overhead")
        print("   Consider optimizing template rendering or caching")

    print()


if __name__ == "__main__":
    run_template_complexity_benchmarks()
