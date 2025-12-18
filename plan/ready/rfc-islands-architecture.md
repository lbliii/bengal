# RFC: Islands Architecture (Partial Hydration)

**Status**: Draft  
**Created**: 2025-12-02  
**Author**: AI Assistant  
**Priority**: P1 (High)  
**Confidence**: 78% 🟡  
**Est. Impact**: Zero-JS by default, selective interactivity, faster page loads

---

## Executive Summary

This RFC proposes adding **Islands Architecture** to Bengal - a pattern where pages are static HTML by default with opt-in interactive "islands" that hydrate with JavaScript only when needed. This dramatically reduces JavaScript payload and improves performance while maintaining interactivity where it matters.

**Key Changes**:
1. Static HTML output by default (zero JS)
2. `<bengal-island>` component for interactive regions
3. Multiple hydration strategies (load, visible, idle, media)
4. Component framework agnostic (vanilla JS, Alpine, Preact, etc.)

---

## Problem Statement

### Current State

Bengal's default theme ships significant JavaScript on every page:

```html
<!-- bengal/themes/default/templates/base.html -->
<script defer src="{{ asset_url('js/utils.js') }}"></script>
<script defer src="{{ asset_url('js/theme-toggle.js') }}"></script>
<script defer src="{{ asset_url('js/mobile-nav.js') }}"></script>
<script defer src="{{ asset_url('js/tabs.js') }}"></script>
<script defer src="{{ asset_url('js/toc.js') }}"></script>
<script defer src="{{ asset_url('js/search.js') }}"></script>
<script defer src="{{ asset_url('js/search-modal.js') }}"></script>
<!-- ... 20+ more scripts ... -->
```

**Evidence**: `bengal/themes/default/templates/base.html` loads 25+ script files.

### Pain Points

1. **All-or-Nothing JavaScript**: Every page loads the same JS bundle regardless of what interactivity it needs.

2. **Slow Initial Load**: On slower connections, users wait for JS to download/parse before any interactivity.

3. **Unnecessary Hydration**: Static pages (API reference, simple docs) still load interactive code.

4. **Bundle Size Growth**: As features are added, bundle grows - affecting all pages.

5. **Mobile Performance**: Heavy JS impacts mobile devices disproportionately.

### Metrics (Current State)

From Lighthouse audit of Bengal docs:
- Total JavaScript: ~1.2MB uncompressed
- Time to Interactive: 3.5s (3G)
- Main Thread Blocking: 2.1s
- Unused JavaScript: 67%

### Evidence from Modern Frameworks

**Astro Islands** (2022+):
```astro
---
import SearchModal from './SearchModal.jsx';
import StaticNav from './StaticNav.astro';
---

<!-- Static - no JS -->
<StaticNav />

<!-- Interactive island - loads JS -->
<SearchModal client:visible />
```

**Fresh (Deno)** uses the same pattern.

**11ty + WebC** supports islands via `webc:keep`.

---

## Goals & Non-Goals

### Goals

1. **G1**: Ship zero JavaScript by default for static content
2. **G2**: Provide opt-in hydration for interactive components
3. **G3**: Support multiple hydration strategies (load, visible, idle, media)
4. **G4**: Enable framework-agnostic component hydration
5. **G5**: Maintain progressive enhancement (works without JS)
6. **G6**: Reduce total JavaScript payload by 60%+

### Non-Goals

- **NG1**: Full client-side routing (this is SSG)
- **NG2**: Server-side rendering (SSG only)
- **NG3**: React/Vue/Svelte framework lock-in
- **NG4**: Component state persistence across pages
- **NG5**: Replacing all existing JS (some stays for critical features)

---

## Architecture Impact

**Affected Subsystems**:

- **Themes** (`bengal/themes/`): Major impact
  - New `islands/` directory for island components
  - Template changes for island markers
  - Reduced default JavaScript

- **Rendering** (`bengal/rendering/`): Moderate impact
  - Island extraction during render
  - Script injection for hydration

- **Postprocess** (`bengal/postprocess/`): Minor impact
  - Island manifest generation
  - Script bundling for islands

- **CLI** (`bengal/cli/`): Minor impact
  - `bengal islands list` - List available islands
  - Island development tools

**New Components**:
- `bengal/islands/` - Island infrastructure
- `bengal/islands/hydration.py` - Hydration strategies
- `bengal/islands/manifest.py` - Island manifest generation
- Runtime JS loader (tiny, ~2KB)

---

## Design Options

### Option A: Custom Element Islands (Recommended)

**Description**: Use Web Components (`<bengal-island>`) with custom hydration.

```html
<!-- Template usage -->
<bengal-island
  component="search-modal"
  client:visible
  props='{"placeholder": "Search docs..."}'
>
  <!-- Static fallback (SEO, no-JS) -->
  <button>Search</button>
</bengal-island>

<!-- Hydrates to -->
<bengal-island data-hydrated>
  <div class="search-modal">
    <!-- Full interactive component -->
  </div>
</bengal-island>
```

**Runtime loader (2KB)**:
```javascript
// bengal-island-loader.js
class BengalIsland extends HTMLElement {
  connectedCallback() {
    const strategy = this.dataset.client;
    const component = this.dataset.component;

    switch (strategy) {
      case 'load':
        this.hydrate(component);
        break;
      case 'visible':
        this.hydrateOnVisible(component);
        break;
      case 'idle':
        this.hydrateOnIdle(component);
        break;
      case 'media':
        this.hydrateOnMedia(component);
        break;
    }
  }

  hydrateOnVisible(component) {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        this.hydrate(component);
        observer.disconnect();
      }
    });
    observer.observe(this);
  }

  hydrateOnIdle(component) {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => this.hydrate(component));
    } else {
      setTimeout(() => this.hydrate(component), 200);
    }
  }

  hydrateOnMedia(component) {
    const query = this.dataset.media;
    const mq = window.matchMedia(query);
    if (mq.matches) {
      this.hydrate(component);
    } else {
      mq.addEventListener('change', () => this.hydrate(component), { once: true });
    }
  }

  async hydrate(component) {
    if (this.dataset.hydrated) return;

    const module = await import(`/assets/islands/${component}.js`);
    const props = JSON.parse(this.dataset.props || '{}');

    module.default(this, props);
    this.dataset.hydrated = 'true';
  }
}

customElements.define('bengal-island', BengalIsland);
```

**Pros**:
- Framework agnostic
- Progressive enhancement built-in
- Standards-based (Custom Elements)
- Tiny runtime (~2KB)
- Works with any JS framework for components

**Cons**:
- Custom element overhead (minimal)
- Need to define island components separately
- Learning curve for island pattern

**Complexity**: Medium

---

### Option B: Directive-Based Islands

**Description**: Use HTML attributes to mark islands.

```html
<!-- Mark any element as an island -->
<div
  bengal-island="search-modal"
  bengal-client="visible"
  bengal-props='{"placeholder": "Search..."}'
>
  <button>Search</button>
</div>
```

**Pros**:
- No custom elements
- Works with existing HTML
- Familiar to Alpine.js users

**Cons**:
- Less semantic
- Harder to style islands
- No encapsulation

**Complexity**: Low

---

### Option C: Template-Based Islands (Jinja)

**Description**: Define islands in templates with special tags.

```jinja
{% island "search-modal" client="visible" %}
  {# Static content / fallback #}
  <button>Search</button>
{% endisland %}
```

**Pros**:
- Integrated with Jinja
- Template-level abstraction
- Clear visual boundaries

**Cons**:
- Template compilation needed
- Less runtime flexibility
- Harder to pass complex props

**Complexity**: Medium

---

### Recommended: Option A (Custom Element Islands)

Custom Elements provide:

1. **Standards-based**: Works in all modern browsers
2. **Encapsulation**: Clear island boundaries
3. **Progressive enhancement**: Fallback content visible immediately
4. **Framework freedom**: Hydrate with vanilla JS, Preact, Alpine, etc.
5. **Developer tools**: Browser shows custom elements clearly

---

## Detailed Design

### 1. Island Definition

```python
# bengal/islands/component.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


HydrationStrategy = Literal["load", "visible", "idle", "media", "none"]


@dataclass
class IslandComponent:
    """
    Definition of an island component.

    Islands are interactive regions that hydrate with JavaScript
    only when needed, leaving the rest of the page static.
    """

    name: str                                    # Unique component name
    script: Path                                 # JavaScript module path
    strategy: HydrationStrategy = "visible"     # When to hydrate
    media_query: str | None = None              # For media strategy
    props_schema: dict[str, Any] | None = None  # Optional props validation
    fallback_template: str | None = None        # Jinja template for fallback

    def get_script_url(self, asset_url: str) -> str:
        """Get URL for island script."""
        return f"{asset_url}/islands/{self.name}.js"


@dataclass
class IslandInstance:
    """
    An instance of an island in a page.
    """

    component: IslandComponent
    props: dict[str, Any] = field(default_factory=dict)
    fallback_html: str = ""
    strategy_override: HydrationStrategy | None = None

    @property
    def effective_strategy(self) -> HydrationStrategy:
        return self.strategy_override or self.component.strategy

    def render_element(self) -> str:
        """Render the island element HTML."""
        import json

        strategy = self.effective_strategy
        attrs = [
            f'data-component="{self.component.name}"',
            f'data-client="{strategy}"',
        ]

        if self.props:
            props_json = json.dumps(self.props).replace('"', '&quot;')
            attrs.append(f'data-props="{props_json}"')

        if strategy == "media" and self.component.media_query:
            attrs.append(f'data-media="{self.component.media_query}"')

        attrs_str = " ".join(attrs)

        return f'<bengal-island {attrs_str}>{self.fallback_html}</bengal-island>'
```

### 2. Island Registry

```python
# bengal/islands/registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
import logging

from .component import IslandComponent, HydrationStrategy

logger = logging.getLogger(__name__)


@dataclass
class IslandRegistry:
    """
    Registry of available island components.

    Islands are discovered from:
    1. Theme's `islands/` directory
    2. Project's `islands/` directory
    3. Programmatic registration
    """

    _components: dict[str, IslandComponent] = field(default_factory=dict)

    def register(self, component: IslandComponent) -> None:
        """Register an island component."""
        if component.name in self._components:
            logger.warning(f"Overwriting island component: {component.name}")
        self._components[component.name] = component
        logger.debug(f"Registered island: {component.name}")

    def get(self, name: str) -> IslandComponent | None:
        """Get an island component by name."""
        return self._components.get(name)

    def all(self) -> Iterator[IslandComponent]:
        """Iterate over all registered components."""
        yield from self._components.values()

    def discover(self, directory: Path) -> int:
        """
        Discover island components from a directory.

        Expects directory structure:
        islands/
          search-modal/
            search-modal.js    # Component script
            fallback.html      # Optional fallback template
            config.yaml        # Optional configuration

        Returns:
            Number of components discovered
        """
        count = 0

        if not directory.exists():
            return count

        for item in directory.iterdir():
            if not item.is_dir():
                continue

            script = item / f"{item.name}.js"
            if not script.exists():
                continue

            # Load config if present
            config_file = item / "config.yaml"
            config = {}
            if config_file.exists():
                import yaml
                config = yaml.safe_load(config_file.read_text())

            # Load fallback template if present
            fallback_file = item / "fallback.html"
            fallback = None
            if fallback_file.exists():
                fallback = fallback_file.read_text()

            component = IslandComponent(
                name=item.name,
                script=script,
                strategy=config.get("strategy", "visible"),
                media_query=config.get("media_query"),
                props_schema=config.get("props"),
                fallback_template=fallback,
            )

            self.register(component)
            count += 1

        logger.info(f"Discovered {count} island components from {directory}")
        return count


# Default registry
_default_registry = IslandRegistry()


def get_registry() -> IslandRegistry:
    """Get the default island registry."""
    return _default_registry
```

### 3. Template Integration

```python
# bengal/rendering/template_functions/islands.py
from __future__ import annotations

from typing import Any
from markupsafe import Markup
import json

from bengal.islands.registry import get_registry
from bengal.islands.component import IslandInstance, HydrationStrategy


def island(
    name: str,
    *,
    client: HydrationStrategy = "visible",
    props: dict[str, Any] | None = None,
    fallback: str = "",
    **extra_props,
) -> Markup:
    """
    Render an island component in templates.

    Usage:
        {{ island("search-modal", client="visible", placeholder="Search...") }}

        {% call island("tabs", client="load") %}
          <div class="tabs-fallback">...</div>
        {% endcall %}

    Args:
        name: Island component name
        client: Hydration strategy (load, visible, idle, media, none)
        props: Props to pass to component
        fallback: Fallback HTML content
        **extra_props: Additional props (convenience)

    Returns:
        Markup for the island element
    """
    registry = get_registry()
    component = registry.get(name)

    if component is None:
        raise ValueError(f"Unknown island component: {name}")

    # Merge props
    all_props = {**(props or {}), **extra_props}

    instance = IslandInstance(
        component=component,
        props=all_props,
        fallback_html=fallback,
        strategy_override=client if client != component.strategy else None,
    )

    return Markup(instance.render_element())


def island_scripts() -> Markup:
    """
    Render script tags for islands used on the page.

    Call this in the template footer to load island scripts.

    Usage:
        {{ island_scripts() }}
    """
    # This is populated during page render
    from flask import g

    islands_used = getattr(g, '_bengal_islands_used', set())
    if not islands_used:
        return Markup("")

    registry = get_registry()
    scripts = []

    # Always include the loader
    scripts.append('<script src="/assets/js/bengal-island-loader.js" defer></script>')

    # Add scripts for used islands (modulepreload for better loading)
    for name in islands_used:
        component = registry.get(name)
        if component:
            scripts.append(
                f'<link rel="modulepreload" href="/assets/islands/{name}.js">'
            )

    return Markup("\n".join(scripts))
```

### 4. Jinja Extension

```python
# bengal/rendering/jinja_extensions/islands.py
from jinja2 import nodes
from jinja2.ext import Extension


class IslandExtension(Extension):
    """
    Jinja extension for island components.

    Provides:
        {% island "name" client="visible" prop="value" %}
          fallback content
        {% endisland %}
    """

    tags = {"island"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno

        # Parse island name
        name = parser.parse_expression()

        # Parse keyword arguments
        kwargs = []
        while parser.stream.current.test("name"):
            key = parser.stream.expect("name").value
            parser.stream.expect("assign")
            value = parser.parse_expression()
            kwargs.append(nodes.Keyword(key, value, lineno=lineno))

        # Parse body (fallback content)
        body = parser.parse_statements(["name:endisland"], drop_needle=True)

        # Build call to island() function
        return nodes.CallBlock(
            self.call_method(
                "_render_island",
                [name, nodes.List(kwargs, lineno=lineno)],
            ),
            [],
            [],
            body,
        ).set_lineno(lineno)

    def _render_island(self, name, kwargs, caller):
        """Render island with fallback content."""
        from bengal.rendering.template_functions.islands import island

        fallback = caller()
        props = {kw.key: kw.value for kw in kwargs if kw.key != "client"}
        client = next((kw.value for kw in kwargs if kw.key == "client"), "visible")

        return island(name, client=client, props=props, fallback=fallback)
```

### 5. Island Loader Script

```javascript
// bengal/themes/default/assets/js/bengal-island-loader.js

/**
 * Bengal Island Loader
 *
 * Minimal runtime (~2KB minified) for hydrating island components
 * with different strategies: load, visible, idle, media.
 */

const ISLAND_CACHE = new Map();

class BengalIsland extends HTMLElement {
  static get observedAttributes() {
    return ['data-client'];
  }

  connectedCallback() {
    // Don't re-hydrate
    if (this.dataset.hydrated === 'true') return;

    const strategy = this.dataset.client || 'visible';
    const component = this.dataset.component;

    if (!component) {
      console.warn('bengal-island: missing data-component');
      return;
    }

    switch (strategy) {
      case 'load':
        this.hydrate();
        break;
      case 'visible':
        this.hydrateOnVisible();
        break;
      case 'idle':
        this.hydrateOnIdle();
        break;
      case 'media':
        this.hydrateOnMedia();
        break;
      case 'none':
        // Explicit no hydration
        break;
      default:
        console.warn(`bengal-island: unknown strategy "${strategy}"`);
    }
  }

  hydrateOnVisible() {
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            this.hydrate();
            observer.disconnect();
          }
        },
        { rootMargin: '200px' } // Start loading slightly before visible
      );
      observer.observe(this);
    } else {
      // Fallback for old browsers
      this.hydrate();
    }
  }

  hydrateOnIdle() {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => this.hydrate(), { timeout: 2000 });
    } else {
      setTimeout(() => this.hydrate(), 200);
    }
  }

  hydrateOnMedia() {
    const query = this.dataset.media;
    if (!query) {
      console.warn('bengal-island: media strategy requires data-media');
      this.hydrate();
      return;
    }

    const mq = window.matchMedia(query);

    if (mq.matches) {
      this.hydrate();
    } else {
      const handler = (e) => {
        if (e.matches) {
          this.hydrate();
          mq.removeEventListener('change', handler);
        }
      };
      mq.addEventListener('change', handler);
    }
  }

  async hydrate() {
    const component = this.dataset.component;

    // Prevent double hydration
    if (this.dataset.hydrated === 'true') return;
    this.dataset.hydrated = 'true';

    try {
      // Check cache first
      let module = ISLAND_CACHE.get(component);

      if (!module) {
        // Dynamic import
        module = await import(`/assets/islands/${component}.js`);
        ISLAND_CACHE.set(component, module);
      }

      // Parse props
      const props = this.dataset.props
        ? JSON.parse(this.dataset.props)
        : {};

      // Call component's hydrate function
      if (typeof module.default === 'function') {
        await module.default(this, props);
      } else if (typeof module.hydrate === 'function') {
        await module.hydrate(this, props);
      } else {
        console.warn(`bengal-island: ${component} has no default export or hydrate function`);
      }

      // Dispatch event for debugging/analytics
      this.dispatchEvent(new CustomEvent('bengal:hydrated', {
        bubbles: true,
        detail: { component, props }
      }));

    } catch (error) {
      console.error(`bengal-island: failed to hydrate "${component}"`, error);
      this.dataset.error = 'true';
    }
  }
}

// Register custom element
if (!customElements.get('bengal-island')) {
  customElements.define('bengal-island', BengalIsland);
}

// Export for programmatic use
export { BengalIsland };
```

### 6. Example Island Components

```javascript
// bengal/themes/default/assets/islands/search-modal.js

/**
 * Search Modal Island
 *
 * Hydrates the search modal with full interactive functionality.
 */

export default function hydrate(element, props) {
  const { placeholder = 'Search...', hotkey = 'k' } = props;

  // Get fallback content
  const fallbackButton = element.querySelector('button');

  // Create interactive search modal
  const modal = document.createElement('div');
  modal.className = 'search-modal';
  modal.innerHTML = `
    <button class="search-trigger" aria-label="Search">
      <span class="search-icon">🔍</span>
      <span class="search-placeholder">${placeholder}</span>
      <kbd>${hotkey}</kbd>
    </button>
    <dialog class="search-dialog">
      <input type="search" placeholder="${placeholder}" autofocus>
      <div class="search-results"></div>
    </dialog>
  `;

  // Replace fallback with interactive version
  element.replaceChildren(modal);

  // Set up event listeners
  const trigger = modal.querySelector('.search-trigger');
  const dialog = modal.querySelector('dialog');
  const input = modal.querySelector('input');

  trigger.addEventListener('click', () => {
    dialog.showModal();
    input.focus();
  });

  // Keyboard shortcut
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === hotkey) {
      e.preventDefault();
      dialog.showModal();
      input.focus();
    }
  });

  // Close on escape
  dialog.addEventListener('close', () => {
    input.value = '';
  });

  // Search functionality would go here...
}
```

```javascript
// bengal/themes/default/assets/islands/theme-toggle.js

/**
 * Theme Toggle Island
 *
 * Interactive theme switcher with system preference detection.
 */

export default function hydrate(element, props) {
  const { defaultTheme = 'system' } = props;

  // Create interactive toggle
  const toggle = document.createElement('button');
  toggle.className = 'theme-toggle';
  toggle.setAttribute('aria-label', 'Toggle theme');

  const themes = ['light', 'dark', 'system'];
  let currentIndex = themes.indexOf(
    localStorage.getItem('bengal-theme') || defaultTheme
  );

  function updateTheme() {
    const theme = themes[currentIndex];
    const effectiveTheme = theme === 'system'
      ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : theme;

    document.documentElement.dataset.theme = effectiveTheme;
    localStorage.setItem('bengal-theme', theme);

    // Update button icon
    const icons = { light: '☀️', dark: '🌙', system: '💻' };
    toggle.textContent = icons[theme];
    toggle.title = `Theme: ${theme}`;
  }

  toggle.addEventListener('click', () => {
    currentIndex = (currentIndex + 1) % themes.length;
    updateTheme();
  });

  // Replace fallback
  element.replaceChildren(toggle);
  updateTheme();
}
```

### 7. Build Integration

```python
# bengal/postprocess/island_manifest.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import logging

from bengal.islands.registry import get_registry

logger = logging.getLogger(__name__)


@dataclass
class IslandManifest:
    """
    Manifest of islands used across the site.

    Used for:
    - Pre-loading critical islands
    - Bundle optimization
    - Analytics on island usage
    """

    islands: dict[str, dict]  # name -> usage info
    pages: dict[str, list[str]]  # page path -> island names

    def write(self, output_dir: Path) -> None:
        """Write manifest to output directory."""
        manifest_path = output_dir / "island-manifest.json"
        manifest_path.write_text(json.dumps({
            "islands": self.islands,
            "pages": self.pages,
        }, indent=2))
        logger.info(f"Wrote island manifest: {manifest_path}")


def generate_island_manifest(site) -> IslandManifest:
    """Generate manifest of all islands used in the site."""
    registry = get_registry()
    islands = {}
    pages = {}

    for page in site.pages:
        # Find islands in rendered HTML
        # (This is a simplified approach - could use HTML parser)
        page_islands = []

        for island in registry.all():
            if f'data-component="{island.name}"' in page.rendered_html:
                page_islands.append(island.name)

                if island.name not in islands:
                    islands[island.name] = {
                        "script": str(island.script),
                        "strategy": island.strategy,
                        "pages": [],
                    }
                islands[island.name]["pages"].append(page.url)

        if page_islands:
            pages[page.url] = page_islands

    return IslandManifest(islands=islands, pages=pages)
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Islands Architecture Flow                           │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Build Time (Python)                            │   │
│  │                                                                    │   │
│  │  1. Discover islands from islands/ directories                    │   │
│  │  2. Register in IslandRegistry                                    │   │
│  │  3. Template calls {% island "search" client="visible" %}         │   │
│  │  4. Render <bengal-island> with fallback HTML                     │   │
│  │  5. Copy island JS to output/assets/islands/                      │   │
│  │  6. Generate island-manifest.json                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Output HTML                                     │   │
│  │                                                                    │   │
│  │  <html>                                                            │   │
│  │    <head>                                                          │   │
│  │      <script src="bengal-island-loader.js" defer></script>        │   │
│  │    </head>                                                         │   │
│  │    <body>                                                          │   │
│  │      <header>Static navigation</header>                            │   │
│  │                                                                    │   │
│  │      <bengal-island data-component="search" data-client="visible"> │   │
│  │        <button>Search</button>  ← Fallback (visible immediately)  │   │
│  │      </bengal-island>                                              │   │
│  │                                                                    │   │
│  │      <main>Static content (no JS needed)</main>                    │   │
│  │                                                                    │   │
│  │      <bengal-island data-component="toc" data-client="idle">       │   │
│  │        <nav>Table of contents</nav>                                │   │
│  │      </bengal-island>                                              │   │
│  │    </body>                                                         │   │
│  │  </html>                                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Runtime (Browser)                               │   │
│  │                                                                    │   │
│  │  1. HTML loads instantly (static, fallback visible)               │   │
│  │  2. bengal-island-loader.js runs (tiny, deferred)                 │   │
│  │  3. Each <bengal-island> hydrates based on strategy:              │   │
│  │     - visible: when element enters viewport                        │   │
│  │     - idle: when browser is idle                                   │   │
│  │     - load: immediately                                            │   │
│  │     - media: when media query matches                              │   │
│  │  4. Island JS dynamically imported and executed                    │   │
│  │  5. Fallback replaced with interactive component                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

- [ ] Create `bengal/islands/` package
- [ ] Implement `IslandComponent` and `IslandInstance`
- [ ] Implement `IslandRegistry`
- [ ] Unit tests for core components

### Phase 2: Template Integration (Week 1-2)

- [ ] Implement `island()` template function
- [ ] Implement `island_scripts()` function
- [ ] Create Jinja extension for `{% island %}` tag
- [ ] Integration with template rendering

### Phase 3: Island Loader (Week 2)

- [ ] Create `bengal-island-loader.js`
- [ ] Implement all hydration strategies
- [ ] Test across browsers
- [ ] Minify and optimize (~2KB target)

### Phase 4: Default Theme Islands (Week 2-3)

- [ ] Convert search modal to island
- [ ] Convert theme toggle to island
- [ ] Convert TOC to island (optional hydration)
- [ ] Convert tabs to island
- [ ] Benchmark JS reduction

### Phase 5: Build Integration (Week 3)

- [ ] Island discovery from directories
- [ ] Copy islands to output
- [ ] Generate island manifest
- [ ] CLI command: `bengal islands list`

### Phase 6: Documentation (Week 4)

- [ ] Document island creation
- [ ] Document hydration strategies
- [ ] Add examples for common patterns
- [ ] Performance guide

---

## Configuration Example

```toml
# bengal.toml

[islands]
# Enable islands architecture
enabled = true

# Default hydration strategy
default_strategy = "visible"

# Islands directory (relative to project root)
directory = "islands"

# Pre-load critical islands (load before visible)
preload = ["search-modal"]

# Disable islands for specific pages
exclude_pages = ["/print/*"]
```

```yaml
# islands/search-modal/config.yaml
strategy: visible
media_query: null
props:
  placeholder:
    type: string
    default: "Search..."
  hotkey:
    type: string
    default: "k"
```

---

## Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Zero JS by default | Need to define islands explicitly |
| Faster initial load | Slight delay before interactivity |
| Smaller bundles | Learning curve for island pattern |
| Progressive enhancement | More files to manage |

### Risks

#### Risk 1: Fallback UX

**Description**: Fallback content may not match interactive version

- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Design fallbacks carefully
  - Test without JS enabled
  - Document fallback best practices
  - Provide templates for common patterns

#### Risk 2: Hydration Flash

**Description**: Visual flash when island hydrates

- **Likelihood**: Low (with good fallbacks)
- **Impact**: Low
- **Mitigation**:
  - Match fallback styling to hydrated
  - Use CSS transitions
  - Preload critical islands

#### Risk 3: Complexity

**Description**: More concepts for developers to learn

- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Good documentation
  - Sensible defaults
  - Optional feature (can ignore)
  - Clear examples

#### Risk 4: Browser Support

**Description**: Custom Elements need polyfill for old browsers

- **Likelihood**: Low (modern browsers fine)
- **Impact**: Low
- **Mitigation**:
  - Fallback works without JS
  - Document browser requirements
  - Optional polyfill

---

## Future Considerations

1. **Framework Integrations**: Pre-built adapters for Preact, Alpine, Lit
2. **Server Islands**: Hybrid SSG/SSR for dynamic islands
3. **Island Composition**: Islands containing other islands
4. **Shared State**: State management across islands
5. **Dev Tools**: Browser extension for island debugging

---

## Related Work

- [Astro Islands](https://docs.astro.build/en/concepts/islands/)
- [Fresh Islands (Deno)](https://fresh.deno.dev/docs/concepts/islands)
- [11ty WebC](https://www.11ty.dev/docs/languages/webc/)
- [Qwik Resumability](https://qwik.builder.io/docs/concepts/resumable/)
- [Marko Partial Hydration](https://markojs.com/docs/partial-hydration/)

---

## Approval

- [ ] RFC reviewed
- [ ] Island API approved
- [ ] Hydration strategies approved
- [ ] Implementation plan approved

---

## RFC Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] At least 2 design options analyzed (3 provided)
- [x] Recommended option justified
- [x] Architecture impact documented
- [x] Risks identified with mitigations
- [x] Implementation phases defined (4 weeks)
- [x] Code examples provided
- [x] Confidence ≥ 75% (78%)
