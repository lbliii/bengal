# RFC: Enhanced Code Tabs Directive

**Status**: Implemented  
**Created**: 2025-12-24  
**Updated**: 2025-12-24  
**Implemented**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Directives, Rendering, Themes (JS)  
**Confidence**: 92% 🟢  
**Priority**: P2 (Medium) — Developer experience, documentation quality  
**Estimated Effort**: 3-4 days

---

## Executive Summary

The `code-tabs` directive currently provides minimal value over the general-purpose `tabs` directive—same features, slightly simpler syntax. This RFC proposes enhancing `code-tabs` with code-specific features that make it the obvious choice for multi-language examples:

1. **Auto language sync** — All code-tabs on a page sync when user picks a language (no config)
2. **Language icons** — Automatic icons from language name (Python → terminal/code icon)
3. **Pygments integration** — Line numbers, highlighting, proper syntax coloring
4. **Copy button** — One-click copy per tab
5. **Filename display** — `### Python (main.py)` shows filename badge

**Value prop**: `tabs` = general content tabs. `code-tabs` = zero-config, code-first experience with smart defaults.

**Key design decision**: Sync functionality is implemented in the existing `tabs.js` enhancement, benefiting both `tabs` and `code-tabs` directives.

---

## Problem Statement

### Current State: Minimal Differentiation

| Feature | `code-tabs` | `tabs` |
|---------|-------------|--------|
| Syntax | `### Language` markers | Nested `tab-item` directives |
| Sync | ❌ None | ✅ Manual `:sync:` (HTML only, no JS) |
| Icons | ❌ None | ✅ Manual `:icon:` per tab |
| Copy | ❌ None | ❌ None |
| Pygments | ❌ Raw `<code>` | ❌ Raw `<code>` |
| Line numbers | ❌ None | ❌ None |
| Filename | ❌ None | ❌ Manual in content |

**Current code-tabs output** (`code_tabs.py:134-136`):

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

**`rendering/parsers/mistune/highlighting.py:132-142`**:

```python
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

### Existing Sync Gap

The `tabs` directive already outputs `data-sync` attributes (`tabs.py:293`), but no JavaScript implements the sync behavior. This RFC closes that gap for both directives.

### Unclear Value Proposition

When should authors use `code-tabs` vs `tabs`? Currently, the only answer is "code-tabs has slightly simpler syntax." This isn't compelling enough to justify two directives.

---

## Goals

1. **Make code-tabs the obvious choice** for multi-language examples
2. **Auto-sync by default** — Pick Python anywhere, all code-tabs switch
3. **Leverage Pygments** — Proper highlighting, line numbers, emphasis
4. **Zero-config experience** — Smart defaults, minimal options needed
5. **Backward compatible** — Existing code-tabs continue working
6. **Unified sync** — Same sync JS works for both `tabs` and `code-tabs`

### Non-Goals

- Replacing `tabs` directive (still needed for mixed content)
- Run/playground integration (separate RFC)
- Diff view between languages (future enhancement)
- Adding new language-specific icons to icon library (use existing icons)

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

**Tab marker pattern** (enhanced with strict filename detection):

```python
# Current: ^### (?:Tab: )?(.+)$
# Proposed: ^### (?:Tab: )?(.+?)(?:\s+\((\w[\w.-]*\.[a-z]+)\))?$
#                  └─ language ─┘    └───── filename ─────┘
#
# Filename pattern only matches: word characters, dots, hyphens
# Must end with .ext (lowercase extension)

# Examples:
# "### Python"              → lang="Python", filename=None
# "### Python (main.py)"    → lang="Python", filename="main.py"
# "### Python (v3.12+)"     → lang="Python (v3.12+)", filename=None  # No match
# "### Tab: Go"             → lang="Go", filename=None
# "### Rust (lib.rs)"       → lang="Rust", filename="lib.rs"
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
│  ├─ data-bengal="tabs" (reuses existing enhancement)        │
│  ├─ data-sync="language" (auto-sync key)                    │
│  ├─ data-sync-value on nav links                            │
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
     data-bengal="tabs"
     data-sync="language">

  <!-- Tab Navigation -->
  <ul class="tab-nav" role="tablist">
    <li class="active" role="presentation">
      <a href="#"
         role="tab"
         aria-selected="true"
         aria-controls="code-tabs-abc123-0"
         data-tab-target="code-tabs-abc123-0"
         data-sync-value="python">
        <span class="tab-icon" aria-hidden="true"><!-- terminal.svg --></span>
        <span class="tab-label">Python</span>
        <span class="tab-filename">main.py</span>
      </a>
    </li>
    <li role="presentation">
      <a href="#"
         role="tab"
         aria-selected="false"
         aria-controls="code-tabs-abc123-1"
         data-tab-target="code-tabs-abc123-1"
         data-sync-value="javascript">
        <span class="tab-icon" aria-hidden="true"><!-- code.svg --></span>
        <span class="tab-label">JavaScript</span>
        <span class="tab-filename">index.js</span>
      </a>
    </li>
  </ul>

  <!-- Tab Panes -->
  <div class="tab-content">
    <div id="code-tabs-abc123-0"
         class="tab-pane active"
         role="tabpanel"
         aria-labelledby="code-tabs-abc123-0-tab">
      <div class="code-toolbar">
        <button class="copy-btn"
                data-copy-target="code-tabs-abc123-0-code"
                aria-label="Copy code to clipboard">
          <span class="copy-icon" aria-hidden="true"><!-- copy.svg --></span>
          <span class="copy-label visually-hidden">Copy</span>
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

**Key HTML decisions**:

1. **`data-bengal="tabs"`** — Reuses existing `tabs.js` enhancement (not a new enhancement)
2. **`data-sync`** — Sync key at container level
3. **`data-sync-value`** — Normalized language name (lowercase) on each nav link
4. **ARIA attributes** — Proper `role`, `aria-selected`, `aria-controls`, `aria-labelledby`

### Auto-Sync Behavior

**Default**: All elements with `data-sync` on a page sync by their sync key.

**JavaScript** — Extend `themes/default/assets/js/enhancements/tabs.js`:

```javascript
/**
 * Tab sync functionality (works for both tabs and code-tabs)
 *
 * Syncs all tab containers with matching data-sync key when user clicks.
 * Persists preference to localStorage for cross-page consistency.
 */

// Add to existing tabs.js IIFE

const STORAGE_PREFIX = 'bengal-tabs-sync-';

/**
 * Handle sync across multiple tab containers
 */
function syncTabs(syncKey, syncValue) {
  if (!syncKey || syncKey === 'none') return;

  // Find all containers with this sync key
  const containers = document.querySelectorAll(`[data-sync="${syncKey}"]`);

  containers.forEach(container => {
    // Find link with matching sync value
    const matchingLink = container.querySelector(
      `[data-sync-value="${syncValue}"]`
    );

    if (matchingLink) {
      const targetId = matchingLink.getAttribute('data-tab-target');
      if (targetId) {
        switchTab(container, matchingLink, targetId);
      }
    }
  });

  // Persist preference
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${syncKey}`, syncValue);
  } catch (e) {
    // localStorage may be unavailable (private browsing, etc.)
  }
}

/**
 * Restore synced tab preference on page load
 */
function restoreSyncPreference() {
  const containers = document.querySelectorAll('[data-sync]');

  containers.forEach(container => {
    const syncKey = container.dataset.sync;
    if (!syncKey || syncKey === 'none') return;

    try {
      const saved = localStorage.getItem(`${STORAGE_PREFIX}${syncKey}`);
      if (saved) {
        const link = container.querySelector(`[data-sync-value="${saved}"]`);
        if (link) {
          const targetId = link.getAttribute('data-tab-target');
          if (targetId) {
            switchTab(container, link, targetId);
          }
        }
      }
    } catch (e) {
      // localStorage unavailable
    }
  });
}

// Update existing click handler to include sync
document.addEventListener('click', (e) => {
  const link = e.target.closest(SELECTOR_NAV_LINK);
  if (!link) return;

  const container = link.closest(SELECTOR_TABS);
  if (!container) return;

  e.preventDefault();

  const targetId = link.getAttribute('data-tab-target');
  if (!targetId) return;

  // Check for sync
  const syncKey = container.dataset.sync;
  const syncValue = link.dataset.syncValue;

  if (syncKey && syncValue && syncKey !== 'none') {
    // Sync all containers with same key
    syncTabs(syncKey, syncValue);
  } else {
    // Just switch this tab
    switchTab(container, link, targetId);
  }
});

// Restore on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', restoreSyncPreference);
} else {
  restoreSyncPreference();
}
```

**User experience**:

1. User visits API docs, clicks "Python" on first example
2. All code examples on page switch to Python
3. User navigates to another page → Python is still selected (localStorage)

### Language Icon Mapping

Use existing icons from Bengal's Phosphor-based library. Map languages to semantically appropriate icons that **actually exist**:

```python
# bengal/directives/code_tabs.py

from bengal.directives._icons import render_svg_icon, icon_exists

# Map languages to existing icons in Bengal's icon library
# Only use icons verified to exist in bengal/themes/default/assets/icons/
LANGUAGE_ICONS: dict[str, str] = {
    # Shell/Terminal (terminal icon exists)
    "bash": "terminal",
    "shell": "terminal",
    "sh": "terminal",
    "zsh": "terminal",
    "powershell": "terminal",
    "console": "terminal",
    "cmd": "terminal",

    # Data/Database (database icon exists)
    "sql": "database",
    "mysql": "database",
    "postgresql": "database",
    "sqlite": "database",

    # Config/Data formats (file-code exists)
    "json": "file-code",
    "yaml": "file-code",
    "toml": "file-code",
    "xml": "file-code",
    "ini": "file-code",

    # Generic code (code icon exists)
    "_default": "code",
}

def get_language_icon(lang: str, size: int = 16) -> str:
    """
    Get icon HTML for a programming language.

    Returns empty string if no icon available (graceful degradation).
    """
    normalized = lang.lower().strip()
    icon_name = LANGUAGE_ICONS.get(normalized, LANGUAGE_ICONS["_default"])

    # Verify icon exists before rendering
    if not icon_exists(icon_name):
        return ""

    return render_svg_icon(icon_name, size=size, css_class="tab-icon")
```

**Note**: Language-specific icons (python, javascript, go, etc.) are not currently in Bengal's Phosphor icon set. Use semantic fallbacks. Future work could add devicon integration or custom language icons.

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
) -> tuple[str, str]:
    """
    Render code with Pygments highlighting.

    Returns:
        Tuple of (highlighted_html, plain_code_for_copy)
    """
    # Get cached lexer (fast path for known languages)
    try:
        lexer = get_lexer_cached(language=language)
    except Exception:
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

    highlighted = highlight(code, lexer, formatter)

    # Fix Pygments .hll newline issue (same as highlighting.py)
    if hl_lines:
        highlighted = highlighted.replace("\n</span>", "</span>")

    return highlighted, code
```

### Performance Consideration

Pygments lexer lookup is expensive. Bengal already caches lexers:

**`rendering/pygments_cache.py:90-110`**:

```python
def get_lexer_cached(language: str | None = None, code: str = "") -> Any:
    """Get a Pygments lexer with caching for performance."""
    # Cache hit rate: >95% after first few pages
    # Cached lookup: ~0.001ms vs Uncached: ~30ms
```

Code-tabs will use this same cache, ensuring no performance regression.

### Line Highlight Parsing

Reuse existing parser from `highlighting.py:26-58`:

```python
def parse_hl_lines(hl_spec: str) -> list[int]:
    """Parse line highlight specification like '1,3-5,7'."""
    lines: set[int] = set()
    for part in hl_spec.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                lines.update(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            try:
                lines.add(int(part))
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
    icons: bool = True          # Show language icons (default: true)

    _field_aliases: ClassVar[dict[str, str]] = {
        "linenos": "line_numbers",
        "line-numbers": "line_numbers",
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

**Disable icons**:

```markdown
:::{code-tabs}
:icons: false              # No icons in tab labels

### Python
```python
print("Hello")
```
:::
```

---

## Implementation Plan

### Phase 1: Pygments Integration (Day 1)

1. Update `parse_directive()` to extract:
   - Language from tab marker
   - Filename from `(filename.ext)` suffix (strict pattern)
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
   - Filename parsing edge cases

### Phase 2: Auto-Sync (Day 2)

1. Add `data-sync` and `data-sync-value` attributes to output
2. **Extend** `tabs.js` with sync handler (not main.js)
3. Add localStorage preference persistence
4. Tests:
   - Multiple code-tabs sync on click
   - Preference persists across pages
   - `tabs` directive also syncs (same JS)

### Phase 3: Language Icons + Copy (Day 3)

1. Add `LANGUAGE_ICONS` mapping (using existing icons only)
2. Integrate with `_icons.py` (`render_svg_icon`)
3. Add copy button to toolbar
4. CSS styling for icons, copy button, filename badge
5. Tests:
   - Icons render for known language categories
   - Graceful fallback for unknown languages
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
| `bengal/directives/code_tabs.py` | Major rewrite: options, Pygments, icons, sync attributes |
| `bengal/themes/default/assets/js/enhancements/tabs.js` | Add sync handler, localStorage persistence |
| `bengal/themes/default/assets/css/components/code.css` | Tab icons, copy button, filename badge styles |
| `bengal/themes/default/assets/css/components/tabs.css` | Sync-related styles if needed |
| `bengal/health/validators/directives/analysis.py` | Update validation for new syntax |
| `site/content/docs/reference/directives/interactive.md` | Update documentation |
| `tests/unit/directives/test_code_tabs.py` | New tests for enhanced features |

---

## Backward Compatibility

### Preserved

- `### Language` and `### Tab: Language` markers (both work)
- Existing HTML classes (`.code-tabs`, `.tab-nav`, `.tab-pane`)
- `data-bengal="tabs"` attribute (unchanged)
- No required options (all have sensible defaults)

### Changed (Minor)

- Output now has Pygments HTML structure instead of plain `<pre><code>`
- CSS may need minor updates for Pygments classes (`.highlight`, `.highlighttable`)
- New `data-sync` and `data-sync-value` attributes added (additive, non-breaking)

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
    assert parse_tab_marker("### Rust (lib.rs)") == ("Rust", "lib.rs")

def test_filename_strict_pattern():
    """Filename only matches file extensions, not version annotations."""
    assert parse_tab_marker("### Python (v3.12+)") == ("Python (v3.12+)", None)
    assert parse_tab_marker("### Node.js (v18)") == ("Node.js (v18)", None)
    assert parse_tab_marker("### Config (config.yaml)") == ("Config", "config.yaml")

def test_pygments_integration():
    """Code is highlighted with Pygments."""
    html, _ = render_code_tab_content("print('hello')", "python")
    assert 'class="highlight"' in html
    assert '<span class="nb">print</span>' in html  # Pygments token

def test_line_numbers():
    """Line numbers appear for 3+ line code."""
    short, _ = render_code_tab_content("x = 1", "python")
    assert "linenos" not in short

    long, _ = render_code_tab_content("x = 1\ny = 2\nz = 3", "python")
    assert "linenos" in long or "highlighttable" in long

def test_sync_attributes():
    """Auto-sync attributes are present."""
    html = render_code_tabs(...)
    assert 'data-sync="language"' in html
    assert 'data-sync-value="python"' in html  # lowercase normalized

def test_language_icons():
    """Icons use existing icon library."""
    assert get_language_icon("bash") != ""  # terminal icon exists
    assert get_language_icon("sql") != ""   # database icon exists
    # Unknown languages get default code icon or empty
    icon = get_language_icon("unknown-lang-xyz")
    assert icon == "" or "code" in icon
```

### Integration Tests

- Verify sync works across multiple code-tabs on a page
- Verify sync works for `tabs` directive with `:sync:` option
- Verify localStorage preference persists across page loads
- Verify copy button copies correct code (plain text, not HTML)
- Verify icons render for known language categories

### Accessibility Tests

- Verify `role="tablist"`, `role="tab"`, `role="tabpanel"` present
- Verify `aria-selected` updates on tab switch
- Verify `aria-controls` matches panel IDs
- Verify keyboard navigation works (left/right arrows)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pygments CSS conflicts | Low | Medium | Use existing `.highlight` class, tested with current theme |
| Performance regression | Low | Medium | Reuse cached lexers from `pygments_cache.py` |
| Breaking existing code-tabs | Low | High | No required changes, all new features opt-in or auto |
| Missing language icons | Medium | Low | Graceful fallback to `code` icon or no icon |
| localStorage unavailable | Low | Low | Try-catch wrapper, sync still works per-page |

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

### 4. New `data-bengal="code-tabs"` enhancement

**Pros**: Cleaner separation  
**Cons**: Duplicate code for similar functionality, more JS to maintain

**Decision**: Extend existing `tabs.js` to handle sync for both directives.

### 5. Add language-specific icons (devicons)

**Pros**: Better visual distinction  
**Cons**: Icon library bloat, licensing concerns, maintenance burden

**Decision**: Use existing Phosphor icons with semantic mapping. Language icons can be a future enhancement (separate RFC).

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Code-tabs usage in docs | Increase adoption over plain `tabs` for code examples |
| Author feedback | "code-tabs is the obvious choice for multi-language examples" |
| Performance | No regression (cached lexers, existing icons) |
| Backward compat | Zero breaking changes to existing sites |
| Sync adoption | `tabs` directive users adopt `:sync:` option |

---

## Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Sync across pages? | Yes, via localStorage | Better UX, aligns with Stripe/other API docs |
| Icon library? | Use existing Phosphor icons | No new dependencies, graceful fallback |
| JS location? | Extend `tabs.js` | Reuse existing enhancement, DRY principle |
| `data-bengal` value? | Keep `"tabs"` | Backward compatible, same JS handles both |
| Filename parsing? | Strict `.ext` pattern | Avoid false positives on version annotations |

## Open Questions

1. **Keyboard navigation?** — Should arrow keys work across synced tabs on page?
2. **Diff mode?** — Future: show diff between tabs for "before/after" examples?
3. **Run button?** — Future: integrate with Marimo for executable Python?

---

## References

- `bengal/rendering/parsers/mistune/highlighting.py` — Existing Pygments integration
- `bengal/rendering/pygments_cache.py` — Cached lexer system
- `bengal/directives/tabs.py` — Tab-set implementation with sync HTML support
- `bengal/themes/default/assets/js/enhancements/tabs.js` — Existing tabs enhancement
- `bengal/directives/_icons.py` — Icon rendering utilities
- [Stripe API Docs](https://stripe.com/docs/api) — Reference for language sync UX
- [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/tab_role) — ARIA tab pattern
