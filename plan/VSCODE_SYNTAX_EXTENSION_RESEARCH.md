# VS Code Syntax Highlighting Extension for Bengal - Research

**Date:** October 4, 2025  
**Status:** Research Complete - Ready to Implement  
**Priority:** High (Developer Experience Enhancement)

---

## 🎯 Objective

Create a VS Code extension that provides syntax highlighting for Bengal's custom markdown directives, with special focus on the `tabs` directive and its `### Tab: TabName` declarations. The extension must work seamlessly in both VS Code and Cursor.

---

## 📋 What Needs Highlighting

### 1. **Directive Fences** (Primary Focus)

```markdown
````{tabs}
:id: my-tabs

### Tab: Python
Content here

### Tab: JavaScript  
More content
````
```

**Elements to highlight:**
- ````{tabs}` - Opening fence with directive type
- `:id: my-tabs` - Directive options
- `### Tab: Python` - Tab markers (CRITICAL)
- ```` - Closing fence

### 2. **All Directive Types**

From `bengal/rendering/plugins/directives/validator.py`:
```python
KNOWN_DIRECTIVES = {
    'tabs', 'note', 'tip', 'warning', 'danger', 'error',
    'info', 'example', 'success', 'caution', 'dropdown',
    'details', 'code-tabs', 'code_tabs'
}
```

**Admonition Example:**
```markdown
```{note} This is a Note
Content with **markdown** support
```
```

**Dropdown Example:**
```markdown
```{dropdown} Click to expand
:open: true

Hidden content here
```
```

### 3. **Directive Options Pattern**

Options always follow the pattern `:key: value`:
```markdown
:id: unique-identifier
:open: true
:class: custom-class
```

### 4. **Tab Markers in Tabs Directive**

The regex pattern from the code: `^### Tab: (.+)$`

Critical patterns:
- `### Tab: Python` ✅
- `### Tab: JavaScript Example` ✅
- `###Tab: Broken` ❌ (missing space)
- `## Tab: Wrong` ❌ (wrong heading level)

---

## 🏗️ Extension Architecture

### Approach: **Markdown Injection Grammar**

We'll use an **injection grammar** rather than a standalone language because:
1. ✅ Works within existing `.md` files (no file extension changes needed)
2. ✅ Preserves all standard Markdown highlighting
3. ✅ Can be combined with other Markdown extensions
4. ✅ Easier to test and maintain

### Key Concept: Injection Grammars

From VS Code docs, injection grammars:
- Add patterns to an existing language scope
- Use `injectTo` to specify target language(s)
- Don't require file extension mapping
- Perfect for extending Markdown

---

## 📁 Extension File Structure

```
bengal-syntax-highlighter/
├── package.json                    # Extension manifest
├── README.md                       # User documentation
├── CHANGELOG.md                    # Version history
├── .vscodeignore                   # Files to exclude from package
├── syntaxes/
│   └── bengal.tmLanguage.json     # TextMate grammar
├── themes/
│   └── bengal-colors.json         # Optional: suggested color theme
└── examples/
    └── demo.md                    # Demo file for testing
```

---

## 🎨 TextMate Grammar Structure

### Complete Grammar File

**File:** `syntaxes/bengal.tmLanguage.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
  "scopeName": "markdown.bengal.injection",
  "injectionSelector": "L:text.html.markdown",
  "patterns": [
    {
      "include": "#bengal-tabs-directive"
    },
    {
      "include": "#bengal-admonition-directive"
    },
    {
      "include": "#bengal-dropdown-directive"
    },
    {
      "include": "#bengal-code-tabs-directive"
    }
  ],
  "repository": {
    "bengal-tabs-directive": {
      "patterns": [
        {
          "name": "meta.embedded.block.bengal.tabs",
          "begin": "^(````)(\\{)(tabs)(\\})",
          "end": "^(````)",
          "beginCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.begin.bengal"
            },
            "2": {
              "name": "punctuation.definition.directive.begin.bengal"
            },
            "3": {
              "name": "entity.name.function.directive.bengal"
            },
            "4": {
              "name": "punctuation.definition.directive.end.bengal"
            }
          },
          "endCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.end.bengal"
            }
          },
          "patterns": [
            {
              "include": "#directive-options"
            },
            {
              "include": "#tab-markers"
            },
            {
              "include": "text.html.markdown"
            }
          ]
        }
      ]
    },
    "bengal-admonition-directive": {
      "patterns": [
        {
          "name": "meta.embedded.block.bengal.admonition",
          "begin": "^(```)(\\{)(note|tip|warning|danger|error|info|example|success|caution)(\\})\\s*(.*)?$",
          "end": "^(```)",
          "beginCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.begin.bengal"
            },
            "2": {
              "name": "punctuation.definition.directive.begin.bengal"
            },
            "3": {
              "name": "entity.name.function.directive.admonition.bengal"
            },
            "4": {
              "name": "punctuation.definition.directive.end.bengal"
            },
            "5": {
              "name": "string.unquoted.directive.title.bengal"
            }
          },
          "endCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.end.bengal"
            }
          },
          "patterns": [
            {
              "include": "#directive-options"
            },
            {
              "include": "text.html.markdown"
            }
          ]
        }
      ]
    },
    "bengal-dropdown-directive": {
      "patterns": [
        {
          "name": "meta.embedded.block.bengal.dropdown",
          "begin": "^(```)(\\{)(dropdown|details)(\\})\\s*(.*)?$",
          "end": "^(```)",
          "beginCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.begin.bengal"
            },
            "2": {
              "name": "punctuation.definition.directive.begin.bengal"
            },
            "3": {
              "name": "entity.name.function.directive.dropdown.bengal"
            },
            "4": {
              "name": "punctuation.definition.directive.end.bengal"
            },
            "5": {
              "name": "string.unquoted.directive.title.bengal"
            }
          },
          "endCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.end.bengal"
            }
          },
          "patterns": [
            {
              "include": "#directive-options"
            },
            {
              "include": "text.html.markdown"
            }
          ]
        }
      ]
    },
    "bengal-code-tabs-directive": {
      "patterns": [
        {
          "name": "meta.embedded.block.bengal.code-tabs",
          "begin": "^(```)(\\{)(code-tabs|code_tabs)(\\})",
          "end": "^(```)",
          "beginCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.begin.bengal"
            },
            "2": {
              "name": "punctuation.definition.directive.begin.bengal"
            },
            "3": {
              "name": "entity.name.function.directive.code-tabs.bengal"
            },
            "4": {
              "name": "punctuation.definition.directive.end.bengal"
            }
          },
          "endCaptures": {
            "1": {
              "name": "punctuation.definition.markdown.code.end.bengal"
            }
          },
          "patterns": [
            {
              "include": "#directive-options"
            },
            {
              "include": "text.html.markdown"
            }
          ]
        }
      ]
    },
    "directive-options": {
      "patterns": [
        {
          "name": "meta.directive.option.bengal",
          "match": "^(:)(\\w+)(:)\\s*(.*)$",
          "captures": {
            "1": {
              "name": "punctuation.definition.option.begin.bengal"
            },
            "2": {
              "name": "variable.parameter.option.bengal"
            },
            "3": {
              "name": "punctuation.definition.option.end.bengal"
            },
            "4": {
              "name": "string.unquoted.option.value.bengal"
            }
          }
        }
      ]
    },
    "tab-markers": {
      "patterns": [
        {
          "name": "meta.tab.marker.bengal",
          "match": "^(###)(\\s+)(Tab:)(\\s+)(.+)$",
          "captures": {
            "1": {
              "name": "punctuation.definition.heading.bengal"
            },
            "2": {
              "name": "punctuation.whitespace.bengal"
            },
            "3": {
              "name": "keyword.control.tab.bengal"
            },
            "4": {
              "name": "punctuation.whitespace.bengal"
            },
            "5": {
              "name": "entity.name.section.tab.bengal"
            }
          }
        }
      ]
    }
  }
}
```

### Scope Naming Convention

Following TextMate scope naming conventions:

| Element | Scope | Typical Color |
|---------|-------|---------------|
| Directive type (`tabs`, `note`) | `entity.name.function.directive.bengal` | Yellow/Gold |
| Braces `{` `}` | `punctuation.definition.directive` | Gray |
| Option keys (`:id:`) | `variable.parameter.option` | Light Blue |
| Option values | `string.unquoted.option.value` | Green |
| `Tab:` keyword | `keyword.control.tab.bengal` | Purple/Pink |
| Tab names | `entity.name.section.tab.bengal` | Orange/Yellow |

---

## 📦 Package.json Configuration

**File:** `package.json`

```json
{
  "name": "bengal-syntax-highlighter",
  "displayName": "Bengal SSG Syntax Highlighter",
  "description": "Syntax highlighting for Bengal SSG markdown directives including tabs, admonitions, and dropdowns",
  "version": "1.0.0",
  "publisher": "bengal-ssg",
  "author": {
    "name": "Bengal SSG Team"
  },
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/your-org/bengal-syntax-highlighter"
  },
  "engines": {
    "vscode": "^1.74.0"
  },
  "categories": [
    "Programming Languages"
  ],
  "keywords": [
    "bengal",
    "ssg",
    "markdown",
    "syntax",
    "highlighting",
    "directives",
    "tabs",
    "admonitions"
  ],
  "activationEvents": [
    "onLanguage:markdown"
  ],
  "contributes": {
    "grammars": [
      {
        "scopeName": "markdown.bengal.injection",
        "path": "./syntaxes/bengal.tmLanguage.json",
        "injectTo": [
          "text.html.markdown"
        ]
      }
    ]
  },
  "icon": "images/bengal-icon.png",
  "galleryBanner": {
    "color": "#1e1e1e",
    "theme": "dark"
  }
}
```

### Key Fields Explained

- **`injectTo`**: Injects grammar into existing Markdown files
- **`activationEvents`**: Extension activates when a Markdown file is opened
- **`scopeName`**: Must match the `scopeName` in the grammar file
- **`engines.vscode`**: Minimum VS Code version (1.74.0 = Nov 2022, widely supported)

---

## 🧪 Testing Strategy

### Local Development Testing

1. **Setup**:
   ```bash
   cd bengal-syntax-highlighter
   npm install
   ```

2. **Launch Extension Development Host**:
   - Open extension folder in VS Code
   - Press `F5` (or Run > Start Debugging)
   - New VS Code window opens with extension loaded

3. **Test Files**:
   Create `examples/demo.md` with all directive types:
   ```markdown
   # Bengal Syntax Test
   
   ## Tabs Directive
   ````{tabs}
   :id: test-tabs
   
   ### Tab: Python
   Python code here
   
   ### Tab: JavaScript
   JavaScript code here
   ````
   
   ## Admonitions
   ```{note} Important Note
   This is a note directive
   ```
   
   ```{warning} Warning!
   This is a warning
   ```
   
   ## Dropdown
   ```{dropdown} Click me
   :open: false
   
   Hidden content
   ```
   ```

4. **Visual Verification**:
   - Open `demo.md` in the Extension Development Host
   - Verify colors match expected scopes
   - Test with different themes (Dark+, Light+, GitHub themes)

### Debugging TextMate Grammar

Use **Developer: Inspect Editor Tokens and Scopes**:
1. In Extension Development Host, open Command Palette
2. Run: `Developer: Inspect Editor Tokens and Scopes`
3. Click on any token to see its scopes
4. Verify scopes match your grammar definitions

### Automated Testing (Optional)

Create `tests/grammar.test.js`:
```javascript
const vscode = require('vscode');
const assert = require('assert');

suite('Bengal Grammar Test Suite', () => {
  test('Tabs directive is recognized', async () => {
    const doc = await vscode.workspace.openTextDocument({
      language: 'markdown',
      content: '````{tabs}\n### Tab: Test\n````'
    });
    // Add token inspection logic
  });
});
```

---

## 📤 Packaging and Distribution

### Local Installation (VSIX)

1. **Install VSCE**:
   ```bash
   npm install -g @vscode/vsce
   ```

2. **Package Extension**:
   ```bash
   cd bengal-syntax-highlighter
   vsce package
   ```
   
   Output: `bengal-syntax-highlighter-1.0.0.vsix`

3. **Install Locally**:
   ```bash
   # Via command line
   code --install-extension bengal-syntax-highlighter-1.0.0.vsix
   
   # Or via VS Code UI:
   # Extensions → ... → Install from VSIX
   ```

4. **Test in Cursor**:
   ```bash
   # Cursor should accept the same .vsix file
   cursor --install-extension bengal-syntax-highlighter-1.0.0.vsix
   ```

### Publishing to Marketplace (Optional)

1. **Create Publisher Account**:
   - Visit: https://marketplace.visualstudio.com/manage
   - Create Microsoft account if needed
   - Create publisher ID

2. **Get Personal Access Token**:
   - Azure DevOps: https://dev.azure.com/
   - Create PAT with "Marketplace (Publish)" scope

3. **Publish**:
   ```bash
   vsce login your-publisher-name
   vsce publish
   ```

---

## 🎯 Cursor Compatibility

### Guaranteed Compatibility

**Cursor is a fork of VS Code**, so extensions work identically:
- ✅ Same extension API
- ✅ Same TextMate grammar engine
- ✅ Same `.vsix` package format
- ✅ Same theme integration

### Testing in Cursor

1. Install extension in Cursor same as VS Code
2. Test with the same `demo.md` file
3. Verify colors render correctly

### Distribution for Cursor Users

Options:
1. **Direct VSIX**: Share `.vsix` file, users install manually
2. **VS Code Marketplace**: Cursor can install from marketplace
3. **OpenVSX Registry**: Alternative marketplace (optional)

---

## 🎨 Color Theme Considerations

### Default Behavior

The grammar defines **scopes**, themes define **colors** for those scopes.

Common scope → color mappings:
- `entity.name.function` → Yellow/Gold (e.g., function names)
- `keyword.control` → Pink/Purple (e.g., keywords)
- `variable.parameter` → Light Blue (e.g., parameters)
- `string` → Green (e.g., strings)
- `punctuation` → Gray (e.g., brackets)

### Custom Theme (Optional)

If users want Bengal-specific colors, create `themes/bengal-colors.json`:

```json
{
  "name": "Bengal Enhanced",
  "type": "dark",
  "colors": {},
  "tokenColors": [
    {
      "scope": "entity.name.function.directive.bengal",
      "settings": {
        "foreground": "#FFB86C",
        "fontStyle": "bold"
      }
    },
    {
      "scope": "keyword.control.tab.bengal",
      "settings": {
        "foreground": "#FF79C6",
        "fontStyle": "bold italic"
      }
    },
    {
      "scope": "entity.name.section.tab.bengal",
      "settings": {
        "foreground": "#50FA7B",
        "fontStyle": "bold"
      }
    }
  ]
}
```

Add to `package.json`:
```json
"contributes": {
  "themes": [
    {
      "label": "Bengal Enhanced",
      "uiTheme": "vs-dark",
      "path": "./themes/bengal-colors.json"
    }
  ]
}
```

---

## ⚠️ Potential Issues and Solutions

### Issue 1: Grammar Not Activating

**Symptom:** No highlighting appears

**Solutions:**
1. Check `scopeName` matches in both files
2. Verify `injectTo` includes `text.html.markdown`
3. Reload window (`Cmd/Ctrl + R` in Extension Development Host)
4. Check file is recognized as Markdown (bottom right corner)

### Issue 2: Regex Not Matching

**Symptom:** Some patterns don't highlight

**Solutions:**
1. Use Developer: Inspect Editor Tokens and Scopes
2. Test regex at https://regex101.com/ with sample text
3. Check for escaping issues (`\{` vs `{`)
4. Verify multiline flags if needed

### Issue 3: Nested Content Not Highlighting

**Symptom:** Markdown inside directives loses highlighting

**Solution:**
Include standard Markdown in patterns:
```json
"patterns": [
  {"include": "#directive-options"},
  {"include": "#tab-markers"},
  {"include": "text.html.markdown"}  // ← This line
]
```

### Issue 4: Conflicts with Other Extensions

**Symptom:** Highlighting breaks with certain extensions

**Solutions:**
1. Test with extensions disabled
2. Adjust injection priority (not always possible)
3. Report to conflicting extension

---

## 📊 Complexity Assessment

### Overall Difficulty: **MEDIUM (2-3 days)**

| Task | Complexity | Time Estimate |
|------|------------|---------------|
| Project setup with Yeoman | Easy | 30 minutes |
| Writing TextMate grammar | Medium | 4-6 hours |
| Testing and iteration | Medium | 3-4 hours |
| Documentation | Easy | 2 hours |
| Packaging | Easy | 1 hour |
| **Total** | | **10-13 hours** |

### Skills Required

✅ **You have:**
- Understanding of regex patterns
- Familiarity with JSON
- Knowledge of Bengal's syntax

🔶 **Learn as you go:**
- TextMate scope conventions
- VS Code extension structure
- VSCE tooling

❌ **Not needed:**
- Advanced programming (mostly JSON/regex)
- VS Code extension API knowledge (no TypeScript needed)
- Complex build tooling

---

## 🚀 Next Steps

### Phase 1: Minimal Viable Extension (4 hours)

1. ✅ Setup project with Yeoman
2. ✅ Create grammar for `tabs` directive only
3. ✅ Highlight `### Tab:` markers
4. ✅ Test with demo file

### Phase 2: Full Directive Support (3 hours)

1. ✅ Add all admonition types
2. ✅ Add dropdown/details
3. ✅ Add code-tabs
4. ✅ Add directive options (`:id:` etc.)

### Phase 3: Polish and Distribute (3 hours)

1. ✅ Test with multiple themes
2. ✅ Write README with screenshots
3. ✅ Package as VSIX
4. ✅ Test in both VS Code and Cursor
5. ✅ Distribute to team

### Phase 4: Optional Enhancements

- [ ] Custom color theme
- [ ] IntelliSense/autocomplete for directives
- [ ] Validation warnings for malformed directives
- [ ] Publish to marketplace

---

## 📚 References

### Official Documentation

- **VS Code Extension API**: https://code.visualstudio.com/api
- **Syntax Highlight Guide**: https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide
- **TextMate Grammars**: https://macromates.com/manual/en/language_grammars
- **Publishing Extensions**: https://code.visualstudio.com/api/working-with-extensions/publishing-extension

### Example Extensions

- **Markdown All in One**: Markdown extension with custom highlighting
- **MDX Extension**: Markdown + JSX highlighting (similar approach)
- **VuePress Highlight**: Custom markdown directives

### Tools

- **Yeoman Generator**: `npm install -g yo generator-code`
- **VSCE**: `npm install -g @vscode/vsce`
- **Regex Tester**: https://regex101.com/
- **Scope Inspector**: Built into VS Code

---

## 💡 Recommendations

### Start Simple

Begin with just the `tabs` directive and `### Tab:` markers. This is your most critical use case. Get it working well, then expand.

### Test Extensively

Create a comprehensive `examples/demo.md` with:
- All directive types
- Nested markdown within directives
- Edge cases (malformed syntax)
- Multiple directives in one file

### Document Well

Include screenshots in README showing:
- Before/after highlighting
- Different themes
- Each directive type

### Consider Open Source

If you publish this, the Bengal community could contribute improvements!

---

## ✅ Ready to Implement

All research is complete. The extension is feasible and will take approximately 2-3 days of focused work. The approach is sound, and Cursor compatibility is guaranteed.

**Key Success Factors:**
1. Use injection grammar (not new language)
2. Start with tabs directive first
3. Test incrementally with F5 debug mode
4. Use scope inspector to verify token scopes
5. Package as VSIX for easy distribution

**Recommendation:** Proceed with implementation! 🚀

