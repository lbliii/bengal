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

# Explain incremental build decisions (why pages rebuilt/skipped)
bengal build --explain

# Preview build without writing files
bengal build --dry-run
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

1. Run `bengal build --explain` to see why pages are rebuilt or skipped
2. Check file timestamps
3. Run `bengal clean --cache` to reset
4. Verify `.bengal/` directory exists

### Too many pages rebuilding

Use `--explain` to diagnose why pages are being rebuilt:

```bash
bengal build --explain
```

Output shows rebuild reasons per page:
- **content_changed** — Page content was modified
- **template_changed** — Template file was updated
- **asset_fingerprint_changed** — CSS/JS assets changed
- **cascade_dependency** — Parent section changed
- **nav_changed** — Navigation structure updated

The `--explain` output also includes a **Decision Trace** showing layer-by-layer debugging info:

```text
═══════════════════════════════════════════════════════════════
                    DECISION TRACE                              
═══════════════════════════════════════════════════════════════

Decision: INCREMENTAL

───────────────────────────────────────────────────────────────
Layer 1: Data Files
───────────────────────────────────────────────────────────────
  Checked:     3
  Changed:     0
  Fingerprints available: ✓

───────────────────────────────────────────────────────────────
Layer 2: Autodoc
───────────────────────────────────────────────────────────────
  Sources tracked: 448
  Sources stale:   0
  Metadata available: ✗
  ⚠ Using fingerprint fallback (metadata unavailable)
  Detection method: fingerprint

───────────────────────────────────────────────────────────────
Layer 3: Section Optimization
───────────────────────────────────────────────────────────────
  Sections total:   5
  Sections changed: 1
    • docs (subsection_changed:about/glossary.md)

───────────────────────────────────────────────────────────────
Layer 4: Page Filtering
───────────────────────────────────────────────────────────────
  In changed sections: 35
  Filtered out:        1028

═══════════════════════════════════════════════════════════════
```

For machine-readable output (CI/tooling):

```bash
bengal build --explain --explain-json
```

### Strict Incremental Mode (Debugging)

For debugging cache issues, enable strict incremental mode to surface fallback paths:

```bash
# Log warnings when fallbacks are used
BENGAL_STRICT_INCREMENTAL=warn bengal build

# Fail when fallbacks are used (useful for CI)
BENGAL_STRICT_INCREMENTAL=error bengal build
```

This helps identify when:
- Autodoc metadata is missing (fingerprint fallback used)
- Data file dependencies aren't tracked
- Cache migration issues occur
