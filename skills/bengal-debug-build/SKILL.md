---
name: bengal-debug-build
description: Debugs Bengal build failures and errors. Use when builds fail, validation errors occur, or when fixing build errors.
---

# Bengal Debug Build

Debug Bengal build failures and validation errors.

## Procedure

### Step 1: Run Build and Capture Output

```bash
bengal build
```

Capture the full error output. Common failure points:
- Template rendering (undefined variables, syntax)
- Directive parsing (invalid syntax, missing required args)
- Config loading (invalid bengal.toml)
- Content parsing (invalid frontmatter, malformed markdown)

### Step 2: Run Validation

```bash
bengal validate
```

Validation runs health checks including:
- Template context validation (missing variables)
- Directive syntax
- Config schema
- Content structure

Use `--verbose` for full output, `--templates` to focus on template errors.

### Step 3: Template Context Errors

If the error mentions "Missing context variables" or a template name:

- Check the template references variables that exist in the context
- Use `params.x` not `page.metadata.get('x')`
- Use `config.x` not `site.config.get('x')`
- Add the variable to the template context or use safe patterns (see bengal-template-fix skill)

### Step 4: Directive Errors

If the error mentions a directive (e.g., `:::{note}`):

- Check directive syntax: `:::{name} optional_title`
- Options use `:key: value` format
- Ensure closing `:::`
- For custom directives, verify registration in directive registry

### Step 5: Cache Issues

If builds behave inconsistently or show stale content:

```bash
bengal build --full
```

Forces a full rebuild, ignoring incremental cache.

### Step 6: Config Errors

- Validate bengal.toml syntax (TOML format)
- Check `[build]`, `[theme]` sections
- Ensure `content_dir` and `output_dir` exist or can be created

## Checklist

- [ ] Run `bengal build` and capture full error
- [ ] Run `bengal validate` for health checks
- [ ] Check template context (undefined vars)
- [ ] Check directive syntax in content
- [ ] Try `bengal build --full` if cache suspected
- [ ] Verify bengal.toml is valid TOML

## Additional Resources

See [references/error-codes.md](references/error-codes.md) for common errors and fixes.
