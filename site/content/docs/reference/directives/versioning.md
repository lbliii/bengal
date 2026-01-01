---
title: Versioning Directives
description: Directives for marking version-specific documentation content
weight: 80
---

# Versioning Directives

Mark content as added, changed, or deprecated in specific versions. Use these directives to help users understand API evolution and migration paths.

## since

Marks content that was **added** in a specific version.

**Alias**: `{versionadded}`

### Syntax

```markdown
:::{since} v2.0
This feature was added in version 2.0.
:::
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| (argument) | `string` | **Required.** Version identifier (e.g., `v2.0`, `2.0`, `2024.1`) |
| `:class:` | `string` | Additional CSS class (default: `version-since`) |

### Examples

:::{example-label} Basic Usage
:::

```markdown
:::{since} v2.0
Webhooks allow real-time event notifications.
:::
```

:::{example-label} Inline Badge (No Content)
:::

```markdown
:::{since} v2.0
:::
```

:::{example-label} Inline in Tables
:::

```markdown
| Option | Description |
|--------|-------------|
| `retries` | Retry count :::{since} v3.1 ::: |
```

### Rendered Output

**Inline badge** (no content):
- Neumorphic badge with subtle shadow
- SVG sparkles icon
- Success/green theme colors

**Full directive** (with content):
- Left-edge accent border with palette-aware colors
- Subtle background blob animation
- Rounded container with badge header

---

## deprecated

Marks content that is **deprecated** and will be removed.

**Alias**: `{versionremoved}`

### Syntax

```markdown
:::{deprecated} v3.0
Use `new_function()` instead.
:::
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| (argument) | `string` | Version when deprecated. If omitted, displays "Deprecated" without version. |
| `:class:` | `string` | Additional CSS class (default: `version-deprecated`) |

### Examples

:::{example-label} Basic Usage
:::

```markdown
:::{deprecated} v3.0
This function is deprecated. Use `new_api()` instead.
:::
```

:::{example-label} With Migration Path
:::

```markdown
:::{deprecated} v3.0
The `legacy_mode` option is deprecated.

**Migration:**
1. Remove `legacy_mode: true` from config
2. Add `compatibility.version: 2`

See [[docs/migration|migration guide]] for details.
:::
```

:::{example-label} Without Version
:::

```markdown
:::{deprecated}
This feature is deprecated and will be removed.
:::
```

### Rendered Output

**Inline badge** (no content):
- Neumorphic badge with subtle shadow
- SVG alert triangle icon
- Warning/orange theme colors

**Full directive** (with content):
- Left-edge accent border with palette-aware colors
- Subtle background blob animation (warning colors)
- Rounded container with badge header

---

## changed

Marks content where **behavior changed** in a specific version.

**Alias**: `{versionchanged}`

### Syntax

```markdown
:::{changed} v2.5
Default timeout changed from 30s to 60s.
:::
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| (argument) | `string` | Version when changed. If omitted, displays "Changed" without version. |
| `:class:` | `string` | Additional CSS class (default: `version-changed`) |

### Examples

:::{example-label} Basic Usage
:::

```markdown
:::{changed} v2.5
The default batch size increased from 100 to 1000.
:::
```

:::{example-label} API Response Change
:::

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

:::{example-label} Without Version
:::

```markdown
:::{changed}
This behavior has been updated.
:::
```

### Rendered Output

**Inline badge** (no content):
- Neumorphic badge with subtle shadow
- SVG refresh icon
- Info/blue theme colors

**Full directive** (with content):
- Left-edge accent border with palette-aware colors
- Subtle background blob animation (info colors)
- Rounded container with badge header

---

## CSS Classes

All versioning directives use consistent CSS classes that integrate with Bengal's theme system:

```css
/* Container classes - full directive with content */
.version-directive { }        /* Base container with glow animation */
.version-directive-header { } /* Badge container */
.version-directive-content { } /* Content wrapper */

/* Type-specific containers */
.version-since { }            /* Success/green theme */
.version-deprecated { }       /* Warning/orange theme */
.version-changed { }          /* Info/blue theme */

/* Badge classes - inline badges */
.version-badge { }            /* Base neumorphic badge */
.version-badge-since { }      /* New in X.X badge */
.version-badge-deprecated { } /* Deprecated badge */
.version-badge-changed { }    /* Changed badge */
.version-badge-icon { }       /* SVG icon styling */
```

### Customizing Styles

Version directives use CSS custom properties for easy theming:

```css
/* Override colors for custom themes */
.version-since {
  --version-color: var(--color-success);
}

.version-deprecated {
  --version-color: var(--color-warning);
}

.version-changed {
  --version-color: var(--color-info);
}
```

Animation respects `prefers-reduced-motion`. For complete customization, see `assets/css/components/versioning.css` in the default theme.

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
