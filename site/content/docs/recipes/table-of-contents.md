---
title: Add Table of Contents
description: Generate a table of contents from page headings
weight: 40
draft: false
lang: en
tags: [recipe, toc, navigation]
keywords: [table of contents, toc, navigation, headings]
category: recipe
---

# Add Table of Contents

Generate a table of contents automatically from page headings.

## Time Required

⏱️ 5-10 minutes

## What You'll Build

- Auto-generated TOC from H2/H3 headings
- Smooth scroll to sections
- Optional sticky sidebar

## Step 1: Enable TOC

Bengal automatically generates TOC data. Access it in templates:

```html
<!-- templates/partials/toc.html -->
{% if page.toc %}
<nav class="toc" aria-label="Table of Contents">
  <h2>On this page</h2>
  {{ page.toc | safe }}
</nav>
{% endif %}
```

## Step 2: Include in Layout

Add to your article template:

```html
<!-- templates/article.html -->
{% extends "base.html" %}

{% block content %}
<div class="article-layout">
  <aside class="sidebar">
    {% include "partials/toc.html" %}
  </aside>
  
  <article>
    <h1>{{ page.title }}</h1>
    {{ page.rendered_html | safe }}
  </article>
</div>
{% endblock %}
```

## Step 3: Style the TOC

```css
/* static/css/toc.css */
.toc {
  position: sticky;
  top: 2rem;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
  padding: 1rem;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.toc h2 {
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.toc ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc li {
  margin: 0.5rem 0;
}

.toc a {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
}

.toc a:hover,
.toc a.active {
  color: var(--color-link);
}

/* Nested items */
.toc ul ul {
  padding-left: 1rem;
}
```

## Step 4: Add Scroll Highlighting (Optional)

Highlight the current section as user scrolls:

```javascript
// static/js/toc-highlight.js
document.addEventListener('DOMContentLoaded', () => {
  const toc = document.querySelector('.toc');
  if (!toc) return;
  
  const headings = document.querySelectorAll('h2[id], h3[id]');
  const links = toc.querySelectorAll('a');
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        links.forEach(link => link.classList.remove('active'));
        const activeLink = toc.querySelector(`a[href="#${entry.target.id}"]`);
        if (activeLink) activeLink.classList.add('active');
      }
    });
  }, { rootMargin: '-20% 0px -80% 0px' });
  
  headings.forEach(heading => observer.observe(heading));
});
```

## Control TOC Generation

### Per-Page Control

Disable TOC for specific pages:

```yaml
---
title: Simple Page
toc: false
---
```

### Heading Levels

Configure which heading levels to include in `bengal.toml`:

```toml
[markup.toc]
start_level = 2  # Start at H2
end_level = 3    # Stop at H3
```

## Result

Your articles now have:
- ✅ Auto-generated table of contents
- ✅ Sticky sidebar navigation
- ✅ Scroll-aware highlighting

## See Also

- [Content Authoring](/docs/content/authoring/) — Writing with headings
- [Theming](/docs/theming/) — Layout customization

