# RFC: Content Enhancement Directives

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-21  
**Subsystems**: `bengal/directives/`, `bengal/themes/default/assets/`

---

## Executive Summary

Introduce a suite of new content directives that address common documentation patterns currently lacking in Bengal:

1. **Timeline** - Changelogs, roadmaps, event histories
2. **File Tree** - Directory structure visualization
3. **FAQ Accordion** - Question/answer format with SEO benefits
4. **Comparison Table** - Feature comparison grids
5. **Keyboard** - Styled keyboard shortcuts
6. **Diff** - Code change visualization

These directives fill gaps in Bengal's content toolkit and are commonly needed in technical documentation.

---

## 1. Timeline Directive

### Problem

Displaying chronological events (changelogs, release history, roadmaps) currently requires manual HTML or awkward list formatting. No semantic structure exists for time-based content.

### Solution

`{timeline}` and `{timeline-event}` directives using the closure pattern.

### Syntax

```markdown
:::{timeline}
:orientation: vertical
:style: alternating

:::{timeline-event} Version 2.0 Released
:date: 2025-01-15
:icon: 🚀
:status: complete

Major architecture rewrite with improved caching.

- New incremental build system
- 3x faster renders
:::{/timeline-event}

:::{timeline-event} Version 2.1 Planned
:date: 2025-03-01
:icon: 🔮
:status: upcoming

Performance improvements and plugin system.
:::{/timeline-event}

:::{/timeline}
```

### Container Options (`{timeline}`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:orientation:` | enum | `vertical` | Layout: `vertical`, `horizontal` |
| `:style:` | enum | `left` | Event position: `left`, `right`, `alternating` |
| `:class:` | string | - | Custom CSS class |
| `:connector:` | enum | `line` | Connector style: `line`, `dashed`, `dots`, `none` |

### Event Options (`{timeline-event}`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:date:` | string | - | Date/time string (displayed as-is) |
| `:icon:` | string | `●` | Icon or emoji for marker |
| `:status:` | enum | - | Status: `complete`, `current`, `upcoming`, `cancelled` |
| `:class:` | string | - | Custom CSS class |
| `:link:` | string | - | URL for "Learn more" link |

### HTML Output

```html
<div class="timeline timeline-vertical timeline-alternating">
  <div class="timeline-connector"></div>

  <article class="timeline-event timeline-event-complete timeline-left">
    <div class="timeline-marker">
      <span class="timeline-icon">🚀</span>
    </div>
    <div class="timeline-content">
      <time class="timeline-date" datetime="2025-01-15">2025-01-15</time>
      <h4 class="timeline-title">Version 2.0 Released</h4>
      <div class="timeline-body">
        <p>Major architecture rewrite...</p>
      </div>
    </div>
  </article>

  <article class="timeline-event timeline-event-upcoming timeline-right">
    <!-- ... -->
  </article>
</div>
```

### Visual Design

```
          ┌─────────────────────────┐
          │ 🚀 Version 2.0 Released │
          │    2025-01-15           │
     ●────│ Major rewrite...        │
     │    └─────────────────────────┘
     │
     │    ┌─────────────────────────┐
     │    │ 🔮 Version 2.1 Planned  │
     │    │    2025-03-01           │
     ○────│ Performance...          │
          └─────────────────────────┘
```

---

## 2. File Tree Directive

### Problem

Directory structures are extremely common in documentation but require manual ASCII art that breaks easily and can't be styled or made interactive.

### Solution

`{file-tree}` directive that parses indented text or ASCII tree format.

### Syntax

**Option A: Indented format (simpler)**
```markdown
:::{file-tree}
:root: my-project/

src/
  main.py
  utils/
    helpers.py [highlighted]
    constants.py
tests/
  test_main.py
pyproject.toml
README.md
:::
```

**Option B: ASCII tree format (paste-friendly)**
```markdown
:::{file-tree}
:root: my-project/

my-project/
├── src/
│   ├── main.py
│   └── utils/
│       ├── helpers.py
│       └── constants.py
├── tests/
│   └── test_main.py
├── pyproject.toml
└── README.md
:::
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:root:` | string | - | Root directory name |
| `:class:` | string | - | Custom CSS class |
| `:icons:` | bool | `true` | Show file/folder icons |
| `:highlight:` | string | - | Comma-separated paths to highlight |
| `:collapse:` | bool | `false` | Make folders collapsible |
| `:max-depth:` | int | - | Maximum depth to display |

### Inline Annotations

```markdown
:::{file-tree}
src/
  main.py        # Entry point
  config.py      # Configuration [new]
  utils/
    helpers.py   # Utility functions [modified]
:::
```

Annotations in `[brackets]` become badges, `# comments` become descriptions.

### HTML Output

```html
<div class="file-tree">
  <ul class="file-tree-root" role="tree">
    <li class="file-tree-dir" role="treeitem" aria-expanded="true">
      <span class="file-tree-icon">📁</span>
      <span class="file-tree-name">src/</span>
      <ul class="file-tree-children" role="group">
        <li class="file-tree-file" role="treeitem">
          <span class="file-tree-icon">📄</span>
          <span class="file-tree-name">main.py</span>
          <span class="file-tree-comment">Entry point</span>
        </li>
        <li class="file-tree-file file-tree-new" role="treeitem">
          <span class="file-tree-icon">📄</span>
          <span class="file-tree-name">config.py</span>
          <span class="file-tree-badge">new</span>
        </li>
      </ul>
    </li>
  </ul>
</div>
```

### Visual Design

```
📁 my-project/
├── 📁 src/
│   ├── 📄 main.py          # Entry point
│   ├── 📄 config.py        [new]
│   └── 📁 utils/
│       └── 📄 helpers.py   [modified]
├── 📁 tests/
│   └── 📄 test_main.py
├── 📄 pyproject.toml
└── 📄 README.md
```

---

## 3. FAQ Accordion Directive

### Problem

FAQ sections are common but lack semantic structure. No Schema.org markup for SEO. Existing dropdown directive doesn't convey Q&A semantics.

### Solution

`{faq}` and `{question}` directives with built-in Schema.org FAQPage markup.

### Syntax

```markdown
:::{faq}
:title: Frequently Asked Questions
:schema: true

:::{question} How do I install Bengal?
Use pip to install Bengal:

```bash
pip install bengal
```
:::{/question}

:::{question} Does Bengal support Windows?
:open: true

Yes! Bengal runs on Windows, macOS, and Linux.
:::{/question}

:::{question} How do I upgrade?
Run `pip install --upgrade bengal` to get the latest version.
:::{/question}

:::{/faq}
```

### Container Options (`{faq}`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:title:` | string | - | Section title |
| `:schema:` | bool | `true` | Include Schema.org FAQPage markup |
| `:class:` | string | - | Custom CSS class |
| `:collapse-all:` | bool | `false` | Start with all items collapsed |
| `:single-open:` | bool | `false` | Only one item open at a time |

### Question Options (`{question}`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:open:` | bool | `false` | Start expanded |
| `:class:` | string | - | Custom CSS class |
| `:id:` | string | (auto) | Anchor ID for deep linking |

### HTML Output

```html
<section class="faq" itemscope itemtype="https://schema.org/FAQPage">
  <h2 class="faq-title">Frequently Asked Questions</h2>

  <details class="faq-item" itemscope itemprop="mainEntity"
           itemtype="https://schema.org/Question">
    <summary class="faq-question" itemprop="name">
      How do I install Bengal?
    </summary>
    <div class="faq-answer" itemscope itemprop="acceptedAnswer"
         itemtype="https://schema.org/Answer">
      <div itemprop="text">
        <p>Use pip to install Bengal:</p>
        <pre><code>pip install bengal</code></pre>
      </div>
    </div>
  </details>

  <details class="faq-item" open itemscope itemprop="mainEntity"
           itemtype="https://schema.org/Question">
    <!-- ... -->
  </details>
</section>
```

### Visual Design

```
┌─────────────────────────────────────────────────────────┐
│  Frequently Asked Questions                             │
├─────────────────────────────────────────────────────────┤
│  ▶ How do I install Bengal?                             │
├─────────────────────────────────────────────────────────┤
│  ▼ Does Bengal support Windows?                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Yes! Bengal runs on Windows, macOS, and Linux.      ││
│  └─────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│  ▶ How do I upgrade?                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Comparison Table Directive

### Problem

Feature comparison tables require manual HTML for check/cross icons and proper styling. No semantic distinction between comparison data and regular tables.

### Solution

`{compare}` directive that transforms markdown tables into styled comparisons.

### Syntax

```markdown
:::{compare}
:items: Free,Pro,Enterprise
:highlight: Pro

| Feature | Free | Pro | Enterprise |
|---------|:----:|:---:|:----------:|
| Pages | 10 | ∞ | ∞ |
| Custom Domain | ❌ | ✅ | ✅ |
| SSL | ✅ | ✅ | ✅ |
| Priority Support | ❌ | ❌ | ✅ |
| Price | $0 | $9/mo | $49/mo |
:::
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:items:` | string | - | Comma-separated column names (for header styling) |
| `:highlight:` | string | - | Column to highlight as "recommended" |
| `:class:` | string | - | Custom CSS class |
| `:sticky-header:` | bool | `true` | Keep header visible on scroll |
| `:sticky-column:` | bool | `true` | Keep first column visible on scroll |

### Symbol Replacements

The directive auto-replaces common symbols:

| Input | Rendered |
|-------|----------|
| `✅` or `yes` or `true` | Green checkmark |
| `❌` or `no` or `false` | Red X |
| `∞` or `unlimited` | Infinity symbol |
| `—` or `-` | Em dash (not available) |
| `~` | Partial/limited indicator |

### Visual Design

```
┌────────────────┬────────┬─────────┬─────────────┐
│ Feature        │  Free  │  ✨Pro  │ Enterprise  │
├────────────────┼────────┼─────────┼─────────────┤
│ Pages          │   10   │    ∞    │      ∞      │
├────────────────┼────────┼─────────┼─────────────┤
│ Custom Domain  │   ❌   │   ✅    │     ✅      │
├────────────────┼────────┼─────────┼─────────────┤
│ Priority Supp. │   ❌   │   ❌    │     ✅      │
├────────────────┼────────┼─────────┼─────────────┤
│ Price          │  Free  │  $9/mo  │   $49/mo    │
└────────────────┴────────┴─────────┴─────────────┘
                     ↑ Highlighted column
```

---

## 5. Keyboard Directive

### Problem

Documenting keyboard shortcuts requires manual `<kbd>` tags or inconsistent styling. No standard way to show key combinations.

### Solution

Inline `{kbd}` directive for keyboard shortcuts.

### Syntax

```markdown
Press :::{kbd}Ctrl+S::: to save.

Use :::{kbd}⌘ K::: then :::{kbd}⌘ S::: to save all.

The shortcut :::{kbd}Ctrl+Shift+P::: opens the command palette.
```

### Key Normalization

The directive normalizes common key representations:

| Input | Rendered |
|-------|----------|
| `Ctrl` or `Control` | Ctrl (or ⌃ on Mac) |
| `Cmd` or `Command` or `⌘` | ⌘ |
| `Alt` or `Option` or `⌥` | Alt (or ⌥ on Mac) |
| `Shift` or `⇧` | ⇧ |
| `Enter` or `Return` | ↵ |
| `Tab` | ⇥ |
| `Backspace` or `Delete` | ⌫ |
| `Escape` or `Esc` | ⎋ |
| `Space` | ␣ |
| `+` (between keys) | Rendered as separator |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:platform:` | enum | `auto` | Platform: `auto`, `mac`, `windows`, `linux` |
| `:style:` | enum | `default` | Style: `default`, `minimal`, `outlined` |

### HTML Output

```html
<kbd class="kbd-combo">
  <kbd class="kbd-key">Ctrl</kbd>
  <span class="kbd-plus">+</span>
  <kbd class="kbd-key">Shift</kbd>
  <span class="kbd-plus">+</span>
  <kbd class="kbd-key">P</kbd>
</kbd>
```

### Visual Design

```
┌──────┐   ┌───────┐   ┌───┐
│ Ctrl │ + │ Shift │ + │ P │
└──────┘   └───────┘   └───┘
```

---

## 6. Diff Directive

### Problem

Showing code changes requires custom styling or external tools. No native support for diff visualization in documentation.

### Solution

`{diff}` directive that renders code changes with +/- line highlighting.

### Syntax

```markdown
:::{diff}
:language: python
:title: Fixing the authentication bug
:line-numbers: true

  def authenticate(user):
-     if user.password == stored_password:
+     if verify_password(user.password, stored_hash):
          return create_session(user)
-     return None
+     raise AuthenticationError("Invalid credentials")
:::
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `:language:` | string | - | Syntax highlighting language |
| `:title:` | string | - | Diff title/description |
| `:line-numbers:` | bool | `false` | Show line numbers |
| `:highlight-only:` | bool | `false` | Only highlight changed lines (hide context) |
| `:side-by-side:` | bool | `false` | Side-by-side instead of unified diff |

### Line Markers

| Prefix | Meaning |
|--------|---------|
| `-` | Removed line (red background) |
| `+` | Added line (green background) |
| ` ` (space) | Context line (no highlight) |
| `!` | Modified line (yellow background) |

### HTML Output

```html
<div class="diff" data-language="python">
  <div class="diff-header">
    <span class="diff-title">Fixing the authentication bug</span>
  </div>
  <pre class="diff-content"><code>
    <span class="diff-context">  def authenticate(user):</span>
    <span class="diff-removed">-     if user.password == stored_password:</span>
    <span class="diff-added">+     if verify_password(user.password, stored_hash):</span>
    <span class="diff-context">          return create_session(user)</span>
    <span class="diff-removed">-     return None</span>
    <span class="diff-added">+     raise AuthenticationError("Invalid credentials")</span>
  </code></pre>
</div>
```

### Visual Design

```
┌─ Fixing the authentication bug ─────────────────────────────┐
│   def authenticate(user):                                   │
│ - ░░░░if user.password == stored_password:░░░░░░░░░░░░░░░░ │
│ + ▓▓▓▓if verify_password(user.password, stored_hash):▓▓▓▓▓ │
│       return create_session(user)                           │
│ - ░░░░return None░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ + ▓▓▓▓raise AuthenticationError("Invalid credentials")▓▓▓▓ │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### File Structure

```
bengal/directives/
├── timeline.py          # Timeline + TimelineEvent
├── file_tree.py         # FileTree
├── faq.py               # FAQ + Question
├── compare.py           # Comparison table
├── kbd.py               # Keyboard shortcuts
└── diff.py              # Code diff

bengal/themes/default/assets/
├── css/components/
│   ├── timeline.css
│   ├── file-tree.css
│   ├── faq.css
│   ├── compare.css
│   ├── kbd.css
│   └── diff.css
└── js/enhancements/
    ├── file-tree.js     # Collapsible folders
    └── faq.js           # Single-open accordion
```

### Contracts

```python
# bengal/directives/contracts.py

TIMELINE_CONTRACT = DirectiveContract(
    requires_children=("timeline_event",),
    min_children=1,
    allowed_children=("timeline_event", "blank_line"),
)

TIMELINE_EVENT_CONTRACT = DirectiveContract(
    requires_parent=("timeline",),
)

FAQ_CONTRACT = DirectiveContract(
    requires_children=("question",),
    min_children=1,
    allowed_children=("question", "blank_line"),
)

QUESTION_CONTRACT = DirectiveContract(
    requires_parent=("faq",),
)
```

---

## Implementation Priority

### Phase 1: High Impact (Week 1)

| Directive | Complexity | Value | Notes |
|-----------|------------|-------|-------|
| **File Tree** | Medium | Very High | Every doc needs this |
| **FAQ** | Low | High | Simple, SEO benefits |
| **Keyboard** | Low | Medium | Small, self-contained |

### Phase 2: Medium Impact (Week 2)

| Directive | Complexity | Value | Notes |
|-----------|------------|-------|-------|
| **Timeline** | Medium | High | Great for changelogs |
| **Diff** | Medium | Medium | Code-focused docs |

### Phase 3: Polish (Week 3)

| Directive | Complexity | Value | Notes |
|-----------|------------|-------|-------|
| **Compare** | Low | Medium | Pricing/feature pages |

---

## Implementation Estimates

| Directive | Python | CSS | JS | Tests | Docs | Total |
|-----------|--------|-----|-----|-------|------|-------|
| Timeline | 2h | 1h | 0.5h | 1h | 0.5h | 5h |
| File Tree | 2h | 1h | 1h | 1h | 0.5h | 5.5h |
| FAQ | 1.5h | 0.5h | 0.5h | 1h | 0.5h | 4h |
| Compare | 1.5h | 1h | 0h | 1h | 0.5h | 4h |
| Keyboard | 1h | 0.5h | 0h | 0.5h | 0.5h | 2.5h |
| Diff | 2h | 1h | 0h | 1h | 0.5h | 4.5h |
| **Total** | | | | | | **~25h** |

---

## Testing Strategy

### Unit Tests

```python
class TestTimelineDirective:
    def test_renders_vertical_layout(self): ...
    def test_alternating_style(self): ...
    def test_event_status_classes(self): ...
    def test_requires_events(self): ...  # Contract

class TestFileTreeDirective:
    def test_parses_indented_format(self): ...
    def test_parses_ascii_format(self): ...
    def test_annotations_become_badges(self): ...
    def test_comments_become_descriptions(self): ...

class TestFAQDirective:
    def test_schema_org_markup(self): ...
    def test_single_open_mode(self): ...
    def test_requires_questions(self): ...  # Contract

class TestCompareDirective:
    def test_symbol_replacement(self): ...
    def test_highlight_column(self): ...
    def test_sticky_header(self): ...

class TestKbdDirective:
    def test_key_normalization(self): ...
    def test_combo_splitting(self): ...
    def test_platform_symbols(self): ...

class TestDiffDirective:
    def test_line_classification(self): ...
    def test_syntax_highlighting(self): ...
    def test_side_by_side_mode(self): ...
```

---

## Success Criteria

- [ ] All 6 directives render correct HTML
- [ ] Contract validation works for nested directives
- [ ] CSS renders properly in default theme
- [ ] JavaScript enhancements work (file-tree, faq)
- [ ] Graceful degradation without JS
- [ ] Accessibility (ARIA, keyboard nav)
- [ ] Documentation with examples
- [ ] Unit tests pass

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| File tree parsing edge cases | Support both indented and ASCII formats; robust parser |
| Schema.org validation | Test with Google's Rich Results Test tool |
| Diff syntax conflicts | Use standard unified diff markers (+/-/space) |
| Platform-specific kbd symbols | Default to universal; option for platform-specific |

---

## Related Work

- **Steps directive**: `bengal/directives/steps.py` - closure pattern model
- **Dropdown directive**: `bengal/directives/dropdown.py` - collapsible content
- **Tabs directive**: `bengal/directives/tabs.py` - interactive switching
- **Checklist**: `bengal/directives/checklist.py` - interactive + JS

---

## References

- Schema.org FAQPage: https://schema.org/FAQPage
- Unified Diff Format: https://en.wikipedia.org/wiki/Diff#Unified_format
- ARIA Tree Role: https://www.w3.org/WAI/ARIA/apg/patterns/treeview/
