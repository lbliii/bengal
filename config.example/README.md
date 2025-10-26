# Bengal Config Directory Example

This directory demonstrates the **recommended configuration structure** for Bengal projects.

## 📁 Directory Structure

```
config/
├── _default/           # Base configuration (always loaded)
│   ├── site.yaml      # Site metadata, menus, taxonomies
│   ├── build.yaml     # Build settings, markdown, assets
│   └── features.yaml  # Feature toggles, outputs, health checks
├── environments/      # Environment-specific overrides
│   ├── local.yaml     # Local development (auto-detected)
│   ├── preview.yaml   # Staging/preview deployments
│   └── production.yaml  # Production builds
└── profiles/          # Build profiles (persona-based configs)
    ├── writer.yaml    # Fast, quiet (content creators)
    ├── theme-dev.yaml # Template debugging (theme devs)
    └── dev.yaml       # Full observability (core devs)
```

## 🎯 Configuration Precedence

Config values are merged in this order (later values override earlier):

```
_default → environment → profile → env vars → CLI flags
```

**Example**:
```yaml
# _default/build.yaml
build:
  parallel: true
  max_workers: 8

# environments/local.yaml
build:
  parallel: false  # ← Overrides default

# profiles/dev.yaml
build:
  parallel: false  # ← Reinforces local
  incremental: false  # ← Adds new setting
```

Result when running `bengal build --profile dev` (local environment):
```yaml
build:
  parallel: false     # From local environment
  max_workers: 8      # From _default (not overridden)
  incremental: false  # From dev profile
```

## 🌍 Environments

### Local (Default)
**Auto-detected**: When no CI/platform env vars present  
**Purpose**: Fast development with debugging conveniences  
**Key settings**: `parallel: false`, localhost baseurl, incremental builds

**Usage**:
```bash
bengal serve  # Defaults to local environment
bengal build --environment local  # Explicit
```

### Preview (Staging)
**Auto-detected**: Netlify (CONTEXT=deploy-preview), Vercel (VERCEL_ENV=preview)  
**Purpose**: Test production-like builds before going live  
**Key settings**: `parallel: true`, preview baseurl, `noindex` robots

**Usage**:
```bash
bengal build --environment preview  # Explicit
# Or deploy to Netlify/Vercel PR preview (auto-detected)
```

### Production
**Auto-detected**: Netlify (CONTEXT=production), Vercel (VERCEL_ENV=production), GitHub Actions  
**Purpose**: Optimized, validated production builds  
**Key settings**: `parallel: true`, `strict_mode: true`, all features enabled

**Usage**:
```bash
bengal build --environment production  # Explicit
# Or deploy to Netlify/Vercel production (auto-detected)
```

## 👤 Profiles

Profiles are **persona-based configurations** that override settings regardless of environment.

### Writer Profile
**Who**: Content creators, bloggers, technical writers  
**Goal**: Fast, clean builds focused on content quality  
**Key settings**: `fast_mode: true`, minimal features, quiet output

**Usage**:
```bash
bengal build --profile writer
bengal serve --profile writer
```

**Best for**:
- Writing/editing blog posts
- Quick content previews
- Distraction-free writing

### Theme-Dev Profile
**Who**: Theme designers, template developers  
**Goal**: Fast rebuilds with detailed template errors  
**Key settings**: `parallel: false`, template validation, detailed errors

**Usage**:
```bash
bengal build --profile theme-dev
bengal build --theme-dev  # Shorthand
```

**Best for**:
- Building custom themes
- Debugging templates
- CSS/JS development

### Dev Profile
**Who**: Bengal core developers, plugin authors  
**Goal**: Maximum observability, full debugging info  
**Key settings**: `debug: true`, full tracebacks, profiling

**Usage**:
```bash
bengal build --profile dev
bengal build --dev  # Shorthand
```

**Best for**:
- Bengal core development
- Debugging complex build issues
- Performance optimization

## 🚀 Quick Start

### 1. Copy to Your Project

```bash
# From Bengal repo root
cp -r config.example/ myproject/config/
cd myproject/
```

### 2. Customize Defaults

Edit `config/_default/site.yaml`:
```yaml
site:
  title: "My Site"  # ← Change this
  author: "Your Name"  # ← Change this
  baseurl: "https://yourdomain.com"  # ← Change this
```

### 3. Update Environment URLs

**Local** (config/environments/local.yaml):
```yaml
site:
  baseurl: "http://localhost:8000"  # Usually fine as-is
```

**Production** (config/environments/production.yaml):
```yaml
site:
  baseurl: "https://yourdomain.com"  # ← YOUR ACTUAL DOMAIN
```

### 4. Build!

```bash
# Local development
bengal serve  # Auto-detects local environment

# Production build
bengal build --environment production

# Writer workflow
bengal serve --profile writer
```

## 🔧 Feature Toggles

Bengal provides **high-level feature toggles** that expand into detailed configuration:

```yaml
# config/_default/features.yaml
features:
  rss: true          # → generate_rss: true, output_formats: [rss]
  sitemap: true      # → generate_sitemap: true
  search: true       # → search.enabled: true, search.preload: smart
  json: true         # → output_formats: [json], generate_index: true
  syntax_highlighting: true  # → syntax_highlighting.enabled: true
  reading_time: true # → reading_time.enabled: true
  related_pages: true  # → related_pages.enabled: true
```

**Override expanded config** if you need finer control:
```yaml
features:
  rss: true  # Expands to generate_rss: true

# Override expansion
rss:
  enabled: true
  filename: "feed.xml"  # Custom filename
  limit: 50  # Custom limit (default: 20)
```

## 📊 Introspection Commands

### Show Merged Config
```bash
# Show final merged configuration
bengal config show

# Show with source file origins
bengal config show --origin

# Show specific environment
bengal config show --environment production --origin
```

### Validate Config
```bash
# Check for errors and warnings
bengal config doctor

# Validate specific environment
bengal config doctor --environment production
```

### Compare Environments
```bash
# Compare local vs production
bengal config diff --environment local --against production

# See what changes between environments
bengal config diff --environment preview --against production
```

### Initialize Config Directory
```bash
# Scaffold new config/ directory
bengal config init

# Choose structure type
bengal config init --type directory
```

## 📚 Advanced Usage

### Environment Variables

Override any config value with environment variables:

```bash
# Override baseurl
export BENGAL_BASEURL="https://custom.com"
bengal build

# Override environment
export BENGAL_ENV="production"
bengal build  # Uses production environment
```

### CLI Flags (Highest Precedence)

```bash
# Override parallelization
bengal build --no-parallel

# Override strict mode
bengal build --strict

# Combine environment + profile
bengal build --environment production --profile dev
```

### Custom Profiles

Create your own profile for specific workflows:

```yaml
# config/profiles/ci.yaml
build:
  parallel: true
  max_workers: 4  # CI has limited cores
  strict_mode: true
  fast_mode: true

health_check:
  enabled: true
  fail_on_error: true
```

Use it:
```bash
bengal build --profile ci
```

## 🔄 Migration from Single-File Config

### Old Style (bengal.toml or bengal.yaml)
```toml
# bengal.toml
title = "My Site"
baseurl = "https://example.com"

[build]
parallel = true
max_workers = 8
```

### New Style (config/ directory)
```yaml
# config/_default/site.yaml
site:
  title: "My Site"
  baseurl: "https://example.com"

# config/_default/build.yaml
build:
  parallel: true
  max_workers: 8
```

### Migration Tool (coming soon)
```bash
# Automatic migration
bengal config migrate --from bengal.toml --to config/
```

## 📖 See Also

- [Bengal Documentation](https://bengal.readthedocs.io)
- [Configuration Reference](https://bengal.readthedocs.io/config)
- [Environment Detection](https://bengal.readthedocs.io/environments)
- [Build Profiles](https://bengal.readthedocs.io/profiles)

---

**Questions?** Open an issue on GitHub or check the docs!

