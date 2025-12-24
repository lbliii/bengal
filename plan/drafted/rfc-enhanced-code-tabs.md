# RFC: Enhanced Code Tabs Directive

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Directives, Rendering  
**Confidence**: 88% 🟢  
**Priority**: P2 (Medium) — Developer experience, documentation quality  
**Estimated Effort**: 3-4 days

---

## Executive Summary

The `code-tabs` directive currently provides minimal value over the general-purpose `tabs` directive—same features, slightly simpler syntax. This RFC proposes enhancing `code-tabs` with code-specific features that make it the obvious choice for multi-language examples:

1. **Auto language sync** — All code-tabs on a page sync when user picks a language (no config)
2. **Language icons** — Automatic icons from language name (Python → python icon)
3. **Pygments integration** — Line numbers, highlighting, proper syntax coloring
4. **Copy button** — One-click copy per tab
5. **Filename display** — `### Python (main.py)` shows filename badge

**Value prop**: `tabs` = general content tabs. `code-tabs` = zero-config, code-first experience with smart defaults.

---

## Problem Statement

### Current State: Minimal Differentiation

| Feature | `code-tabs` | `tabs` |
|---------|-------------|--------|
| Syntax | `### Language` markers | Nested `tab-item` directives |
| Sync | ❌ None | ✅ Manual `:sync:` |
| Icons | ❌ None | ✅ Manual `:icon:` per tab |
| Copy | ❌ None | ❌ None |
| Pygments | ❌ Raw `<code>` | ❌ Raw `<code>` |
| Line numbers | ❌ None | ❌ None |
| Filename | ❌ None | ❌ Manual in content |

**Current code-tabs output** (`code_tabs.py:130-138`):
```python
content_html += (
    f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n'
    f'      <pre><code class="language-{lang}">{code}</code></pre>\n'
    f"    </div>\n"
)
```

This bypasses Bengal's Pygments infrastructure entirely—no syntax highlighting, no line numbers, no line emphasis.

### Missed Pygments Integration

Bengal has rich code block support that `code-tabs` doesn't use:

**`rendering/parsers/mistune/highlighting.py:90-139`**:
```python
# Supports: python, python title="file.py", python {1,3}, python title="file.py" {1,3}
language = info_stripped
title: str | None = None
hl_lines: list[int] = []

# ...parsing...

formatter = HtmlFormatter(
    cssclass="highlight",
    wrapcode=True,
    noclasses=False,  # CSS classes for theming
    linenos="table" if line_count >= 3 else False,
    linenostart=1,
    hl_lines=hl_lines,  # Line highlighting
)
highlighted = highlight(code, lexer, formatter)
```

All of this is available but unused by `code-tabs`.

### Unclear Value Proposition

When should authors use `code-tabs` vs `tabs`? Currently, the only answer is "code-tabs has slightly simpler syntax." This isn't compelling enough to justify two directives.

---

## Goals

1. **Make code-tabs the obvious choice** for multi-language examples
2. **Auto-sync by default** — Pick Python anywhere, all code-tabs switch
3. **Leverage Pygments** — Proper highlighting, line numbers, emphasis
4. **Zero-config experience** — Smart defaults, minimal options needed
5. **Backward compatible** — Existing code-tabs continue working

### Non-Goals

- Replacing `tabs` directive (still needed for mixed content)
- Run/playground integration (separate RFC)
- Diff view between languages (future enhancement)

---

## Design

### Proposed Syntax

```markdown
:::{code-tabs}
:sync: language          # Optional: sync key (defaults to "language")
:line-numbers: true      # Optional: force line numbers
:highlight: 3-5          # Optional: highlight lines (all tabs)

### Python (main.py)
```python
def greet(name):
    """Say hello."""
    print(f"Hello, {name}!")

greet("World")
```

### JavaScript (index.js)
```javascript {2-3}       # Per-tab highlighting also supported
function greet(name) {
    // Say hello
    console.log(`Hello, ${name}!`);
}

greet("World");
```

### Go
```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
```
:::
```

### Parsing Changes

**Tab marker pattern** (enhanced):
```python
# Current: ^### (?:Tab: )?(.+)$
# Proposed: ^### (?:Tab: )?(.+?)(?:\s+\(([^)]+)\))?$
#                  └─ language ─┘    └─ filename ─┘

# Examples:
# "### Python"           → lang="Python", filename=None
# "### Python (main.py)" → lang="Python", filename="main.py"
# "### Tab: Go"          → lang="Go", filename=None
```

**Code block pattern** (enhanced to capture info string):
```python
# Current: ```\w*\n(.*?)```
# Proposed: ```(\w+)?(?:\s+(.+?))?\n(.*?)```
#               └─ lang ─┘ └─ info ─┘ └─ code ─┘

# Examples:
# ```python              → lang="python", info=None
# ```python {1,3-5}      → lang="python", info="{1,3-5}"
# ```python title="x"    → lang="python", info='title="x"'
```

### Rendering Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  Input: :::{code-tabs} with ### Language markers            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Parse tab markers (language, filename)                  │
│  2. Extract code blocks (language, info string, code)       │
│  3. Parse info strings (line highlights, title override)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  For each tab:                                              │
│  ├─ Get cached Pygments lexer (pygments_cache.py)           │
│  ├─ Apply HtmlFormatter with:                               │
│  │   ├─ CSS classes (not inline styles)                     │
│  │   ├─ Line numbers (if enabled or ≥3 lines)               │
│  │   └─ Line highlighting (hl_lines)                        │
│  └─ Wrap in tab structure                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Output: HTML with:                                         │
│  ├─ data-sync="language" (auto-sync)                        │
│  ├─ Language icons in tab nav                               │
│  ├─ Filename badges (if specified)                          │
│  ├─ Pygments-highlighted code                               │
│  └─ Copy button per pane                                    │
└─────────────────────────────────────────────────────────────┘
```

### HTML Output Structure

```html
<div class="code-tabs" 
     id="code-tabs-abc123" 
     data-bengal="code-tabs" 
     data-sync="language">
  
  <!-- Tab Navigation -->
  <ul class="tab-nav" role="tablist">
    <li class="active" role="presentation">
      <a href="#" 
         role="tab" 
         data-tab-target="code-tabs-abc123-0"
         data-sync-value="Python">
        <span class="tab-icon"><!-- python.svg --></span>
        <span class="tab-label">Python</span>
        <span class="tab-filename">main.py</span>
      </a>
    </li>
    <li role="presentation">
      <a href="#" 
         role="tab" 
         data-tab-target="code-tabs-abc123-1"
         data-sync-value="JavaScript">
        <span class="tab-icon"><!-- javascript.svg --></span>
        <span class="tab-label">JavaScript</span>
        <span class="tab-filename">index.js</span>
      </a>
    </li>
  </ul>
  
  <!-- Tab Panes -->
  <div class="tab-content">
    <div id="code-tabs-abc123-0" 
         class="tab-pane active" 
         role="tabpanel">
      <div class="code-toolbar">
        <button class="copy-btn" 
                data-copy-target="code-tabs-abc123-0-code"
                aria-label="Copy code">
          <span class="copy-icon"><!-- copy icon --></span>
        </button>
      </div>
      <!-- Pygments output -->
      <div class="highlight">
        <table class="highlighttable">
          <tr>
            <td class="linenos">...</td>
            <td class="code">
              <code id="code-tabs-abc123-0-code">
                <!-- Pygments-highlighted spans -->
              </code>
            </td>
          </tr>
        </table>
      </div>
    </div>
    <!-- ... more panes -->
  </div>
</div>
```

### Auto-Sync Behavior

**Default**: All `code-tabs` on a page sync by language name.

**JavaScript** (`themes/default/assets/js/main.js` addition):
```javascript
// Code-tabs auto-sync
document.addEventListener('DOMContentLoaded', () => {
  const codeTabs = document.querySelectorAll('[data-bengal="code-tabs"]');
  
  codeTabs.forEach(tabContainer => {
    const syncKey = tabContainer.dataset.sync || 'language';
    
    tabContainer.querySelectorAll('.tab-nav a').forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        const syncValue = tab.dataset.syncValue;
        
        // Sync all code-tabs with same sync key
        document.querySelectorAll(`[data-sync="${syncKey}"]`).forEach(other => {
          const matchingTab = other.querySelector(`[data-sync-value="${syncValue}"]`);
          if (matchingTab) {
            activateTab(matchingTab);
          }
        });
        
        // Remember preference
        localStorage.setItem(`bengal-code-tabs-${syncKey}`, syncValue);
      });
    });
  });
  
  // Restore preference on page load
  codeTabs.forEach(tabContainer => {
    const syncKey = tabContainer.dataset.sync || 'language';
    const saved = localStorage.getItem(`bengal-code-tabs-${syncKey}`);
    if (saved) {
      const tab = tabContainer.querySelector(`[data-sync-value="${saved}"]`);
      if (tab) activateTab(tab);
    }
  });
});
```

**User experience**: 
1. User visits API docs, clicks "Python" on first example
2. All code examples on page switch to Python
3. User navigates to another page → Python is still selected (localStorage)

### Language Icon Mapping

Leverage existing icon system with language → icon mapping:

```python
# bengal/directives/code_tabs.py

LANGUAGE_ICONS: dict[str, str] = {
    # Common languages
    "python": "python",
    "javascript": "javascript", 
    "typescript": "typescript",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "java": "java",
    "csharp": "csharp",
    "cpp": "cpp",
    "c": "c",
    
    # Web
    "html": "html",
    "css": "css",
    "json": "json",
    "yaml": "yaml",
    "toml": "toml",
    
    # Shell
    "bash": "terminal",
    "shell": "terminal",
    "sh": "terminal",
    "zsh": "terminal",
    "powershell": "terminal",
    
    # Data
    "sql": "database",
    "graphql": "graphql",
    
    # Config
    "dockerfile": "docker",
    "nginx": "file-code",
    "apache": "file-code",
    
    # Default
    "_default": "code",
}

def get_language_icon(lang: str) -> str:
    """Get icon name for a programming language."""
    normalized = lang.lower().strip()
    return LANGUAGE_ICONS.get(normalized, LANGUAGE_ICONS["_default"])
```

---

## Pygments Integration Details

### Current Gap

`code_tabs.py` outputs raw code without Pygments:
```python
# Current render (line 136)
f'<pre><code class="language-{lang}">{code}</code></pre>\n'
```

This means:
- No syntax highlighting (requires client-side JS like Prism)
- No line numbers
- No line emphasis
- No title support

### Proposed Integration

Use Bengal's existing highlighting infrastructure:

```python
# bengal/directives/code_tabs.py

from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from bengal.rendering.pygments_cache import get_lexer_cached
from bengal.rendering.parsers.mistune.highlighting import parse_hl_lines

def render_code_tab_content(
    code: str,
    language: str,
    hl_lines: list[int] | None = None,
    line_numbers: bool | None = None,  # None = auto (3+ lines)
) -> str:
    """Render code with Pygments highlighting."""
    try:
        lexer = get_lexer_cached(language=language)
    except Exception:
        # Fallback for unknown languages
        lexer = get_lexer_cached(language="text")
    
    line_count = code.count("\n") + 1
    
    # Auto line numbers for 3+ lines unless explicitly disabled
    show_linenos = line_numbers if line_numbers is not None else (line_count >= 3)
    
    formatter = HtmlFormatter(
        cssclass="highlight",
        wrapcode=True,
        noclasses=False,
        linenos="table" if show_linenos else False,
        linenostart=1,
        hl_lines=hl_lines or [],
    )
    
    return highlight(code, lexer, formatter)
```

### Performance Consideration

Pygments lexer lookup is expensive. Bengal already caches lexers:

**`rendering/pygments_cache.py:90`**:
```python
def get_lexer_cached(language: str | None = None, code: str = "") -> Any:
    """Get a Pygments lexer with caching for performance."""
```

Code-tabs will use this same cache, ensuring no performance regression.

### Line Highlight Parsing

Reuse existing parser from highlighting.py:

```python
# From highlighting.py:26-58
def parse_hl_lines(hl_spec: str) -> list[int]:
    """Parse line highlight specification like '1,3-5,7'."""
    lines = []
    for part in hl_spec.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                lines.extend(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            try:
                lines.append(int(part))
            except ValueError:
                continue
    return sorted(lines)
```

---

## Options

### CodeTabsOptions (Updated)

```python
@dataclass
class CodeTabsOptions(DirectiveOptions):
    """Options for code-tabs directive."""
    
    sync: str = "language"      # Sync key (default syncs by language)
    line_numbers: bool | None = None  # None = auto (3+ lines)
    highlight: str = ""         # Global line highlights "1,3-5"
    
    _field_aliases: ClassVar[dict[str, str]] = {
        "linenos": "line_numbers",
        "hl": "highlight",
        "hl-lines": "highlight",
    }
```

### Usage Examples

**Minimal (smart defaults)**:
```markdown
:::{code-tabs}
### Python
```python
print("Hello")
```

### JavaScript  
```javascript
console.log("Hello");
```
:::
```

**With options**:
```markdown
:::{code-tabs}
:sync: api-examples        # Custom sync group
:line-numbers: true        # Force line numbers
:highlight: 2              # Highlight line 2 in all tabs

### Python (client.py)
```python
import requests

response = requests.get("/api/users")
print(response.json())
```

### JavaScript (client.js)
```javascript {3-4}        # Per-tab highlighting
import fetch from 'node-fetch';

const response = await fetch('/api/users');
const data = await response.json();
console.log(data);
```
:::
```

**Disable sync**:
```markdown
:::{code-tabs}
:sync: none                # No syncing for this block

### Before
```python
# Old code
```

### After
```python
# New code
```
:::
```

---

## Implementation Plan

### Phase 1: Pygments Integration (Day 1)

1. Update `parse_directive()` to extract:
   - Language from tab marker
   - Filename from `(filename.ext)` suffix
   - Code block language and info string
   - Per-tab line highlights from `{1,3-5}` syntax

2. Update `render()` to use Pygments:
   - Call `get_lexer_cached()` for each language
   - Use `HtmlFormatter` with line numbers and highlights
   - Preserve existing HTML structure (backward compat)

3. Tests:
   - Syntax highlighting output
   - Line number rendering
   - Line highlight rendering

### Phase 2: Auto-Sync (Day 2)

1. Add `data-sync` and `data-sync-value` attributes to output
2. Add JavaScript sync handler to `main.js`
3. Add localStorage preference persistence
4. Tests:
   - Multiple code-tabs sync on click
   - Preference persists across pages

### Phase 3: Language Icons + Copy (Day 3)

1. Add `LANGUAGE_ICONS` mapping
2. Integrate with existing icon system (`get_icon_svg()`)
3. Add copy button to toolbar
4. CSS styling for icons and copy button
5. Tests:
   - Icons render correctly
   - Copy functionality works

### Phase 4: Documentation + Polish (Day 4)

1. Update directive reference docs
2. Add examples to site
3. Migration guide (existing code-tabs continue working)
4. Update validator to check new syntax

---

## Files Changed

| File | Changes |
|------|---------|
| `bengal/directives/code_tabs.py` | Major rewrite: options, Pygments, icons |
| `bengal/themes/default/assets/js/main.js` | Add code-tabs sync handler |
| `bengal/themes/default/assets/css/components/code.css` | Tab icons, copy button, filename badge |
| `bengal/health/validators/directives/analysis.py` | Update validation for new syntax |
| `site/content/docs/reference/directives/interactive.md` | Update documentation |

---

## Backward Compatibility

### Preserved

- `### Language` and `### Tab: Language` markers (both work)
- Existing HTML classes (`.code-tabs`, `.tab-nav`, `.tab-pane`)
- No required options (all have sensible defaults)

### Changed (Minor)

- Output now has Pygments HTML structure instead of plain `<pre><code>`
- CSS may need minor updates for Pygments classes (`.highlight`, `.highlighttable`)

### Migration Path

Existing code-tabs continue working with enhanced output. No author action required.

---

## Testing Strategy

### Unit Tests

```python
def test_language_extraction():
    """Tab markers parse language and filename."""
    assert parse_tab_marker("### Python") == ("Python", None)
    assert parse_tab_marker("### Python (main.py)") == ("Python", "main.py")
    assert parse_tab_marker("### Tab: Go") == ("Go", None)

def test_pygments_integration():
    """Code is highlighted with Pygments."""
    html = render_code_tab_content("print('hello')", "python")
    assert 'class="highlight"' in html
    assert '<span class="nb">print</span>' in html  # Pygments token

def test_line_numbers():
    """Line numbers appear for 3+ line code."""
    short = render_code_tab_content("x = 1", "python")
    assert "linenos" not in short
    
    long = render_code_tab_content("x = 1\ny = 2\nz = 3", "python")
    assert "linenos" in long or "highlighttable" in long

def test_sync_attributes():
    """Auto-sync attributes are present."""
    html = render_code_tabs(...)
    assert 'data-sync="language"' in html
    assert 'data-sync-value="Python"' in html
```

### Integration Tests

- Verify sync works across multiple code-tabs on a page
- Verify localStorage preference persists
- Verify copy button copies correct code
- Verify icons render for known languages

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pygments CSS conflicts | Low | Medium | Use existing `.highlight` class, tested with current theme |
| Performance regression | Low | Medium | Reuse cached lexers from `pygments_cache.py` |
| Breaking existing code-tabs | Low | High | No required changes, all new features opt-in or auto |
| Icon bloat | Medium | Low | Lazy-load icons only for used languages |

---

## Alternatives Considered

### 1. Deprecate code-tabs, Enhance tabs

**Pros**: One directive to maintain  
**Cons**: More verbose syntax for common case, can't have code-specific defaults

**Decision**: Keep both—`tabs` for general content, `code-tabs` for code-first experience.

### 2. Client-side highlighting (Prism/Highlight.js)

**Pros**: Lighter server output  
**Cons**: Flash of unstyled code, extra JS payload, harder to cache

**Decision**: Use server-side Pygments (consistent with rest of Bengal).

### 3. No auto-sync by default

**Pros**: More predictable  
**Cons**: Loses the key differentiator from `tabs`

**Decision**: Auto-sync on by default (can disable with `:sync: none`).

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Code-tabs usage in docs | Increase adoption over plain `tabs` for code examples |
| Author feedback | "code-tabs is the obvious choice for multi-language examples" |
| Performance | No regression (cached lexers, lazy icons) |
| Backward compat | Zero breaking changes to existing sites |

---

## Open Questions

1. **Sync across pages?** — Currently localStorage per-page. Should we sync site-wide?
2. **Icon library?** — Use Phosphor (current) or add language-specific icons?
3. **Diff mode?** — Future: show diff between tabs for "before/after" examples?
4. **Run button?** — Future: integrate with Marimo for executable Python?

---

## References

- `bengal/rendering/parsers/mistune/highlighting.py` — Existing Pygments integration
- `bengal/rendering/pygments_cache.py` — Cached lexer system
- `bengal/directives/tabs.py` — Tab-set implementation with sync support
- [Stripe API Docs](https://stripe.com/docs/api) — Reference for language sync UX

