
---
title: "variable_substitution"
type: "python-module"
source_file: "bengal/bengal/rendering/plugins/variable_substitution.py"
line_number: 1
description: "Variable substitution plugin for Mistune. Provides safe {{ variable }} replacement in markdown content while keeping code blocks literal and maintaining clear separation from template logic."
---

# variable_substitution
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/plugins/variable_substitution.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[plugins](/api/bengal/rendering/plugins/) ›variable_substitution

Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.

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









## Methods



#### `__init__`
```python
def __init__(self, context: dict[str, Any])
```


Initialize with rendering context.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `context` | `dict[str, Any]` | - | Dict with variables (page, site, config, etc.) |








#### `update_context`
```python
def update_context(self, context: dict[str, Any]) -> None
```


Update the rendering context (for parser reuse).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `context` | `dict[str, Any]` | - | New context dict with variables (page, site, config, etc.) |







**Returns**


`None`



#### `__call__`
```python
def __call__(self, md)
```


Register the plugin with Mistune.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `md` | - | - | *No description provided.* |








#### `preprocess`
```python
def preprocess(self, text: str) -> str
```


Handle escaped syntax {{/* ... */}} before parsing.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |







**Returns**


`str`



#### `substitute_variables`
```python
def substitute_variables(self, text: str) -> str
```


Substitute {{ variable }} expressions in text nodes.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |







**Returns**


`str`




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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `html` | `str` | - | HTML output from Mistune |







**Returns**


`str` - HTML with placeholders restored as HTML entities



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/plugins/variable_substitution.py`*
