# Bengal Syntax Highlighting - Visual Guide

**What colors will users see in their editors?**

---

## The Problem: Current State (No Highlighting)

Right now, Bengal directives look like this in VS Code/Cursor:

```
Plain Text View:
────────────────────────────────────────────────────────────
````{tabs}
:id: my-tabs

### Tab: Python
Some content here

### Tab: JavaScript
More content here
````
────────────────────────────────────────────────────────────
```

Everything is either:
- Plain text color (white/light gray)
- Generic markdown heading color for `###`
- No distinction between directive syntax and content

**Problems:**
- ❌ Can't quickly spot directive boundaries
- ❌ `### Tab:` looks like regular Markdown heading
- ❌ No visual feedback on syntax correctness
- ❌ Hard to scan through directives quickly

---

## The Solution: With Syntax Highlighting

After the extension, the same text will look like:

```
Color-Coded View:
────────────────────────────────────────────────────────────
````{tabs}
    └─── YELLOW/GOLD (bold) - Directive type stands out
:id: my-tabs
└─┬┘  └──────── GREEN - Value
  └─────────── CYAN - Option key

### Tab: Python
    └──┘ └─────── ORANGE (bold) - Tab name clearly visible
    └──────────── PINK (bold) - "Tab:" keyword distinctive

Some content here
└─────────────────── WHITE - Normal content unchanged

### Tab: JavaScript
    └──┘ └────────────── ORANGE (bold) - Easy to scan tabs
    └───────────────────── PINK (bold) - Consistent keyword

More content here
````
────────────────────────────────────────────────────────────
```

**Benefits:**
- ✅ Directive type (`tabs`) immediately visible in yellow
- ✅ `### Tab:` clearly distinct from regular headings
- ✅ Tab names pop out in orange
- ✅ Options (`:id:`) visually separated from content
- ✅ Structure is obvious at a glance

---

## Color Breakdown by Element

### 1. Directive Opener/Closer

**Pattern:** ````{tabs}`

```
````{tabs}
││││ │   │
││││ │   └── GRAY - Closing brace
││││ └────── YELLOW/GOLD (bold) - Directive name  
││││──────── GRAY - Opening brace
└───────────── GRAY - Fence markers (backticks)
```

**Scopes:**
- Backticks: `punctuation.definition.markdown.code.begin`
- Braces: `punctuation.definition.directive.bengal`
- Directive name: `entity.name.function.directive.bengal`

### 2. Tab Marker

**Pattern:** `### Tab: Python`

```
### Tab: Python
│││ │   │ │
│││ │   │ └────────── ORANGE (bold) - Tab name (most important!)
│││ │   └──────────── GRAY - Space
│││ └──────────────── PINK (bold) - "Tab:" keyword
│││────────────────── GRAY - Heading markers
```

**Why these colors:**
- **PINK** makes "Tab:" distinct from regular Markdown `###` headings
- **ORANGE** makes tab names easy to scan (like function names in code)
- **BOLD** ensures visibility even in light themes

**Scopes:**
- `###`: `punctuation.definition.heading.bengal`
- `Tab:`: `keyword.control.tab.bengal`
- `Python`: `entity.name.section.tab.bengal`

### 3. Directive Options

**Pattern:** `:id: my-tabs`

```
:id: my-tabs
│││ │ │
│││ │ └────────────── GREEN - Option value
│││ └──────────────── GRAY - Separator colon
││└────────────────── CYAN - Option key
│└─────────────────── GRAY - Opening colon
```

**Scopes:**
- Colons: `punctuation.definition.option.bengal`
- Key (`id`): `variable.parameter.option.bengal`
- Value: `string.unquoted.option.value.bengal`

### 4. Admonition with Title

**Pattern:** ````{note} Important Information`

```
```{note} Important Information
│││ │   │ │
│││ │   │ └─────────────── GREEN - Title text
│││ │   └───────────────── GRAY - Space
│││ └───────────────────── YELLOW/GOLD - Directive type
│││─────────────────────── GRAY - Braces
└──────────────────────────── GRAY - Fence
```

**Scopes:**
- Directive type: `entity.name.function.directive.admonition.bengal`
- Title: `string.unquoted.directive.title.bengal`

---

## Theme Compatibility

### How Colors Adapt to Themes

The extension defines **scopes**, not colors. Each theme decides what color to use for each scope.

**Common scope mappings across themes:**

| Scope | Dark+ | Light+ | Dracula | GitHub Dark | Meaning |
|-------|-------|--------|---------|-------------|---------|
| `entity.name.function` | #DCDCAA | #795E26 | #FFB86C | #D2A8FF | Function names |
| `keyword.control` | #C586C0 | #AF00DB | #FF79C6 | #FF7B72 | Keywords (if, for) |
| `variable.parameter` | #9CDCFE | #001080 | #8BE9FD | #79C0FF | Parameters |
| `string` | #CE9178 | #A31515 | #50FA7B | #A5D6FF | Strings |
| `punctuation` | #6A9955 | #6A9955 | #6272A4 | #8B949E | Brackets, braces |

**Result:** Extension looks good in ANY theme!

---

## Real-World Examples

### Example 1: Kitchen Sink Demo

**Before:**
```
````{tabs}
:id: why-bengal

### Tab: ⚡ Performance
**Lightning-fast builds:**
- 0.3s to build 100 pages

### Tab: 🎯 Feature Complete
**Comprehensive feature set**
````
```
*Everything is similar colors, hard to distinguish structure*

**After:**
```
````{tabs}                          ← Gray + GOLD "tabs"
:id: why-bengal                     ← CYAN "id" + GREEN "why-bengal"

### Tab: ⚡ Performance            ← PINK "Tab:" + ORANGE "⚡ Performance"
**Lightning-fast builds:**          ← Normal markdown (unchanged)
- 0.3s to build 100 pages

### Tab: 🎯 Feature Complete       ← PINK "Tab:" + ORANGE "🎯 Feature Complete"
**Comprehensive feature set**
````                                ← Gray
```
*Structure is immediately obvious, tabs stand out*

### Example 2: Nested Directives

**Before:**
```
````{tabs}
### Tab: Setup

```{note} Requirements
Install Python 3.11+
```

### Tab: Usage
Run `bengal build`
````
```
*Nested directive is hard to spot*

**After:**
```
````{tabs}                          ← GOLD "tabs"
### Tab: Setup                      ← PINK "Tab:" + ORANGE "Setup"

```{note} Requirements              ← GOLD "note" + GREEN "Requirements"
Install Python 3.11+
```                                 ← Normal markdown colors return

### Tab: Usage                      ← PINK "Tab:" + ORANGE "Usage"
Run `bengal build`
````
```
*Both outer and inner directives are clearly visible*

### Example 3: Multiple Options

**Before:**
```
````{dropdown} Advanced Configuration
:open: false
:class: advanced-section
:data-category: config
````
```
*Options blend into content*

**After:**
```
````{dropdown} Advanced Configuration    ← GOLD "dropdown" + GREEN title
:open: false                             ← CYAN "open" + GREEN "false"
:class: advanced-section                 ← CYAN "class" + GREEN "advanced-section"
:data-category: config                   ← CYAN "data-category" + GREEN "config"
````
```
*Each option is clearly a key-value pair*

---

## Scanning Efficiency

### Finding Tab Names

**Before:** Read every line to find tab names
```
### Tab: Installation Guide
...200 lines...
### Tab: Configuration Options
...150 lines...
### Tab: Troubleshooting
```

**After:** Tab names jump out instantly
```
### Tab: Installation Guide     ← ORANGE immediately visible
...200 lines...
### Tab: Configuration Options  ← Scan down, spot ORANGE
...150 lines...
### Tab: Troubleshooting        ← Easy to find
```

**Time saved:** 5-10 seconds per search × 100 times/day = **8-15 minutes/day**

### Identifying Directive Types

**Before:** Must read `{...}` carefully
```
```{note} Info
```{tip} Suggestion  
```{warning} Alert
```

**After:** Color-coded by type (could even use different shades)
```
```{note} Info        ← YELLOW
```{tip} Suggestion   ← YELLOW (or GREEN for tips)
```{warning} Alert    ← YELLOW (or RED for warnings)
```

---

## Error Detection

### Catching Typos Visually

**Correct syntax:**
```
### Tab: Python        ← Highlighted in PINK + ORANGE
```

**Common mistakes (NOT highlighted):**
```
###Tab: Python         ← No space - stays plain text
### Tabs: Python       ← Wrong keyword - stays plain text
## Tab: Python         ← Wrong heading level - stays plain text
```

**Benefit:** Instant feedback - if it doesn't highlight, something's wrong!

---

## Accessibility Considerations

### Not Just Color

The extension uses multiple visual cues:
1. **Color** - Primary distinction
2. **Bold** - Tab markers and directive names
3. **Pattern** - Consistent syntax structure

**Result:** Even with color blindness or monochrome displays, structure is still visible through:
- Bold text for keywords
- Consistent patterns
- Clear syntax markers

---

## Before/After Comparison: Full Document

### Current State
```markdown
# Documentation

````{tabs}
:id: installation

### Tab: macOS
Install with homebrew

### Tab: Linux  
Install with apt
````

```{note} System Requirements
Python 3.11 or higher
```

```{warning} Beta Warning
This is beta software
```
```

**Visual experience:**
- Everything blends together
- Hard to spot directive boundaries
- `### Tab:` looks like any other heading
- No feedback on syntax correctness

### With Extension
```markdown
# Documentation                                    ← Normal heading

````{tabs}                                         ← GOLD directive
:id: installation                                  ← CYAN key + GREEN value

### Tab: macOS                                     ← PINK keyword + ORANGE name
Install with homebrew                              ← White content

### Tab: Linux                                     ← PINK keyword + ORANGE name
Install with apt
````                                               ← Gray fence

```{note} System Requirements                      ← GOLD + GREEN title
Python 3.11 or higher
```

```{warning} Beta Warning                          ← GOLD + GREEN (could be RED)
This is beta software
```
```

**Visual experience:**
- ✅ Clear directive boundaries
- ✅ Tab structure immediately obvious  
- ✅ Options visually distinct
- ✅ Syntax errors visible (missing highlights)
- ✅ Easy to scan and navigate

---

## Color Intensity Guide

### Suggested Emphasis Levels

1. **Highest Emphasis** (Bold + Bright)
   - `Tab:` keyword (PINK/PURPLE)
   - Tab names (ORANGE)
   - Directive types (YELLOW/GOLD)

2. **Medium Emphasis** (Standard)
   - Option keys (CYAN)
   - Option values (GREEN)
   - Titles (GREEN)

3. **Low Emphasis** (Muted)
   - Punctuation (GRAY)
   - Fence markers (GRAY)

**Why this hierarchy:**
- Most important = What users scan for (tabs, directive types)
- Medium = Configuration (options)
- Low = Syntax markers (punctuation)

---

## User Testing Feedback (Predicted)

### Expected Positive Reactions

> "Wow, I can actually **see** where my tabs are now!"

> "The `### Tab:` markers **pop out** - so much easier to navigate long files"

> "I caught a typo immediately because it **didn't highlight**"

> "Makes our **documentation look more professional**"

### Expected Questions

> "Can I customize the colors?"
**Yes** - via VS Code theme settings or custom themes

> "Does it slow down the editor?"
**No** - TextMate grammars are compiled and very fast

> "Will it work with my theme?"
**Yes** - uses standard scopes that all themes support

---

## Summary: What Changes

### Visual Changes

| Element | Before | After |
|---------|--------|-------|
| ````{tabs}` | Gray text | GOLD directive name, gray punctuation |
| `### Tab: Name` | Gray `###`, white text | Gray `###`, PINK `Tab:`, ORANGE `Name` |
| `:id: value` | White text | CYAN `id`, GREEN `value` |
| Directive titles | White text | GREEN text |
| Content | White | White (unchanged) |

### Workflow Changes

| Task | Before | After | Improvement |
|------|--------|-------|-------------|
| Find tab by name | Read every line | Scan for orange text | 5-10× faster |
| Check syntax | Read carefully | Look for missing colors | Instant feedback |
| Understand structure | Mental parsing | Visual hierarchy | Less cognitive load |
| Navigate large files | Linear reading | Quick scanning | 3-5× faster |

### Cognitive Changes

**Before:** Brain must parse text → recognize pattern → understand structure
**After:** Colors pre-parse structure → brain sees hierarchy instantly

**Result:** **Less mental effort** = **higher productivity** = **better DX**

---

## The "Wow" Moment

When you first open a file with 10+ tabs directives after installing the extension:

**Before:** Wall of text, must read carefully to understand structure

**After:** Tab names **jump off the screen**, directive boundaries are **crystal clear**, options are **obviously configuration** - the entire document's structure is visible **at a glance**.

That's when you realize: "How did I work without this before?"

---

## Files Reference

- **VSCODE_SYNTAX_EXTENSION_RESEARCH.md** - Complete technical implementation guide
- **VSCODE_EXTENSION_SUMMARY.md** - Executive summary and decision framework
- **bengal-syntax-demo.md** - All syntax patterns for testing
- **SYNTAX_HIGHLIGHTING_VISUAL_GUIDE.md** - This file

**Next step:** Implement the extension! 🚀

