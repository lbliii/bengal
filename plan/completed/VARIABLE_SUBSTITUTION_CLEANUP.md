# Variable Substitution Cleanup - October 4, 2025

## Problem

Documentation files that need to **show** template syntax (like `{{ variable }}` or `{% for %}`) were being **processed** instead of displayed literally. This required wrapping entire files in `{% raw %}` tags.

## The Two Rendering Paths

### Path 1: Normal Content (preprocess enabled, default)

**Input markdown:**
```markdown
---
title: "API Documentation"
product_name: "DataFlow API"
api_url: "https://api.example.com"
---

Connect to {{ page.metadata.api_url }} to access {{ page.metadata.product_name }}.
```

**What happens:**
1. VariableSubstitutionPlugin processes the markdown
2. `{{ page.metadata.api_url }}` → `https://api.example.com`
3. `{{ page.metadata.product_name }}` → `DataFlow API`

**Output HTML:**
```html
<p>Connect to https://api.example.com to access DataFlow API.</p>
```

### Path 2: Documentation Content (preprocess: false)

**Input markdown:**
```markdown
---
title: "String Functions"
preprocess: false  # ← Disable variable substitution
---

Use `{{ text | truncate(50) }}` to truncate text.

Example template:
{{ page.title }}
{% for post in posts %}
  <li>{{ post.title }}</li>
{% endfor %}
```

**What happens:**
1. Pipeline checks `page.metadata.get('preprocess')`
2. Sees it's `False`
3. Skips `parse_with_toc_and_context()` (with variable substitution)
4. Uses `parse_with_toc()` (plain markdown parsing only)
5. All `{{ }}` and `{% %}` syntax stays literal

**Output HTML:**
```html
<p>Use <code>{{ text | truncate(50) }}</code> to truncate text.</p>

<p>Example template:
{{ page.title }}
{% for post in posts %}
  <li>{{ post.title }}</li>
{% endfor %}</p>
```

## The Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│ Markdown File                                           │
├─────────────────────────────────────────────────────────┤
│ ---                                                     │
│ title: "My Page"                                        │
│ preprocess: ???  ← This controls the path               │
│ ---                                                     │
│                                                         │
│ Content with {{ variables }}                            │
└─────────────────────────────────────────────────────────┘
                         ↓
                         ↓
         ┌───────────────┴────────────────┐
         │                                 │
         ↓                                 ↓
┌─────────────────────┐         ┌──────────────────────┐
│ preprocess != false │         │ preprocess == false  │
│ (DEFAULT)           │         │                      │
└─────────────────────┘         └──────────────────────┘
         ↓                                 ↓
         ↓                                 ↓
┌─────────────────────┐         ┌──────────────────────┐
│ parse_with_toc_and_ │         │ parse_with_toc()     │
│ context()           │         │                      │
│                     │         │ Plain Mistune        │
│ VariableSubstitution│         │ No variable subst    │
│ Plugin ACTIVE       │         │ {{ }} stays literal  │
└─────────────────────┘         └──────────────────────┘
         ↓                                 ↓
         ↓                                 ↓
┌─────────────────────┐         ┌──────────────────────┐
│ Variables replaced  │         │ Syntax preserved     │
│ {{ var }} → value   │         │ {{ var }} → {{ var }}│
└─────────────────────┘         └──────────────────────┘
```

## Why This Matters

### Before Our Change

**Documentation files looked like this:**
```markdown
---
title: "String Functions"
---

{% raw %}
# String Functions

Use {{ text | truncate(50) }} to truncate...
{% endraw %}
```

- **Problem**: `{% raw %}` everywhere
- **Problem**: Only worked with python-markdown (Jinja2 preprocessing)
- **Problem**: Mistune ignored `preprocess: false`

### After Our Change

**Documentation files now look like this:**
```markdown
---
title: "String Functions"
preprocess: false
---

# String Functions

Use {{ text | truncate(50) }} to truncate...
```

- ✅ Clean, no `{% raw %}` noise
- ✅ Works with Mistune (recommended parser)
- ✅ Consistent behavior across parsers
- ✅ Frontmatter control (standard Hugo pattern)

## Use Cases

### Use Case 1: Regular Content (Variable Substitution ON)

**API documentation with cascading values:**
```markdown
---
title: "Users Endpoint"
# These cascade from parent _index.md:
# api_url: "https://api.example.com/v2"
---

Access the users endpoint at {{ page.metadata.api_url }}/users
```

### Use Case 2: Template Documentation (Variable Substitution OFF)

**Teaching people how to use templates:**
```markdown
---
title: "Template Tutorial"
preprocess: false
---

In your template, use {{ page.title }} to display the title.

Loop through posts:
{% for post in posts %}
  {{ post.title }}
{% endfor %}
```

### Use Case 3: Mixed Content

**Blog post about templating (variable substitution ON, careful escaping in code blocks):**
```markdown
---
title: "How to Use Bengal Templates"
author: "Jane Doe"
---

Hi, I'm {{ page.metadata.author }} and today I'll teach you about templates.

In code blocks, {{ }} stays literal automatically:

\`\`\`jinja2
{{ page.title }}
{% for item in items %}
  {{ item }}
{% endfor %}
\`\`\`
```

**Why code blocks work:** VariableSubstitutionPlugin operates at the AST level, so it only processes **text tokens**, not **code tokens**. Code blocks are naturally protected!

## Technical Implementation

**File:** `bengal/rendering/pipeline.py:107-124`

```python
if hasattr(self.parser, 'parse_with_toc_and_context'):
    # Mistune with VariableSubstitutionPlugin (recommended)
    # Check if preprocessing is disabled
    if page.metadata.get('preprocess') is False:
        # Parse without variable substitution (for docs showing template syntax)
        parsed_content, toc = self.parser.parse_with_toc(
            page.content,
            page.metadata
        )
    else:
        # Single-pass parsing with variable substitution - fast and simple!
        context = {
            'page': page,
            'site': self.site,
            'config': self.site.config
        }
        parsed_content, toc = self.parser.parse_with_toc_and_context(
            page.content,
            page.metadata,
            context
        )
```

## Better Solution: Inline Escaping (Hugo-Style)

We also implemented **Hugo-style inline escaping** for more ergonomic usage:

```markdown
Use {{/* page.title */}} to display the page title.

Variables like {{/* site.config.baseurl */}} are useful.
```

**Renders as:**
```
Use {{ page.title }} to display the page title.

Variables like {{ site.config.baseurl }} are useful.
```

### When to Use Each Approach

**Inline escaping (`{{/* */}}`):**
- ✅ Mixed content (some variables execute, some display)
- ✅ Quick examples in documentation
- ✅ Teaching one or two syntax examples
- ✅ Most documentation use cases

**File-level (`preprocess: false`):**
- ✅ Template reference pages (all syntax is examples)
- ✅ Large code samples with many examples
- ✅ When you want NO variable processing at all
- ✅ "Nuclear option" for entire files

## Summary

**Two ways to handle template syntax in content:**

1. **Inline escaping**: `{{/* expression */}}` → shows as `{{ expression }}`
2. **File-level**: `preprocess: false` → disables all variable processing

**Key insight:** Most documentation should use inline escaping. Only use `preprocess: false` for files that are entirely template examples.

