---
title: Cross-Version Links
description: Link to specific documentation versions from any page
weight: 30
---

# Cross-Version Links

Bengal extends its `[[link]]` syntax to support **cross-version links**—links that point to a specific version of a page.

## Syntax

```markdown
[[version:path]]
[[version:path|Custom Text]]
[[version:path#anchor]]
```

## Examples

### Basic Cross-Version Link

```markdown
See the [[v2:docs/installation]] for the old setup process.
```

Renders as a link to `/docs/v2/installation/` with the page title as link text.

### With Custom Text

```markdown
Check the [[v2:docs/migration|v2 Migration Guide]] before upgrading.
```

Renders as a link to `/docs/v2/migration/` with text "v2 Migration Guide"

### With Anchor

```markdown
The [[v2:docs/api#authentication|v2 auth section]] explains the old flow.
```

Links to `/docs/v2/api/#authentication`.

### Using Aliases

You can use version aliases instead of IDs:

```markdown
[[latest:docs/guide]]    <!-- Links to latest version -->
[[stable:docs/api]]      <!-- Links to stable alias -->
[[lts:docs/security]]    <!-- Links to LTS alias -->
```

## Use Cases

### Migration Guides

When writing upgrade documentation, link to the old version for reference:

````markdown
# Upgrading from v2 to v3

## Breaking Changes

### Authentication

In v3, we switched from API keys to OAuth. See [[v2:docs/auth|v2 authentication docs]]
for the old approach.

**Before (v2):**
```python
client = Client(api_key="...")
```

**After (v3):**
```python
client = Client(oauth_token="...")
```
````

### Changelogs

Reference specific version documentation in your changelog:

```markdown
## v3.0.0

### Breaking Changes

- Removed `legacy_mode` option ([[v2:docs/config#legacy-mode|see v2 docs]])
- Changed default timeout from 30s to 60s

### New Features

- Added webhook support ([[latest:docs/webhooks|see docs]])
```

### Deprecation Notices

Point users to the new approach while documenting the old:

```markdown
:::{deprecated} v3.0
The `old_function()` is deprecated. See [[latest:docs/api#new-function]]
for the replacement.
:::
```

## Behavior

### Version Not Found

If the specified version doesn't exist, Bengal renders a broken reference indicator:

```markdown
[[v99:docs/guide]]
```

Renders as:

```html
<span class="broken-ref" data-ref="v99:docs/guide"
      title="Version not found: v99">[docs/guide]</span>
```

The `broken-ref` class allows styling via CSS, and the `title` attribute shows the error on hover.

### Page Not Found in Version

If the version exists but the page doesn't, Bengal still generates the link (it might be a valid page in that version's build).

### Latest Version Links

Links to the latest version use clean URLs without version prefix:

```markdown
[[latest:docs/guide]]  →  /docs/guide/  (not /docs/v3/guide/)
```

## Configuration

Cross-version links work automatically when versioning is enabled. No additional configuration needed.

```yaml
# bengal.yaml
versioning:
  enabled: true
  versions:
    - id: v3
      latest: true
    - id: v2
    - id: v1
  aliases:
    latest: v3
    stable: v3
    lts: v2
```

## Combining with Regular Links

You can mix cross-version links with regular links:

```markdown
## Related Documentation

- [[docs/installation]] — Current installation guide
- [[v2:docs/installation]] — v2 installation guide
- [[v1:docs/installation]] — v1 installation guide (deprecated)
```

## Tips

### Use for Upgrade Paths

Create a clear upgrade path by linking between versions:

```markdown
# v2 → v3 Migration

1. Review [[v2:docs/breaking-changes|v2 breaking changes]]
2. Update your config ([[v3:docs/config|v3 config reference]])
3. Test your integration
```

### Don't Overuse

Cross-version links are powerful but can clutter content. Use them primarily in:

- Migration guides
- Changelogs
- Deprecation notices
- Version comparison pages

For regular content, users expect links to stay within their current version.

## Next Steps

- [Version Directives](./directives.md) — Mark version-specific content
- [Versioning Overview](./_index.md) — Full versioning documentation
