---
title: Writing Plugins
description: Create plugins that add directives, template functions, content sources, and build hooks
weight: 45
icon: puzzle
tags:
- plugins
- extending
- extensibility
keywords:
- plugin
- entry point
- registry
- extension
category: guide
---

# Writing Plugins

Plugins extend Bengal with custom directives, template functions, content sources, validators, and build lifecycle hooks — all through a single `register()` method. The plugin system uses Python entry points for automatic discovery and a builder→immutable pattern for thread safety.

## Quick Start

Create a plugin in three steps:

### 1. Implement the Plugin Protocol

```python
# my_bengal_plugin/__init__.py
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry


class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_template_filter("shout", lambda v: v.upper() + "!")
```

### 2. Declare the Entry Point

```toml
# pyproject.toml
[project.entry-points."bengal.plugins"]
my-plugin = "my_bengal_plugin:MyPlugin"
```

### 3. Install and Build

```bash
uv pip install -e ./my-bengal-plugin
bengal build  # Plugin auto-discovered
```

Your filter is now available in templates:

```kida
{{ page.title | shout }}
```

## Plugin Protocol

Every plugin must have `name`, `version`, and a `register()` method:

```python
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry


class MyPlugin(Plugin):
    name: str = "my-plugin"
    version: str = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        # Register extensions here
        ...
```

`Plugin` is a `runtime_checkable` Protocol — no base class inheritance required. Any object with the right attributes works.

## Extension Points

The `PluginRegistry` provides 9 registration methods:

Current integration status:

- Ready in builds: template functions, template filters, template tests, build phase hooks
- Registered but pending subsystem wiring: directives, roles, content sources, health validators, shortcodes

Use `bengal plugin list`, `bengal plugin info <name>`, and
`bengal plugin validate` to inspect installed plugins and see whether their
registered capabilities are active in the current Bengal build pipeline.

### Template Extensions

```python
def register(self, registry: PluginRegistry) -> None:
    # Global function: {{ my_func(page) }}
    registry.add_template_function("my_func", my_func, phase=1)

    # Filter: {{ value | my_filter }}
    registry.add_template_filter("my_filter", my_filter)

    # Test: {% if value is my_test %}
    registry.add_template_test("my_test", my_test)
```

The `phase` parameter on `add_template_function` controls registration order (1–9), matching Bengal's internal template function phases.

### Directives and Roles

```python
def register(self, registry: PluginRegistry) -> None:
    # Block directive: :::{my_directive}
    registry.add_directive(MyDirectiveHandler)

    # Inline role: {my_role}`text`
    registry.add_role(MyRoleHandler)
```

Directive and role registration is discoverable through plugin introspection,
but parser injection is not wired yet.

### Content Sources

```python
def register(self, registry: PluginRegistry) -> None:
    registry.add_content_source("my-source", MyContentSource)
```

Content source registration is discoverable through plugin introspection, but
content discovery does not consume plugin sources yet.

### Health Validators

```python
def register(self, registry: PluginRegistry) -> None:
    registry.add_health_validator(MyValidator())
```

Health validator registration is discoverable through plugin introspection, but
health checks do not consume plugin validators yet.

### Shortcodes

```python
def register(self, registry: PluginRegistry) -> None:
    registry.add_shortcode(
        "alert",
        '<div class="alert alert-{{ type | default("info") }}">{{ content }}</div>',
    )
```

Shortcode registration is discoverable through plugin introspection, but the
shortcode registry does not consume plugin shortcodes yet.

### Build Phase Hooks

```python
def register(self, registry: PluginRegistry) -> None:
    registry.on_phase("pre_render", self.before_render)
    registry.on_phase("post_render", self.after_render)

def before_render(self, site, build_context):
    print(f"Rendering {len(site.pages)} pages")

def after_render(self, site, build_context):
    print("Render complete")
```

Lifecycle hook names currently emitted by builds:

- `build_start`, `build_complete`
- `pre_discovery`, `post_discovery`
- `pre_content`, `post_content`
- `pre_parsing`, `post_parsing`
- `pre_snapshot`, `post_snapshot`
- `pre_assets`, `post_assets`
- `pre_render`, `post_render`
- `pre_rendering`, `post_rendering`
- `pre_finalization`, `post_finalization`
- `pre_health`, `post_health`

## How Discovery Works

Bengal discovers plugins via the `bengal.plugins` [entry point group](https://packaging.python.org/en/latest/specifications/entry-points/):

1. On startup, `discover_plugins()` calls `importlib.metadata.entry_points(group="bengal.plugins")`
2. Each entry point is loaded and validated against the `Plugin` protocol
3. Valid plugins call `register()` on a mutable `PluginRegistry`
4. The registry is frozen into an immutable `FrozenPluginRegistry` before rendering begins

The frozen registry is a dataclass with tuple fields — safe to share across threads during parallel rendering.

## Combining Multiple Extensions

A single plugin can register any number of extensions:

```python
class KitchenSinkPlugin(Plugin):
    name = "kitchen-sink"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_template_filter("slugify", self._slugify)
        registry.add_template_function("badge", self._badge, phase=1)
        registry.add_directive(MyDirective)
        registry.add_health_validator(MyValidator())
        registry.on_phase("post_render", self._post_render)
```

## Programmatic Registration

If you don't want entry-point discovery, pass plugins directly:

```python
from bengal.plugins.loader import load_plugins

frozen = load_plugins(extra_plugins=[MyPlugin()])
```

## See Also

- [Extension Points](/docs/reference/architecture/meta/extension-points/) — Full reference for all extension points
- [Custom Directives](../custom-directives/) — Directive authoring guide
- [Template Shortcodes](../shortcodes/) — Template-only shortcodes (no Python required)
