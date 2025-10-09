# Directive Nesting Guide - Backtick Fence Rules

**Date:** October 8, 2025  
**Status:** Reference Document

## The Golden Rule

**Outer fence MUST have MORE backticks than any inner fence**

This is standard CommonMark/Mistune behavior, not Bengal-specific.

## Examples

### Level 1: Simple Admonition (3 backticks)

```markdown
```{note} Simple Note
Just text content, no nested code blocks.
```
```

✅ **Works** - No nested fences

---

### Level 2: Admonition with Code Block (4 backticks)

```markdown
````{warning} Warning with Code
Here's some problematic code:

```python
# Inner code block uses 3 backticks
dangerous_function()
```

More text after the code.
````
```

✅ **Works** - Outer has 4, inner has 3

❌ **Broken:**
```markdown
```{warning} This Breaks!
Text here.

```python
# Parser thinks this closes the warning!
code()
```
```
```

The first closing ```` ``` ```` is seen as closing the warning, not starting the Python block.

---

### Level 3: Nested Directives (5 backticks)

```markdown
`````{note} Complex Example
Text content.

````{tabs}
### Tab: Python
```python
code()
```

### Tab: JavaScript
```javascript
code();
```
````

More text.
`````
```

✅ **Works** - Outer: 5, middle: 4, inner: 3

---

### Level 4: Maximum Nesting (6 backticks)

```markdown
``````{warning} Deeply Nested
Content.

`````{tabs}
### Tab: Example

````{note} Nested Admonition
Text.

```python
code()
```
````
`````
``````
```

✅ **Works** - Outer: 6, L2: 5, L3: 4, L4: 3

---

## Quick Reference Table

| Nesting Level | Backticks | Common Use Case |
|---------------|-----------|-----------------|
| Level 1 | 3 ` ``` ` | Simple directive, no code |
| Level 2 | 4 ` ```` ` | Directive + code block |
| Level 3 | 5 ` ````` ` | Nested directives + code |
| Level 4 | 6 ` `````` ` | Complex nesting (rare) |

## Practical Guidelines

### 1. Default to 4 Backticks for Admonitions

If you're documenting code, always use 4:

```markdown
````{tip} Best Practice
Use 4 backticks by default for admonitions:

```python
# You can include examples
example_code()
```
````
```

### 2. Count Your Deepest Nest

Find the deepest code block, add 1:

- Deepest code block: 3 backticks
- Tabs around it: 4 backticks
- Admonition around that: 5 backticks

### 3. When in Doubt, Add One More

Extra backticks don't hurt:

```markdown
`````{note}
Even if I don't need 5, it works fine!

```python
code()
```
`````
```

✅ **Still works** - Just uses more than necessary

---

## Common Directives That Need Nesting

### Admonitions
- `{note}`, `{tip}`, `{warning}`, `{danger}`, `{info}`, `{success}`, `{error}`, `{caution}`, `{example}`
- **Usually need 4 backticks** if containing code examples

### Tabs
- `{tabs}` - General purpose tabs
- **Usually need 4 backticks** minimum
- **5 backticks** if tabs contain admonitions with code

### Code Tabs
- `{code-tabs}` - Multi-language code examples
- **Usually need 4 backticks** since they contain code by definition

### Dropdowns
- `{dropdown}` or `{details}` - Collapsible content
- **4 backticks** if containing code

---

## Troubleshooting

### Problem: Directive closes early

**Symptom:**
```markdown
```{warning}
Text

```python  ← This closes the warning!
```
```

**Solution:** Add one more backtick to outer fence:
```markdown
````{warning}
Text

```python  ← Now this is inner content
```
````
```

### Problem: Nested directive breaks

**Symptom:**
```markdown
````{note}
````{tabs}  ← This breaks!
```

**Solution:** Inner needs fewer backticks:
```markdown
`````{note}
````{tabs}  ← Now it works!
```

### Problem: Visual confusion

**Solution:** Use consistent indentation:
```markdown
`````{warning}
  Main content here.
  
  ````{tabs}
    ### Tab: One
    ```python
    code()
    ```
  ````
`````
```

Indentation is optional but helps readability!

---

## Bengal-Specific Notes

1. **All directives support nesting** - Admonitions, tabs, dropdowns, code-tabs all parse nested markdown via `self.parse_tokens(block, content, state)`

2. **No arbitrary nesting limit** - Use as many levels as needed (though >4 is rare)

3. **Code highlighting works** - Inner code blocks maintain their syntax highlighting

4. **Performance** - Nesting doesn't significantly impact build time

---

## Examples from Bengal Docs

### Documentation Pattern
```markdown
````{note} Installation Note
Install dependencies first:

```bash
pip install bengal-ssg
```

Then build your site:

```bash
bengal build
```
````
```

### Tutorial Pattern
```markdown
`````{tip} Complete Example

Here's a full workflow:

````{tabs}
### Tab: Development
```bash
bengal serve --watch
```

### Tab: Production
```bash
bengal build
bengal deploy
```
````
`````
```

### API Documentation Pattern
```markdown
````{warning} Breaking Change
This method signature changed in v2.0:

```python
# Old (v1.x)
page.render(template)

# New (v2.0)
page.render(template, context={})
```
````
```

---

## Summary

✅ **DO:**
- Count your deepest fence
- Add 1 more backtick for each outer level
- Use 4 backticks as default for admonitions with code
- Test your nesting in build output

❌ **DON'T:**
- Use same number of backticks for nested and outer
- Use fewer backticks for outer than inner
- Forget to close fences with matching backtick count

**Remember:** When in doubt, **add one more backtick to the outer fence**! 🎯

