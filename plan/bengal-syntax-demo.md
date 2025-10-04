# Bengal Syntax Highlighting Demo

This file demonstrates all Bengal directive patterns that need syntax highlighting.

---

## 1. Tabs Directive (Primary Focus)

````{tabs}
:id: example-tabs
:class: custom-class

### Tab: Python

This is Python content with **markdown** support.

```python
def hello():
    print("Hello, Bengal!")
```

### Tab: JavaScript

This is JavaScript content.

```javascript
console.log("Hello, Bengal!");
```

### Tab: TypeScript Example

TypeScript with a longer name.

```typescript
const greeting: string = "Hello, Bengal!";
console.log(greeting);
```
````

**What should be highlighted:**
- ````{tabs}` - Opening fence (yellow/gold)
- `tabs` - Directive name (bold yellow)
- `:id:` - Option key (light blue)
- `example-tabs` - Option value (green)
- `### Tab: Python` - Entire line:
  - `###` - Gray punctuation
  - `Tab:` - Pink/purple keyword (BOLD)
  - `Python` - Orange/yellow tab name (BOLD)

---

## 2. Admonition Directives

### Note Admonition

```{note} This is a Note Title
This is the content of a note admonition.

It can contain **markdown** and `code`.

- Bullet points
- Multiple lines
```

### Tip Admonition

```{tip} Pro Tip!
Use this for helpful suggestions.
```

### Warning Admonition

```{warning} Be Careful!
This is a warning message.
```

### Danger Admonition

```{danger} Critical Warning
This is a danger admonition for serious issues.
```

### Error Admonition

```{error} Error Message
Shows error information.
```

### Info Admonition

```{info} Information
Provides additional context.
```

### Example Admonition

```{example} Code Example
Shows example usage.
```

### Success Admonition

```{success} Success!
Indicates successful completion.
```

### Caution Admonition

```{caution} Proceed with Caution
Be careful here.
```

**What should be highlighted:**
- ``` - Fence markers (gray)
- `{note}`, `{tip}`, etc. - Directive type (yellow/gold, each type can have unique color)
- Title text after directive - Green string

---

## 3. Dropdown Directive

```{dropdown} Click to Expand
:open: false
:class: custom-dropdown

Hidden content goes here.

Can contain **markdown** and code blocks.
```

**Alias: details**

```{details} Another Dropdown
Same as dropdown, just different name.
```

**What should be highlighted:**
- Same pattern as admonitions
- `:open: false` - Option with boolean value

---

## 4. Code Tabs Directive

```{code-tabs}
:id: code-example

### Tab: Python
```python
print("Hello")
```

### Tab: JavaScript
```javascript
console.log("Hello");
```
```

**Alternative spelling:**

```{code_tabs}
Same directive, underscore instead of hyphen.
```

**What should be highlighted:**
- Same as regular tabs directive
- Both `code-tabs` and `code_tabs` variations

---

## 5. Directive Options Patterns

All directives support options with the pattern `:key: value`:

```{tabs}
:id: unique-identifier
:class: custom-class my-other-class
:data-custom: some-value
:open: true

### Tab: Example
Content
```

**Pattern to match:** `^:(\w+):\s*(.*)$`

**What should be highlighted:**
- `:` - Punctuation (gray)
- `id`, `class`, `data-custom`, `open` - Parameter name (light blue)
- `:` - Punctuation (gray)
- Rest of line - String value (green)

---

## 6. Nested Directives

Directives can be nested:

````{tabs}
:id: nested-example

### Tab: With Admonition

```{note} Nested Note
This note is inside a tab!
```

Regular markdown continues here.

### Tab: With Dropdown

```{dropdown} Nested Dropdown
Hidden content in a tab.
```
````

**Important:** Inner directive highlighting should still work!

---

## 7. Edge Cases to Test

### Multiple Tabs Blocks in One File

````{tabs}
:id: first-tabs

### Tab: One
Content
````

Some text between blocks.

````{tabs}
:id: second-tabs

### Tab: Two
More content
````

### Tabs with Special Characters in Names

````{tabs}
### Tab: Python 3.11+
Content

### Tab: Node.js (v18)
Content

### Tab: C++ / C# Examples
Content

### Tab: 🐍 Python with Emoji
Content
````

### Malformed Syntax (Should NOT Highlight)

These should not trigger highlighting (or show as errors):

```
{tabs}  - Missing opening fence
````

````{tabs}
##Tab: Missing space
### Tabs: Wrong keyword
## Tab: Wrong heading level
#### Tab: Wrong heading level
````

---

## 8. Complex Real-World Example

````{tabs}
:id: real-world-example
:class: code-example-tabs

### Tab: Complete Example

Here's a complete example:

```python
# Bengal configuration
site_title = "My Site"
site_url = "https://example.com"
```

**Features:**
- ✅ Feature 1
- ✅ Feature 2
- ✅ Feature 3

```{note} Important
Don't forget to configure this!
```

### Tab: Alternative Approach

You can also do it this way:

```yaml
# YAML config
site:
  title: My Site
  url: https://example.com
```

```{tip} Pro Tip
YAML is more readable for some users.
```

### Tab: Troubleshooting

Common issues:

```{warning} Configuration Error
Check your `bengal.toml` file if you see errors.
```

**Solution:**
1. Check syntax
2. Validate options
3. Restart server
````

---

## Summary of Highlighting Requirements

### Critical Patterns (High Priority)

1. **`### Tab: TabName`** - The most important pattern
   - `###` → gray
   - Space → gray
   - `Tab:` → bold pink/purple
   - Space → gray  
   - `TabName` → bold orange/yellow

2. **Directive opener: ````{tabs}`**
   - ```` → gray
   - `{` → gray
   - `tabs` → bold yellow/gold
   - `}` → gray

3. **Options: `:id: value`**
   - First `:` → gray
   - `id` → light blue
   - Second `:` → gray
   - `value` → green

### All Directive Types to Support

```
tabs, note, tip, warning, danger, error, info, 
example, success, caution, dropdown, details,
code-tabs, code_tabs
```

### Color Scheme Recommendations

| Element | Scope | Suggested Color |
|---------|-------|-----------------|
| Directive name (`tabs`) | `entity.name.function.directive.bengal` | Yellow/Gold (#FFB86C) |
| `{` `}` braces | `punctuation.definition.directive` | Gray (#6272A4) |
| `:id:` key | `variable.parameter.option` | Cyan (#8BE9FD) |
| Option value | `string.unquoted.option.value` | Green (#50FA7B) |
| `Tab:` keyword | `keyword.control.tab.bengal` | Pink (#FF79C6) BOLD |
| Tab name | `entity.name.section.tab.bengal` | Orange (#FFB86C) BOLD |

Colors based on Dracula theme - should adapt to user's theme via scope mapping.

---

## Testing Checklist

When testing the extension, verify:

- [ ] All directive types are highlighted
- [ ] `### Tab:` markers are prominently highlighted
- [ ] Options (`:key: value`) are highlighted
- [ ] Nested markdown still works inside directives
- [ ] Multiple directives in one file all work
- [ ] Works with different VS Code themes
- [ ] Works in Cursor editor
- [ ] Malformed syntax doesn't break highlighting
- [ ] Tab names with special characters work
- [ ] Both `code-tabs` and `code_tabs` work

---

**End of Demo File**

