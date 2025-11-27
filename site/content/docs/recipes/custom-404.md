---
title: Custom 404 Page
description: Create a branded error page for your Bengal site
weight: 40
type: doc
tags: [recipe, 404, error-page]
---

# Custom 404 Page

Create a branded 404 error page in 5 minutes.

## Goal

After this recipe, visitors who hit a missing page will see:

- Your site's branding and navigation
- A helpful error message
- Links to get back on track

## Prerequisites

- A working Bengal site

## Steps

### 1. Create the 404 Page

Create `content/404.md`:

```markdown
---
title: Page Not Found
description: The page you're looking for doesn't exist
type: page
layout: 404
url: /404.html
outputs: [html]
---

# Page Not Found

Sorry, the page you're looking for doesn't exist or has been moved.

## What happened?

- The page may have been deleted or renamed
- The URL might be mistyped
- The link you followed may be outdated

## Try these instead

- [Go to homepage](/)
- [Browse all articles](/blog/)
- [Search the site](/search/)
```

:::{note}
The `url: /404.html` ensures the page is output as `/404.html` at the root, which most hosting platforms expect.
:::

### 2. Create a 404 Template (Optional)

For a custom layout, create `templates/page/404.html`:

```jinja2
{% extends "base.html" %}

{% block content %}
<div class="error-page">
  <div class="error-code">404</div>
  <h1>{{ page.title }}</h1>
  
  <p class="error-message">
    The page <code>{{ request.path | default('/unknown') }}</code> doesn't exist.
  </p>
  
  {{ page.content }}
  
  <div class="error-actions">
    <a href="/" class="button primary">Go Home</a>
    <a href="/search/" class="button secondary">Search</a>
  </div>
</div>

<style>
.error-page {
  text-align: center;
  padding: 4rem 1rem;
  max-width: 600px;
  margin: 0 auto;
}

.error-code {
  font-size: 8rem;
  font-weight: bold;
  color: var(--color-muted, #9ca3af);
  line-height: 1;
  margin-bottom: 1rem;
}

.error-message {
  color: var(--color-muted, #6b7280);
  margin-bottom: 2rem;
}

.error-message code {
  background: var(--color-code-bg, #f3f4f6);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.error-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.button {
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 500;
}

.button.primary {
  background: var(--color-primary, #3b82f6);
  color: white;
}

.button.secondary {
  background: var(--color-muted-bg, #f3f4f6);
  color: var(--color-text, #1f2937);
}
</style>
{% endblock %}
```

### 3. Configure Your Host

Most static hosts automatically serve `/404.html` for missing pages. Here's how to verify:

::::{tab-set}

:::{tab-item} Netlify
Netlify automatically uses `/404.html`. No configuration needed.
:::

:::{tab-item} Vercel
Vercel automatically uses `/404.html`. No configuration needed.
:::

:::{tab-item} GitHub Pages
GitHub Pages automatically uses `/404.html`. No configuration needed.
:::

:::{tab-item} Cloudflare Pages
Cloudflare Pages automatically uses `/404.html`. No configuration needed.
:::

:::{tab-item} Nginx
Add to your Nginx config:

```nginx
error_page 404 /404.html;
location = /404.html {
    internal;
}
```
:::

:::{tab-item} Apache
Create a `.htaccess` file in your output directory:

```apache
ErrorDocument 404 /404.html
```
:::

::::

## Done

Build your site and visit a non-existent URL like `/this-page-does-not-exist/`. You should see your custom 404 page.

## Enhancements

### Add Recent Posts

Show recent content to keep visitors engaged:

```jinja2
<h2>Recent Posts</h2>
<ul>
  {% for post in site.pages | selectattr('section', 'equalto', 'blog') | sort(attribute='date', reverse=true) | batch(5) | first %}
    <li><a href="{{ post.url }}">{{ post.title }}</a></li>
  {% endfor %}
</ul>
```

### Add Search

Include your search partial:

```jinja2
<h2>Search for what you need</h2>
{% include "partials/search.html" %}
```

### Track 404 Errors

If using analytics, you can track 404 hits:

```html
<script>
  // For Plausible
  plausible('404', { props: { path: document.location.pathname } });
  
  // For Google Analytics
  gtag('event', '404_error', { page_path: document.location.pathname });
</script>
```

## See Also

- [Deployment Guide](/docs/guides/deployment/)
- [Add Search Recipe](/docs/recipes/search/)
- [Template Reference](/docs/reference/template-functions/)

