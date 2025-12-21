# RFC: Path Display Guidelines for CLI Output

**Status**: Draft  
**Created**: 2025-12-21  
**Author**: AI Assistant  
**Confidence**: 85% 🟢

---

## Executive Summary

Standardize how file and directory paths are displayed across Bengal CLI output. The core principle: **default to short/relative paths** because users know their current working directory, and absolute paths add visual noise without proportional value.

---

## Problem Statement

Currently, Bengal CLI output displays paths inconsistently:

```bash
# Verbose absolute paths (noisy)
● subdirectory_site_detected  current=/Users/llane/Documents/github/python/bengal subdirectory=/Users/llane/Documents/github/python/bengal/site

# vs cleaner relative paths
⚠️  Subdirectory 'site/' appears to be a Bengal site with content.
```

**Issues:**
1. Absolute paths starting from `/Users/` add significant visual noise
2. Path format varies across different CLI commands and log outputs
3. Long paths wrap awkwardly in terminal output
4. No clear guideline for when to use absolute vs relative paths

---

## Goals

1. **Reduce visual noise** - Paths should be as short as useful
2. **Maintain consistency** - Same path types formatted the same way across CLI
3. **Preserve utility** - Absolute paths where users need to copy-paste
4. **Support debugging** - Structured logs should have enough context

## Non-Goals

- Changing how paths are stored internally
- Modifying config file path specifications
- Affecting programmatic API outputs (only CLI/human-readable output)

---

## Design

### Path Display Tiers

| Tier | Format | When to Use |
|------|--------|-------------|
| **T1: Name only** | `site/`, `bengal/` | Warnings, info, structured logs |
| **T2: Project-relative** | `content/docs/guide.md` | File references within project |
| **T3: CWD-relative** | `./site/content/` | When navigating from current directory |
| **T4: Absolute** | `/Users/.../project/public` | Copy-paste paths, out-of-context logs |

### Decision Matrix

| Context | Tier | Rationale |
|---------|------|-----------|
| **User warnings/info** | T1 | User knows CWD, minimal noise |
| **Structured logs (normal)** | T1-T2 | Scannable, debugging-friendly |
| **Structured logs (CI/debug mode)** | T4 | Context may be unclear |
| **Error messages** | T2 + context | `file.md (in project/)` pattern |
| **Output paths (build results)** | T2 | Relative to project root |
| **Cache/state paths** | T2 | `.bengal/` is recognizable |
| **"Navigate here" prompts** | T4 | User needs to copy-paste |

### Implementation Rules

#### Rule 1: Default to Project-Relative or Shorter

```python
# ✅ Good - short and clear
logger.warning("subdirectory_site_detected", current=root_path.name, subdirectory=subdir_name)

# ❌ Avoid - absolute path noise  
logger.warning("subdirectory_site_detected", current=str(root_path), subdirectory=str(subdir))
```

#### Rule 2: Use `.name` for Directory References

When referencing a directory in context, use the directory name only:

```python
# ✅ Good
cli.warning(f"Parent directory has Bengal project: {parent.name}/")
cli.info(f"Building site in {site.root_path.name}/")

# ❌ Avoid
cli.warning(f"Parent directory has Bengal project: {parent}")
```

#### Rule 3: Project-Relative for File References

For files within the project, show path relative to project root:

```python
# ✅ Good
cli.error(f"Invalid frontmatter in content/docs/guide.md")
logger.warning("parse_error", file="content/docs/guide.md", line=12)

# ❌ Avoid
cli.error(f"Invalid frontmatter in {absolute_path}")
```

#### Rule 4: Absolute Paths for "Navigate Here" Use Cases

When the user might need to copy-paste the path:

```python
# ✅ Appropriate - user might want to open this
cli.success(f"Site built successfully!")
cli.info(f"   Output: {output_dir}")  # Absolute OK here

# Or use a hybrid approach
cli.info(f"   Output: public/ ({output_dir})")  # Best of both
```

#### Rule 5: Structured Logs Follow Same Rules

Structured log fields should use short paths by default:

```python
# ✅ Good - scannable
logger.info("build_complete", output="public/", pages=150)
logger.warning("config_not_found", search_path=root.name, tried=["bengal.toml"])

# ❌ Noisy
logger.info("build_complete", output="/Users/llane/.../public/", pages=150)
```

### Helper Function (Optional)

Consider adding a utility for consistent path formatting:

```python
# bengal/utils/paths.py

def display_path(path: Path, relative_to: Path | None = None, style: str = "short") -> str:
    """
    Format path for CLI display.

    Args:
        path: Path to format
        relative_to: Base path for relative formatting
        style: "short" (name only), "relative", or "absolute"

    Returns:
        Formatted path string
    """
    if style == "short":
        return path.name + ("/" if path.is_dir() else "")
    elif style == "relative" and relative_to:
        try:
            return str(path.relative_to(relative_to))
        except ValueError:
            return str(path)
    else:
        return str(path)
```

---

## Examples

### Before (Current State)

```bash
⚠️  ⚠️  Subdirectory 'site/' appears to be a Bengal site with content.
⚠️     Did you mean to run: cd site && bengal serve

● subdirectory_site_detected  current=/Users/llane/Documents/github/python/bengal subdirectory=/Users/llane/Documents/github/python/bengal/site hint=cd site && bengal serve
● config_file_not_found  search_path=/Users/llane/Documents/github/python/bengal tried_files=['bengal.toml', 'bengal.yaml', 'bengal.yml'] action=using_defaults

    ᓚᘏᗢ  Cleaning output directory...

   ↪ /Users/llane/Documents/github/python/bengal/public
   ℹ Cache preserved at /Users/llane/Documents/github/python/bengal/.bengal
```

### After (Proposed)

```bash
⚠️  Subdirectory 'site/' appears to be a Bengal site with content.
     Did you mean to run: cd site && bengal serve

● subdirectory_site_detected  current=bengal subdirectory=site hint=cd site && bengal serve
● config_file_not_found  search_path=bengal tried_files=['bengal.toml', 'bengal.yaml', 'bengal.yml'] action=using_defaults

    ᓚᘏᗢ  Cleaning output directory...

   ↪ public/
   ℹ Cache preserved at .bengal/
```

### Error Messages

```bash
# Before
❌ Failed to parse /Users/llane/Documents/github/python/bengal/content/docs/guide.md: Invalid YAML at line 5

# After  
❌ Failed to parse content/docs/guide.md: Invalid YAML at line 5
```

---

## Migration Strategy

### Phase 1: Core CLI Output (This RFC)
- [x] `site_loader.py` - Subdirectory/parent detection warnings
- [x] `config/loader.py` - Config file not found logs
- [ ] `cli/commands/build.py` - Output directory paths
- [ ] `cli/commands/clean.py` - Cache/output paths
- [ ] `cli/commands/serve.py` - Server paths

### Phase 2: Structured Logging
- [ ] Audit all `logger.warning()` / `logger.info()` calls for path fields
- [ ] Update to use short/relative paths

### Phase 3: Error Messages
- [ ] Audit error messages for absolute paths
- [ ] Standardize on project-relative format

### Phase 4: Optional Helper
- [ ] Implement `display_path()` utility if patterns warrant it

---

## Alternatives Considered

### Alternative A: Always Use Absolute Paths
- **Pro**: Unambiguous, good for copy-paste
- **Con**: Extremely noisy, poor scannability
- **Decision**: Rejected as default, use only for "navigate here" cases

### Alternative B: Make Path Format Configurable
- **Pro**: User choice
- **Con**: Adds complexity, inconsistent outputs
- **Decision**: Rejected - consistency is more valuable

### Alternative C: Use ~ for Home Directory
- **Pro**: Shorter than full absolute
- **Con**: Still noisy, not universally understood
- **Decision**: Rejected - short/relative is cleaner

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Debugging harder with short paths | Medium | Structured logs can include full path in debug mode |
| CI logs lack context | Low | CI mode could use absolute paths (future enhancement) |
| Breaking change for log parsers | Low | Structured log field names unchanged, just values shorter |

---

## Open Questions

1. **Should there be a `--verbose-paths` flag?** For cases where users want full paths in output.

2. **CI mode behavior?** Should CI environments automatically use absolute paths for better log context?

3. **Helper function scope?** Is a `display_path()` utility worth adding, or is inline formatting sufficient?

---

## Success Criteria

- [ ] All CLI warnings/info use short/relative paths
- [ ] Structured logs use T1-T2 paths by default
- [ ] No `/Users/` or `/home/` prefixes in normal output
- [ ] Error messages use project-relative paths
- [ ] Output paths are relative to project root

---

## References

- Evidence: `bengal/cli/helpers/site_loader.py:144-155` - Current warning implementation
- Evidence: `bengal/config/loader.py:135-140` - Config not found log
- Evidence: `bengal/output/core.py:267-275` - CLIOutput warning method

---

## Changelog

- **2025-12-21**: Initial draft


