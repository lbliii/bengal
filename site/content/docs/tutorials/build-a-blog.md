---
title: Build a Blog from Scratch
description: Create, configure, and customize a personal blog from scratch
weight: 10
draft: false
lang: en
tags: [tutorial, beginner, blog, setup]
keywords: [tutorial, blog, getting started, python, ssg, setup]
category: tutorial
aliases:
  - /docs/guides/blog-from-scratch/
---

# Build a Blog in 15 Minutes

In this tutorial, you will build a fully functional personal blog with Bengal. We will go from an empty folder to a running website with custom content, configuration, and theming.

:::{note}
**Who is this for?**
This guide is for developers who want to see the full end-to-end workflow of Bengal. No prior experience with Bengal is required, but basic familiarity with the terminal is assumed.
:::

## Goal

By the end of this tutorial, you will have:
1.  Initialized a new Bengal project
2.  Created blog posts with tags and categories
3.  Configured site metadata and navigation
4.  Customized the theme (without breaking updates)
5.  Built the site for production

## Prerequisites

*   **Python 3.10+** installed
*   **Bengal** installed (`pip install bengal`)

## Step 1: Initialize Your Project

First, let's create a new site. Open your terminal and run:

```bash
# Create a new directory for your blog
mkdir my-blog
cd my-blog

# Initialize a fresh Bengal site
bengal init
```

You will see a structure like this:

```text
my-blog/
├── bengal.toml       # Main configuration
├── site/
│   ├── content/      # Your markdown files
│   ├── static/       # Images, CSS, JS
│   └── templates/    # Theme overrides
└── themes/           # Installed themes
```

:::{tip}
**Why this structure?**
Bengal separates **configuration** (`bengal.toml`) from **data** (`site/`) to keep your project clean. The `site/` folder contains everything that makes your site unique.
:::

## Step 2: Create Your First Post

Bengal provides a CLI to generate content with the correct frontmatter.

```bash
# Create a new blog post
bengal new page content/blog/hello-world.md
```

Open `site/content/blog/hello-world.md` in your editor. You'll see the **Frontmatter** (metadata) at the top:

```yaml
---
title: Hello World
date: 2023-10-27
draft: true
---

Write your content here...
```

Update it to look like this:

```yaml
---
title: "My First Bengal Post"
date: 2023-10-27
draft: false
tags: ["python", "bengal"]
category: "tech"
---

# Hello, World!

This is my first post using **Bengal**, the Pythonic static site generator.

## Why Bengal?

*   It's fast ⚡️
*   It uses Jinja2 templates 🐍
*   It's easy to configure ⚙️
```

:::{warning}
**Don't forget `draft: false`!**
By default, new pages are drafts. They won't show up in production builds unless you set `draft: false`.
:::

## Step 3: Configure Your Site

Now, let's give your site an identity. Open `bengal.toml` and update the basics.

::::{tab-set}
:::{tab-item} bengal.toml
```toml
[site]
title = "My Awesome Blog"
description = "Thoughts on code and coffee."
baseurl = "https://example.com"
author = "Jane Doe"
language = "en"

# Define navigation menu
[[site.menu.main]]
name = "Home"
url = "/"
weight = 1

[[site.menu.main]]
name = "Blog"
url = "/blog/"
weight = 2

[[site.menu.main]]
name = "About"
url = "/docs/about/"
weight = 3
```
:::

:::{tab-item} Explanation
*   **`[site]`**: Global metadata used by themes (SEO tags, header titles).
*   **`[[site.menu.main]]`**: Defines the top navigation bar. Each item is an object in the `main` menu list.
*   **`weight`**: Controls the sort order (lower numbers appear first).
:::
::::

## Step 4: Preview Your Site

Let's see what we have so far. Start the development server:

```bash
bengal site serve
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

*   Navigate to "Blog" to see your "Hello World" post.
*   Notice the site title and menu matches your configuration.

:::{note}
**Live Reload**
Try editing `hello-world.md` while the server is running. Save the file, and the browser will automatically refresh with your changes!
:::

## Step 5: Customize the Theme

You want your blog to stand out. Instead of forking the entire theme, we'll use **Theme Inheritance** to override just the parts we want to change.

Let's change the header color and add a custom footer.

### 1. Create a Custom CSS File

Create `site/static/css/custom.css`:

```css
/* site/static/css/custom.css */
:root {
    --primary-color: #6c5ce7; /* Purple header */
    --font-family: 'Helvetica Neue', sans-serif;
}

.custom-footer {
    text-align: center;
    padding: 2rem;
    background: #f1f2f6;
    margin-top: 4rem;
}
```

### 2. Override the Base Template

Create `site/templates/base.html`. We will extend the default theme and inject our changes.

```html
<!-- site/templates/base.html -->
{% extends "default::base.html" %}

{# Inject our custom CSS into the head #}
{% block extra_head %}
<link rel="stylesheet" href="{{ asset_url('css/custom.css') }}">
{% endblock %}

{# Add a custom footer after the main content #}
{% block footer %}
<footer class="custom-footer">
    <p>
        &copy; {{ now.year }} {{ site.author }}.
        Built with <a href="https://bengal.dev">Bengal</a>.
    </p>
</footer>
{% endblock %}
```

Check your browser. The header color should change (if the theme uses the `--primary-color` variable), and your custom footer should appear.

:::{dropdown} How does this work?
Bengal looks for templates in your `site/templates/` folder first.
*   `{% extends "default::base.html" %}` tells Bengal to load the *original* theme template first.
*   `{% block %}` allows you to replace specific sections without copy-pasting the whole file.
:::

## Step 6: Build for Production

When you're ready to publish, build the static files.

```bash
bengal site build
```

This creates a `public/` directory containing your complete website: HTML, CSS, and optimized images.

### Review Build Output

```text
public/
├── index.html
├── blog/
│   ├── index.html
│   └── hello-world/
│       └── index.html
└── static/
    └── css/
        └── custom.a1b2c3d4.css  # Fingerprinted for caching
```

## Next Steps

Congratulations! You've built a custom blog. Here is where to go next:

*   **[Deployment Guide](/docs/building/deployment/)**: Learn how to host on GitHub Pages or Netlify.
*   **[Theme Customization](/docs/theming/themes/customize/)**: Deep dive into template overrides.
*   **[Configuration Reference](/docs/building/configuration/)**: Explore all available settings.


