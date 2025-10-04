# Template Whitespace & DX Improvements

**Date**: October 4, 2025  
**Status**: Design Proposal  
**Problem**: Template whitespace issues caused markdown rendering bugs

---

## The Problem

When writing autodoc templates, we hit several whitespace-related issues:

1. **Indented text rendered as code blocks** (4+ spaces = code in markdown)
2. **Code blocks not closing properly** (backticks on same line as content)
3. **Metadata fields running together** (no line breaks between fields)

These were only caught after generation → build → inspect HTML.

---

## Root Causes

### 1. Input Data Has Whitespace

Click's `help` text preserves Python docstring indentation:

```python
@click.command()
def build():
    """
    🔨 Build the static site.    ← 4 spaces!
    
    Generates HTML...
    """
```

When written to markdown, this becomes a code block!

**Solution**: Always `textwrap.dedent()` user-provided strings before storing in DocElement.

### 2. Templates Generate Whitespace

```jinja2
{# This generates extra blank lines #}
{% if condition %}
Content here
{% endif %}

{# The {% %} lines become blank lines in output #}
```

**Solution**: Use Jinja2's whitespace control.

### 3. No Validation

No way to preview or validate generated markdown before it hits the parser.

**Solution**: Add template linting and markdown preview.

---

## Solution 1: Jinja2 Whitespace Control

Jinja2 has Hugo-style whitespace control that we weren't using:

### Syntax

```jinja2
{%- statement -%}   ← Strip whitespace before AND after
{%- statement %}    ← Strip whitespace before only
{% statement -%}    ← Strip whitespace after only
{{- variable -}}    ← Same for variable output
```

### Example: Before vs After

**Before (verbose)**:
```jinja2
{% if arg.metadata.type %}**Type:** `{{ arg.metadata.type }}`  
{% endif %}{% if arg.metadata.required %}**Required:** Yes  
{% endif %}
```

**After (clean with whitespace control)**:
```jinja2
{%- if arg.metadata.type %}
**Type:** `{{ arg.metadata.type }}`  
{%- endif %}
{%- if arg.metadata.required %}
**Required:** Yes  
{%- endif %}
```

Much more readable!

### When to Use

**Use `{%- -%}` when**:
- You don't want blank lines between conditional blocks
- You're generating compact output (metadata fields, lists)
- You're inside code blocks or other whitespace-sensitive contexts

**Don't use when**:
- You want blank lines for readability (between sections)
- Whitespace doesn't matter (HTML rendering)
- You're generating human-readable markdown

---

## Solution 2: Input Data Sanitization

**Principle**: Clean all user-provided strings BEFORE storing in DocElement.

### Implementation

```python
# bengal/autodoc/extractors/base.py (new utility)

import textwrap
import re

def sanitize_description(text: str) -> str:
    """
    Clean user-provided description text for markdown output.
    
    - Strips leading/trailing whitespace
    - Dedents indented blocks
    - Normalizes line endings
    - Removes excessive blank lines
    
    Args:
        text: Raw description text (from docstrings, help text, etc.)
        
    Returns:
        Cleaned text safe for markdown
    """
    if not text:
        return ''
    
    # Dedent to remove common leading whitespace
    text = textwrap.dedent(text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    
    # Collapse multiple blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text
```

**Use everywhere**:
```python
# In PythonExtractor
description=sanitize_description(ast.get_docstring(node) or ''),

# In CLIExtractor
description=sanitize_description(cmd.help or ''),

# In OpenAPIExtractor (future)
description=sanitize_description(operation.get('description', '')),
```

---

## Solution 3: Template Validation

Add validation BEFORE generation to catch issues early.

### Markdown Preview Validator

```python
# bengal/autodoc/template_validator.py

from typing import List, Dict, Any
import re

class TemplateOutputValidator:
    """Validate generated markdown for common issues."""
    
    CHECKS = [
        'indented_code_blocks',
        'unclosed_code_fences',
        'missing_line_breaks',
        'excessive_blank_lines',
        'malformed_links',
    ]
    
    def validate(self, markdown: str, source: str) -> List[Dict[str, Any]]:
        """
        Validate generated markdown for issues.
        
        Args:
            markdown: Generated markdown content
            source: Source identifier (template name, element name)
            
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check for accidental code blocks (4+ spaces)
        issues.extend(self._check_indented_blocks(markdown, source))
        
        # Check for unclosed code fences
        issues.extend(self._check_code_fences(markdown, source))
        
        # Check for missing line breaks (markdown needs 2 spaces or blank line)
        issues.extend(self._check_line_breaks(markdown, source))
        
        # Check for malformed links
        issues.extend(self._check_links(markdown, source))
        
        return issues
    
    def _check_indented_blocks(self, markdown: str, source: str) -> List[Dict]:
        """Detect accidental indented code blocks."""
        issues = []
        lines = markdown.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for 4+ spaces that might be accidental
            if re.match(r'^    \S', line):
                # But not inside code fences
                if not self._inside_code_fence(lines, i - 1):
                    issues.append({
                        'level': 'warning',
                        'type': 'indented_code_block',
                        'line': i,
                        'message': f'Line has 4+ leading spaces (will render as code block)',
                        'suggestion': 'Remove leading spaces or use code fence',
                        'source': source,
                    })
        
        return issues
    
    def _check_code_fences(self, markdown: str, source: str) -> List[Dict]:
        """Check for unclosed code fences."""
        issues = []
        
        # Find all code fence markers
        fence_pattern = re.compile(r'^```', re.MULTILINE)
        fences = [(m.start(), m.group()) for m in fence_pattern.finditer(markdown)]
        
        # Should be even number (open + close)
        if len(fences) % 2 != 0:
            issues.append({
                'level': 'error',
                'type': 'unclosed_code_fence',
                'message': f'Found {len(fences)} code fences (should be even)',
                'suggestion': 'Add closing ``` for each code block',
                'source': source,
            })
        
        return issues
    
    def _check_line_breaks(self, markdown: str, source: str) -> List[Dict]:
        """Check for missing line breaks in metadata fields."""
        issues = []
        lines = markdown.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Look for **Field:** immediately followed by **Field:** on next line
            if line.strip().startswith('**') and i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('**'):
                    # Check if previous line ends with 2 spaces or blank line between
                    if not (line.endswith('  ') or lines[i - 1].strip() == ''):
                        issues.append({
                            'level': 'warning',
                            'type': 'missing_line_break',
                            'line': i,
                            'message': 'Multiple bold fields without line break (will run together)',
                            'suggestion': 'Add 2 trailing spaces or blank line between fields',
                            'source': source,
                        })
        
        return issues
    
    def _inside_code_fence(self, lines: List[str], line_idx: int) -> bool:
        """Check if line is inside a code fence."""
        fence_count = 0
        for i in range(line_idx):
            if lines[i].strip().startswith('```'):
                fence_count += 1
        return fence_count % 2 == 1
```

### Usage in Generator

```python
# In DocumentationGenerator.generate_single()

def generate_single(self, element: DocElement, output_dir: Path) -> Path:
    """Generate documentation for single element."""
    
    # Render template
    content = self._render_template(template_name, element)
    
    # VALIDATE before writing
    validator = TemplateOutputValidator()
    issues = validator.validate(content, element.qualified_name)
    
    # Report issues
    for issue in issues:
        level = issue['level']
        msg = f"{level.upper()}: {issue['message']}"
        
        if level == 'error':
            print(f"  ❌ {element.qualified_name}: {msg}")
        else:
            print(f"  ⚠️  {element.qualified_name}: {msg}")
        
        if 'suggestion' in issue:
            print(f"     💡 {issue['suggestion']}")
    
    # Write file
    output_path.write_text(content)
    
    return output_path
```

---

## Solution 4: Template Linting

Lint templates BEFORE using them to catch common mistakes.

### Template Linter

```python
# bengal/autodoc/template_linter.py

class TemplateLinter:
    """Lint Jinja2 templates for common issues."""
    
    def lint(self, template_path: Path) -> List[Dict[str, Any]]:
        """
        Lint template file.
        
        Returns:
            List of lint warnings/errors
        """
        issues = []
        content = template_path.read_text()
        lines = content.split('\n')
        
        # Check for missing whitespace control
        issues.extend(self._check_whitespace_control(lines, template_path))
        
        # Check for proper code fence usage
        issues.extend(self._check_code_fences(lines, template_path))
        
        # Check for line break syntax
        issues.extend(self._check_line_breaks(lines, template_path))
        
        return issues
    
    def _check_whitespace_control(self, lines: List[str], path: Path) -> List[Dict]:
        """Suggest using whitespace control where appropriate."""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Look for {% endif %} followed by {% if
            if '{% endif %}' in line and i < len(lines):
                next_line = lines[i]
                if '{% if' in next_line and lines[i].strip() == '':
                    issues.append({
                        'level': 'info',
                        'type': 'whitespace_control_suggestion',
                        'line': i,
                        'message': 'Consider using {%- endif %} to avoid blank line',
                        'file': str(path),
                    })
        
        return issues
    
    def _check_code_fences(self, lines: List[str], path: Path) -> List[Dict]:
        """Check code fence patterns."""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Code fence should have blank line before closing
            if line.strip() == '```' and i > 1:
                prev_line = lines[i - 2]
                if prev_line.strip() != '' and not prev_line.strip().startswith('```'):
                    issues.append({
                        'level': 'warning',
                        'type': 'code_fence_format',
                        'line': i,
                        'message': 'Code fence closing should have blank line before it',
                        'file': str(path),
                    })
        
        return issues
```

---

## Solution 5: Developer Tools

### Preview Command

```bash
# Preview generated markdown BEFORE building
$ bengal autodoc --preview

📄 Previewing generated markdown...

content/cli/commands/build.md:
┌────────────────────────────────────────────────────────────
│ # build
│ 
│ 🔨 Build the static site.
│ 
│ Generates HTML files from your content, applies templates,
│ processes assets, and outputs a production-ready site.
│ 
│ ## Usage
│ 
│ ```bash
│ main build [ARGUMENTS] [OPTIONS]
│ 
│ ```
│ 
│ ## Arguments
│ 
│ ### source
│ 
│ **Type:** `path`  
│ **Required:** No  
│ **Default:** `.`
│ 
│ ## Options
│ ...
└────────────────────────────────────────────────────────────

✅ No markup issues found
```

### Validation Command

```bash
# Validate templates
$ bengal autodoc --validate-templates

🔍 Validating templates...

✅ command-group.md.jinja2: No issues
⚠️  command.md.jinja2: 2 warnings
   Line 27: Consider using {%- endif %} to avoid blank lines
   Line 45: Consider adding blank line before code fence close

Summary: 2 templates checked, 2 warnings, 0 errors
```

---

## Best Practices Going Forward

### For Template Authors

1. **Always use `textwrap.dedent()` on user input**
   ```python
   description=textwrap.dedent(raw_text or '').strip()
   ```

2. **Use whitespace control for compact output**
   ```jinja2
   {%- if condition %}
   Content
   {%- endif %}
   ```

3. **Add blank line before closing code fences**
   ```jinja2
   ```bash
   command here
   
   ```
   ```

4. **Use two trailing spaces for line breaks**
   ```jinja2
   **Type:** `string`  
   **Required:** Yes  
   ```

5. **Run validation before committing**
   ```bash
   bengal autodoc --validate-templates
   ```

### For Bengal Core

1. **Add `sanitize_description()` utility** (use everywhere)
2. **Integrate template validator into generator**
3. **Add `--preview` flag to autodoc**
4. **Add `--validate-templates` flag**
5. **Update template documentation with examples**

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
- ✅ Add `textwrap.dedent()` to all extractors (DONE)
- ✅ Fix template formatting (DONE)
- Add `sanitize_description()` utility
- Update extractor base class to use it

### Phase 2: Validation (2-3 hours)
- Implement `TemplateOutputValidator`
- Integrate into `DocumentationGenerator`
- Add `--validate-templates` flag

### Phase 3: Preview Tools (2-3 hours)
- Implement `--preview` flag
- Add markdown preview rendering
- Add issue highlighting

### Phase 4: Documentation (1 hour)
- Update template authoring guide
- Add best practices doc
- Add troubleshooting guide

---

## Summary

**What we have**:
- ✅ Jinja2 whitespace control (just not using it)
- ✅ Working templates (after manual fixes)

**What we need**:
- Input sanitization (prevent issues at source)
- Template validation (catch issues early)
- Preview tools (see issues before build)
- Better documentation (teach best practices)

**The DX improvement**:
Instead of: Generate → Build → Inspect HTML → Fix template → Repeat
We get: Validate → Preview → Generate (with confidence)

---

*This would make Bengal's autodoc template system more ergonomic than Hugo's!*

