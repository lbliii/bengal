---
title: Versioning Directives
description: Directives for marking version-specific documentation content
weight: 80
---

# Versioning Directives

Mark content as added, changed, or deprecated in specific versions.

## since

Marks content that was **added** in a specific version.

### Syntax

```markdown
:::{since} v2.0
This feature was added in version 2.0.
:::
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| (argument) | `string` | Version identifier (e.g., `v2.0`, `2.0`, `2024.1`) |

### Examples

**Basic usage:**

```markdown
:::{since} v2.0
Webhooks allow real-time event notifications.
:::
```

**Without version (generic):**

```markdown
:::{since}
This is a recent addition.
:::
```

**Inline in tables:**

```markdown
| Option | Description |
|--------|-------------|
| `retries` | Retry count :::{since} v2.0 ::: |
```

### Rendered Output

Renders with Bengal's theme aesthetic:

**Inline badge** (no content):
- Neumorphic badge styling
- SVG sparkles icon
- Success/green theme colors

**Full directive** (with content):
- Luminescent left-edge glow animation
- Palette-aware blob background
- Rounded container with badge header

---

## deprecated

Marks content that is **deprecated** and will be removed.

### Syntax

```markdown
:::{deprecated} v3.0
Use `new_function()` instead.
:::
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| (argument) | `string` | Version when deprecated (e.g., `v3.0`) |

### Examples

**Basic usage:**

```markdown
:::{deprecated} v3.0
This function is deprecated. Use `new_api()` instead.
:::
```

**With migration path:**

```markdown
:::{deprecated} v3.0
The `legacy_mode` option is deprecated.

**Migration:**
1. Remove `legacy_mode: true` from config
2. Add `compatibility.version: 2`

See [[docs/migration|migration guide]] for details.
:::
```

**Without version:**

```markdown
:::{deprecated}
This feature is deprecated and will be removed.
:::
```

### Rendered Output

Renders with Bengal's theme aesthetic:

**Inline badge** (no content):
- Neumorphic badge styling
- SVG alert triangle icon
- Warning/orange theme colors

**Full directive** (with content):
- Luminescent left-edge glow animation
- Palette-aware blob background (warning colors)
- Rounded container with badge header

---

## changed

Marks content where **behavior changed** in a specific version.

### Syntax

```markdown
:::{changed} v2.5
Default timeout changed from 30s to 60s.
:::
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| (argument) | `string` | Version when changed (e.g., `v2.5`) |

### Examples

**Basic usage:**

```markdown
:::{changed} v2.5
The default batch size increased from 100 to 1000.
:::
```

**API response change:**

```markdown
:::{changed} v3.0
Response now includes a `metadata` field:

```json
{
  "data": [...],
  "metadata": { "total": 100, "page": 1 }
}
```
:::
```

**Without version:**

```markdown
:::{changed}
This behavior has been updated.
:::
```

### Rendered Output

Renders as an info admonition:

- Badge text: "📝 Changed in v2.5"
- Background: Info/blue theme
- Icon: Memo emoji

---

## CSS Classes

All versioning directives use consistent CSS classes:

```css
/* Container classes */
.version-directive { }
.version-since { }
.version-deprecated { }
.version-changed { }

/* Badge classes */
.version-badge { }
.since-badge { }
.deprecated-badge { }
.changed-badge { }
```

### Customizing Styles

Override in your theme CSS:

```css
/* Custom since styling */
.version-since {
  background-color: #d4edda;
  border-left: 4px solid #28a745;
}

/* Custom deprecated styling */
.version-deprecated {
  background-color: #fff3cd;
  border-left: 4px solid #ffc107;
}

/* Custom changed styling */
.version-changed {
  background-color: #cce5ff;
  border-left: 4px solid #007bff;
}
```

---

## Best Practices

### Be Specific

Include details about what changed:

```markdown
<!-- ❌ Vague -->
:::{changed} v2.0
This was updated.
:::

<!-- ✅ Specific -->
:::{changed} v2.0
Return type changed from `list[dict]` to `Iterator[dict]`
for improved memory efficiency with large datasets.
:::
```

### Include Migration Paths

For deprecations, explain the alternative:

```markdown
:::{deprecated} v3.0
`old_function()` is deprecated.

**Use instead:**
```python
from mylib import new_function
result = new_function(data)
```

See [[docs/api#new-function]] for details.
:::
```

### Use Sparingly

Version directives are most valuable for:

- ✅ Breaking changes
- ✅ Major new features
- ✅ Deprecations with removal timeline
- ✅ Significant behavior changes

Avoid for:
- ❌ Minor bug fixes
- ❌ Internal changes
- ❌ Every small addition

---

## Related

- [[/docs/content/versioning|Versioning Documentation]] — Full versioning guide
- [[/docs/content/versioning/cross-version-links|Cross-Version Links]] — Link between versions
- [Admonitions](admonitions.md) — Standard callout directives
