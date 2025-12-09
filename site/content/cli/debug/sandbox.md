---
title: "debug sandbox"
type: "cli-reference"
description: "🧪 Test shortcodes/directives in isolation without building the site."
weight: 50
params:
  css_class: "api-content"
  source_file: "bengal/cli/commands/debug.py"
---

# debug sandbox

**Type:** Command  
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/cli/commands/debug.py)

:::{badge} Command
:class: badge-secondary
:::

**Command:** `bengal debug sandbox`

🧪 Test shortcodes/directives in isolation.

Renders directives without building the entire site, useful for testing and debugging directive syntax before adding to content. Validates syntax, detects typos in directive names, and shows rendered output.

## Usage

```bash
bengal debug sandbox [OPTIONS] [CONTENT]
```

## Arguments

### `content` (optional)

Directive/shortcode content to test. Use escaped newlines (`\n`) for multi-line content from the command line.

## Options

### `--file PATH`

Read content from a file instead of command line argument.

### `--validate-only`

Only validate syntax without rendering. Faster for quick syntax checks.

### `--list-directives`

List all available directives with descriptions.

### `--help-directive NAME`

Get detailed help for a specific directive.

### `--format [console|html|json]`

Output format. Default is `console`.

- **console**: Human-readable output with status
- **html**: Raw HTML output
- **json**: JSON output for programmatic use

## Examples

### Test a note directive

```bash
bengal debug sandbox '```{note}\nThis is a test note.\n```'
```

### Test from a file

Create `test-directive.md`:
```markdown
```{tabs}

```{tab} Tab 1
Content for tab 1.
```

```{tab} Tab 2
Content for tab 2.
```

```
```

Then test:
```bash
bengal debug sandbox --file test-directive.md
```

### List available directives

```bash
bengal debug sandbox --list-directives
```

Output shows all ~40 available directives organized by type.

### Get help for a directive

```bash
bengal debug sandbox --help-directive tabs
```

### Validate syntax only

```bash
bengal debug sandbox --validate-only '```{note}\nTest\n```'
```

### Get JSON output

```bash
bengal debug sandbox --format json '```{tip}\nA tip!\n```'
```

## Validation Features

### Typo Detection

The sandbox detects typos in directive names and suggests corrections:

```bash
bengal debug sandbox '```{nots}\nTypo!\n```'
```

Output:
```
❌ Invalid syntax
   Unknown directive: nots
   💡 Did you mean: note?
```

### Syntax Validation

Checks for common syntax errors:

- Missing closing fence (`\`\`\``)
- Unknown directive names
- Invalid directive options

## Use Cases

### Testing New Directives

Before adding a complex directive to your content:

```bash
bengal debug sandbox '```{code-tabs}
```python
print("Hello")
```
```javascript
console.log("Hello");
```
```'
```

### Debugging Directive Issues

When a directive isn't rendering correctly:

1. Extract just the directive from your content
2. Test it in isolation
3. Check for syntax errors or typos

### Learning Available Directives

```bash
# See all directives
bengal debug sandbox --list-directives

# Get detailed help
bengal debug sandbox --help-directive dropdown
```

### CI Integration

Validate directive syntax in CI:

```bash
# Fails if syntax is invalid
bengal debug sandbox --validate-only --format json '```{note}\nTest\n```' | jq -e '.success'
```

## Output

### Successful Render

```
🧪 Shortcode Sandbox

✅ Rendered successfully
   Directive: note
   Time: 2.34ms

Output HTML:
<div class="admonition note">
<p>This is a test note.</p>
</div>
```

### Validation Error

```
🧪 Shortcode Sandbox

❌ Invalid syntax
   Unknown directive: unknowndirective
   💡 Did you mean: note, tip, warning?
```

## Available Directives

Run `bengal debug sandbox --list-directives` to see all available directives. Common ones include:

| Category | Directives |
|----------|------------|
| **Admonitions** | `note`, `tip`, `warning`, `danger`, `error`, `info`, `example`, `success`, `caution`, `seealso` |
| **Layout** | `tabs`, `tab-set`, `tab-item`, `dropdown`, `container` |
| **Cards** | `cards`, `card`, `child-cards`, `grid`, `grid-item-card` |
| **Code** | `code-tabs`, `literalinclude` |
| **Content** | `badge`, `button`, `checklist`, `steps`, `step`, `rubric` |
| **Data** | `list-table`, `data-table`, `glossary` |
| **Navigation** | `breadcrumbs`, `siblings`, `prev-next`, `related` |
| **Include** | `include`, `literalinclude` |

## Related Commands

- [`bengal debug deps`](/cli/debug/deps/) - Visualize dependencies
- [`bengal explain`](/cli/explain/) - Explain how a page is built
- [`bengal validate`](/cli/validate/) - Validate site content

## See Also

- [Directives Reference](/docs/authoring/directives/) - Full directive documentation
- [Shortcode Syntax](/docs/authoring/shortcodes/) - Shortcode usage guide
