# Autodoc Partials

Reusable template partials for the unified autodoc HTML skeleton.
These partials work across all autodoc types: Python API, CLI, and OpenAPI.

## Usage

Include partials in your autodoc templates:

```jinja
{% include 'autodoc/partials/header.html' %}
{% include 'autodoc/partials/params-table.html' %}
```

Or import macros:

```jinja
{% from 'autodoc/partials/_macros/class-member.html' import class_member %}
{% from 'autodoc/partials/_macros/function-member.html' import function_member %}
{{ class_member(cls, is_first=loop.first) }}
{{ function_member(func, is_first=loop.first) }}
```

## Available Macros (_macros/)

| Macro | Purpose | Args |
|-------|---------|------|
| `class-member.html` | Collapsible class card with dots, counts | `cls`, `is_first` |
| `function-member.html` | Collapsible function card with dots, return type | `func`, `is_first` |
| `element-card.html` | Link card for navigation | `child`, `card_type`, `url_prefix` |

## Available Partials

| Partial | Purpose | Variables Required |
|---------|---------|-------------------|
| `badges.html` | Element type badges (module, dataclass, async, etc.) | `element` |
| `header.html` | Title, badges, description, stats | `element` |
| `signature.html` | Code signature block | `element` |
| `usage.html` | CLI/import usage block | `element` |
| `params-table.html` | Parameters as table | `params` (list) |
| `params-list.html` | Parameters as definition list | `params` (list) |
| `returns.html` | Return type/value | `element` |
| `raises.html` | Exception list | `element` |
| `examples.html` | Code examples | `element` or `examples` |
| `members.html` | Collapsible methods/attributes (with internal separation) | `members` (list) |
| `cards.html` | Card grid for children | `children` (list) |

## CSS Classes

All partials use classes from `autodoc.css`:
- `.autodoc-*` prefix for all classes
- `data-*` attributes for variants
- Semantic HTML elements (`<article>`, `<section>`, `<details>`, etc.)

## Data Attributes

| Attribute | Purpose | Values |
|-----------|---------|--------|
| `data-autodoc` | Root marker | (presence only) |
| `data-type` | Doc type | `python`, `cli`, `openapi` |
| `data-element` | Element kind | `module`, `class`, `function`, `command`, `endpoint`, etc. |
| `data-section` | Section type | `parameters`, `returns`, `raises`, `examples`, `methods`, etc. |
| `data-badge` | Badge variant | `deprecated`, `async`, `abstract`, `dataclass`, `required` |
| `data-required` | Required param | `true`, `false` |
| `data-method` | HTTP method | `get`, `post`, `put`, `delete`, `patch` |

## Related Files

- `bengal/themes/default/assets/css/components/autodoc.css` - Styles
- `tests/fixtures/autodoc-skeleton-test.html` - Visual test fixture
- `plan/drafted/rfc-autodoc-html-reset.md` - Design RFC
