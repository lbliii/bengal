# Ink Theme

A minimalist, typography-focused theme for Bengal. Inspired by traditional ink-on-paper aesthetics, Japanese minimalism, and classic technical publishing.

## Philosophy

**"Content is the interface."**

Ink removes visual chrome to let your content breathe. Typography is the primary design element—every pixel serves readability.

## Features

- **Typography-first design** — Generous line heights, optimal reading width (65ch)
- **Minimal JavaScript** — ~2KB inline, optional search
- **Small CSS footprint** — ~10KB target
- **Light & dark modes** — System preference + manual toggle
- **Inline table of contents** — Collapsible, at the top of each doc
- **No sidebar** — Reduced cognitive load
- **Print-optimized** — Clean PDF output

## Design Tokens

### Colors

The palette is intentionally limited:

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `--color-text-primary` | `#1a1a1a` | `#f8f6f3` | Main text |
| `--color-text-secondary` | `#6b6b6b` | `#d6d5d2` | Secondary text |
| `--color-accent` | `#c24d2c` | `#e07b5f` | Links, highlights |
| `--color-bg-primary` | `#fdfcfa` | `#121211` | Page background |

### Typography

| Role | Font Stack |
|------|------------|
| Body | Charter, Georgia, serif |
| Headings | Newsreader, Georgia, serif |
| Code | SF Mono, JetBrains Mono, monospace |
| UI | System UI, sans-serif |

### Spacing

4px base scale: 4, 8, 12, 16, 24, 32, 48, 64, 80, 96

## Configuration

```yaml
# bengal.toml or config.yaml
theme: ink

[theme.features.navigation]
toc = true
prev_next = true
breadcrumbs = false
back_to_top = false

[theme.features.content]
code_copy = true
reading_time = true
lightbox = false
```

## Templates (Kida-Native)

All templates use **Kida**, Bengal's native template engine, taking full advantage of its unique features.

### Kida Features Used

| Feature | Example | Description |
|---------|---------|-------------|
| **Multi-let** | `{% let a = 1, b = 2, c = 3 %}` | Group related variable assignments |
| **Tuple unpacking** | `{% let (x, y) = (a, b) %}` | Destructure values |
| **Optional chaining** `?.` | `page?.metadata?.author` | Safe nested access, returns `None` if any part is missing |
| **Null coalescing** `??` | `title ?? 'Untitled'` | Fallback value when left side is `None` |
| **Pipeline operator** `\|>` | `posts \|> where('draft', false) \|> sort(...)` | Left-to-right filter chains |
| **Pattern matching** | `{% match x %}{% case y %}...{% end %}` | Clean conditional logic |
| **Unified endings** | `{% end %}` | Single ending for all blocks |
| **Fragment caching** | `{% cache "key" %}...{% end %}` | Cache expensive operations |
| **Spaceless** | `{% spaceless %}...{% end %}` | Remove whitespace in output |
| **Loop control** | `{% break %}`, `{% continue %}` | Control loop execution |
| **Tests** | `x is defined`, `x is none` | Built-in condition tests |

### Example: Pipeline vs Traditional

```kida
{# Kida: Read left-to-right (natural) #}
{% let posts = pages_by_section('blog')
    |> where('draft', false)
    |> sort(attribute='date', reverse=true)
    |> take(5) %}

{# Jinja2: Read inside-out (awkward) #}
{% let posts = pages_by_section('blog')
    | selectattr('draft', 'false')
    | sort(attribute='date', reverse=true)
    | first(5) %}
```

### Example: Multi-let + Optional Chaining + Null Coalescing

```kida
{# Multi-let groups related variables together #}
{% let
    _site_title = config?.title ?? 'Untitled Site',
    _page_title = page?.title ?? config?.title ?? 'Page',
    _description = page?.description ?? config?.description ?? '',
    _favicon = config?.site?.favicon %}

{# Multi-let for navigation #}
{% let
    _prev = get_prev_page(page),
    _next = get_next_page(page),
    _has_nav = _prev is defined or _next is defined %}

{# Pattern matching for conditional display #}
{% match _prev %}
{% case prev if prev is defined %}
<a href="{{ prev._path | absolute_url }}">{{ prev?.title ?? 'Previous' }}</a>
{% case _ %}
{# No previous page #}
{% end %}
```

### Templates

| Template | Purpose | Kida Features Used |
|----------|---------|-------------------|
| `base.html` | Root layout | `?.`, `??`, `{% match %}`, `{% spaceless %}` |
| `home.html` | Landing page | `??`, `{% match %}`, `\|>` for featured posts |
| `page.html` | Generic page | `?.`, `??`, `{% match %}` |
| `doc/single.html` | Docs with TOC | `?.`, `??`, `{% match %}`, `{% spaceless %}` |
| `post.html` | Blog post | `?.`, `??`, `{% match %}`, `~` concatenation |
| `blog/list.html` | Blog listing | `\|>` pipeline, `{% continue %}` |
| `search.html` | Search page | `??`, `{% cache %}` |

## CSS Architecture

```
assets/css/
├── style.css              # Main entry point with @layer
└── tokens/
    ├── foundation.css     # Primitives (colors, spacing, type)
    └── semantic.css       # Purpose-based tokens
```

Uses CSS Layers for cascade control: `@layer tokens, base, components;`

## Customization

### Override Accent Color

```css
:root {
  --vermillion-500: #your-color;
  --color-accent: var(--vermillion-500);
}
```

### Change Display Font

```css
:root {
  --font-display: 'Your Font', Georgia, serif;
  --font-heading: var(--font-display);
}
```

### Extend Styles

Create `static/css/custom.css` and add to your config:

```yaml
[theme]
custom_css = ["css/custom.css"]
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Uses modern CSS: `clamp()`, CSS Layers, `:focus-visible`, logical properties.

## Performance

| Metric | Target |
|--------|--------|
| CSS | <10KB gzipped |
| JS | <3KB inline |
| LCP | <1.5s |
| CLS | 0 |

## Credits

Design inspired by:
- [Minimalist Hugo Theme](https://github.com/ronv/minimalist)
- [Sphinx Alabaster](https://alabaster.readthedocs.io/)
- [Tufte CSS](https://edwardtufte.github.io/tufte-css/)
- Traditional Japanese woodblock prints

## License

MIT — Same as Bengal
