# RFC: Inline Version Directories

**Status**: Draft  
**Created**: 2025-12-21  
**Author**: AI Assistant  
**Subsystem**: Discovery, Core, Versioning

---

## Summary

Refactor versioned content storage from top-level `_versions/<id>/<section>/` to inline `<section>/_v<id>/` structure. This places version content adjacent to its section, simplifying path transforms and improving content authoring UX.

---

## Problem Statement

### Current Structure
```
content/
  _versions/
    v1/
      docs/
        about/
          _index.md
        guide.md
    v2/
      docs/
        about/
          _index.md
  docs/              # latest (v3)
    about/
      _index.md
    guide.md
```

### Issues with Current Approach

1. **Content scattered** - Version content is far from the section it belongs to
2. **Complex path transforms** - `_versions/v1/docs/about` → `docs/v1/about` requires parsing and restructuring
3. **Poor authoring UX** - Hard to compare versions or find related content
4. **Unintuitive git history** - Changes to "docs" are split between `docs/` and `_versions/*/docs/`
5. **Multi-module complexity** - Section discovery must filter `_versions/` at root level

---

## Proposed Solution

### New Structure
```
content/
  docs/
    _v1/             # Version v1 content
      about/
        _index.md
      guide.md
    _v2/             # Version v2 content  
      about/
        _index.md
    about/           # Latest (v3)
      _index.md
    guide.md
```

### Key Changes

1. **Version directories use `_v<id>/` naming** inside each section
2. **Latest version** stays at section root (no prefix)
3. **Simple path transform** - `docs/_v1/about` → `docs/v1/about` (strip underscore)
4. **Content proximity** - All versions of a section are adjacent

---

## Design Details

### Directory Naming Convention

| Pattern | Meaning | Example |
|---------|---------|---------|
| `_v<id>/` | Specific version | `_v1/`, `_v2/`, `_v2.1/` |
| `_versions/<id>/` | Alternative (for clarity) | `_versions/v1/` |
| No prefix | Latest version | `docs/guide.md` |

Both `_v<id>/` and `_versions/<id>/` should be supported for flexibility.

### Path Transformation

**Before (current):**
```
_versions/v1/docs/about/_index.md → docs/v1/about/index.html
```

**After (proposed):**
```
docs/_v1/about/_index.md → docs/v1/about/index.html
```

Transformation is simpler:
1. Detect `/_v<id>/` or `/_versions/<id>/` in path
2. Strip the underscore prefix
3. Done (section already in correct position)

### Configuration

```yaml
# bengal.yaml
versioning:
  enabled: true
  versions:
    - id: v3
      latest: true
    - id: v2
    - id: v1
  sections:
    - docs      # Versioned section
    - api       # Another versioned section
  # Optional: directory pattern (default: _v<id>)
  directory_pattern: "_v{id}"  # or "_versions/{id}"
```

### Section Discovery Changes

**Current logic:**
```python
# In content discovery
if section.name == "_versions":
    skip_section()  # Handle specially at root
```

**Proposed logic:**
```python
# In content discovery
def is_version_directory(name: str) -> bool:
    """Check if directory is a version directory."""
    if name.startswith("_v"):
        return True
    if name == "_versions":
        # Check if parent is in versioned sections
        return True
    return False

# Skip version directories in normal section walk
if is_version_directory(section.name):
    handle_version_content()
```

### URL Generation

**Section `_path` property:**
```python
def _apply_version_path_transform(self, url: str) -> str:
    """Transform _v<id> to proper versioned URL."""
    # Match /_v<id>/ or /_versions/<id>/
    import re

    # Pattern: /<section>/_v<id>/... or /<section>/_versions/<id>/...
    match = re.match(r'^(/[^/]+)/_v(\d+(?:\.\d+)?)/(.*)$', url)
    if match:
        section, version_id, rest = match.groups()
        version_obj = self._get_version(version_id)
        if version_obj and version_obj.latest:
            return f"{section}/{rest}"
        return f"{section}/{version_id}/{rest}"

    # Also support _versions/<id>/ format
    match = re.match(r'^(/[^/]+)/_versions/([^/]+)/(.*)$', url)
    if match:
        section, version_id, rest = match.groups()
        version_obj = self._get_version(version_id)
        if version_obj and version_obj.latest:
            return f"{section}/{rest}"
        return f"{section}/{version_id}/{rest}"

    return url
```

---

## Migration Path

### Phase 1: Support Both Structures
1. Update `VersionResolver` to detect both patterns
2. Update `ContentDiscovery` to handle both
3. Update path transforms in `Section._path` and `URLStrategy`

### Phase 2: Documentation & Tooling
1. Add migration script: `bengal migrate-versions`
2. Update documentation
3. Deprecation warnings for old structure

### Phase 3: Remove Old Structure (Future)
1. Remove support for top-level `_versions/` after deprecation period

---

## Affected Components

### Core Changes

| File | Change |
|------|--------|
| `bengal/discovery/version_resolver.py` | Detect `_v<id>/` directories under sections |
| `bengal/discovery/content_discovery.py` | Skip version dirs in normal section walk |
| `bengal/core/section.py` | Simpler `_apply_version_path_transform()` |
| `bengal/utils/url_strategy.py` | Simpler path transform for pages |
| `bengal/core/page/metadata.py` | Update version detection logic |

### Configuration Changes

| File | Change |
|------|--------|
| `bengal/config/version.py` | Add `directory_pattern` option |

### Template Changes

None required - templates use `page.href` and `section.href` which will work correctly.

---

## Example: Multi-Section Versioning

```
content/
  docs/
    _v1/
      getting-started.md
    _v2/
      getting-started.md
    getting-started.md      # v3 (latest)

  api/
    _v1/                    # API is on different version cadence
      reference.md
    _v2/
      reference.md
    reference.md            # v3 (latest)
```

This structure naturally supports:
- Different sections at different versions
- Independent version histories
- Easy content comparison

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing sites | Phase 1 supports both structures |
| Complex regex matching | Comprehensive test suite |
| Performance impact | Minimal - directory detection is O(1) |
| Git history disruption | Migration script preserves history with `git mv` |

---

## Alternatives Considered

### 1. Keep Current Structure
- **Rejected**: Complex path transforms, poor authoring UX

### 2. Use `.v1/` (dot prefix)
- **Rejected**: Hidden directories cause confusion, some editors hide them

### 3. Use `v1/` (no prefix)
- **Rejected**: Ambiguous with regular content directories

### 4. Use `@v1/` (at prefix)
- **Rejected**: Some filesystems/tools have issues with `@`

---

## Success Criteria

1. ✅ Versioned content lives under its section
2. ✅ Path transform is ≤3 lines of code
3. ✅ Existing sites can migrate without content changes (just directory moves)
4. ✅ Both `_v<id>/` and `_versions/<id>/` patterns supported
5. ✅ All existing tests pass
6. ✅ New tests cover inline version directories

---

## Tasks

### Phase 1: Core Support (Required)

- [ ] 1.1 Update `VersionResolver.get_version_for_path()` to detect `<section>/_v<id>/`
- [ ] 1.2 Update `ContentDiscovery` to skip `_v<id>` directories in normal section walk
- [ ] 1.3 Simplify `Section._apply_version_path_transform()` for inline pattern
- [ ] 1.4 Update `URLStrategy._apply_version_path_transform()` for inline pattern
- [ ] 1.5 Add tests for inline version directory detection
- [ ] 1.6 Add integration tests with new structure

### Phase 2: Migration (Optional)

- [ ] 2.1 Create `bengal migrate-versions` CLI command
- [ ] 2.2 Add deprecation warning for old structure
- [ ] 2.3 Update documentation

---

## Appendix: Migration Script Logic

```python
def migrate_versions(site_root: Path, dry_run: bool = True):
    """
    Migrate from _versions/v1/docs/ to docs/_v1/ structure.

    Uses git mv to preserve history.
    """
    versions_dir = site_root / "content" / "_versions"
    if not versions_dir.exists():
        print("No _versions/ directory found")
        return

    for version_dir in versions_dir.iterdir():
        if not version_dir.is_dir():
            continue

        version_id = version_dir.name  # e.g., "v1"

        for section_dir in version_dir.iterdir():
            if not section_dir.is_dir():
                continue

            section_name = section_dir.name  # e.g., "docs"
            target = site_root / "content" / section_name / f"_v{version_id}"

            print(f"Moving {section_dir} → {target}")
            if not dry_run:
                subprocess.run(["git", "mv", str(section_dir), str(target)])
```

---

## References

- Current versioning implementation: `bengal/discovery/version_resolver.py`
- URL strategy: `bengal/utils/url_strategy.py`
- Section model: `bengal/core/section.py`
- Related: Hugo's module system, Docusaurus versioning
