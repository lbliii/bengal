# Bengal Site Structure

## Directory Layout

```
site-root/
├── bengal.toml           # Config (required)
├── content/              # Markdown content (default)
│   ├── _index.md         # Home (required)
│   ├── about.md
│   ├── posts/
│   │   ├── _index.md     # Section index
│   │   └── *.md          # Posts
│   └── docs/
│       ├── _index.md
│       └── *.md
├── templates/            # Optional: override theme templates
├── static/               # Optional: static assets
├── themes/               # Optional: custom theme
│   └── my-theme/
│       ├── templates/
│       └── assets/
└── public/               # Output (default output_dir)
```

## bengal.toml Schema

```toml
# Site metadata
title = "Site Title"
baseurl = "https://example.com"
description = "Site description"
author = "Author Name"

[build]
output_dir = "public"    # Where built site goes
content_dir = "content"  # Where markdown lives

[theme]
name = "default"         # Theme from bengal package
# features = ["search", "rss"]
```

## _index.md Pattern

Every section (directory with content) needs `_index.md`:

- Root: `content/_index.md` — home page
- Section: `content/posts/_index.md` — section metadata (type, title)

## Content Types

- `type: blog` — Blog section (posts with date, tags)
- `type: doc` — Documentation section
- Omit for generic pages
