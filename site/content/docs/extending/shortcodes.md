---
title: Template Shortcodes
description: Create template-only embeds without writing Python
weight: 35
---

Shortcodes are template-based content components you can add without writing Python. Place a Kida template in `templates/shortcodes/` and call it from Markdown using Hugo-compatible syntax.

## When to Use Shortcodes vs Directives

| Criterion | Shortcode (template) | Directive (Python) |
|-----------|----------------------|--------------------|
| **Implementation** | Kida template file | Python class |
| **Location** | `templates/shortcodes/name.html` | `bengal/.../directives/builtins/` |
| **Validation** | Template conditionals only | Regex, typed options |
| **Who can add** | Content/template authors | Developers |

**Choose a shortcode when:**

- Output is simple HTML from args (styled blockquote, custom figure)
- No strict validation needed (e.g., "any URL" iframe)
- You want non-developers to add or customize it
- You want to override without touching code

**Choose a directive when:**

- You need validation (YouTube 11-char ID, Spotify 22-char ID)
- You need computed URLs, privacy mode, or complex options
- You need parent-child nesting (e.g., `:::{step}` inside `:::{steps}`)
- You want structured errors and build-time safety

See [Custom Directives](/docs/extending/custom-directives/) for the Python path.

## Notation: Markdown vs Standard

Shortcodes support two notations that control how inner content is processed:

| Notation | Example | Inner content |
|----------|---------|---------------|
| **Standard** | `{{< name args >}}`...`{{< /name >}}` | Passed raw to template |
| **Markdown** | `{{% name args %}}`...`{{% /name %}}` | Parsed as Markdown first |

Use **Markdown notation** when inner content should support formatting (e.g. `**bold**`, `[links](url)`):

```markdown
{{% blockquote author="Jane" %}}
The only way to do great work is to **love** what you do.
{{% /blockquote %}}
```

Use **standard notation** when inner content should stay as-is (e.g. raw HTML or code):

```markdown
{{< highlight lang=python >}}
def hello(): print("world")
{{< /highlight >}}
```

## Creating a Shortcode

1. Create a template at `templates/shortcodes/<name>.html`
2. Use it in content with `{{< name args >}}` or `{{< name >}}content{{< /name >}}`

### Self-Closing Shortcodes

For shortcodes without inner content:

```html
{# templates/shortcodes/audio.html #}
{% set src = shortcode.Get("src") %}
{% if src %}<audio controls preload="auto" src="{{ src }}"></audio>{% end %}
```

In content:

```markdown
{{< audio src=/audio/test.mp3 >}}
```

### Paired Shortcodes

For shortcodes with inner content:

```html
{# templates/shortcodes/blockquote.html #}
<blockquote class="blockquote">
  {{- shortcode.Inner -}}
  {% set author = shortcode.Get("author") %}
  {% if author %}<footer>— {{ author }}</footer>{% end %}
</blockquote>
```

In content (use `{{% %}}` for Markdown in inner content):

```markdown
{{% blockquote author="Jane Doe" %}}
The only way to do great work is to **love** what you do.
{{% /blockquote %}}
```

## Shortcode Context

Templates receive a `shortcode` object with Hugo-compatible methods:

| Property | Description |
|----------|-------------|
| `shortcode.Get("key")` | Get named argument |
| `shortcode.Get(0)` | Get positional argument (0-indexed) |
| `shortcode.GetInt("key", 0)` | Get argument as int |
| `shortcode.GetBool("key", false)` | Get argument as bool (true/false, 1/0) |
| `shortcode.Inner` | Inner content (paired shortcodes only) |
| `shortcode.InnerDeindent` | Inner with leading indentation stripped |
| `shortcode.IsNamedParams` | True if named args were used |
| `shortcode.Params` | All params as dict or list |
| `shortcode.Ref("path")` | Resolve content path to absolute URL |
| `shortcode.RelRef("path")` | Resolve content path to relative URL |
| `shortcode.Parent` | Parent shortcode context when nested (or None) |

You also have `page`, `site`, and `config` in context. Use `page.HasShortcode("name")` in layouts to check if a page uses a given shortcode (e.g. to conditionally load CSS).

## Arguments

**Named arguments:**

```markdown
{{< figure src=/images/cat.jpg alt="A cat" caption="Photo by Jane" >}}
```

**Positional arguments:**

```markdown
{{< audio /audio/podcast.mp3 >}}
```

Arguments with spaces must be quoted:

```markdown
{{< blockquote author="Jane Doe" >}}Quote{{< /blockquote >}}
```

## Subdirectory Shortcodes

Organize shortcodes in subdirectories:

```
templates/shortcodes/
├── media/
│   ├── audio.html
│   └── video.html
└── blockquote.html
```

Call with the path relative to `shortcodes/`:

```markdown
{{< media/audio src=/audio/test.mp3 >}}
```

## Built-in Shortcodes

The default theme ships with these shortcodes. Override any by placing a template with the same name in your project's `templates/shortcodes/`.

| Shortcode | Usage | Purpose |
|-----------|-------|---------|
| `audio` | `{{< audio src=/path.mp3 >}}` | HTML5 audio player |
| `blockquote` | `{{% blockquote author="Name" %}}Quote{{% /blockquote %}}` | Styled blockquote with attribution |
| `figure` | `{{< figure src=/img.jpg alt="..." caption="..." >}}` | Image with optional caption and link |
| `details` | `{{% details summary="Click" %}}Content{{% /details %}}` | Collapsible `<details>` |
| `highlight` | `{{< highlight lang=python >}}code{{< /highlight >}}` | Code block with language class |
| `param` | `{{< param "key" >}}` | Insert config or frontmatter value |
| `tip` | `{{% tip %}}Hint{{% /tip %}}` | Tip callout box |
| `warning` | `{{% warning %}}Caution{{% /warning %}}` | Warning callout box |
| `danger` | `{{% danger %}}Critical{{% /danger %}}` | Danger callout box |
| `ref` | `{{< ref "docs/guide/intro" >}}` | Internal page link (absolute URL) |
| `relref` | `{{< relref "docs/guide/intro" >}}` | Internal page link (relative URL) |

## Strict Mode

Configure in `bengal.toml`:

```toml
[shortcodes]
strict = true
```

Or in `config/_default/site.yaml`:

```yaml
shortcodes:
  strict: true
```

When enabled, the build fails when:
- An unknown shortcode is used (no template found)
- A shortcode template fails to render

Useful for CI and catching typos early.

## Discoverability

List available shortcodes:

```bash
bengal shortcodes list
```

## Shortcode Cookbook

Copy-paste snippets for common patterns.

### Conditional CSS in base layout

```html
{% if page.HasShortcode("audio") %}
  <link rel="stylesheet" href="/css/audio-player.css">
{% end %}
```

### Nested shortcode with parent

```html
{# templates/shortcodes/img.html — used inside gallery #}
{% set cls = shortcode.Parent.Get("class") if shortcode.Parent else "" %}
<img src="{{ shortcode.Get('src') }}"{% if cls %} class="{{ cls }}"{% end %}>
```

### Internal link with custom text

```markdown
{{< ref "docs/guide/intro" text="Get started" >}}
```

### Typed arguments

```html
{% set cols = shortcode.GetInt("cols", 3) %}
<div class="grid grid-cols-{{ cols }}">
  {{ shortcode.Inner }}
</div>
```

## Related

- [Custom Directives](/docs/extending/custom-directives/) — Python-based directives with validation
- [Theme Customization](/docs/extending/theme-customization/) — Override templates
- [Kida Syntax](/docs/theming/templating/kida/syntax/) — Template language reference
