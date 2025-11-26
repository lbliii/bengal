---
title: Troubleshoot Issues
description: Solutions to common errors, build failures, and configuration issues
weight: 40
tags: [troubleshooting, errors, help, debug]
category: guide
---

# Troubleshooting Guide

Stuck? This guide covers common issues you might encounter when building sites with Bengal.

## Common Errors

### `TemplateNotFound`

**Error Message**:
```text
jinja2.exceptions.TemplateNotFound: base.html
```

**Cause**:
Bengal cannot find the template file you requested to extend or include.

**Solutions**:
1.  **Check file location**: Ensure your template is in `site/templates/` or your theme's `templates/` directory.
2.  **Check inheritance path**: If extending a theme template, use the `theme::template.html` syntax (e.g., `default::base.html`).
3.  **Check theme installation**: Run `bengal utils theme list` to verify your theme is installed and detected.

### `YAML Error` in Frontmatter

**Error Message**:
```text
yaml.parser.ParserError: while parsing a block mapping...
```

**Cause**:
Invalid syntax in the YAML frontmatter of a markdown file.

**Solutions**:
1.  **Check indentation**: YAML is sensitive to indentation. Ensure list items align correctly.
2.  **Check quotes**: If your title contains a colon (`:`), wrap the entire title in quotes.
    *   ❌ `title: Python: A Love Story`
    *   ✅ `title: "Python: A Love Story"`

### `Build Error: 'NoneType' object is not iterable`

**Cause**:
Usually happens when a template tries to loop over a variable that doesn't exist or is None.

**Solutions**:
1.  **Check loop variables**: Ensure `site.menu.main` or `site.taxonomies` are defined in your `bengal.toml`.
2.  **Use `default` filter**: `{% for item in menu.main | default([]) %}` prevents crashing on empty menus.

## Debugging Tools

Bengal includes built-in tools to help you debug issues.

### 1. Theme Debugger

If templates aren't loading correctly, check the resolution chain:

```bash
bengal utils theme debug
```

This shows exactly which theme is active and where Bengal looks for templates.

### 2. Verbose Logging

Run any command with `-v` (or `-vv` for more detail) to see what Bengal is doing under the hood.

```bash
bengal site build -v
```

### 3. Strict Mode

By default, Bengal tries to be forgiving. To catch every possible issue (like broken links or missing variables), run in strict mode:

```bash
bengal site build --strict
```

## Performance Issues

### Slow Builds?

If your build is taking longer than expected:

1.  **Check asset pipeline**: Image optimization is heavy. Try disabling it temporarily in `bengal.toml`:
    ```toml
    [assets]
    optimize = false
    ```
2.  **Check syntax highlighting**: Large code blocks can be slow to process.
3.  **Profile the build**:
    ```bash
    bengal utils perf profile
    ```

## Getting Help

If you're still stuck:

1.  **Search the Docs**: Use the search bar (Cmd+K).
2.  **Check GitHub Issues**: See if others have reported the same bug.
3.  **Ask the Community**: Join our Discord or GitHub Discussions.
