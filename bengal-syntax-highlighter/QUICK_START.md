# Quick Start Guide

## Test the Extension (1 minute)

1. **Open this folder in VS Code:**
   ```bash
   cd bengal-syntax-highlighter
   code .
   ```

2. **Launch Extension Development Host**
   - **Mac:** Press `Fn+F5` (or `Cmd+Shift+P` → "Debug: Start Debugging")
   - **Windows/Linux:** Press `F5`
   - This launches "Extension Development Host"
   - A new VS Code window opens with the extension loaded

3. **Open the test file:**
   - In the new window: File → Open File
   - Navigate to `examples/test.md`

4. **Verify highlighting:**
   - Directive names (`tabs`, `note`, etc.) should be **yellow/gold**
   - `### Tab:` should be **bold pink**
   - Tab names should be **bold orange**
   - `:id:` keys should be **cyan**
   - Values should be **green**

---

## Install for Daily Use (2 minutes)

### Step 1: Package the Extension

```bash
cd bengal-syntax-highlighter
npm install -g @vscode/vsce
vsce package
```

This creates `bengal-syntax-highlighter-1.0.0.vsix`

### Step 2: Install in VS Code

```bash
code --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

Or use the UI:
- VS Code → Extensions → `...` menu → "Install from VSIX..."

### Step 3: Install in Cursor (Optional)

```bash
cursor --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

### Step 4: Test with Your Files

Open any Bengal markdown file with directives - they should now be highlighted!

---

## Troubleshooting

**Q: Nothing highlights**
- A: Make sure file is recognized as Markdown (check bottom-right corner)
- Try: Reload window (Cmd+R in Extension Development Host, or Cmd+Shift+P → "Reload Window")

**Q: Some patterns don't work**
- A: Check syntax - must be exactly `### Tab:` with spaces

**Q: Colors look weird**
- A: Colors depend on your theme - try a different theme to see variations

**Q: Want to see the scopes?**
- A: Cmd+Shift+P → "Developer: Inspect Editor Tokens and Scopes" → Click on text

---

## What's Next?

1. **Test with real files:** Open your Bengal markdown files
2. **Try different themes:** See how colors adapt
3. **Customize (optional):** Edit `syntaxes/bengal.tmLanguage.json` to adjust patterns
4. **Share:** Distribute the `.vsix` file to your team!

---

## Quick Reference

### Test in development:
```bash
# Open in VS Code
cd bengal-syntax-highlighter
code .

# Press F5 to launch Extension Development Host
# Open examples/test.md to verify highlighting
```

### Package and install:
```bash
# Package
vsce package

# Install in VS Code
code --install-extension bengal-syntax-highlighter-1.0.0.vsix

# Install in Cursor
cursor --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

### Verify it works:
```bash
# Open any Bengal markdown file
# Look for yellow directive names and pink/orange tab markers
```

---

**That's it! Your extension is ready to use! 🎉**
