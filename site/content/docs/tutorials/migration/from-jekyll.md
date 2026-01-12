---
title: From Jekyll
nav_title: Jekyll
description: Onboarding guide for Jekyll users migrating to Bengal
weight: 25
tags:
- tutorial
- migration
- jekyll
- github-pages
keywords:
- jekyll
- github pages
- ruby
- liquid
- migration
---

# Bengal for Jekyll Users

Moving from Ruby to Python? Bengal simplifies your stack while keeping the content-first approach you know.

## Quick Wins (5 Minutes)

### What Works The Same

| Jekyll | Bengal | Status |
|--------|--------|--------|
| Markdown files | Markdown files | ✅ Identical |
| YAML frontmatter | YAML frontmatter | ✅ Identical |
| `_posts/` for blog | `content/blog/` | ✅ Similar |
| `_data/` | `data/` | ✅ Similar |
| Collections | Built-in | ✅ Similar |
| Static site output | Static site output | ✅ Same |

### The Key Difference

Liquid templates → Bengal directives:

````markdown
<!-- Jekyll (Liquid) -->
{% highlight python %}
print("Hello")
{% endhighlight %}

<!-- Bengal -->
```python
print("Hello")
```
````

No more `{% %}` tags in your content.

---

## Liquid → Markdown Translation

### Code Blocks

:::{tab-set}

:::{tab} Jekyll (Liquid)
````markdown
{% highlight python linenos %}
def hello():
    print("Hello!")
{% endhighlight %}
````
:::{/tab}

:::{tab} Bengal
````markdown
```python
def hello():
    print("Hello!")
```
````
:::{/tab}

:::{/tab-set}

### Including Files

:::{tab-set}

:::{tab} Jekyll
```markdown
{% include note.html content="This is a note." %}

{% include_relative ../snippets/example.md %}
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{note}
This is a note.
:::

:::{include} ../snippets/example.md
:::
```
:::{/tab}

:::{/tab-set}

### Callouts / Alerts

Jekyll doesn't have built-in callouts (you use includes or custom CSS). Bengal has them built-in:

```markdown
:::{note}
This is a note.
:::

:::{warning}
Be careful!
:::

:::{tip}
Pro tip here.
:::

:::{danger}
Critical warning!
:::
```

### Links and References

:::{tab-set}

:::{tab} Jekyll
```markdown
<!-- Post URL -->
[Read more]({{ site.baseurl }}{% post_url 2024-01-15-my-post %})

<!-- Page link -->
[About]({{ "/about/" | relative_url }})

<!-- Asset -->
![Logo]({{ "/assets/logo.png" | relative_url }})
```
:::{/tab}

:::{tab} Bengal
```markdown
<!-- Post URL -->
[Read more](/blog/2024-01-15-my-post/)

<!-- Page link -->
[About](/about/)

<!-- Asset -->
![Logo](/images/logo.png)
```
:::{/tab}

:::{/tab-set}

:::{tip}
Bengal handles URLs automatically. No filters needed.
:::

---

## Frontmatter Mapping

### Post/Page Frontmatter

:::{tab-set}

:::{tab} Jekyll
```yaml
---
layout: post
title: "My Blog Post"
date: 2024-01-15 10:30:00 -0500
categories: [python, tutorial]
tags: [beginner, tips]
author: jane
excerpt: "A brief introduction..."
published: true
---
```
:::{/tab}

:::{tab} Bengal
```yaml
---
title: "My Blog Post"
date: 2024-01-15
category: python
tags: [tutorial, beginner, tips]
author: jane
description: "A brief introduction..."
draft: false
---
```
:::{/tab}

:::{/tab-set}

### Key Differences

| Jekyll | Bengal | Notes |
|--------|--------|-------|
| `layout: post` | Auto-detected | Based on directory |
| `date: 2024-01-15 10:30:00 -0500` | `date: 2024-01-15` | Simpler format |
| `categories: [a, b]` | `category: a` | Single category |
| `excerpt:` | `description:` | Different name |
| `published: false` | `draft: true` | Inverted logic |
| `permalink:` | Auto-generated | From file path |

---

## Configuration Mapping

### Basic Site Config

:::{tab-set}

:::{tab} Jekyll (_config.yml)
```yaml
title: My Site
description: A great site
baseurl: ""
url: "https://example.com"

# Build settings
markdown: kramdown
theme: minima
plugins:
  - jekyll-feed
  - jekyll-seo-tag
  - jekyll-sitemap

# Collections
collections:
  docs:
    output: true
    permalink: /docs/:path/
```
:::{/tab}

:::{tab} Bengal (bengal.toml)
```toml
[site]
title = "My Site"
description = "A great site"
baseurl = "https://example.com"
theme = "bengal"

# Feed, SEO, sitemap are built-in
# No plugins needed

# Collections auto-detected from content/
```
:::{/tab}

:::{/tab-set}

### No Plugin Configuration

Jekyll features that require plugins are built into Bengal:

| Jekyll Plugin | Bengal |
|---------------|--------|
| `jekyll-feed` | Built-in RSS/Atom |
| `jekyll-seo-tag` | Built-in meta tags |
| `jekyll-sitemap` | Built-in sitemap |
| `jekyll-toc` | Built-in TOC |
| `jekyll-redirect-from` | Redirect in frontmatter |
| `jekyll-paginate` | Built-in pagination |
| `jekyll-archives` | Built-in archives |

---

## Directory Structure Comparison

| Jekyll | Bengal | Notes |
|--------|--------|-------|
| `_posts/` | `content/blog/` | Blog posts |
| `_drafts/` | Use `draft: true` | Frontmatter flag |
| `_pages/` | `content/` | Regular pages |
| `_data/` | `data/` | YAML/JSON data |
| `_includes/` | `themes/[name]/templates/partials/` | Reusable snippets |
| `_layouts/` | `themes/[name]/templates/` | Page templates |
| `_sass/` | `themes/[name]/assets/css/` | Stylesheets |
| `assets/` | `assets/` | ✅ Same |
| `_config.yml` | `bengal.toml` | Configuration |
| `Gemfile` | `pyproject.toml` | Dependencies |

---

## Template Variable Mapping

### Page Variables

| Jekyll (Liquid) | Bengal (Jinja2) | Notes |
|-----------------|-----------------|-------|
| `{{ page.title }}` | `{{ page.title }}` | ✅ Same |
| `{{ page.date }}` | `{{ page.date }}` | ✅ Same |
| `{{ page.content }}` | `{{ content }}` | Use `{{ content }}` for rendered HTML (preferred). `{{ page.content }}` also works. |
| `{{ page.excerpt }}` | `{{ page.excerpt }}` | ✅ Same |
| `{{ page.url }}` | `{{ page.url }}` | ✅ Same |
| `{{ page.categories }}` | `{{ page.category }}` | Single |
| `{{ page.tags }}` | `{{ page.tags }}` | ✅ Same |
| `{{ page.custom_var }}` | `{{ page.metadata.custom_var }}` | Nested |

### Site Variables

| Jekyll (Liquid) | Bengal (Jinja2) | Notes |
|-----------------|-----------------|-------|
| `{{ site.title }}` | `{{ site.title }}` | ✅ Same (preferred). `{{ site.config.title }}` also works. |
| `{{ site.description }}` | `{{ site.description }}` | ✅ Same (preferred). `{{ site.config.description }}` also works. |
| `{{ site.url }}` | `{{ site.baseurl }}` | Different name (use `baseurl` instead of `url`) |
| `{{ site.posts }}` | `{{ site.pages \| selectattr('type', 'eq', 'post') }}` | Filter |
| `{{ site.data.file }}` | `{{ site.data.file }}` | ✅ Same |
| `{{ site.pages }}` | `{{ site.pages }}` | ✅ Same |

### Template Logic

| Jekyll (Liquid) | Bengal (Jinja2) |
|-----------------|-----------------|
| `{% if page.title %}` | `{% if page.title %}` |
| `{% for post in site.posts %}` | `{% for post in posts %}` |
| `{% include header.html %}` | `{% include "partials/header.html" %}` |
| `{{ "text" \| upcase }}` | `{{ "text" \| upper }}` |
| `{{ page.date \| date: "%B %d, %Y" }}` | `{{ page.date \| dateformat("%B %d, %Y") }}` |
| `{% assign x = "value" %}` | `{% set x = "value" %}` |

---

## What Bengal Adds (Jekyll Doesn't Have)

:::::{tab-set}

::::{tab} Admonitions
```markdown
:::{note}
Built-in callout boxes.
:::

:::{warning}
No plugins or includes needed.
:::

:::{tip}
Multiple types available.
:::
```
::::{/tab}

::::{tab} Tabs
````markdown
:::{tab-set}
:::{tab} Ruby
```ruby
puts "Hello"
```
:::{/tab}
:::{tab} Python
```python
print("Hello")
```
:::{/tab}
:::{/tab-set}
````
::::{/tab}

::::{tab} Cards
```markdown
:::{cards}
:columns: 2

:::{card} Feature 1
:icon: rocket

Description here
:::{/card}

:::{card} Feature 2
:icon: star

Another feature
:::{/card}

:::{/cards}
```
::::{/tab}

::::{tab} Steps
````markdown
:::{steps}

:::{step} Clone Repository
```bash
git clone https://github.com/user/repo.git
```
:::{/step}

:::{step} Install Dependencies
```bash
pip install -r requirements.txt
```
:::{/step}

:::{/steps}
````
::::{/tab}

::::{tab} Live Reload
```bash
bengal serve
# Hot reload at http://localhost:5173
# Instant updates on save
```

Faster than `jekyll serve --livereload`.
::::{/tab}

:::::{/tab-set}

---

## What's Different (Honest Gaps)

| Jekyll Feature | Bengal Status | Workaround |
|----------------|---------------|------------|
| Liquid templates | [[ext:kida:|Kida]] templates | Similar syntax |
| Ruby plugins | Python/built-in | Most features built-in |
| GitHub Pages native | Manual deploy | Use GitHub Actions |
| `permalink:` control | Auto from path | Restructure content |
| Sass processing | External build | Use CSS or preprocessor |
| Multiple categories | Single category | Use tags for additional |

### GitHub Pages Deployment

Jekyll has native GitHub Pages support. With Bengal, use GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'  # Or '3.14t' for free-threading build
      - run: pip install bengal
      - run: bengal build
      # Pin to SHA for supply chain security (v3.9.3)
      - uses: peaceiris/actions-gh-pages@373f7f263a76c20808c831209c920827a82a2847
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```

---

## Migration Steps

:::{steps}
:::{step} Install Bengal
```bash
pip install bengal
# or with uv
uv add bengal
```
:::{/step}

:::{step} Create New Site
```bash
bengal new site mysite
cd mysite
```
:::{/step}

:::{step} Migrate Posts
```bash
# Create blog directory
mkdir -p content/blog

# Copy posts (remove date prefix from filename)
for f in /path/to/jekyll/_posts/*.md; do
  # 2024-01-15-my-post.md -> my-post.md
  newname=$(basename "$f" | sed 's/^[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-//')
  cp "$f" "content/blog/$newname"
done
```

Or keep date in filename—Bengal handles both.
:::{/step}

:::{step} Migrate Pages
```bash
# Copy regular pages
cp /path/to/jekyll/*.md content/
cp -r /path/to/jekyll/_pages/* content/
```
:::{/step}

:::{step} Update Frontmatter
Convert Jekyll frontmatter:

| Change | From | To |
|--------|------|-----|
| Layout | `layout: post` | Remove (auto-detected) |
| Categories | `categories: [a, b]` | `category: a` |
| Excerpt | `excerpt:` | `description:` |
| Published | `published: false` | `draft: true` |
:::{/step}

:::{step} Remove Liquid Tags
Search and replace Liquid syntax:

```bash
# Find Liquid tags
grep -r "{%" content/
grep -r "{{" content/
```

| Find | Replace With |
|------|--------------|
| `{% highlight lang %}...{% endhighlight %}` | ` ```lang...``` ` |
| `{% include note.html content="..." %}` | `:::{note}...:::` |
| `{{ site.baseurl }}` | Remove (auto-handled) |
| `{{ page.url \| relative_url }}` | Remove filter |
:::{/step}

:::{step} Migrate Data
```bash
cp -r /path/to/jekyll/_data/* data/
```
:::{/step}

:::{step} Migrate Assets
```bash
cp -r /path/to/jekyll/assets/* assets/
```
:::{/step}

:::{step} Create Config
Create `bengal.toml` from `_config.yml`:

```toml
[site]
title = "My Site"
baseurl = "https://example.com"
description = "My awesome site"
theme = "bengal"
```
:::{/step}

:::{step} Test
```bash
bengal build
bengal health linkcheck
bengal serve
```
:::{/step}
:::{/steps}

---

## Migration Checklist

:::{checklist} Before You Start
- [ ] Install Bengal: `pip install bengal`
- [ ] Backup your Jekyll site
- [ ] Create new Bengal site: `bengal new site mysite`
:::

:::{checklist} Content Migration
- [ ] Copy `_posts/` to `content/blog/`
- [ ] Copy pages to `content/`
- [ ] Update frontmatter format
- [ ] Remove Liquid template tags
- [ ] Convert `{% highlight %}` to fenced code blocks
- [ ] Convert includes to directives
:::

:::{checklist} Assets Migration
- [ ] Copy `assets/` to `assets/`
- [ ] Copy `_data/` to `data/`
- [ ] Update asset paths in content
:::

:::{checklist} Config Migration
- [ ] Create `bengal.toml` from `_config.yml`
- [ ] Remove plugin references (built-in)
- [ ] Remove Gemfile (no Ruby needed)
:::

:::{checklist} Deployment
- [ ] Set up GitHub Actions for deployment
- [ ] Update repository settings for GitHub Pages
- [ ] Test deployment workflow
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | Jekyll | Bengal |
|------|--------|--------|
| New site | `jekyll new` | `bengal new site` |
| Build | `jekyll build` | `bengal build` |
| Serve | `jekyll serve` | `bengal serve` |
| Posts | `_posts/YYYY-MM-DD-title.md` | `content/blog/title.md` |
| Drafts | `_drafts/` | `draft: true` frontmatter |
| Data | `_data/file.yml` | `data/file.yaml` |
| Code block | `{% highlight %}` | ` ```lang ` |
| Include | `{% include %}` | `:::{include}` |
| Config | `_config.yml` | `bengal.toml` |

---

## Common Questions

:::{dropdown} Can I keep my Jekyll theme?
:icon: question

No. Jekyll themes (Ruby/Liquid) are not compatible. Bengal has its own theme system using [[ext:kida:|Kida]] templates. The default Bengal theme is designed for technical documentation with modern features like dark mode and built-in search.
:::

:::{dropdown} What about my Ruby plugins?
:icon: question

Ruby plugins won't work. However, most common plugin functionality is built into Bengal: RSS feeds, sitemaps, SEO meta tags, pagination, archives, and more. Check if there's a built-in equivalent before looking for workarounds.
:::

:::{dropdown} Can I still deploy to GitHub Pages?
:icon: question

Yes, but not using the native Jekyll integration. Use GitHub Actions to build with Bengal and deploy the output. This gives you more control and faster builds anyway.
:::

:::{dropdown} What about my custom Liquid includes?
:icon: question

Convert them to Bengal directives or [[ext:kida:|Kida]] templates. Simple includes like callout boxes have built-in directive equivalents (`:::{note}`, `:::{warning}`). Complex includes can be recreated as [[ext:kida:docs/syntax/functions|Kida functions]] (`{% def %}`) or template partials.
:::

---

## Related Migration Guides

If you're migrating from multiple platforms or need additional context:

- [From Hugo](./from-hugo) - Similar template-to-directive conversion patterns
- [Migration Overview](../migration/) - Common migration patterns across all platforms

## Next Steps

- [Writer Quickstart](/docs/get-started/quickstart-writer/) - Full markdown reference
- [Directives Reference](/docs/reference/directives/) - All available directives
- [Configuration Reference](/docs/building/configuration/) - Full config options
- [Cheatsheet](/docs/reference/cheatsheet/) - Quick syntax reference
