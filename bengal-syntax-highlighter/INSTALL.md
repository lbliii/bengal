# Installation Instructions

## ⚡ Quick Install (Recommended)

### Step 1: Test It First (30 seconds)

Open this folder in VS Code and launch the Extension Development Host:

```bash
cd bengal-syntax-highlighter
code .
# Mac: Press Fn+F5 (or Cmd+Shift+P → "Debug: Start Debugging")
# Windows/Linux: Press F5
# Open examples/test.md in the new window
```

You should see:
- ✅ Yellow/gold directive names (`tabs`, `note`, etc.)
- ✅ Bold pink `Tab:` keywords
- ✅ Bold orange tab names
- ✅ Cyan option keys
- ✅ Green option values

### Step 2: Package It (1 minute)

```bash
# Install packaging tool (one-time only)
npm install -g @vscode/vsce

# Package the extension
vsce package
```

This creates: `bengal-syntax-highlighter-1.0.0.vsix`

### Step 3: Install It (30 seconds)

**For VS Code:**
```bash
code --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

**For Cursor:**
```bash
cursor --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

**Or use the UI:**
1. Open VS Code/Cursor
2. Go to Extensions (Cmd+Shift+X)
3. Click `...` menu (top right)
4. Select "Install from VSIX..."
5. Choose `bengal-syntax-highlighter-1.0.0.vsix`

### Step 4: Verify It Works

1. Open any Bengal markdown file
2. Add a tabs directive:
   ````markdown
   ````{tabs}
   ### Tab: Test
   ````
   ```
3. The highlighting should appear immediately!

---

## 📦 What You Just Installed

The extension adds syntax highlighting for:

### ✨ Tabs Directive (The Main Feature!)

```markdown
````{tabs}               ← YELLOW directive
:id: example            ← CYAN key, GREEN value

### Tab: Python         ← PINK "Tab:", ORANGE "Python" (bold)
Content here

### Tab: JavaScript     ← Easy to scan!
More content
````
```

### 📝 All Admonitions

```markdown
```{note} Important     ← YELLOW + GREEN
```{warning} Alert      ← YELLOW + GREEN
```{tip} Helpful        ← YELLOW + GREEN
```

### 🎯 Everything Else

- Dropdowns (`{dropdown}`, `{details}`)
- Code tabs (`{code-tabs}`, `{code_tabs}`)
- All directive options (`:key: value`)

---

## 🎨 How It Looks

Colors adapt to your theme, but typically:

| Element | Color | Style |
|---------|-------|-------|
| `tabs`, `note`, etc. | Yellow/Gold | Normal |
| `Tab:` keyword | Pink/Purple | **Bold** |
| Tab names | Orange | **Bold** |
| `:id:` keys | Cyan | Normal |
| Values | Green | Normal |

**The key win:** `### Tab:` markers **stand out** instead of looking like regular headings!

---

## 🔧 Troubleshooting

### Highlighting doesn't appear

1. **Check file type**: Bottom-right corner should say "Markdown"
2. **Reload window**: Cmd+Shift+P → "Developer: Reload Window"
3. **Restart editor**: Quit and reopen VS Code/Cursor

### Some patterns don't highlight

Check your syntax:
- ✅ `### Tab: Name` (correct - with spaces)
- ❌ `###Tab: Name` (missing space after ###)
- ❌ `### Tabs: Name` (wrong keyword)
- ❌ `## Tab: Name` (wrong heading level)

### Want to see what's happening?

Use the scope inspector:
1. Cmd+Shift+P → "Developer: Inspect Editor Tokens and Scopes"
2. Click on any text to see its scopes
3. Bengal scopes end with `.bengal`

---

## 🚀 Advanced Usage

### Uninstall

```bash
code --uninstall-extension bengal-ssg.bengal-syntax-highlighter
```

### Update

1. Make changes to `syntaxes/bengal.tmLanguage.json`
2. Increment version in `package.json`
3. Re-run `vsce package`
4. Install the new `.vsix` file

### Share with Team

Just send them the `.vsix` file:
```bash
# They install it with:
code --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

### Publish to Marketplace (Optional)

To share with the world:

1. Create publisher account: https://marketplace.visualstudio.com/manage
2. Get Personal Access Token from Azure DevOps
3. Login: `vsce login your-publisher-name`
4. Publish: `vsce publish`

---

## ✅ Success Checklist

After installation, verify:

- [ ] Opened a Bengal markdown file
- [ ] `````{tabs}``` directive names are yellow/gold
- [ ] `### Tab:` markers are bold pink + orange
- [ ] `:id:` options are cyan + green
- [ ] Admonitions (`{note}`, etc.) are highlighted
- [ ] Works in both VS Code and Cursor (if you use both)

---

## 🎉 You're Done!

Your Bengal markdown files should now be **much easier** to read and navigate!

**Key benefits:**
- 🔍 Spot directive boundaries instantly
- 📑 Scan tab names effortlessly
- ✏️ Catch syntax errors visually
- 💼 More professional editing experience

Enjoy your new syntax highlighting! 🚀

---

## 📞 Need Help?

Check these files:
- `README.md` - Full documentation
- `QUICK_START.md` - Fast setup guide
- `examples/test.md` - Test all features

Or open an issue on the Bengal SSG repository.

