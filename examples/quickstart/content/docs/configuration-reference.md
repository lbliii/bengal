---
title: "Configuration Reference"
date: 2025-10-03
tags: ["configuration", "reference", "setup"]
categories: ["Documentation", "Reference"]
type: "reference"
description: "Complete reference for all Bengal SSG configuration options"
author: "Bengal Documentation Team"
---

# Configuration Reference

Complete reference for all Bengal SSG configuration options in `bengal.toml` or `bengal.yaml`.

## Configuration Files

Bengal supports two configuration formats:

- `bengal.toml` (recommended)
- `bengal.yaml` or `bengal.yml`

Bengal automatically detects and loads the configuration file from your project root.

## Basic Configuration

### Minimal Configuration

```toml
[site]
title = "My Site"
baseurl = "https://example.com"
```

This is all you need to get started!

## Complete Configuration

### Full Example (TOML)

```toml
[site]
title = "My Bengal Site"
baseurl = "https://example.com"
description = "A powerful static site built with Bengal"
theme = "default"
author = "Your Name"
language = "en"

[build]
output_dir = "public"
content_dir = "content"
assets_dir = "assets"
templates_dir = "templates"
parallel = true
incremental = false
max_workers = 0
pretty_urls = true

[assets]
minify = true
optimize = true
fingerprint = true

[features]
generate_sitemap = true
generate_rss = true
validate_links = true

[dev]
strict_mode = false
debug = false
validate_build = true
min_page_size = 1000

[pagination]
items_per_page = 10
```

### Full Example (YAML)

```yaml
site:
  title: "My Bengal Site"
  baseurl: "https://example.com"
  description: "A powerful static site built with Bengal"
  theme: "default"
  author: "Your Name"
  language: "en"

build:
  output_dir: "public"
  content_dir: "content"
  assets_dir: "assets"
  templates_dir: "templates"
  parallel: true
  incremental: false
  max_workers: 0
  pretty_urls: true

assets:
  minify: true
  optimize: true
  fingerprint: true

features:
  generate_sitemap: true
  generate_rss: true
  validate_links: true

dev:
  strict_mode: false
  debug: false
  validate_build: true
  min_page_size: 1000

pagination:
  items_per_page: 10
```

## Configuration Sections

### [site] - Site Metadata

Core site information:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | "Bengal Site" | Site title |
| `baseurl` | string | "" | Full site URL |
| `description` | string | "" | Site description |
| `theme` | string | "default" | Theme name |
| `author` | string | "" | Default author |
| `language` | string | "en" | Site language (ISO 639-1) |

**Example**:

```toml
[site]
title = "TechBlog"
baseurl = "https://techblog.example.com"
description = "Thoughts on software development"
theme = "default"
author = "Jane Developer"
language = "en"
```

### [build] - Build Settings

Control how Bengal builds your site:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `output_dir` | string | "public" | Output directory |
| `content_dir` | string | "content" | Content source directory |
| `assets_dir` | string | "assets" | Assets source directory |
| `templates_dir` | string | "templates" | Custom templates directory |
| `parallel` | boolean | true | Enable parallel processing |
| `incremental` | boolean | false | Enable incremental builds |
| `max_workers` | integer | 0 | Worker threads (0 = auto) |
| `pretty_urls` | boolean | true | Use pretty URLs (/about/ vs /about.html) |

**Example**:

```toml
[build]
output_dir = "dist"
content_dir = "content"
parallel = true
incremental = true
max_workers = 4
pretty_urls = true
```

#### Parallel Processing

```toml
[build]
parallel = true      # Enable parallel processing
max_workers = 0      # Auto-detect CPU cores
```

**Worker Count Options**:
- `0` - Auto-detect (recommended)
- `N` - Use N workers
- `-1` - Use all available cores

See: [Parallel Processing Guide](/docs/parallel-processing/)

#### Incremental Builds

```toml
[build]
incremental = true   # Enable incremental builds
```

Enables 18-42x faster rebuilds by only processing changed files.

See: [Incremental Builds Guide](/docs/incremental-builds/)

#### Pretty URLs

```toml
[build]
pretty_urls = true
```

| Setting | Output Path | URL |
|---------|-------------|-----|
| `true` | `/about/index.html` | `/about/` |
| `false` | `/about.html` | `/about.html` |

Pretty URLs are more SEO-friendly and work better with static hosting.

### [assets] - Asset Processing

Configure asset optimization:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `minify` | boolean | true | Minify CSS/JS |
| `optimize` | boolean | true | Optimize images |
| `fingerprint` | boolean | true | Add content hash to filenames |

**Example**:

```toml
[assets]
minify = true
optimize = true
fingerprint = true
```

#### Minification

```toml
[assets]
minify = true   # Minify CSS and JavaScript
```

Reduces file sizes for faster loading.

#### Optimization

```toml
[assets]
optimize = true   # Optimize images
```

Compresses images without visible quality loss.

#### Fingerprinting

```toml
[assets]
fingerprint = true   # Add content hash to filenames
```

Adds content-based hashes to filenames for cache busting:
- `style.css` → `style.a1b2c3d4.css`
- `app.js` → `app.e5f6g7h8.js`

### [features] - Feature Toggles

Enable/disable site features:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `generate_sitemap` | boolean | true | Generate sitemap.xml |
| `generate_rss` | boolean | true | Generate RSS feed |
| `validate_links` | boolean | true | Validate internal links |

**Example**:

```toml
[features]
generate_sitemap = true
generate_rss = true
validate_links = true
```

#### Sitemap Generation

```toml
[features]
generate_sitemap = true
```

Automatically generates `/sitemap.xml` for search engines.

#### RSS Feed

```toml
[features]
generate_rss = true
```

Automatically generates `/feed.xml` with recent posts.

#### Link Validation

```toml
[features]
validate_links = true
```

Checks for broken internal links during build.

### [dev] - Development Settings

Settings for development and debugging:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `strict_mode` | boolean | false | Fail on template errors |
| `debug` | boolean | false | Enable debug output |
| `validate_build` | boolean | true | Run post-build checks |
| `min_page_size` | integer | 1000 | Minimum page size (bytes) |

**Example**:

```toml
[dev]
strict_mode = false
debug = false
validate_build = true
min_page_size = 1000
```

#### Strict Mode

```toml
[dev]
strict_mode = true
```

Causes build to fail on template errors instead of using fallback rendering. Useful for catching template bugs.

#### Debug Mode

```toml
[dev]
debug = true
```

Enables verbose debug output and full tracebacks.

#### Build Validation

```toml
[dev]
validate_build = true
```

Runs health checks after build completes:
- Checks for empty pages
- Validates output structure
- Reports warnings

#### Minimum Page Size

```toml
[dev]
min_page_size = 1000
```

Warns if generated pages are smaller than this (in bytes). Helps catch template issues.

### [pagination] - Pagination Settings

Configure automatic pagination:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `items_per_page` | integer | 10 | Items per page |

**Example**:

```toml
[pagination]
items_per_page = 10
```

Applies to:
- Archive pages (section listings)
- Tag pages
- Category pages

## Environment-Specific Configuration

### Development Configuration

```toml
[site]
title = "My Site (Dev)"
baseurl = "http://localhost:8000"

[build]
parallel = true
incremental = true
pretty_urls = true

[assets]
minify = false      # Faster builds
optimize = false    # Faster builds
fingerprint = false # Easier debugging

[dev]
debug = true
strict_mode = false
```

### Production Configuration

```toml
[site]
title = "My Site"
baseurl = "https://example.com"

[build]
parallel = true
incremental = false  # Clean builds
pretty_urls = true

[assets]
minify = true
optimize = true
fingerprint = true

[dev]
debug = false
strict_mode = true   # Catch errors
validate_build = true
```

## CLI Overrides

You can override configuration via CLI flags:

```bash
# Override parallel setting
bengal build --parallel
bengal build --no-parallel

# Override incremental setting
bengal build --incremental
bengal build --no-incremental

# Override max workers
bengal build --max-workers=8

# Combine flags
bengal build --incremental --parallel --max-workers=4
```

CLI flags take precedence over configuration file settings.

## Configuration Access in Templates

Access configuration in templates:

```jinja2
{{ site.title }}
{{ site.baseurl }}
{{ site.description }}

{{ config.output_dir }}
{{ config.parallel }}
{{ config.theme }}
```

## Default Configuration

If no configuration file is found, Bengal uses these defaults:

```toml
[site]
title = "Bengal Site"
baseurl = ""
theme = "default"

[build]
output_dir = "public"
content_dir = "content"
assets_dir = "assets"
templates_dir = "templates"
parallel = true
incremental = false
max_workers = 0
pretty_urls = true

[assets]
minify = true
optimize = true
fingerprint = true

[features]
generate_sitemap = true
generate_rss = true
validate_links = true

[dev]
strict_mode = false
debug = false
validate_build = true
min_page_size = 1000

[pagination]
items_per_page = 10
```

## Configuration Validation

Bengal validates your configuration on load:

### Valid Configuration

```toml
[build]
parallel = true          # ✅ Boolean
max_workers = 4          # ✅ Integer
output_dir = "public"    # ✅ String
```

### Invalid Configuration

```toml
[build]
parallel = "yes"         # ❌ Should be boolean
max_workers = "four"     # ❌ Should be integer
output_dir = 123         # ❌ Should be string
```

Bengal will report errors and use defaults for invalid values.

## Best Practices

### ✅ Do

- **Use version control** for your config file
- **Set baseurl** for production builds
- **Enable incremental** for development
- **Use parallel** for faster builds
- **Validate links** before deployment

### ❌ Don't

- **Don't commit** sensitive data (API keys, passwords)
- **Don't disable validation** for production
- **Don't use absolute** paths (breaks portability)
- **Don't forget baseurl** for production

## Migration from Other SSGs

### From Hugo

Hugo's `config.toml`:
```toml
baseURL = "https://example.com"
title = "My Site"
theme = "mytheme"
```

Bengal equivalent:
```toml
[site]
baseurl = "https://example.com"
title = "My Site"
theme = "mytheme"
```

### From Jekyll

Jekyll's `_config.yml`:
```yaml
title: My Site
baseurl: ""
url: "https://example.com"
```

Bengal equivalent:
```toml
[site]
title = "My Site"
baseurl = "https://example.com"
```

## Troubleshooting

### Configuration Not Loading

**Problem**: Changes to config file not taking effect.

**Solutions**:
1. Check file name: `bengal.toml` or `bengal.yaml`
2. Check file location: Project root
3. Check syntax: Valid TOML/YAML
4. Rebuild: `bengal clean && bengal build`

### Invalid Configuration

**Problem**: Build fails with "Invalid configuration" error.

**Solutions**:
1. Check data types (strings, booleans, integers)
2. Check for typos in option names
3. Validate TOML/YAML syntax
4. Use verbose mode: `bengal build --verbose`

### CLI Flags Not Working

**Problem**: CLI flags seem ignored.

**Solutions**:
1. CLI flags override config file
2. Check flag syntax: `--incremental` not `--incremental=true`
3. Use `--verbose` to see effective configuration

## Examples

### Blog Configuration

```toml
[site]
title = "My Tech Blog"
baseurl = "https://blog.example.com"
description = "Writing about software development"
author = "Jane Doe"

[build]
parallel = true
incremental = true
pretty_urls = true

[pagination]
items_per_page = 10

[features]
generate_sitemap = true
generate_rss = true
```

### Documentation Site

```toml
[site]
title = "Product Documentation"
baseurl = "https://docs.example.com"
description = "Official product documentation"
theme = "docs"

[build]
parallel = true
incremental = false  # Always clean for docs
pretty_urls = true

[dev]
strict_mode = true   # Catch all errors
validate_build = true
```

### Portfolio Site

```toml
[site]
title = "Jane Doe - Portfolio"
baseurl = "https://janedoe.com"
description = "Designer and developer"

[build]
parallel = true
pretty_urls = true

[assets]
minify = true
optimize = true      # Important for images
fingerprint = true

[features]
generate_sitemap = true
generate_rss = false  # No blog
```

## Learn More

- [Getting Started](/posts/getting-started-with-bengal/)
- [Incremental Builds](/docs/incremental-builds/)
- [Parallel Processing](/docs/parallel-processing/)
- [Template System](/docs/template-system/)

## Reference

- [TOML Specification](https://toml.io/)
- [YAML Specification](https://yaml.org/)
- [Bengal GitHub](https://github.com/bengal-ssg/bengal)

