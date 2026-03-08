# Add Directive Reference

## DirectiveHandler Protocol

Handlers must implement:

- `names: tuple[str, ...]` — Directive names (e.g., `("note", "warning")`)
- `token_type: str` — AST dispatch identifier
- `parse(name, title, options, content, children, location) -> Directive`
- `render(node, rendered_children, sb) -> None`

Optional:

- `contract: DirectiveContract | None` — Nesting validation
- `options_class: type[DirectiveOptions]` — Typed options

## DirectiveOptions

Subclass `DirectiveOptions` for typed :key: value parsing. Use `class_` for the `class` option (alias).

Type coercion: str, bool, int, float, list[str] (whitespace-split).

## DirectiveContract

- `requires_parent` — Must be inside one of these parents
- `requires_children` — Must contain at least one of these
- `allows_children` — Only these allowed (None = any)
- `forbids_children` — These forbidden

## File Locations

- Handlers: `bengal/parsing/backends/patitas/directives/builtins/`
- Options: `bengal/parsing/backends/patitas/directives/options.py`
- Registry: `bengal/parsing/backends/patitas/directives/registry.py`
- Protocol: `bengal/parsing/backends/patitas/directives/protocol.py`
