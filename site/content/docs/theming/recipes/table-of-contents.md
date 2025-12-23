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

```jinja2
{% if page.toc %}
<nav class="toc" aria-label="On this page">
  <h2>On this page</h2>
  {{ page.toc | safe }}
</nav>
{% endif %}
```

That's it. Bengal parses headings and generates nested HTML lists.

## What's Happening

| Component | Purpose |
|-----------|---------|
| `page.toc` | Pre-rendered HTML list of headings |
| `\| safe` | Render as HTML, not escaped text |

## Control Which Headings

Configure in `bengal.toml`:

```toml
[markup.toc]
start_level = 2  # Start at H2 (skip H1 page title)
end_level = 3    # Stop at H3
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

```jinja2
{% if page.toc and page.metadata.toc != false %}
  {{ page.toc | safe }}
{% endif %}
```

:::{/tab-item}
:::{tab-item} Article Layout

```jinja2
<div class="article-layout">
  <aside class="sidebar">
    {% if page.toc %}
    <nav class="toc">
      <h2>On this page</h2>
      {{ page.toc | safe }}
    </nav>
    {% endif %}
  </aside>

  <main>
    <h1>{{ page.title }}</h1>
    {{ page.rendered_html | safe }}
  </main>
</div>
```

:::{/tab-item}
:::{tab-item} Conditional by Section

```jinja2
{# Only show TOC for docs section #}
{% if page.section == 'docs' and page.toc %}
  <nav class="toc">
    {{ page.toc | safe }}
  </nav>
{% endif %}
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
- [Template Variables](/docs/theming/variables/) — All page properties
- [Configuration](/docs/building/configuration/) — Markup options
:::
