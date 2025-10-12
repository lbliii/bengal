# 🍎 Mac Quick Start

**For macOS users** - The fastest way to test your extension.

---

## 🚀 Test in 30 Seconds

### Step 1: Open in VS Code
```bash
cd bengal-syntax-highlighter
code .
```

### Step 2: Launch Extension (Choose ONE)

**Option A - Function Key:**
```
Fn + F5
```

**Option B - Command Palette (Recommended):**
```
Cmd + Shift + P
Type: "debug start"
Press: Enter
```

**Option C - Menu:**
```
Click: Run → Start Debugging
```

**Option D - Debug View:**
```
Cmd + Shift + D
Click the green ▶️ play button
```

### Step 3: Open Test File

In the **new window** that opens:
```
Cmd + O
Navigate to: examples/test.md
Open it
```

### Step 4: Verify

You should see colorful syntax highlighting:
- ✅ `tabs` in yellow/gold
- ✅ `### Tab:` in bold pink
- ✅ Tab names in bold orange
- ✅ `:id:` in cyan

---

## 📦 Install for Daily Use

After testing, install it permanently:

```bash
# 1. Install packaging tool (one-time)
npm install -g @vscode/vsce

# 2. Package the extension
vsce package

# 3. Install in VS Code
code --install-extension bengal-syntax-highlighter-1.0.0.vsix

# 4. Optional: Install in Cursor too
cursor --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

---

## 🍎 Mac-Specific Tips

### If Fn+F5 Doesn't Work

Your Mac may have "Use F1, F2, etc. keys as standard function keys" disabled.

**To enable:**
1. System Settings → Keyboard
2. Enable: "Use F1, F2, etc. keys as standard function keys"

**Or just use:** `Cmd+Shift+P` → "Debug: Start Debugging"

### Keyboard Shortcuts Cheat Sheet

| Action | Shortcut |
|--------|----------|
| Open folder in VS Code | `code .` in terminal |
| Command Palette | `Cmd+Shift+P` |
| Debug/Run Extension | `Fn+F5` or palette |
| Open file | `Cmd+O` |
| Extensions view | `Cmd+Shift+X` |
| Reload window | `Cmd+R` (in dev host) |
| Inspect scopes | Palette → "Inspect Editor Tokens" |

### Testing with Your Files

1. Launch Extension Dev Host (`Fn+F5`)
2. In the new window, open your Bengal markdown files
3. Directives will be highlighted immediately!

Try it with:
```bash
# In Extension Development Host window:
Cmd+O
# Navigate to: examples/showcase/content/docs/templates/function-reference/collections.md
```

You'll see all those `### Tab:` markers beautifully highlighted! 🎨

---

## 🐛 Troubleshooting

### "Nothing happens when I press Fn+F5"

Try:
1. `Cmd+Shift+P` → "Debug: Start Debugging"
2. Or use Run menu → Start Debugging
3. Make sure you have the extension folder open in VS Code

### "Extension Development Host opens but no highlighting"

1. Make sure you're opening `.md` files
2. Check bottom-right corner says "Markdown"
3. Reload the window: `Cmd+R`

### "Colors look weird"

Colors adapt to your theme. Try:
- Dark+ (default dark)
- Light+ (default light)
- Dracula
- GitHub Dark

---

## ✅ Quick Verification

Paste this into any `.md` file in the Extension Development Host:

```markdown
````{tabs}
### Tab: Test
Content
````
```

**You should see:**
- `tabs` in yellow/gold
- `Tab:` in bold pink
- `Test` in bold orange

If yes, it's working! 🎉

---

## 🎯 What's Next?

1. **Test with real files** - Open your showcase examples
2. **Install permanently** - Run `vsce package` and install
3. **Share with team** - Send them the `.vsix` file
4. **Enjoy!** - Your markdown files are now prettier! 🎨

---

**Total time:** 30 seconds to test, 2 minutes to install

**Ready?** Run `code .` in the extension folder and press `Fn+F5`! 🚀
