# Kida 2.0 Moonshot Vision

**Status**: Vision Document  
**Author**: Bengal Core Team  
**Date**: 2025-12-26  
**Tagline**: *"Templates that think, adapt, and fly."*

---

## 🌙 Executive Summary

This document outlines an ambitious vision for **Kida 2.0** — transforming Bengal's template engine from "best-in-class static site generator" to "the most powerful template platform in the Python ecosystem."

We're not just catching up with modern frameworks. We're **leap-frogging** them.

---

## 🚀 The Big Ideas

### 1. **Streaming Templates** — Real-time Progressive Rendering

**What**: Templates that stream their output chunk-by-chunk using async generators.

**Why**: For large pages with expensive computations, users see content immediately instead of waiting for the entire page.

**Syntax**:
```html
{% stream %}
  <header>{{ page.title }}</header>
  {% flush %}  {# Send immediately to client #}

  {% async for item in fetch_large_dataset() %}
    <article>{{ item.content }}</article>
    {% if loop.index % 10 == 0 %}{% flush %}{% end %}
  {% end %}
{% end %}
```

**Implementation**:
- Add `{% stream %}` and `{% flush %}` directives
- Compile to `async def render_stream()` that yields chunks
- Integrate with ASGI servers (Starlette, FastAPI)

---

### 2. **Component Islands** — Independent Hydration Zones

**What**: Server-rendered components that can specify their own hydration behavior.

**Why**: Mix static and dynamic content. Critical sections hydrate immediately; others defer.

**Syntax**:
```html
{% island "user-dashboard" hydrate="visible" %}
  <div data-island="user-dashboard">
    {{ render_dashboard(user) }}
  </div>
{% end %}

{% island "analytics" hydrate="idle" priority="low" %}
  {{ analytics_widget() }}
{% end %}
```

**Hydration Modes**:
- `hydrate="load"` — Hydrate on page load (default)
- `hydrate="visible"` — Hydrate when scrolled into view
- `hydrate="idle"` — Hydrate when browser is idle
- `hydrate="interaction"` — Hydrate on first click/hover
- `hydrate="never"` — Pure static (no JS)

---

### 3. **Reactive Templates** — Live Data Binding

**What**: Templates that automatically re-render when their data changes.

**Why**: Build real-time dashboards, live previews, and collaborative editing without writing JavaScript.

**Syntax**:
```html
{% reactive source="websocket://localhost:8000/updates" %}
  <div class="live-counter">
    {{ data.count }} active users
  </div>
{% end %}

{# Or with polling #}
{% reactive source="/api/stats.json" interval="5s" transition="fade" %}
  {{ render_stats(data) }}
{% end %}
```

**Features**:
- WebSocket, SSE, and polling support
- Morphdom-style DOM diffing (minimal repaints)
- CSS transition hooks
- Works with HTMX, Alpine.js, or standalone

---

### 4. **Template Inheritance 2.0** — Multi-Parent Composition

**What**: Inherit from multiple parent templates with conflict resolution.

**Why**: Compose complex layouts from orthogonal concerns (theme, layout, feature).

**Syntax**:
```html
{% extends "layouts/base.html", "mixins/sidebar.html", "features/comments.html" %}

{% override sidebar.content %}
  {# Override from sidebar.html #}
  {{ super() }}  {# Include parent's content #}
  <nav>Custom nav</nav>
{% end %}

{% merge head %}
  {# Combine with parent's head block (don't replace) #}
  <link rel="stylesheet" href="extra.css">
{% end %}
```

---

### 5. **Smart Slots** — Named Slots with Type Contracts

**What**: Typed, validated slots for component composition.

**Why**: Catch template errors at compile time, not runtime.

**Syntax**:
```html
{# Define component with typed slots #}
{% def card(title: str) %}
  {% slot header required %}
    <h3>{{ title }}</h3>
  {% end %}

  {% slot body optional %}
    <p>Default body content</p>
  {% end %}

  {% slot actions type="list[button]" %}
  {% end %}
{% end %}

{# Use with named slots #}
{% call card("My Card") %}
  {% fill header %}
    <h2 class="custom">{{ title }}</h2>
  {% end %}

  {% fill actions %}
    <button>Save</button>
    <button>Cancel</button>
  {% end %}
{% end %}
```

---

### 6. **Template DevTools** — In-Browser Inspector

**What**: A browser extension/overlay that shows template structure, performance, and cache status.

**Why**: Debug templates visually. See what's slow. Understand the hierarchy.

**Features**:
- **Template Tree View**: See the inheritance/include tree
- **Performance Flame Graph**: Which macro is slow?
- **Cache Inspector**: Hit/miss rates for `{% cache %}` blocks
- **Context Viewer**: What variables are available here?
- **Hot Reload**: Edit templates in browser, see changes live
- **Breakpoints**: Pause rendering at specific template lines

**Implementation**:
```html
{# Enable in development #}
{% if config.debug %}
  {% include 'partials/kida-devtools.html' %}
{% end %}
```

---

### 7. **AI Template Generation** — Natural Language to Kida

**What**: Generate templates from natural language descriptions or sketches.

**Why**: Accelerate prototyping. Let AI handle boilerplate.

**CLI Interface**:
```bash
# Generate from description
bengal template generate \
  --prompt "A blog post card with title, excerpt, author avatar, and publish date" \
  --output templates/partials/blog-card.html

# Generate from wireframe image
bengal template generate \
  --from-image wireframe.png \
  --style "modern, minimal, dark mode" \
  --output templates/landing.html

# Improve existing template
bengal template improve \
  --input templates/old-page.html \
  --goals "accessibility, performance, mobile-first"
```

**In-Editor**:
```html
{# @ai Generate a responsive navigation menu with dropdown support #}
{# @ai-context: This is for a documentation site with versioning #}
```

---

### 8. **Multi-Format Rendering** — One Template, Many Outputs

**What**: Render the same template to HTML, PDF, Markdown, or custom formats.

**Why**: Single source of truth. Documentation that works everywhere.

**Syntax**:
```html
{# Template with format-aware sections #}
{% format html %}
  <article class="prose">
    {{ content | safe }}
  </article>
{% end %}

{% format pdf %}
  \section{ {{ title }} }
  {{ content | latex_escape }}
{% end %}

{% format markdown %}
# {{ title }}

{{ content | strip_html }}
{% end %}
```

**CLI**:
```bash
bengal build --format html,pdf,markdown
```

---

### 9. **Template Testing Framework** — Unit Tests for Templates

**What**: First-class testing support for templates.

**Why**: Catch regressions. Test edge cases. TDD for templates.

**Syntax** (`tests/templates/test_card.py`):
```python
from bengal.testing import TemplateTest

class TestBlogCard(TemplateTest):
    template = "partials/blog-card.html"

    def test_renders_title(self):
        result = self.render(post={"title": "Hello World"})
        self.assertContains(result, "<h3>Hello World</h3>")

    def test_handles_missing_author(self):
        result = self.render(post={"title": "Hello", "author": None})
        self.assertNotContains(result, "undefined")
        self.assertAccessible(result)  # Axe-core checks

    def test_snapshot(self):
        result = self.render(post=sample_post)
        self.assertMatchesSnapshot(result)  # Snapshot testing
```

---

### 10. **Design Token System** — Dynamic Theming

**What**: CSS variables + Kida for runtime theme customization.

**Why**: Let users customize themes without rebuilding.

**Syntax** (`tokens.yaml`):
```yaml
colors:
  primary: "#3b82f6"
  secondary: "#10b981"
  background:
    light: "#ffffff"
    dark: "#0f172a"

typography:
  font-family:
    heading: "Space Grotesk, sans-serif"
    body: "Inter, sans-serif"
  scale: 1.25
```

**Template Integration**:
```html
{% tokens from 'tokens.yaml' %}

<style>
:root {
  {% for name, value in tokens.colors | flatten %}
  --color-{{ name }}: {{ value }};
  {% end %}

  {% for name, value in tokens.typography | flatten %}
  --{{ name }}: {{ value }};
  {% end %}
}
</style>
```

---

### 11. **Edge Rendering** — Deploy to CDN Edge

**What**: Compile templates to run at the edge (Cloudflare Workers, Vercel Edge).

**Why**: Render personalized content at the edge without origin servers.

**Implementation**:
- Compile Kida templates to JavaScript/WASM
- Runtime context injected per-request (cookies, geo, A/B tests)
- Cache fragments at edge

```html
{# Edge-aware template #}
{% edge %}
  {% if request.geo.country == 'DE' %}
    {% include 'partials/gdpr-banner.html' %}
  {% end %}

  {% cache 'user-greeting-' ~ request.user_id edge_ttl=60 %}
    {{ personalized_greeting(request.user) }}
  {% end %}
{% end %}
```

---

### 12. **While Loops** — Actually Implement Them

**Status**: `while` is already a keyword but not implemented!

**What**: Complete the implementation.

**Syntax**:
```html
{% let counter = 0 %}
{% while counter < items | length %}
  {{ render_item(items[counter]) }}
  {% let counter = counter + 1 %}
{% end %}

{# Or with async #}
{% while has_more_pages %}
  {% let page = await fetch_next_page() %}
  {{ render_page(page) }}
{% end %}
```

---

## 📊 Implementation Roadmap

### Phase 1: Foundation (Q1 2026)
- [x] Template showcase (DONE ✅)
- [ ] Implement `{% while %}`
- [ ] Implement `{% stream %}` and `{% flush %}`
- [ ] Template Testing Framework MVP
- [ ] Design Token System v1

### Phase 2: Components (Q2 2026)
- [ ] Smart Slots with named slots
- [ ] Component Islands
- [ ] Template DevTools browser extension
- [ ] Multi-format rendering (HTML + Markdown)

### Phase 3: Intelligence (Q3 2026)
- [ ] AI Template Generation CLI
- [ ] Reactive Templates (WebSocket integration)
- [ ] Multi-parent inheritance
- [ ] PDF rendering support

### Phase 4: Edge (Q4 2026)
- [ ] Edge compilation (WASM target)
- [ ] Distributed caching
- [ ] Real-time collaboration hooks

---

## 🎯 Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Template compile time | ~5ms | <2ms |
| Render time (10k page site) | ~30s | <10s |
| Template features vs Jinja | 80% | 200% |
| Edge deployment support | None | Full |
| Test coverage | ~75% | 95% |

---

## 🤝 Call to Action

This vision is ambitious. We need:

1. **Contributors** — Help implement these features
2. **Testers** — Early adopters for beta features
3. **Feedback** — Which features matter most to you?
4. **Sponsors** — Support development of advanced features

---

## 📚 Related Documents

- [RFC: Kida Modernization for Python 3.14+](../drafted/rfc-kida-modernization-314-315.md)
- [Advanced Patterns Showcase](../../bengal/themes/default/templates/partials/components/advanced-patterns.html)
- [Kida Architecture Docs](../../bengal/rendering/kida/COMPLEXITY.md)

---

*"The best template engine is the one that gets out of your way while giving you superpowers."*

— Bengal Core Team
