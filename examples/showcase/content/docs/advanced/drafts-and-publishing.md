---
title: Drafts and Publishing
description: Publishing workflows from draft to production
type: doc
weight: 5
tags: ["advanced", "publishing", "workflow"]
toc: true
---

# Drafts and Publishing

**Purpose**: Manage content from draft stage through production deployment.

## What You'll Learn

- Mark pages as drafts
- Preview drafts locally
- Publish content
- Deploy to production
- Validate before deployment

## Draft Status

Mark pages as drafts in frontmatter:

```yaml
---
title: Work in Progress
draft: true
---
```

**Draft behavior:**
- Excluded from production builds
- Visible in development (with `--drafts`)
- Not in sitemap or RSS
- Not linked in navigation

## Development Workflow

### 1. Create Draft

```yaml
---
title: New Feature Announcement
draft: true
date: 2025-10-15
---

# Coming Soon

We're excited to announce...
```

### 2. Preview Drafts

```bash
# View drafts in development
bengal serve --drafts
```

Visit http://localhost:5173 to preview.

### 3. Publish

Remove or set `draft: false`:

```yaml
---
title: New Feature Announcement
draft: false  # or omit entirely
date: 2025-10-15
---
```

### 4. Build for Production

```bash
bengal build
```

Drafts automatically excluded.

## Publishing Checklist

Before publishing:

```{success} Pre-Publication Checklist
- [ ] Content reviewed and edited
- [ ] Links tested
- [ ] Images optimized
- [ ] SEO metadata complete
- [ ] Draft status removed
- [ ] Date set appropriately
- [ ] Tags and categories added
- [ ] Preview looks correct
```

## Build for Production

### Standard Build

```bash
# Build without drafts
bengal build
```

### With Options

```bash
# Incremental build
bengal build --incremental

# Strict mode (fail on errors)
bengal build --strict

# Both
bengal build --incremental --strict
```

### Verify Build

```bash
# Check output
ls -la public/

# Test locally
cd public/
python -m http.server 8000
# Visit http://localhost:8000
```

## Deployment Options

### Netlify

1. **Connect repo** - Link your Git repository
2. **Configure build**:
   - Build command: `bengal build`
   - Publish directory: `public`
3. **Deploy** - Push to main branch

**netlify.toml:**

```toml
[build]
command = "pip install -e . && bengal build"
publish = "public"

[[redirects]]
from = "/*"
to = "/404.html"
status = 404
```

### Vercel

1. **Import project** - Connect Git repository
2. **Configure**:
   - Build command: `bengal build`
   - Output directory: `public`
3. **Deploy**

### GitHub Pages

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
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: bengal build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```

### Custom Server

```bash
# Build locally
bengal build

# Upload public/ directory
rsync -avz public/ user@server:/var/www/html/
```

## Health Validation

Run health checks before deployment:

```bash
# Build with validation
bengal build --strict
```

**Checks include:**
- Link validation
- Asset verification
- Template errors
- Configuration issues

Review health report at end of build.

## Link Validation

Ensure all links work:

```bash
# Build includes link validation
bengal build

# Check health report for broken links
```

**Common issues:**
- Internal 404s
- Missing images
- Broken cross-references
- External redirects

## CI/CD Workflow

### Example Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e .
      - run: bengal build --strict
      - run: # Run tests
```

### Deployment Pipeline

```
1. Push to Git
   ↓
2. CI runs tests
   ↓
3. Build site
   ↓
4. Run validation
   ↓
5. Deploy to hosting
   ↓
6. Verify deployment
```

## Best Practices

### Version Control

```bash
# Commit source files
git add content/ bengal.toml
git commit -m "Add new post"

# Don't commit build output
# (Add public/ to .gitignore)
```

### Staging Environment

Test before production:

```bash
# Build for staging
bengal build

# Deploy to staging.example.com
# Test thoroughly
# Then deploy to production
```

### Backup Strategy

Backup before major changes:

```bash
# Git provides version control
git tag v1.0.0
git push --tags

# Backup hosting separately
# (Most hosts have automatic backups)
```

## Troubleshooting

### Build Fails

```{error} Build Errors
Check:
- Python version (3.8+)
- Dependencies installed
- Config file valid
- Template syntax correct
```

### Missing Content

```{warning} Content Not Showing
Verify:
- Draft status removed
- File in content/ directory
- Valid frontmatter
- Build completed successfully
```

### Broken Links

```{tip} Link Issues
Fix:
- Update internal links
- Check file paths
- Verify external URLs
- Run link validation
```

## Quick Reference

**Mark as draft:**
```yaml
---
draft: true
---
```

**Build for production:**
```bash
bengal build
```

**Preview drafts:**
```bash
bengal serve --drafts
```

**Deploy checklist:**
1. Review content
2. Remove draft status
3. Build site
4. Validate links
5. Test locally
6. Deploy

## Next Steps

- **[SEO](seo.md)** - Optimize for search
- **[Navigation](navigation.md)** - Configure menus
- **[Health Checks](../health-checks.md)** - Validation

## Related

- [Getting Started](../writing/getting-started.md) - Create content
- [Content Organization](../writing/content-organization.md) - Structure
- [Frontmatter Guide](../writing/frontmatter-guide.md) - Metadata
