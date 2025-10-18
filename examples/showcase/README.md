# Bengal Showcase Site

This is Bengal's showcase and documentation site, demonstrating all features and serving as the official docs.

## Building the Showcase

### Prerequisites

```bash
# From repo root
pip install -e .
```

### Full Build

```bash
cd examples/showcase

# Generate autodoc content
bengal autodoc        # Python API docs → content/api/
bengal autodoc-cli    # CLI docs → content/cli/

# Build the site
bengal build
```

### Quick Build (No Autodoc)

If you don't need the API/CLI docs:

```bash
cd examples/showcase
bengal build
```

The site will build without autodoc content.

## Development Workflow

### With Live Reload

```bash
cd examples/showcase
bengal serve
```

**Note:** The dev server watches for changes in:
- `content/` (markdown files)
- `templates/` (Jinja2 templates)
- `assets/` (CSS, JS, images)

It does NOT auto-regenerate autodoc content. If you change Python/CLI code, run:

```bash
bengal autodoc && bengal autodoc-cli
```

### Autodoc Content

The `content/api/` and `content/cli/` directories are **auto-generated** and **not committed to git**.

**To regenerate:**
```bash
# Python API docs
bengal autodoc

# CLI docs  
bengal autodoc-cli

# Or both
bengal autodoc && bengal autodoc-cli
```

**Do not manually edit these files!** Changes will be lost on next generation.

## Site Structure

```
examples/showcase/
├── content/          # Content (committed)
│   ├── docs/         # Documentation pages (manual)
│   ├── features/     # Feature demos (manual)
│   ├── api/          # Python API docs (generated, gitignored)
│   └── cli/          # CLI docs (generated, gitignored)
├── templates/        # Custom templates
├── assets/           # CSS, JS, images
├── bengal.toml       # Site configuration
└── public/           # Build output (gitignored)
```

## What's Gitignored

- `public/` - Build output
- `content/api/` - Generated API docs
- `content/cli/` - Generated CLI docs
- `.bengal/` - Build cache

## Autodoc Configuration

See `bengal.toml` for autodoc settings:

```toml
[autodoc.python]
enabled = true
source_dirs = ["../../bengal"]  # Bengal's own source
output_dir = "content/api"

[autodoc.cli]
enabled = true
app_module = "bengal.cli:main"
output_dir = "content/cli"
```

## Health Checks

After building, Bengal runs health checks:

```bash
bengal build --quiet  # Minimal output
bengal build          # Full stats + health checks
```

Common warnings:
- **Breadcrumb issues:** Expected for generated API docs
- **Directive issues:** Check `content/docs/` pages
- **Menu links:** Update `bengal.toml` menu config

## Deployment

```bash
# Build for production
bengal build --quiet

# Output is in public/
# Deploy public/ to your hosting service
```

## Troubleshooting

### "Content directory not found"
Run `bengal autodoc` first to generate the API/CLI docs.

### Stale docs
Regenerate autodoc content:
```bash
rm -rf content/api content/cli
bengal autodoc && bengal autodoc-cli
```

### Build errors
Check the health report at the end of `bengal build` for specific issues.

---

**Questions?** Check the main [ARCHITECTURE.md](../../ARCHITECTURE.md) or [TESTING.md](../../TESTING.md).
