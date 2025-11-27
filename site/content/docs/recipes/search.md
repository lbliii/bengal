---
title: Add Search
description: Add client-side search to your Bengal site with Pagefind
weight: 10
type: doc
tags: [recipe, search, pagefind]
---

# Add Search

Add fast, client-side search to your site in 5 minutes using [Pagefind](https://pagefind.app).

## Goal

After this recipe, your site will have:

- Full-text search across all pages
- Instant results as you type
- Zero server-side dependencies
- Works on any static host

## Prerequisites

- A working Bengal site
- Node.js installed (for Pagefind CLI)

## Steps

### 1. Install Pagefind

```bash
npm install -g pagefind
# or with Homebrew
brew install pagefind
```

### 2. Update Your Build Script

Run Pagefind after Bengal builds your site:

```bash
# Build site, then index it
bengal site build
pagefind --site public --output-subdir pagefind
```

For convenience, add to a `build.sh` script:

```bash
#!/bin/bash
set -e
bengal site build "$@"
pagefind --site public --output-subdir pagefind
```

### 3. Create Search Partial

Create `templates/partials/search.html`:

```html
<div id="search" class="search-container"></div>

<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<script src="/pagefind/pagefind-ui.js"></script>
<script>
  window.addEventListener('DOMContentLoaded', () => {
    new PagefindUI({
      element: "#search",
      showSubResults: true,
      showImages: false
    });
  });
</script>

<style>
  .search-container {
    max-width: 600px;
    margin: 0 auto;
  }
  /* Customize Pagefind styles to match your theme */
  :root {
    --pagefind-ui-scale: 1;
    --pagefind-ui-primary: var(--color-primary, #3b82f6);
    --pagefind-ui-text: var(--color-text, #1f2937);
    --pagefind-ui-background: var(--color-background, #ffffff);
    --pagefind-ui-border: var(--color-border, #e5e7eb);
    --pagefind-ui-border-width: 1px;
    --pagefind-ui-border-radius: 8px;
  }
</style>
```

### 4. Add Search to Your Layout

Include the partial where you want search to appear:

```jinja2
{# In your header or navigation #}
{% include "partials/search.html" %}
```

Or create a dedicated search page at `content/search.md`:

```markdown
---
title: Search
description: Search all content on this site
type: page
layout: search
---

Use the search box below to find content.
```

With a `templates/page/search.html` template:

```jinja2
{% extends "base.html" %}

{% block content %}
<div class="search-page">
  <h1>{{ page.title }}</h1>
  {% include "partials/search.html" %}
</div>
{% endblock %}
```

### 5. Configure What Gets Indexed

By default, Pagefind indexes all HTML. To exclude elements:

```html
<!-- Exclude from search -->
<nav data-pagefind-ignore>...</nav>
<footer data-pagefind-ignore>...</footer>

<!-- Force include (even if parent excluded) -->
<div data-pagefind-body>
  Main content here
</div>
```

## Done

Build your site and visit `/search/`. You should see:

- A search input box
- Instant results as you type
- Highlighted matches in results

## CI/CD Integration

For automated builds, add Pagefind to your workflow:

### GitHub Actions

```yaml
- name: Build site
  run: |
    bengal site build
    npx pagefind --site public --output-subdir pagefind
```

### Netlify

```toml
[build]
  command = "bengal site build && npx pagefind --site public --output-subdir pagefind"
```

## Troubleshooting

**"No results found" for existing content**

Pagefind may not have indexed your content. Check that:
- You ran `pagefind --site public` after `bengal site build`
- The `public/pagefind/` directory exists
- Your content isn't excluded via `data-pagefind-ignore`

**Search box doesn't appear**

Verify the Pagefind assets are being served:
- Check that `/pagefind/pagefind-ui.js` returns a file
- Ensure the partial is included in your template

## See Also

- [Pagefind Documentation](https://pagefind.app/docs/)
- [Pagefind UI Options](https://pagefind.app/docs/ui/)
- [Search Configuration](/docs/reference/architecture/tooling/config/#search)

