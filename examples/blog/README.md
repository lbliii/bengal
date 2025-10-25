# Simple Blog Example

This is a minimal blog demonstrating Bengal's **config directory structure**.

## Structure

```
blog/
├── config/
│   ├── _default/           # Base configuration
│   │   ├── site.yaml       # Site metadata, menus
│   │   ├── build.yaml      # Build settings
│   │   └── features.yaml   # Feature toggles
│   └── environments/
│       ├── local.yaml      # Local development
│       └── production.yaml # Production deployment
└── content/
    ├── _index.md          # Homepage
    └── posts/
        └── hello-world.md # Sample post
```

## Usage

### Local Development

```bash
# Serve locally (auto-detects local environment)
bengal serve

# Or explicitly
bengal serve --environment local

# With writer profile (fast, clean output)
bengal serve --profile writer
```

Opens at `http://localhost:8000`

### Production Build

```bash
# Build for production
bengal build --environment production

# Output in public/
```

### Introspection

```bash
# Show merged configuration
bengal config show

# Show with source origins
bengal config show --origin

# Compare environments
bengal config diff --environment local --against production

# Validate configuration
bengal config doctor
```

## Configuration Highlights

### Environment Overrides

**Local** (`config/environments/local.yaml`):
- `baseurl: http://localhost:8000`
- `parallel: false` (easier debugging)

**Production** (`config/environments/production.yaml`):
- `baseurl: https://myblog.com`
- `parallel: true` (fast builds)
- `strict_mode: true` (catch errors)

### Feature Toggles

Enabled in `config/_default/features.yaml`:
- ✅ RSS feed (`rss: true`)
- ✅ Sitemap (`sitemap: true`)
- ✅ Search (`search: true`)
- ✅ Syntax highlighting
- ✅ Reading time estimates

These expand into full configuration automatically!

## Customization

### Change Site Title

Edit `config/_default/site.yaml`:
```yaml
site:
  title: "My Awesome Blog"  # Change this
  author: "Your Name"       # And this
```

### Add a Profile

Create `config/profiles/writer.yaml`:
```yaml
build:
  fast_mode: true  # Quick builds
features:
  search: false    # Skip heavy features
```

Use it:
```bash
bengal serve --profile writer
```

## Learn More

- [Full config reference](/config.example/)
- [Bengal documentation](/)
- [Configuration guide](/docs/config/)

---

**Happy blogging!** 📝

