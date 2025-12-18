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
{% from 'autodoc/partials/cards.html' import element_card with context %}
{{ element_card(child) }}
```

## Available Partials

| Partial | Purpose | Variables Required |
|---------|---------|-------------------|
| `header.html` | Title, badges, description, stats | `element` |
| `signature.html` | Code signature block | `element` |
| `usage.html` | CLI/import usage block | `element` |
| `params-table.html` | Parameters as table | `params` (list) |
| `params-list.html` | Parameters as definition list | `params` (list) |
| `returns.html` | Return type/value | `element` |
| `raises.html` | Exception list | `element` |
| `examples.html` | Code examples | `element` or `examples` |
| `members.html` | Collapsible methods/attributes | `members` (list) |
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
