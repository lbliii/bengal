# Bengal Syntax Highlighting Test

This file tests all Bengal directive patterns.

## 1. Tabs Directive (Primary Feature)

````{tabs}
:id: test-tabs
:class: example-tabs

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

### Tab: TypeScript

TypeScript example.

```typescript
const greeting: string = "Hello!";
```
````

**Expected:** `tabs` in yellow, `:id:` in cyan, `### Tab:` in pink, tab names in orange.

---

## 2. All Admonition Types

### Note

```{note} This is a Note
Important information goes here.
```

### Tip

```{tip} Pro Tip!
Helpful suggestion.
```

### Warning

```{warning} Be Careful
Warning message.
```

### Danger

```{danger} Critical Warning
Serious issue.
```

### Error

```{error} Error Message
Error details.
```

### Info

```{info} Information
Additional context.
```

### Example

```{example} Code Example
Example usage.
```

### Success

```{success} Success!
Task completed.
```

### Caution

```{caution} Proceed with Caution
Be careful.
```

**Expected:** Each directive type in yellow/gold, titles in green.

---

## 3. Dropdown/Details

```{dropdown} Click to Expand
:open: false
:class: custom-dropdown

Hidden content here.
```

```{details} Alternative Name
Same as dropdown.
```

**Expected:** Same highlighting as admonitions.

---

## 4. Code Tabs

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

**Expected:** Same tab marker highlighting.

---

## 5. Nested Directives

````{tabs}
:id: nested-example

### Tab: With Admonition

```{note} Nested Note
This note is inside a tab!
```

Regular content continues.

### Tab: With Dropdown

```{dropdown} Nested Dropdown
Hidden content.
```
````

**Expected:** Both outer tabs and inner directives should highlight.

---

## 6. Multiple Options

```{tabs}
:id: unique-identifier
:class: custom-class another-class
:data-custom: some-value
:open: true

### Tab: Example
Content with many options.
````

**Expected:** Each option line highlighted (cyan keys, green values).

---

## 7. Edge Cases

### Correct Syntax (Should Highlight)

````{tabs}
### Tab: With Emoji 🐍
### Tab: With (Parentheses)
### Tab: With-Dashes
### Tab: Multiple Words Here
````

### Incorrect Syntax (Should NOT Highlight)

These should remain plain text:

```
###Tab: Missing space
### Tabs: Wrong keyword
## Tab: Wrong level
```

---

## 8. Real-World Example

````{tabs}
:id: installation-guide
:class: guide-tabs

### Tab: macOS

Install using Homebrew:

```bash
brew install bengal-ssg
```

```{tip} Recommended
macOS users should use Homebrew for easy updates.
```

### Tab: Linux

Install using pip:

```bash
pip install bengal-ssg
```

```{warning} Python Version
Requires Python 3.11 or higher.
```

### Tab: Windows

Download from releases:

```powershell
# Download and install
```

```{note} WSL Recommended
Consider using WSL for better compatibility.
```
````

---

## Testing Checklist

Open this file in VS Code/Cursor and verify:

- [ ] `tabs` directive name is **yellow/gold**
- [ ] `### Tab:` keyword is **bold pink/purple**
- [ ] Tab names are **bold orange**
- [ ] `:id:` and other option keys are **cyan**
- [ ] Option values are **green**
- [ ] All 9 admonition types highlight
- [ ] Nested directives work
- [ ] Dropdown/details work
- [ ] Code-tabs work
- [ ] Incorrect syntax doesn't highlight

## Scope Inspection

To verify scopes are correct:

1. Open Command Palette (`Cmd+Shift+P`)
2. Run: `Developer: Inspect Editor Tokens and Scopes`
3. Click on any highlighted element
4. Should see scopes like:
   - `entity.name.function.directive.bengal` (directive names)
   - `keyword.control.tab.bengal` (Tab: keyword)
   - `entity.name.section.tab.bengal` (tab names)
   - `variable.parameter.option.bengal` (option keys)

---

**If everything highlights correctly, the extension is working! 🎉**

