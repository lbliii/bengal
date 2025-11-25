---
title: Migrating Content from Other SSGs
description: Step-by-step guide to migrate your site from Hugo, Jekyll, Gatsby, or other static site generators to Bengal
weight: 10
type: doc
draft: false
lang: en
tags: [migration, content, import, hugo, jekyll, gatsby]
keywords: [migration, import, hugo, jekyll, gatsby, content conversion]
category: guide
---

# Migrating Content from Other SSGs

This guide helps you migrate your existing static site to Bengal. Whether you're coming from Hugo, Jekyll, Gatsby, or another SSG, these steps will help you preserve your content and URLs.

## When to Use This Guide

```{checklist}
- You have an existing site built with another static site generator
- You want to preserve your content structure and URLs
- You need to convert frontmatter formats
- You want to maintain your site's SEO and link structure
```

## Prerequisites

```{checklist} Before You Begin
- [Bengal installed](/getting-started/installation/)
- Access to your existing site's source files
- Basic knowledge of Markdown and YAML/TOML
```

## Step 1: Create Your Bengal Site

Start by creating a new Bengal site:

```bash
bengal new site mysite
cd mysite
```

Choose **Blank** preset if you're migrating existing content, or select a preset that matches your site type.

## Step 2: Understand Content Structure Differences

### File Organization

Bengal uses **file-system routing** where the `content/` directory structure directly maps to URLs:

| SSG | Content Location | Bengal Equivalent |
|-----|------------------|-------------------|
| Hugo | `content/` | `content/` |
| Jekyll | `_posts/`, `_pages/` | `content/blog/`, `content/` |
| Gatsby | `src/pages/` | `content/` |
| Next.js | `pages/` | `content/` |

### Index Files

Bengal distinguishes between section and page index files:

- **`_index.md`** - Creates a section (folder that can contain pages)
- **`index.md`** - Creates a page in its own folder

This is different from Hugo's `_index.md` (always a section) and Jekyll's `index.html` (always a page).

## Step 3: Convert Frontmatter

### Common Frontmatter Mappings

#### From Hugo

```yaml
# Hugo frontmatter
---
title: "My Post"
date: 2023-10-25
draft: false
tags: [python, web]
categories: [tutorial]
slug: my-post
weight: 10
---

# Converted to Bengal
---
title: My Post
date: 2023-10-25
draft: false
tags: [python, web]
category: tutorial  # Note: singular, not plural
slug: my-post
weight: 10
---
```

**Key differences:**
- `categories` (plural) → `category` (singular) in Bengal
- Remove quotes from simple string values
- Date format remains the same (ISO format)

#### From Jekyll

```yaml
# Jekyll frontmatter
---
layout: post
title: "My Post"
date: 2023-10-25 14:30:00 +0000
categories: [tutorial, python]
tags: [web]
published: true
---

# Converted to Bengal
---
type: post  # layout → type
title: My Post
date: 2023-10-25T14:30:00Z  # Convert to ISO format
category: tutorial  # Use first category
tags: [web]
draft: false  # published: true → draft: false
---
```

**Key differences:**
- `layout` → `type` in Bengal
- `published: true` → `draft: false`
- `categories` → `category` (use first category)
- Date format: Convert to ISO format

#### From Gatsby/MDX

```yaml
# Gatsby frontmatter
---
title: "My Post"
date: "2023-10-25"
author: "John Doe"
tags: ["python", "web"]
featured: true
---

# Converted to Bengal
---
title: My Post
date: 2023-10-25
author: John Doe
tags: [python, web]
# featured can be stored in params or custom frontmatter
---
```

## Step 4: Migrate Content Files

### Automated Migration Script

Create a simple Python script to help with bulk conversion:

```python
#!/usr/bin/env python3
"""Convert Hugo/Jekyll content to Bengal format."""

import re
from pathlib import Path

def convert_frontmatter(content: str, source_format: str = "hugo") -> str:
    """Convert frontmatter from source format to Bengal."""
    # Extract frontmatter
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not frontmatter_match:
        return content

    frontmatter = frontmatter_match.group(1)
    body = content[frontmatter_match.end():]

    # Convert categories to category (singular)
    frontmatter = re.sub(r'categories:\s*\[(.*?)\]', r'category: \1', frontmatter)

    # Convert published to draft
    if 'published: true' in frontmatter:
        frontmatter = frontmatter.replace('published: true', 'draft: false')
    elif 'published: false' in frontmatter:
        frontmatter = frontmatter.replace('published: false', 'draft: true')

    # Remove quotes from simple strings
    frontmatter = re.sub(r'"(.*?)"', r'\1', frontmatter)

    return f"---\n{frontmatter}\n---\n{body}"

# Usage
source_dir = Path("path/to/hugo/content")
target_dir = Path("content")

for md_file in source_dir.rglob("*.md"):
    content = md_file.read_text()
    converted = convert_frontmatter(content, source_format="hugo")

    # Preserve directory structure
    relative_path = md_file.relative_to(source_dir)
    target_file = target_dir / relative_path
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(converted)

    print(f"Converted: {md_file} → {target_file}")
```

### Manual Migration Steps

1. **Copy content files:**
   ```bash
   # From Hugo
   cp -r /path/to/hugo/content/* content/

   # From Jekyll
   mkdir -p content/blog
   cp -r /path/to/jekyll/_posts/* content/blog/
   ```

2. **Rename index files:**
   ```bash
   # Hugo _index.md → Bengal _index.md (same)
   # Jekyll index.html → Bengal index.md
   ```

3. **Convert frontmatter:**
   - Use the script above or convert manually
   - Check each file for format-specific fields

## Step 5: Preserve URLs

### URL Structure Mapping

Bengal generates URLs from file paths. To preserve existing URLs:

1. **Use `slug` frontmatter** to override generated URLs:
   ```yaml
   ---
   title: My Post
   slug: /old/url/path  # Preserves old URL structure
   ---
   ```

2. **Create redirects** (if URLs must change):
   ```yaml
   # content/old-url.md
   ---
   title: Redirect
   redirect: /new-url/
   ---
   ```

3. **Check URL generation:**
   ```bash
   bengal site build
   # Check public/ directory for generated URLs
   ```

## Step 6: Migrate Assets

### Asset Locations

Bengal looks for assets in:
- `assets/` - Site-specific assets
- `themes/[theme-name]/static/` - Theme assets

**Migration steps:**

1. **Copy static files:**
   ```bash
   # From Hugo
   cp -r /path/to/hugo/static/* assets/

   # From Jekyll
   cp -r /path/to/jekyll/assets/* assets/
   ```

2. **Update image references:**
   - Hugo: `![alt](images/photo.jpg)` → `![alt](../assets/images/photo.jpg)`
   - Jekyll: `![alt](/assets/images/photo.jpg)` → `![alt](../assets/images/photo.jpg)`

3. **Update CSS/JS references:**
   - Move to `assets/css/` and `assets/js/`
   - Update template references if using custom themes

## Step 7: Migrate Configuration

### Configuration Mapping

#### From Hugo `config.toml`

```toml
# Hugo config.toml
baseURL = "https://example.com"
title = "My Site"
languageCode = "en-us"

# Converted to Bengal bengal.toml
[site]
baseurl = "https://example.com"
title = "My Site"
language = "en"
```

#### From Jekyll `_config.yml`

```yaml
# Jekyll _config.yml
title: My Site
url: https://example.com
lang: en

# Converted to Bengal bengal.toml
[site]
title = "My Site"
baseurl = "https://example.com"
language = "en"
```

### Menu Configuration

```toml
# Bengal menu structure
[[site.menu.main]]
name = "Home"
url = "/"
weight = 1

[[site.menu.main]]
name = "Blog"
url = "/blog/"
weight = 2
```

## Step 8: Test Your Migration

```{checklist} Verification Steps
- [ ] Build the site: `bengal site build`
- [ ] Check for errors: `bengal site build --verbose`
- [ ] Validate links: `bengal health check`
- [ ] Preview locally: `bengal site serve` (visit http://localhost:5173)
```

## Step 9: Handle Special Cases

### Taxonomies

Bengal uses `tags` and `category` (singular) for taxonomies:

```yaml
# Convert multiple categories to tags
# Hugo: categories: [tutorial, python]
# Bengal: category: tutorial, tags: [python]
```

### Shortcodes

Bengal doesn't have Hugo-style shortcodes. Options:

1. **Convert to Markdown:**
   ```markdown
   # Hugo shortcode
   {{< youtube id="dQw4w9WgXcQ" >}}

   # Bengal: Use HTML or Markdown
   <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>
   ```

2. **Use Jinja2 templates** (for advanced cases)

### Data Files

Bengal doesn't have Jekyll-style `_data/` files. Options:

1. **Move to `config/params.yaml`:**
   ```yaml
   # config/params.yaml
   authors:
     - name: John Doe
       email: john@example.com
   ```

2. **Use Python scripts** to generate content from data

## Troubleshooting

### Common Issues

**Frontmatter parsing errors:**

```{checklist}
- Check YAML syntax (proper indentation, no tabs)
- Verify date formats (use ISO format: `2023-10-25`)
- Remove unsupported fields
```

**Missing pages:**

```{checklist}
- Check if files are in `content/` directory
- Verify `_index.md` vs `index.md` usage
- Check for `draft: true` (excluded from builds)
```

**Broken links:**

```{checklist}
- Run `bengal health check` to find broken links
- Update internal links to use relative paths
- Check URL generation matches expectations
```

**Assets not loading:**

```{checklist}
- Verify assets are in `assets/` directory
- Check image paths in content (use relative paths)
- Ensure asset references match Bengal's structure
```

### Getting Help

- Check [Content Organization](/about/concepts/content-organization/) for structure details
- Review [Configuration](/about/concepts/configuration/) for config options
- See [Getting Started](/getting-started/) for basics

## Next Steps

- **[Content Workflow](/guides/content-workflow/)** - Set up your content creation workflow
- **[Customizing Themes](/guides/customizing-themes/)** - Customize your site's appearance
- **[Deployment](/guides/deployment/)** - Deploy your migrated site
