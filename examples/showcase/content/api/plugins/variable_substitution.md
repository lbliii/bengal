---
title: "plugins.variable_substitution"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/variable_substitution.py"
---

# plugins.variable_substitution

Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.

**Source:** `../../bengal/rendering/plugins/variable_substitution.py`

---

## Classes

### VariableSubstitutionPlugin


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




**Methods:**

#### __init__

```python
def __init__(self, context: Dict[str, Any])
```

Initialize with rendering context.

**Parameters:**

- **self**
- **context** (`Dict[str, Any]`) - Dict with variables (page, site, config, etc.)







---
#### update_context

```python
def update_context(self, context: Dict[str, Any]) -> None
```

Update the rendering context (for parser reuse).

**Parameters:**

- **self**
- **context** (`Dict[str, Any]`) - New context dict with variables (page, site, config, etc.)

**Returns:** `None`






---
#### __call__

```python
def __call__(self, md)
```

Register the plugin with Mistune.

**Parameters:**

- **self**
- **md**







---


