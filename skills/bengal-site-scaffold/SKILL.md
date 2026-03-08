---
name: bengal-site-scaffold
description: Scaffolds a new Bengal static site with config, content structure, and theme. Use when creating a new site, starting a blog, or converting a project to Bengal.
---

# Bengal Site Scaffold

Create a new Bengal static site from scratch.

## Procedure

### Step 1: Create bengal.toml

At the site root:

```toml
title = "My Site"
baseurl = "https://example.com"
description = "A Bengal static site"

[build]
output_dir = "public"
content_dir = "content"

[theme]
name = "default"
```

### Step 2: Create Content Structure

```
content/
├── _index.md          # Home page (required)
├── about.md           # About page
├── posts/             # Blog section
│   ├── _index.md      # Section index (type: blog)
│   └── first-post.md
```

### Step 3: Create _index.md Files

**Root index** (`content/_index.md`):

```markdown
---
title: Home
---

# Welcome

Your site content.
```

**Section index** (`content/posts/_index.md`):

```markdown
---
type: blog
title: Posts
description: Blog posts
---

# Posts
```

### Step 4: Create a Blog Post

```markdown
---
type: blog
title: "First Post"
date: '2026-01-01'
tags: [meta, welcome]
description: My first post.
---

# First Post

Content here.
```

### Step 5: Build and Serve

```bash
bengal build
bengal serve
```

## Theme Setup

Bengal uses the default theme from the package. To override:

- Add `templates/` at site root to override templates
- Add `static/` for static assets
- Or create `themes/my-theme/` with `templates/` and `assets/`

## Checklist

- [ ] bengal.toml with title, baseurl, build section
- [ ] content/_index.md (required)
- [ ] content_dir and output_dir match your layout
- [ ] Section directories have _index.md with type
- [ ] Run bengal build and bengal serve

## Additional Resources

See [references/site-structure.md](references/site-structure.md) for directory layout and config schema.
