---
title: Troubleshooting
description: Common issues and how to resolve them
weight: 50
category: guide
icon: warning
card_color: red
---
# Troubleshooting

Guides for diagnosing and resolving common Bengal issues.

## Quick Diagnosis

```bash
# Check configuration
bengal config doctor

# Run health checks
bengal validate

# Verbose build output
bengal build --verbose

# Full debug mode
bengal build --dev
```

## Common Issues

- [Template Errors](./template-errors/) - Syntax errors, undefined variables, and missing templates

## Build Failures

### "Content directory not found"

Ensure you're running Bengal from your site root directory:

```bash
cd my-site
bengal build
```

### "Template not found"

1. Check template search paths in error message
2. Verify template exists in `templates/` or theme `templates/`
3. Run `bengal build --verbose` for detailed template resolution

### Build hangs or is very slow

1. Check for infinite loops in templates
2. Use `--profile-templates` to identify slow templates
3. For large sites (5K+ pages), use `--memory-optimized`

## Server Issues

### Port already in use

```bash
# Clean up stale server processes
bengal clean --stale-server

# Use a different port
bengal serve --port 8080
```

### Changes not reflecting

1. Hard refresh browser (Ctrl+Shift+R)
2. Clear browser cache
3. Restart server: `bengal serve`

## Cache Issues

### Stale content after changes

```bash
# Clear build cache
bengal clean --cache

# Force full rebuild
bengal build --no-incremental
```

### Incremental build not detecting changes

1. Check file timestamps
2. Run `bengal clean --cache` to reset
3. Verify `.bengal/` directory exists
