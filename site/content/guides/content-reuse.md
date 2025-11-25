---
title: Content Reuse Strategies
description: Write once, publish everywhere using Data Files and Snippets.
type: guide
weight: 51
tags: [content-strategy, snippets, data-files]
---

# Content Reuse Strategies

Maintaining consistency across hundreds of pages is hard. If you copy-paste the same "Warning" or "Pricing Table" into 20 pages, updating it becomes a nightmare.

Bengal provides powerful tools to implement a "Write Once, Publish Everywhere" strategy.

## Strategy 1: Global Data Strings

For small text snippets (product names, version numbers, legal disclaimers), use **Data Files**.

1.  Create `site/data/globals.yaml`:
    ```yaml
    product_name: "Bengal v1.0"
    contact_email: "support@example.com"
    legal_warning: "This software is provided as-is without warranty."
    ```

2.  Use in Templates (Layouts):
    ```html
    <footer>
      {{ site.data.globals.legal_warning }}
    </footer>
    ```

    *Note: To use these inside Markdown content, you need a custom shortcode (see Strategy 3).*

## Strategy 2: Shared HTML Components (Partials)

For complex UI components (CTAs, Cards, Pricing Tables) that appear on multiple pages.

1.  Create `themes/default/templates/partials/cta_box.html`:
    ```html
    <div class="cta-box bg-light p-4 border rounded">
      <h3>Ready to start?</h3>
      <p>Get up and running in 5 minutes.</p>
      <a href="/getting-started/" class="btn btn-primary">Get Started</a>
    </div>
    ```

2.  Include in any Layout:
    ```jinja2
    {% include "partials/cta_box.html" %}
    ```

## Strategy 3: The "Include" Directive (Advanced)

To inject reusable content *inside* your Markdown articles, you can create a custom **Directive**.

### 1. Create the Directive Plugin

Create `rendering/plugins/directives/include.py`:

```python
from mistune.directives import DirectivePlugin
import os

class IncludeDirective(DirectivePlugin):
    def parse(self, block, m, state):
        # Syntax: ::include path/to/snippet.md::
        path = m.group(1).strip()
        return {"type": "include", "path": path}

    def __call__(self, directive, md):
        directive.register("include", self.parse)
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("include", render_include)

def render_include(renderer, path: str) -> str:
    # Security check: Ensure path is within site content
    full_path = os.path.join("site/content/snippets", path)
    try:
        with open(full_path, "r") as f:
            content = f.read()
        # Render the included markdown
        return renderer.mistune.parse(content)
    except FileNotFoundError:
        return f'<div class="alert alert-danger">Snippet not found: {path}</div>'
```

### 2. Register the Plugin

Register it in `bengal/rendering/template_engine.py` (or where plugins are loaded).

### 3. Usage

Create your snippets in `site/content/snippets/`:
- `site/content/snippets/warning.md`

Then use it in any article:

```markdown
# My Article

Here is some content.

::include warning.md::

More content.
```

## Summary

| Strategy | Best For | Complexity |
|----------|----------|------------|
| **Data Files** | Text strings (versions, names) | Low |
| **Partials** | HTML UI components (Layout level) | Low |
| **Directives** | Reusing content *inside* articles | High (requires coding) |

