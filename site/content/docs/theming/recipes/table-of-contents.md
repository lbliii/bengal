---
title: Add Table of Contents
nav_title: TOC
description: Use Bengal's auto-generated page.toc for navigation
weight: 50
draft: false
lang: en
tags:
- cookbook
- toc
- navigation
keywords:
- table of contents
- toc
- headings
- navigation
category: cookbook
---

# Add Table of Contents

Bengal automatically generates a table of contents from page headings. Access it via `page.toc`.

## The Pattern

```kida
{% if page.toc %}
<nav class="toc" aria-label="On this page">
  <h2>On this page</h2>
  {{ page.toc | safe }}
</nav>
{% end %}
```

That's it. Bengal parses headings and generates nested HTML lists.

## What's Happening

| Component | Purpose |
|-----------|---------|
| `page.toc` | Pre-rendered HTML list of headings |
| `\| safe` | Render as HTML, not escaped text |

## Control Which Headings

Configure TOC depth in `bengal.toml`:

```toml
[content]
toc_depth = 4  # Maximum heading depth (1-6). Default: 4
```

This controls how deep the TOC goes. For example:
- `toc_depth = 2` includes only H2 headings
- `toc_depth = 3` includes H2 and H3 headings
- `toc_depth = 4` includes H2, H3, and H4 headings (default)

For parser-specific control, use `markdown.toc_depth` with a range string:

```toml
[markdown]
toc_depth = "2-4"  # String format for parser-level control
```

## Variations

:::{tab-set}
:::{tab-item} Per-Page Disable

```yaml
---
title: Simple Page
toc: false
---
```

Then in template:

```kida
{% if page.toc and page.metadata.toc != false %}
  {{ page.toc | safe }}
{% end %}
```

:::{/tab-item}
:::{tab-item} Article Layout

```kida
<div class="article-layout">
  <aside class="sidebar">
    {% if page.toc %}
    <nav class="toc">
      <h2>On this page</h2>
      {{ page.toc | safe }}
    </nav>
    {% end %}
  </aside>

  <main>
    <h1>{{ page.title }}</h1>
    {{ page.rendered_html | safe }}
  </main>
</div>
```

:::{/tab-item}
:::{tab-item} Conditional by Section

```kida
{# Only show TOC for docs section #}
{% if page.section == 'docs' and page.toc %}
  <nav class="toc">
    {{ page.toc | safe }}
  </nav>
{% end %}
```

:::{/tab-item}
:::{/tab-set}

## Scroll Highlighting (JavaScript)

Highlight current section as user scrolls — this part is standard JS, not Bengal-specific:

```javascript
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      document.querySelectorAll('.toc a').forEach(a => a.classList.remove('active'));
      document.querySelector(`.toc a[href="#${entry.target.id}"]`)?.classList.add('active');
    }
  });
}, { rootMargin: '-20% 0px -80% 0px' });

document.querySelectorAll('h2[id], h3[id]').forEach(h => observer.observe(h));
```

:::{seealso}
- [Template Variables](/docs/reference/theme-variables/) — All page properties
- [Configuration](/docs/building/configuration/) — Markup options
:::
