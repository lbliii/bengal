# Mistune Variable Substitution Plugin - The Right Architecture

**Date:** October 3, 2025  
**Status:** Design Proposal - Replacing Jinja2 Preprocessing

---

## The Problem with Current Approach

### Current: Jinja2 Preprocessing (Brittle)

```
Markdown (with {{ vars }})
    ↓
Jinja2 Preprocessing (BLIND - sees everything including code blocks)
    ↓
Mistune Parsing
    ↓
HTML
```

**Issues:**
- ❌ Jinja2 can't distinguish code blocks from content
- ❌ Requires complex placeholder extraction
- ❌ Two-stage Jinja2 rendering causes {% raw %} spanning issues
- ❌ False positives in health checks for docs with examples
- ❌ Requires `preprocess: false` workarounds

---

## The Solution: Mistune Plugin

### Proposed: Variable Substitution Plugin (Clean)

```
Markdown (with {{ vars }})
    ↓
Mistune Parsing → AST with identified text vs code nodes
    ↓
Variable Substitution Plugin (SMART - only processes text nodes)
    ↓
HTML Rendering
```

**Advantages:**
- ✅ Mistune already knows what's code vs text (parsed AST)
- ✅ Plugin operates on tokens, naturally skips code blocks
- ✅ Single-pass processing
- ✅ No special escaping needed in documentation
- ✅ Clean architecture following Mistune's design
- ✅ Health checks work correctly

---

## How Mistune Plugins Work

### Mistune's Token System

After parsing, Mistune creates an AST of tokens:

```python
# Example token structure after parsing:
[
    {'type': 'heading', 'level': 1, 'children': [
        {'type': 'text', 'raw': 'My Title'}
    ]},
    {'type': 'paragraph', 'children': [
        {'type': 'text', 'raw': 'Welcome to {{ page.metadata.product_name }}'}
    ]},
    {'type': 'block_code', 'attrs': {'lang': 'bash'}, 'raw': '{{ this.stays.literal }}'},
]
```

**Key insight:** Code blocks are separate token types! The plugin can process `text` tokens and ignore `block_code` tokens.

---

## Implementation Design

### 1. Create Variable Substitution Plugin

```python
# bengal/rendering/mistune_plugins.py

import re
from typing import Any, Dict

class VariableSubstitutionPlugin:
    """
    Mistune plugin for safe variable substitution in text content.
    
    Supports:
    - {{ page.metadata.xxx }} - Access page metadata
    - {{ site.config.xxx }} - Access site config
    - {% if condition %}...{% endif %} - Conditional blocks
    
    ONLY processes text nodes - code blocks remain untouched.
    """
    
    # Pattern to match Jinja2-style variables
    VARIABLE_PATTERN = re.compile(r'\{\{\s*([^}]+)\s*\}\}')
    
    def __init__(self, context: Dict[str, Any]):
        """
        Initialize with rendering context.
        
        Args:
            context: Dict with 'page', 'site', 'config' keys
        """
        self.context = context
    
    def __call__(self, md):
        """Register the plugin with Mistune."""
        # Hook into the renderer to post-process text tokens
        if md.renderer and md.renderer.NAME == 'html':
            # Store original text renderer
            original_text_renderer = md.renderer.text
            
            # Create wrapped renderer that substitutes variables
            def text_with_substitution(text):
                """Render text with variable substitution."""
                substituted = self._substitute_variables(text)
                return original_text_renderer(substituted)
            
            # Replace text renderer
            md.renderer.text = text_with_substitution
    
    def _substitute_variables(self, text: str) -> str:
        """
        Substitute {{ variable }} expressions in text.
        
        Args:
            text: Raw text content
            
        Returns:
            Text with variables substituted
        """
        def replace_var(match):
            expr = match.group(1).strip()
            try:
                # Evaluate expression in context
                result = self._eval_expression(expr)
                return str(result) if result is not None else match.group(0)
            except Exception:
                # On error, leave original syntax
                return match.group(0)
        
        return self.VARIABLE_PATTERN.sub(replace_var, text)
    
    def _eval_expression(self, expr: str) -> Any:
        """
        Safely evaluate a simple expression like 'page.metadata.title'.
        
        Args:
            expr: Expression to evaluate (e.g., 'page.metadata.title')
            
        Returns:
            Evaluated result
            
        Raises:
            Exception: If evaluation fails
        """
        # Support simple dot notation: page.metadata.title
        parts = expr.split('.')
        result = self.context
        
        for part in parts:
            if hasattr(result, part):
                result = getattr(result, part)
            elif isinstance(result, dict):
                result = result.get(part)
            else:
                raise ValueError(f"Cannot access {part} in {expr}")
        
        return result


# For conditional blocks ({% if %}), we'd need a more advanced plugin
class ConditionalBlockPlugin:
    """
    Plugin for conditional content blocks.
    
    Syntax:
        {% if page.metadata.show_section %}
        This content is conditional
        {% endif %}
    """
    
    CONDITIONAL_PATTERN = re.compile(
        r'\{%\s*if\s+([^%]+)\s*%\}(.*?)\{%\s*endif\s*%\}',
        re.DOTALL
    )
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
    
    def __call__(self, md):
        """Register the plugin."""
        # This would hook into block parsing
        # More complex - could process markdown before parsing
        pass
```

### 2. Integrate into Parser

```python
# bengal/rendering/parser.py

class MistuneParser(BaseMarkdownParser):
    """Parser with variable substitution support."""
    
    def __init__(self, enable_variables: bool = True) -> None:
        """Initialize with optional variable substitution."""
        self.enable_variables = enable_variables
        # ... existing code ...
    
    def parse_with_context(self, content: str, context: Dict[str, Any]) -> str:
        """
        Parse markdown with variable substitution.
        
        Args:
            content: Markdown content
            context: Dict with page, site, config
            
        Returns:
            Rendered HTML with variables substituted
        """
        if not self.enable_variables:
            return self.md(content)
        
        # Create a temporary markdown instance with variable plugin
        import mistune
        from bengal.rendering.mistune_plugins import (
            VariableSubstitutionPlugin,
            plugin_documentation_directives
        )
        
        md_with_vars = mistune.create_markdown(
            plugins=[
                'table',
                'strikethrough',
                'task_lists',
                'url',
                'footnotes',
                'def_list',
                plugin_documentation_directives,
                VariableSubstitutionPlugin(context),  # Add variable substitution
            ],
            renderer='html',
        )
        
        return md_with_vars(content)
```

### 3. Update Pipeline

```python
# bengal/rendering/pipeline.py

class RenderingPipeline:
    """Pipeline with Mistune-based variable substitution."""
    
    def process_page(self, page: Page) -> None:
        """Process page with variable substitution."""
        # ... existing setup ...
        
        # NEW: Parse with context (Mistune handles variables internally)
        if hasattr(self.parser, 'parse_with_context'):
            # Mistune with variable substitution
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
        else:
            # Fallback for python-markdown (uses old Jinja2 preprocessing)
            content = self._preprocess_content(page)  # Keep for compatibility
            parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        
        # ... rest of pipeline ...
```

---

## Advantages of This Approach

### 1. **Correctness by Design**

The plugin operates on the **parsed AST** where code blocks are already identified:

```markdown
Use {{ page.title }} in your content.

Code example:
```python
# This {{ stays.literal }} - it's in a code block!
```
```

**How it works:**
1. Mistune parses → identifies text nodes vs code nodes
2. Variable plugin → only processes `text` tokens
3. Code blocks → ignored naturally

### 2. **No Escaping Needed in Docs**

Documentation can show Jinja2 examples naturally:

```markdown
## Template Variables

Use `{{ page.title }}` to display the page title.

Example:
```jinja2
<h1>{{ page.title }}</h1>
{% if page.date %}
  <time>{{ page.date }}</time>
{% endif %}
```
```

**Result:**
- Inline code `{{ page.title }}` → stays literal (inline_code token)
- Code block → stays literal (block_code token)
- Regular text with `{{ vars }}` → gets substituted

### 3. **Single Rendering Pass**

No more two-stage Jinja2 issues:
- No {% raw %} spanning problems
- No template syntax in output
- Cleaner error handling
- Faster (one pass instead of two)

### 4. **Better Error Handling**

```python
def _substitute_variables(self, text: str) -> str:
    """Substitute with clear error handling."""
    def replace_var(match):
        expr = match.group(1).strip()
        try:
            result = self._eval_expression(expr)
            return str(result)
        except Exception as e:
            # Option 1: Leave original (for docs)
            return match.group(0)
            
            # Option 2: Show placeholder with error
            return f'<span class="var-error" title="{e}">{{ {expr} }}</span>'
    
    return self.VARIABLE_PATTERN.sub(replace_var, text)
```

### 5. **Follows Mistune's Architecture**

Uses the same pattern as other plugins:
- Admonitions → DirectivePlugin
- Footnotes → Built-in plugin
- Variables → VariableSubstitutionPlugin

All plugins work on the AST level, giving consistent behavior.

---

## Migration Strategy

### Phase 1: Implement Plugin (Parallel)

1. Create `VariableSubstitutionPlugin`
2. Add to Mistune parser
3. Test with example content
4. Keep Jinja2 preprocessing for python-markdown

### Phase 2: Switch Default

1. Update config: `markdown_engine: mistune` (already default)
2. Enable variable substitution by default
3. Remove `preprocess: false` from docs
4. Update health checks

### Phase 3: Deprecate Jinja2 Preprocessing

1. Mark `_preprocess_content()` as deprecated
2. Only use for python-markdown engine
3. Eventually remove completely

---

## Implementation Complexity

### Simple Version (Variables Only)

**Effort:** ~2-3 hours  
**Scope:** Just `{{ page.metadata.xxx }}` substitution

```python
# Minimal implementation
class SimpleVariablePlugin:
    def __call__(self, md):
        original_text = md.renderer.text
        def text_with_vars(text):
            return self.PATTERN.sub(self.replace, original_text(text))
        md.renderer.text = text_with_vars
```

### Full Version (Variables + Conditionals)

**Effort:** ~1-2 days  
**Scope:** Variables + `{% if %}` blocks + `{% for %}` loops

Would need to:
- Process markdown before parsing (for block-level {% if %})
- Or implement as a block-level plugin
- Handle nesting correctly

---

## Recommendation

**START WITH SIMPLE VERSION:**

1. Implement `VariableSubstitutionPlugin` for `{{ var }}` syntax
2. Test with api/v2/_index.md example
3. Verify code blocks stay literal
4. Measure performance impact (should be negligible)

**For conditionals:** Keep using Jinja2 preprocessing for now, OR implement as a separate pre-processing step that's Mistune-aware.

---

## Expected Results

### Before (Jinja2 Preprocessing)
```markdown
Use {{ '{{ page.title }}' }} in templates.  # Ugly escaping

Code:
```jinja2
{{ '{{ toc }}' }}  # More ugly escaping
```
```

### After (Mistune Plugin)
```markdown
Use {{ page.title }} in templates.  # Natural - in inline code

Code:
```jinja2
{{ toc }}  # Natural - in code block
```
```

**Both "just work" without escaping!**

---

## Conclusion

**This is the right architectural approach:**

1. ✅ Solves the recurring problem permanently
2. ✅ Cleaner code (remove Jinja2 complexity)
3. ✅ Better user experience (no escaping)
4. ✅ Follows Mistune's design patterns
5. ✅ Easier to test and maintain

**The insight:** Let the markdown parser do what it's good at (identifying structure), then process variables at the right abstraction level (AST tokens, not raw text).

