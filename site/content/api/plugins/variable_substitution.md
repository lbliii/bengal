
---
title: "plugins.variable_substitution"
type: python-module
source_file: "bengal/rendering/plugins/variable_substitution.py"
css_class: api-content
description: "Variable substitution plugin for Mistune.  Provides safe {{ variable }} replacement in markdown content while keeping code blocks literal and maintaining clear separation from template logic."
---

# plugins.variable_substitution

Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.

---

## Classes

### `VariableSubstitutionPlugin`


Mistune plugin for safe variable substitution in markdown content.

ARCHITECTURE: Separation of Concerns
=====================================

This plugin handles ONLY variable substitution ({{ vars }}) in markdown.
It operates at the AST level after Mistune parses the markdown structure.

WHAT THIS HANDLES:
------------------
✅ {{ page.metadata.xxx }} - Access page frontmatter
✅ {{ site.config.xxx }} - Access site configuration
✅ {{ page.title }}, {{ page.date }}, etc. - Page properties

WHAT THIS DOESN'T HANDLE:
--------------------------
❌ {% if condition %} - Conditional blocks
❌ {% for item %} - Loop constructs
❌ Complex Jinja2 logic

WHY: Conditionals and loops belong in TEMPLATES, not markdown.

Example - Using in Markdown:
    Welcome to {{ page.metadata.product_name }} version {{ page.metadata.version }}.

    Connect to {{ page.metadata.api_url }}/users

Example - Escaping Syntax (Hugo-style):
    Use {{/* page.title */}} to display the page title.

    This renders as: Use {{ page.title }} to display the page title.

Example - Using Conditionals in Templates:
    <!-- templates/page.html -->
    <article>
      {% if page.metadata.beta %}
      <div class="beta-notice">Beta Feature</div>
      {% endif %}

      {{ content }}  <!-- Markdown with {{ vars }} renders here -->
    </article>

KEY FEATURE: Code blocks stay literal naturally!
------------------------------------------------
Since this plugin only processes text tokens (not code tokens),
code blocks and inline code automatically preserve their content:

    Use `{{ page.title }}` to show the title.  ← Stays literal in output

    ```python
    # This {{ var }} stays literal too!
    print("{{ page.title }}")
    ```

This is the RIGHT architectural approach:
- Single-pass parsing (fast!)
- Natural code block handling (no escaping needed!)
- Clear separation: content (markdown) vs logic (templates)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, context: dict[str, Any])
```

Initialize with rendering context.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `context`
  - `dict[str, Any]`
  - -
  - Dict with variables (page, site, config, etc.)
:::

::::




---
#### `update_context`
```python
def update_context(self, context: dict[str, Any]) -> None
```

Update the rendering context (for parser reuse).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `context`
  - `dict[str, Any]`
  - -
  - New context dict with variables (page, site, config, etc.)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `__call__`
```python
def __call__(self, md)
```

Register the plugin with Mistune.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `md`
  - -
  - -
  - -
:::

::::




---
#### `restore_placeholders`
```python
def restore_placeholders(self, html: str) -> str
```

Restore placeholders to HTML-escaped template syntax.

This uses HTML entities to prevent Jinja2 from processing the restored
template syntax. The browser will render &#123;&#123; as {{ in the final output.

This is the correct long-term solution because:
- Jinja2 won't see {{ so it won't try to template it
- The browser renders entities as literal {{ for users to see
- No timing issues or re-processing concerns
- Works for documentation examples, code snippets, etc.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `html`
  - `str`
  - -
  - HTML output from Mistune
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - HTML with placeholders restored as HTML entities




---


