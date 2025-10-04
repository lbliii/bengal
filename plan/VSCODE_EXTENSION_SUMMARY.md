# VS Code Extension for Bengal - Quick Summary

**Date:** October 4, 2025  
**Status:** Research Complete  
**Recommendation:** ✅ Proceed - Feasible and valuable

---

## TL;DR

**Difficulty:** Medium (2-3 days of work)  
**Cursor Compatibility:** ✅ Guaranteed (Cursor is VS Code fork)  
**Approach:** Markdown injection grammar (no new file extensions needed)  
**Skills Needed:** Regex, JSON (no programming required)

---

## What Gets Highlighted

### 1. **Tabs Directive** (Primary Focus)

```markdown
````{tabs}
:id: my-tabs

### Tab: Python
Content here

### Tab: JavaScript  
More content
````
```

**Highlighting:**
- ````{tabs}` - Yellow/gold directive name
- `:id: my-tabs` - Blue key, green value
- `### Tab: Python` - **Pink "Tab:" keyword** + **Orange tab name** (BOLD)

### 2. **All Other Directives**

```markdown
```{note} Title
```{warning} Alert
```{dropdown} Expand me
:open: true
```{code-tabs}
```

---

## Technical Approach

### Architecture: Injection Grammar

✅ **What it means:**
- Works with existing `.md` files (no file extension changes)
- Preserves all standard Markdown highlighting  
- Can coexist with other Markdown extensions

### File Structure (Simple!)

```
bengal-syntax-highlighter/
├── package.json                    # Extension config (20 lines)
└── syntaxes/
    └── bengal.tmLanguage.json     # Grammar rules (~200 lines of JSON)
```

That's it! No TypeScript, no build tooling, just JSON/regex.

---

## Key Implementation Details

### The Critical Pattern: `### Tab: TabName`

From your code: `^### Tab: (.+)$`

**TextMate grammar:**
```json
{
  "match": "^(###)(\\s+)(Tab:)(\\s+)(.+)$",
  "captures": {
    "1": {"name": "punctuation.definition.heading.bengal"},
    "3": {"name": "keyword.control.tab.bengal"},  // ← Pink/bold
    "5": {"name": "entity.name.section.tab.bengal"}  // ← Orange/bold
  }
}
```

### All Directive Types (From Your Code)

```python
# bengal/rendering/plugins/directives/validator.py
KNOWN_DIRECTIVES = {
    'tabs', 'note', 'tip', 'warning', 'danger', 'error',
    'info', 'example', 'success', 'caution', 'dropdown',
    'details', 'code-tabs', 'code_tabs'
}
```

---

## Development Workflow

### Step 1: Setup (30 min)

```bash
npm install -g yo generator-code
yo code
# Select "New Language Support"
```

### Step 2: Write Grammar (4-6 hours)

Create `syntaxes/bengal.tmLanguage.json` with patterns for:
1. Tabs directive (priority)
2. Tab markers `### Tab:`
3. Other directives
4. Options `:key: value`

### Step 3: Test (2-3 hours)

- Press `F5` in VS Code to launch Extension Development Host
- Open demo file with directives
- Use "Inspect Editor Tokens and Scopes" to verify
- Test with multiple themes

### Step 4: Package (1 hour)

```bash
npm install -g @vscode/vsce
vsce package
# Output: bengal-syntax-highlighter-1.0.0.vsix
```

### Step 5: Install (5 min)

```bash
# VS Code
code --install-extension bengal-syntax-highlighter-1.0.0.vsix

# Cursor (same command!)
cursor --install-extension bengal-syntax-highlighter-1.0.0.vsix
```

---

## Cursor Compatibility

### Why It Works

Cursor is a **fork of VS Code**, so:
- ✅ Same extension API
- ✅ Same TextMate grammar engine
- ✅ Same `.vsix` package format
- ✅ Same marketplace (can install from VS Code marketplace)

### Testing

Just install the `.vsix` in Cursor and it works identically.

---

## Example: Before and After

### Before (No Highlighting)

```markdown
````{tabs}
:id: example
### Tab: Python
Code here
````
```

Everything looks like plain text or generic code block.

### After (With Extension)

```markdown
````{tabs}                    ← Gray fence
    {tabs}                    ← Yellow/gold "tabs"
:id: example                  ← Blue "id", green "example"
### Tab: Python               ← PINK "Tab:", ORANGE "Python" (both bold)
Code here
````                          ← Gray fence
```

Much easier to see structure at a glance!

---

## Effort Breakdown

| Task | Time | Complexity |
|------|------|------------|
| Project setup | 30 min | Easy |
| Grammar for tabs + Tab markers | 3 hours | Medium |
| Grammar for all directives | 2 hours | Easy |
| Testing and iteration | 3 hours | Medium |
| Documentation | 2 hours | Easy |
| Packaging | 1 hour | Easy |
| **Total** | **11-12 hours** | **Medium** |

Spread over 2-3 days with breaks and testing.

---

## Why This Is Worth It

### Developer Experience Improvements

1. **Instant Visual Feedback**
   - Spot directive types at a glance
   - See tab structure without reading carefully
   - Catch typos (malformed syntax won't highlight)

2. **Reduced Cognitive Load**
   - Directives "pop out" from content
   - Tab markers are immediately obvious
   - Options are visually distinct

3. **Professional Polish**
   - Shows attention to detail
   - Improves Bengal's perceived quality
   - Makes documentation easier to write

4. **Onboarding**
   - New users see syntax structure clearly
   - Examples are more readable
   - Reduces learning curve

---

## Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Regex not matching all cases | Medium | Medium | Comprehensive test file + iteration |
| Conflicts with other extensions | Low | Low | Use standard scopes, test with common extensions |
| Theme colors don't work well | Low | Low | Test with popular themes, provide custom theme |
| Maintenance burden | Low | Low | Simple JSON, rarely changes |

**Overall Risk:** Low

---

## Decision Factors

### ✅ Proceed If:

- [ ] Team has 2-3 days for this task
- [ ] Developer experience is a priority
- [ ] You're comfortable with regex and JSON
- [ ] You want to distinguish Bengal from other SSGs

### ⏸️ Defer If:

- [ ] More critical features need attention
- [ ] No bandwidth for 2-3 day project
- [ ] Users haven't requested it

### ❌ Skip If:

- [ ] Team only uses basic text editors
- [ ] Documentation is written in other tools
- [ ] No VS Code/Cursor users

---

## Recommendation

**✅ Proceed with implementation**

**Reasoning:**
1. **Low risk** - Well-defined scope, proven approach
2. **High value** - Significant DX improvement
3. **Feasible** - 2-3 days with clear path forward
4. **Unique** - Few SSGs have syntax highlighting extensions
5. **Compound benefits** - Easier to maintain docs, better onboarding

**Suggested Timeline:**
- Day 1: Setup + tabs directive + Tab markers
- Day 2: All other directives + testing
- Day 3: Polish + package + distribute

---

## Next Actions

1. **Review research docs:**
   - `VSCODE_SYNTAX_EXTENSION_RESEARCH.md` - Comprehensive guide
   - `bengal-syntax-demo.md` - Visual examples of all patterns

2. **Create extension:**
   - Use Yeoman to scaffold
   - Copy grammar from research doc
   - Test with demo file

3. **Iterate:**
   - Test with real Bengal markdown files
   - Adjust colors/scopes as needed
   - Get feedback from team

4. **Distribute:**
   - Package as `.vsix`
   - Share with team for testing
   - Consider publishing to marketplace

---

## Questions?

### Can we do just the tabs directive first?

**Yes!** Start with minimal viable extension:
- Just `````{tabs}``` directive
- Just `### Tab:` markers
- Test it, then expand

### Will this work in web editors (GitHub, GitLab)?

**No.** This is VS Code/Cursor only. For web highlighting, you'd need:
- Linguist/Rouge grammar (for GitHub)
- Different approach, similar complexity

### Can we add autocomplete/IntelliSense?

**Yes**, but that's a Phase 2 feature requiring TypeScript and VS Code extension API knowledge. Start with just highlighting.

### What if we want to change the colors?

Users can customize via themes. You can also provide a suggested theme as part of the extension.

---

## Files Created

1. **VSCODE_SYNTAX_EXTENSION_RESEARCH.md** (12KB)
   - Comprehensive research
   - Complete grammar code
   - Testing strategies
   - All technical details

2. **bengal-syntax-demo.md** (8KB)
   - Visual examples
   - All directive types
   - Edge cases
   - Testing checklist

3. **VSCODE_EXTENSION_SUMMARY.md** (this file)
   - Executive summary
   - Decision framework
   - Quick reference

---

**Status:** Research Complete ✅  
**Next Step:** Decide whether to proceed with implementation

