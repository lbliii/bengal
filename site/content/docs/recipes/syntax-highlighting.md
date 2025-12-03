---
title: Customize Syntax Highlighting
description: Configure code block themes and languages
weight: 50
draft: false
lang: en
tags: [recipe, syntax-highlighting, code, pygments]
keywords: [syntax highlighting, code blocks, pygments, theme]
category: recipe
---

# Customize Syntax Highlighting

Configure syntax highlighting themes and options for code blocks.

## Time Required

⏱️ 5 minutes

## What You'll Build

- Custom syntax highlighting theme
- Line numbers and highlighting
- Copy-to-clipboard button

## Step 1: Choose a Theme

Bengal uses Pygments for syntax highlighting. Available themes:

- `monokai` — Dark theme (popular)
- `dracula` — Dark purple theme
- `github-dark` — GitHub dark mode
- `one-dark` — Atom One Dark
- `solarized-dark` — Solarized Dark
- `solarized-light` — Solarized Light
- `friendly` — Light theme
- `vs` — Visual Studio light

Configure in `bengal.toml`:

```toml
[markup.highlight]
theme = "monokai"
line_numbers = false
line_number_style = "table"  # or "inline"
```

## Step 2: Enable Line Numbers

Show line numbers on code blocks:

```toml
[markup.highlight]
line_numbers = true
```

Or per-block in Markdown:

````markdown
```python {linenos=true}
def hello():
    print("Hello, World!")
```
````

## Step 3: Highlight Specific Lines

Draw attention to specific lines:

````markdown
```python {hl_lines="2 4"}
def example():
    important_line()  # Highlighted
    regular_line()
    another_important()  # Highlighted
```
````

## Step 4: Add Copy Button

Add a copy-to-clipboard button:

```javascript
// static/js/copy-code.js
document.querySelectorAll('pre').forEach(pre => {
  const button = document.createElement('button');
  button.className = 'copy-button';
  button.textContent = 'Copy';
  
  button.addEventListener('click', async () => {
    const code = pre.querySelector('code').textContent;
    await navigator.clipboard.writeText(code);
    button.textContent = 'Copied!';
    setTimeout(() => button.textContent = 'Copy', 2000);
  });
  
  pre.style.position = 'relative';
  pre.appendChild(button);
});
```

Style the button:

```css
/* static/css/code.css */
.copy-button {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

pre:hover .copy-button {
  opacity: 1;
}

.copy-button:hover {
  background: rgba(255, 255, 255, 0.2);
}
```

## Custom Theme CSS

Override theme colors with CSS:

```css
/* static/css/code-override.css */
.highlight {
  background: #1e1e1e !important;
  border-radius: 8px;
  padding: 1rem;
}

.highlight .k { color: #569cd6; }  /* Keywords */
.highlight .s { color: #ce9178; }  /* Strings */
.highlight .c { color: #6a9955; }  /* Comments */
.highlight .n { color: #9cdcfe; }  /* Names */
```

## Result

Your code blocks now have:
- ✅ Custom syntax theme
- ✅ Optional line numbers
- ✅ Line highlighting
- ✅ Copy-to-clipboard button

## See Also

- [Content Authoring](/docs/content/authoring/) — Code block syntax
- [Theming](/docs/theming/) — Theme customization

