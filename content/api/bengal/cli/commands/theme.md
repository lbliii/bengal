
---
title: "theme"
type: "python-module"
source_file: "bengal/cli/commands/theme.py"
line_number: 1
description: "Theme-related CLI commands (themes, swizzle)."
---

# theme
**Type:** Module
**Source:** [View source](bengal/cli/commands/theme.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cli](/api/bengal/cli/) ›[commands](/api/bengal/cli/commands/) ›theme

Theme-related CLI commands (themes, swizzle).

## Functions



### `theme`


```python
def theme() -> None
```



Theme utilities (list/info/discover/install, swizzle).



**Returns**


`None`




### `swizzle`


```python
def swizzle(template_path: str, source: str) -> None
```



🎨 Copy a theme template/partial to project templates.

Swizzling copies a template from the active theme to your project's
templates/ directory, allowing you to customize it while tracking
provenance for future updates.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_path` | `str` | - | *No description provided.* |
| `source` | `str` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme swizzle layouts/article.html
    bengal theme swizzle partials/header.html

See also:
    bengal theme swizzle-list - List swizzled templates
    bengal theme swizzle-update - Update swizzled templates
```





### `swizzle_list`


```python
def swizzle_list(source: str) -> None
```



📋 List swizzled templates.

Shows all templates that have been copied from themes to your project,
along with their source theme for tracking.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme swizzle-list

See also:
    bengal theme swizzle - Copy a template from theme
    bengal theme swizzle-update - Update swizzled templates
```





### `swizzle_update`


```python
def swizzle_update(source: str) -> None
```



🔄 Update swizzled templates if unchanged locally.

Checks swizzled templates and updates them from the theme if you haven't
modified them locally. Templates you've customized are skipped.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme swizzle-update

See also:
    bengal theme swizzle - Copy a template from theme
    bengal theme swizzle-list - List swizzled templates
```





### `list_themes`


```python
def list_themes(source: str) -> None
```



📋 List available themes.

Shows themes from three sources:
- Project themes: themes/ directory in your site
- Installed themes: Themes installed via pip/uv
- Bundled themes: Themes included with Bengal


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme list

See also:
    bengal theme info - Show details about a specific theme
    bengal theme install - Install a theme package
```





### `info`


```python
def info(slug: str, source: str) -> None
```



ℹ️  Show theme info for a slug.

Displays information about a theme including:
- Source location (project, installed, or bundled)
- Version (if installed)
- Template and asset paths


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `slug` | `str` | - | *No description provided.* |
| `source` | `str` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme info default
    bengal theme info my-theme

See also:
    bengal theme list - List all available themes
```





### `discover`


```python
def discover(source: str) -> None
```



🔍 List swizzlable templates from the active theme chain.

Shows all templates available in your active theme(s) that can be
swizzled (copied) to your project for customization.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme discover

See also:
    bengal theme swizzle - Copy a template from theme
```





### `debug`


```python
def debug(source: str, template: str | None) -> None
```



🐛 Debug theme resolution and template paths.

Shows comprehensive information about:
- Active theme chain (inheritance order)
- Template resolution paths (priority order)
- Template source locations
- Theme validation (circular inheritance, missing themes)
- Specific template resolution (if --template provided)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | *No description provided.* |
| `template` | `str \| None` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme debug
    bengal theme debug --template page.html

See also:
    bengal theme info - Show details about a specific theme
    bengal theme list - List available themes
```





### `install`


```python
def install(name: str, force: bool) -> None
```



📦 Install a theme via uv pip.

Installs a theme package from PyPI. NAME may be a package name or a slug.
If a slug without prefix is provided, suggests canonical 'bengal-theme-<slug>'.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | *No description provided.* |
| `force` | `bool` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme install bengal-theme-minimal
    bengal theme install minimal --force

See also:
    bengal theme list - List available themes
```





### `features`


```python
def features(source: str, category: str | None, enabled: bool, defaults: bool) -> None
```



📋 List available theme features.

Shows all features that can be enabled in [theme.features] config.
Feature flags allow declarative control over theme behavior.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | *No description provided.* |
| `category` | `str \| None` | - | *No description provided.* |
| `enabled` | `bool` | - | *No description provided.* |
| `defaults` | `bool` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme features                    # List all features
    bengal theme features --category nav     # Filter by category
    bengal theme features --enabled          # Show only enabled
    bengal theme features --defaults         # Show default features

Usage in config:
    [theme]
    features = [
        "navigation.toc",
        "content.code.copy",
    ]

See also:
    bengal theme info - Show details about a specific theme
```





### `new`


```python
def new(slug: str, mode: str, output: str, extends: str, force: bool) -> None
```



🎨 Create a new theme scaffold.

Creates a new theme with templates, partials, and assets. SLUG is the
theme identifier used in config (e.g., [site].theme = SLUG).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `slug` | `str` | - | *No description provided.* |
| `mode` | `str` | - | *No description provided.* |
| `output` | `str` | - | *No description provided.* |
| `extends` | `str` | - | *No description provided.* |
| `force` | `bool` | - | *No description provided.* |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
bengal theme new my-theme
    bengal theme new my-theme --mode package

See also:
    bengal theme list - List available themes
```



---
*Generated by Bengal autodoc from `bengal/cli/commands/theme.py`*

