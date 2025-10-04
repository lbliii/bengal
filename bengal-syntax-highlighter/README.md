# Bengal SSG Syntax Highlighter

A Visual Studio Code extension that provides beautiful syntax highlighting for Bengal SSG markdown directives.

## ✨ Features

This extension enhances your Bengal markdown files with syntax highlighting for:

- **Tabs directive** with prominent `### Tab:` markers
- **Admonitions** (note, tip, warning, danger, error, info, example, success, caution)
- **Dropdown/Details** collapsible sections
- **Code-tabs** for multi-language examples
- **Directive options** (`:id:`, `:open:`, etc.)

### Before and After

**Without Extension:**
```markdown
````{tabs}
:id: my-tabs
### Tab: Python
Content here
````
```
Everything looks like plain text.

**With Extension:**
```markdown
````{tabs}           ← Yellow/gold directive name
:id: my-tabs        ← Cyan key, green value
### Tab: Python     ← Pink "Tab:", orange "Python" (both bold!)
Content here
````
```
Structure is immediately obvious!

## 🚀 Installation

### Method 1: Install from VSIX (Recommended)

1. Package the extension:
   ```bash
   cd bengal-syntax-highlighter
   npm install -g @vscode/vsce
   vsce package
   ```

2. Install the generated `.vsix` file:
   ```bash
   # In VS Code or Cursor
   code --install-extension bengal-syntax-highlighter-1.0.0.vsix
   ```

   Or use VS Code UI:
   - Open Extensions view (`Cmd+Shift+X`)
   - Click `...` menu
   - Choose "Install from VSIX..."
   - Select the `.vsix` file

### Method 2: Development Mode

1. Open this folder in VS Code
2. Launch Extension Development Host:
   - **Mac:** Press `Fn+F5` or `Cmd+Shift+P` → "Debug: Start Debugging"
   - **Windows/Linux:** Press `F5`
3. Open any `.md` file with Bengal directives

## 🎨 What Gets Highlighted

### Tabs Directive

The most important feature - makes tab markers stand out:

```markdown
````{tabs}
:id: example-tabs

### Tab: Python      ← "Tab:" in bold pink, name in bold orange
Python content

### Tab: JavaScript  ← Easy to scan and find!
JavaScript content
````
```

### Admonitions

All 9 admonition types:

```markdown
```{note} Important Note
Content with title highlighted
```

```{warning} Be Careful!
Warning content
```

```{tip} Pro Tip
Helpful suggestion
```
```

### Dropdowns

```markdown
```{dropdown} Click to Expand
:open: false

Hidden content
```
```

### Directive Options

```markdown
:id: unique-identifier     ← "id" in cyan, value in green
:class: custom-class       ← Clear key-value pairs
:open: true
```

## 🎯 Key Highlights

### `### Tab:` Markers (Most Important!)

The extension makes tab markers **instantly visible**:
- `Tab:` keyword in **bold pink/purple**
- Tab name in **bold orange**
- Stands out from regular markdown headings

### Color Scheme

Colors adapt to your theme, but typically:

| Element | Color | Why |
|---------|-------|-----|
| Directive name (`tabs`, `note`) | Yellow/Gold | Like function names |
| `Tab:` keyword | Pink/Purple | Stands out, bold |
| Tab names | Orange | Easy to scan, bold |
| Option keys (`:id:`) | Cyan | Like parameters |
| Option values | Green | Like strings |
| Punctuation | Gray | Subtle |

## 🧪 Testing

Open `examples/test.md` in VS Code to see all directive types highlighted.

To verify highlighting is working:
1. Open any Bengal markdown file
2. Add a tabs directive
3. The `### Tab:` markers should be prominently colored

To debug scopes:
1. Open Command Palette (`Cmd+Shift+P`)
2. Run: `Developer: Inspect Editor Tokens and Scopes`
3. Click on any highlighted token to see its scope

## 📦 Compatibility

- **VS Code:** Version 1.74.0+ (Nov 2022 or later)
- **Cursor:** ✅ Fully compatible (Cursor is a VS Code fork)
- **Themes:** Works with all themes (uses standard scope names)

## 🔧 Development

### Project Structure

```
bengal-syntax-highlighter/
├── package.json                    # Extension manifest
├── syntaxes/
│   └── bengal.tmLanguage.json     # TextMate grammar
├── examples/
│   └── test.md                    # Test file
└── README.md                      # This file
```

### Making Changes

1. Edit `syntaxes/bengal.tmLanguage.json` to modify patterns
2. Press `Cmd+R` in Extension Development Host to reload
3. Test changes immediately

### Grammar Structure

The grammar uses an **injection pattern** to add highlighting to existing Markdown files without requiring a new file extension.

Key patterns:
- `bengal-tabs-directive` - Tabs with `### Tab:` markers
- `bengal-admonition-directive` - All 9 admonition types
- `bengal-dropdown-directive` - Dropdown/details
- `bengal-code-tabs-directive` - Code tabs
- `directive-options` - `:key: value` options
- `tab-markers` - The critical `### Tab: Name` pattern

## 🐛 Troubleshooting

### Highlighting Not Working

1. **Check file is recognized as Markdown**
   - Look at bottom-right corner of VS Code
   - Should say "Markdown"

2. **Reload window**
   - Command Palette → "Developer: Reload Window"

3. **Verify extension is active**
   - Extensions view → Search "Bengal"
   - Should show "Bengal SSG Syntax Highlighter" as enabled

4. **Test with simple example**
   ```markdown
   ````{tabs}
   ### Tab: Test
   ````
   ```
   If `tabs` isn't yellow/gold and `Tab:` isn't pink, something's wrong.

### Some Patterns Don't Highlight

Check for syntax errors:
- `###Tab: Name` ❌ (missing space after ###)
- `### Tab:Name` ❌ (missing space after colon)
- `### Tab: Name` ✅ (correct!)

## 📝 License

MIT License - See parent project for details

## 🤝 Contributing

This extension is part of the Bengal SSG project. Contributions welcome!

To add new directive types:
1. Add pattern to `syntaxes/bengal.tmLanguage.json`
2. Test with examples
3. Update README

## 🔗 Links

- [Bengal SSG](https://github.com/yourusername/bengal)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [TextMate Grammars](https://macromates.com/manual/en/language_grammars)

## 💡 Tips

### Maximize the Benefit

1. **Use consistent tab naming** - Makes scanning easier
2. **Add IDs to tabs** - Good practice, and the `:id:` will be highlighted
3. **Nest directives** - Works! Admonitions inside tabs highlight correctly

### Keyboard Shortcuts

Create snippets for common directives:

```json
{
  "Bengal Tabs": {
    "prefix": "btabs",
    "body": [
      "````{tabs}",
      ":id: ${1:tab-id}",
      "",
      "### Tab: ${2:First}",
      "${3:Content}",
      "",
      "### Tab: ${4:Second}",
      "${5:Content}",
      "````"
    ]
  }
}
```

## 🎉 Enjoy!

Your Bengal markdown files should now be much easier to read and navigate!

If you find this useful, consider:
- ⭐ Starring the Bengal SSG project
- 🐛 Reporting issues
- 💡 Suggesting improvements

