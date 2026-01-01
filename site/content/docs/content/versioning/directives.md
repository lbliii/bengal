---
title: Version Directives
description: Mark content as added, deprecated, or changed in specific versions
weight: 40
---

# Version Directives

Bengal provides three directives for marking version-specific content:

| Directive | Purpose | Rendered As |
|-----------|---------|-------------|
| `:::{since}` | Feature added in version X | New in X |
| `:::{deprecated}` | Feature deprecated in version X | Deprecated since X |
| `:::{changed}` | Behavior changed in version X | Changed in X |

Each directive renders with an SVG icon and themed styling using CSS classes.

## Since Directive

Marks content that was **added** in a specific version.

### Syntax

```markdown
:::{since} v2.0
This feature was added in version 2.0.
:::
```

### Rendered Output

<div class="version-directive version-since">
  <div class="version-directive-header">
    <span class="version-badge version-badge-since">New in v2.0</span>
  </div>
  <div class="version-directive-content">
    <p>This feature was added in version 2.0.</p>
  </div>
</div>

### Use Cases

Document new features:

```markdown
## Webhooks

:::{since} v2.5
Webhooks allow you to receive real-time notifications when events occur.
:::

To configure webhooks:
1. Go to Settings → Webhooks
2. Add your endpoint URL
3. Select events to subscribe to
```

Mark new parameters:

```markdown
### Parameters

| Name | Type | Description |
|------|------|-------------|
| `timeout` | `int` | Request timeout in seconds |
| `retries` | `int` | Number of retries :::{since} v2.1 ::: |
```

## Deprecated Directive

Marks content that is **deprecated** and will be removed in a future version.

### Syntax

```markdown
:::{deprecated} v3.0
Use `new_function()` instead. This will be removed in v4.0.
:::
```

### Rendered Output

<div class="version-directive version-deprecated">
  <div class="version-directive-header">
    <span class="version-badge version-badge-deprecated">Deprecated since v3.0</span>
  </div>
  <div class="version-directive-content">
    <p>Use <code>new_function()</code> instead. This will be removed in v4.0.</p>
  </div>
</div>

### Use Cases

Deprecate a function:

````markdown
## old_function()

:::{deprecated} v3.0
This function is deprecated. Use [[docs/api#new-function|new_function()]] instead.
:::

```python
# Don't use this
result = old_function(data)

# Use this instead
result = new_function(data)
```
````

Deprecate a configuration option:

````markdown
### legacy_mode

:::{deprecated} v2.5
The `legacy_mode` option is deprecated and will be removed in v3.0.
Migrate to the new configuration format.
:::

```yaml
# Deprecated
legacy_mode: true

# New approach
compatibility:
  version: 2
```
````

## Changed Directive

Marks content where **behavior changed** in a specific version.

### Syntax

```markdown
:::{changed} v2.5
Default timeout changed from 30 seconds to 60 seconds.
:::
```

### Rendered Output

<div class="version-directive version-changed">
  <div class="version-directive-header">
    <span class="version-badge version-badge-changed">Changed in v2.5</span>
  </div>
  <div class="version-directive-content">
    <p>Default timeout changed from 30 seconds to 60 seconds.</p>
  </div>
</div>

### Use Cases

Document behavior changes:

```markdown
## Configuration

### timeout

The request timeout in seconds.

:::{changed} v2.5
Default changed from 30 to 60 seconds for better reliability with slow networks.
:::

**Default:** 60 seconds
```

Document API changes:

````markdown
## Response Format

:::{changed} v3.0
The response now includes a `metadata` field with additional information.
:::

```json
{
  "data": [...],
  "metadata": {    // New in v3.0
    "total": 100,
    "page": 1
  }
}
```
````

## Inline Usage

All directives can be used inline for brief annotations:

```markdown
| Option | Default | Description |
|--------|---------|-------------|
| `timeout` | 60s | Request timeout :::{changed} v2.5 was 30s ::: |
| `retries` | 3 | Retry count :::{since} v2.0 ::: |
| `legacy` | false | Legacy mode :::{deprecated} v3.0 ::: |
```

## Without Version Number

The `deprecated` and `changed` directives support omitting the version number for generic notices:

```markdown
:::{deprecated}
This feature is deprecated.
:::

:::{changed}
This behavior has changed.
:::
```

:::{note}
The `since` directive requires a version number. Without one, no output is rendered.
:::

## Styling

Each directive renders with an inline SVG icon and themed styling. The directives use CSS classes you can customize:

```css
/* Since directive - success/green theme */
.version-since {
  --version-color: var(--color-success);
  background-color: var(--color-success-bg);
}

/* Deprecated directive - warning/orange theme */
.version-deprecated {
  --version-color: var(--color-warning);
  background-color: var(--color-warning-bg);
}

/* Changed directive - info/blue theme */
.version-changed {
  --version-color: var(--color-info);
  background-color: var(--color-info-bg);
}
```

Badges include Lucide-style SVG icons (`.version-badge-icon`) that inherit the theme color via `currentColor`. Full directive containers (when content is provided) feature a luminescent glow animation and neumorphic styling.

## Combining Directives

You can combine directives for comprehensive version history:

```markdown
## process_data()

:::{since} v1.0
Core data processing function.
:::

:::{changed} v2.0
Added support for streaming data.
:::

:::{changed} v2.5
Default batch size increased from 100 to 1000.
:::

Processes data with automatic batching and retry logic.
```

## Best Practices

### Be Specific

❌ **Vague:**
```markdown
:::{changed} v2.0
This was changed.
:::
```

✅ **Specific:**
```markdown
:::{changed} v2.0
Return type changed from `list` to `iterator` for memory efficiency.
:::
```

### Include Migration Path

For deprecations, always explain what to use instead:

```markdown
:::{deprecated} v3.0
Use `new_api()` instead. See the [[docs/migration|migration guide]] for details.
:::
```

### Don't Overuse

Version directives are most valuable for:
- Breaking changes
- New major features
- Deprecations

Don't annotate every minor change—it creates noise.

## Next Steps

- [Cross-Version Links](./cross-version-links.md) — Link between versions
- [Folder Mode](./folder-mode.md) — Set up folder-based versioning
- [Git Mode](./git-mode.md) — Set up git-based versioning
