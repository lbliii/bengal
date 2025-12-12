---
title: From Hugo
description: Onboarding guide for Hugo users migrating to Bengal
weight: 20
tags:
- tutorial
- migration
- hugo
- shortcodes
keywords:
- hugo
- shortcodes
- go templates
- migration
---

# Bengal for Hugo Users

Good news: Bengal's content model is almost identical to Hugo's. The main difference? Shortcodes become directives.

## Quick Wins (5 Minutes)

### What Works The Same

| Hugo | Bengal | Status |
|------|--------|--------|
| `content/` structure | `content/` | ✅ Identical |
| `_index.md` for sections | `_index.md` | ✅ Identical |
| YAML/TOML frontmatter | YAML frontmatter | ✅ Identical |
| `{{ .Params.x }}` | `{{ page.metadata.x }}` | ✅ Similar |
| `{{ .Site.Title }}` | `{{ site.config.title }}` | ✅ Similar |
| `config.toml` | `bengal.toml` | ✅ Similar |

### The Key Difference

Hugo shortcodes → Bengal directives:

```markdown
<!-- Hugo -->
{{</* notice warning */>}}
This is a warning
{{</* /notice */>}}

<!-- Bengal -->
:::{warning}
This is a warning
:::
```

---

## Shortcode → Directive Translation

### Callout Boxes

:::{tab-set}

:::{tab} Hugo
```markdown
{{</* notice note */>}}
This is a note with **bold** text.
{{</* /notice */>}}

{{</* notice warning */>}}
Be careful!
{{</* /notice */>}}

{{</* notice tip */>}}
Pro tip here.
{{</* /notice */>}}
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{note}
This is a note with **bold** text.
:::

:::{warning}
Be careful!
:::

:::{tip}
Pro tip here.
:::
```
:::{/tab}

:::{/tab-set}

### Tabs

:::{tab-set}

:::{tab} Hugo
````markdown
{{</* tabs */>}}
{{</* tab "Python" */>}}
```python
print("Hello")
```
{{</* /tab */>}}
{{</* tab "JavaScript" */>}}
```javascript
console.log("Hello");
```
{{</* /tab */>}}
{{</* /tabs */>}}
````
:::{/tab}

:::{tab} Bengal
````markdown
:::{tab-set}
:::{tab} Python
```python
print("Hello")
```
:::{/tab}
:::{tab} JavaScript
```javascript
console.log("Hello");
```
:::{/tab}
:::{/tab-set}
````

:::{/tab}

:::{/tab-set}

### Code Highlighting

:::{tab-set}

:::{tab} Hugo
```markdown
{{</* highlight python "linenos=table,hl_lines=2" */>}}
def hello():
    print("Hello!")  # highlighted
    return True
{{</* /highlight */>}}
```
:::{/tab}

:::{tab} Bengal
````markdown
```python
def hello():
    print("Hello!")  # use comments to draw attention
    return True
```
````
:::{/tab}

:::{/tab-set}

### Figure / Image

:::{tab-set}

:::{tab} Hugo
```markdown
{{</* figure src="/static/images/photo.jpg" title="My Photo" caption="A description" */>}}
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{figure} /images/photo.jpg
:alt: My Photo
:caption: A description
:align: center
:::
```
:::{/tab}

:::{/tab-set}

:::{tip}
Bengal's `{figure}` directive produces semantic HTML (`<figure>` + `<figcaption>`) with proper accessibility support. The `:alt:` option is required for images. Use `:alt:` with an empty value for decorative images.
:::

### YouTube Embed

:::{tab-set}

:::{tab} Hugo
```markdown
{{</* youtube dQw4w9WgXcQ */>}}
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{youtube} dQw4w9WgXcQ
:title: Video Title (required for accessibility)
:::
```
:::{/tab}

:::{/tab-set}

:::{tip}
Bengal's `{youtube}` directive uses **privacy-enhanced mode** by default (`youtube-nocookie.com`), which is better for GDPR compliance.
:::

### All Media Embed Directives

Bengal provides built-in directives for all common media embeds:

| Hugo Shortcode | Bengal Directive | Notes |
|----------------|------------------|-------|
| `{{</* youtube id */>}}` | `:::{youtube} id` | Privacy-enhanced by default |
| `{{</* youtube id autoplay="true" */>}}` | `:::{youtube} id`<br>`:autoplay: true` | Options as directive options |
| `{{</* vimeo id */>}}` | `:::{vimeo} id`<br>`:title: Title` | DNT mode by default |
| `{{</* gist user id */>}}` | `:::{gist} user/id` | Combined user/id format |
| `{{</* gist user id "file.py" */>}}` | `:::{gist} user/id`<br>`:file: file.py` | File as option |
| `{{</* figure src="..." */>}}` | `:::{figure} path`<br>`:alt: Alt text` | Semantic HTML output |
| `{{</* figure src="..." caption="..." */>}}` | `:::{figure} path`<br>`:caption: ...` | Caption as option |
| N/A | `:::{video} /path.mp4` | Self-hosted video |
| N/A | `:::{audio} /path.mp3` | Self-hosted audio |
| N/A | `:::{codepen} user/pen` | CodePen embeds |
| N/A | `:::{codesandbox} id` | CodeSandbox embeds |
| N/A | `:::{stackblitz} id` | StackBlitz embeds |
| N/A | `:::{asciinema} id` | Terminal recordings |

**All directives with iframes require `:title:` for accessibility.**

---

## Template Variable Mapping

### Page Variables

| Hugo | Bengal | Notes |
|------|--------|-------|
| `{{ .Title }}` | `{{ page.title }}` | Page title |
| `{{ .Content }}` | `{{ content }}` | Rendered content |
| `{{ .Date }}` | `{{ page.date }}` | Publication date |
| `{{ .Params.x }}` | `{{ page.metadata.x }}` | Custom frontmatter |
| `{{ .Summary }}` | `{{ page.excerpt }}` | Auto-generated |
| `{{ .WordCount }}` | `{{ page.word_count }}` | Word count |
| `{{ .ReadingTime }}` | `{{ page.reading_time }}` | Minutes to read |
| `{{ .Permalink }}` | `{{ page.url }}` | Full URL |
| `{{ .RelPermalink }}` | `{{ page.path }}` | Relative path |

### Site Variables

| Hugo | Bengal | Notes |
|------|--------|-------|
| `{{ .Site.Title }}` | `{{ site.config.title }}` | Site title |
| `{{ .Site.BaseURL }}` | `{{ site.config.baseurl }}` | Base URL |
| `{{ .Site.Params.x }}` | `{{ site.config.params.x }}` | Custom params |
| `{{ .Site.Pages }}` | `{{ site.pages }}` | All pages |
| `{{ .Site.Menus }}` | `{{ site.menus }}` | Menu data |

### Variable Substitution in Content

Bengal supports variable substitution directly in markdown (not just templates):

```markdown
---
title: Release Notes
version: "2.5.0"
release_date: "2025-01-15"
---

# {{ page.title }}

**Version {{ page.metadata.version }}** released on {{ page.metadata.release_date }}.

Current site: {{ site.config.title }}
```

:::{tip}
This is unique to Bengal—Hugo only supports variables in templates, not content files.
:::

---

## Configuration Mapping

### Basic Site Config

:::{tab-set}

:::{tab} Hugo (config.toml)
```toml
baseURL = "https://example.com"
title = "My Site"
languageCode = "en-us"
theme = "docsy"

[params]
  description = "My awesome site"
  github_repo = "https://github.com/user/repo"
```
:::{/tab}

:::{tab} Bengal (bengal.toml)
```toml
[site]
baseurl = "https://example.com"
title = "My Site"
language = "en"
theme = "bengal"

[site.params]
description = "My awesome site"
github_repo = "https://github.com/user/repo"
```
:::{/tab}

:::{/tab-set}

### Menu Configuration

:::{tab-set}

:::{tab} Hugo
```toml
[[menu.main]]
  name = "Docs"
  url = "/docs/"
  weight = 10

[[menu.main]]
  name = "Blog"
  url = "/blog/"
  weight = 20
```
:::{/tab}

:::{tab} Bengal
```toml
[[site.menu.main]]
name = "Docs"
url = "/docs/"
weight = 10

[[site.menu.main]]
name = "Blog"
url = "/blog/"
weight = 20
```
:::{/tab}

:::{/tab-set}

---

## Directory Structure Comparison

| Hugo | Bengal | Notes |
|------|--------|-------|
| `content/` | `content/` | ✅ Same |
| `static/` | `assets/` | Different name |
| `layouts/` | `templates/` | Template location |
| `themes/` | `themes/` | ✅ Same |
| `data/` | `data/` | ✅ Same |
| `config.toml` | `bengal.toml` | Different name |
| `archetypes/` | Not used | Use templates |
| `resources/` | Auto-managed | No equivalent |

---

## What Bengal Adds (Hugo Doesn't Have Built-in)

### Cards Grid

```markdown
:::{cards}
:columns: 3

:::{card} Feature 1
:icon: 🚀
:link: /docs/feature1/

Quick description
:::

:::{card} Feature 2
:icon: 📦
:link: /docs/feature2/

Another feature
:::

:::{/cards}
```

### Visual Steps

```markdown
:::{steps}

:::{step} Install
```bash
pip install bengal
```
:::{/step}

:::{step} Create Site
```bash
bengal new site mysite
```
:::{/step}

:::{step} Start Server
```bash
bengal serve
```
:::{/step}

:::{/steps}
```

### Interactive Data Tables

```markdown
:::{data-table}
:source: data/products.yaml
:columns: name, price, stock
:sortable: true
:filterable: true
:::
```

### Centralized Glossary

```markdown
<!-- Define in data/glossary.yaml -->
<!-- Use in any page: -->
:::{glossary}
:tags: api, authentication
:::
```

### Navigation Directives

```markdown
<!-- Auto-generate from section children -->
:::{child-cards}
:columns: 2
:::

<!-- Show sibling pages -->
:::{siblings}
:::

<!-- Prev/Next navigation -->
:::{prev-next}
:::
```

---

## What's Different (Honest Gaps)

| Hugo Feature | Bengal Status | Workaround |
|--------------|---------------|------------|
| Custom shortcodes | Use directives | Built-in directives cover most cases |
| Go templates | Jinja2 templates | Similar concepts, different syntax |
| Hugo Modules | Local themes only | Copy theme files |
| `.GetPage` function | Template functions | Different API |
| Image processing | Not built-in | External tools |
| Multilingual i18n | `lang` frontmatter | Simpler approach |

### Template Syntax Differences

| Hugo (Go) | Bengal (Jinja2) |
|-----------|-----------------|
| `{{ if .Params.x }}` | `{% if page.metadata.x %}` |
| `{{ range .Pages }}` | `{% for page in pages %}` |
| `{{ .Title \| upper }}` | `{{ page.title \| upper }}` |
| `{{ with .Params.x }}` | `{% if page.metadata.x %}` |
| `{{ partial "name" . }}` | `{% include "partials/name.html" %}` |

---

## Migration Steps

:::{steps}
:::{step} Copy Content
```bash
# Copy your Hugo content
cp -r /path/to/hugo/content/* content/

# Content structure is compatible
```
:::{/step}

:::{step} Convert Frontmatter
The only change: `categories` (plural) → `category` (singular)

```yaml
# Hugo
categories: [tutorial, python]

# Bengal
category: tutorial
tags: [python]  # Use tags for multiple
```
:::{/step}

:::{step} Convert Shortcodes
Search for `{{<` and replace with directives:

```bash
# Find all shortcode usages
grep -r "{{<" content/
```

Common conversions:

| Find | Replace With |
|------|--------------|
| `{{</* notice note */>}}...{{</* /notice */>}}` | `:::{note}...:::` |
| `{{</* highlight python */>}}...{{</* /highlight */>}}` | ` ```python...``` ` |
| `{{</* tabs */>}}...{{</* /tabs */>}}` | `:::{tab-set}...:::{/tab-set}` |
:::{/step}

:::{step} Update Config
```bash
# Rename config
mv config.toml bengal.toml

# Update format (see config mapping above)
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
- [ ] Backup your Hugo site
- [ ] Create new Bengal site: `bengal new site mysite`
:::

:::{checklist} Content Migration
- [ ] Copy `content/` directory
- [ ] Convert shortcodes to directives
- [ ] Update `categories` → `category` in frontmatter
- [ ] Check variable syntax in templates
:::

:::{checklist} Assets Migration
- [ ] Copy `static/` to `assets/`
- [ ] Update asset paths in content if needed
:::

:::{checklist} Config Migration
- [ ] Convert `config.toml` to `bengal.toml`
- [ ] Update menu configuration
- [ ] Set theme and other options
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | Hugo | Bengal |
|------|------|--------|
| New site | `hugo new site` | `bengal new site` |
| Build | `hugo` | `bengal build` |
| Serve | `hugo server` | `bengal serve` |
| New content | `hugo new docs/page.md` | Create file directly |
| Check links | External tool | `bengal health linkcheck` |
| Note callout | `{{</* notice note */>}}` | `:::{note}` |
| Warning | `{{</* notice warning */>}}` | `:::{warning}` |
| Tabs | `{{</* tabs */>}}` | `:::{tab-set}` |
| Code | `{{</* highlight */>}}` | ` ```lang ` |

---

## Next Steps

- [Directives Reference](/docs/reference/directives/) - All available directives
- [Configuration](/docs/about/concepts/configuration/) - Full config reference
