# RFC: Bengal Terminal UX Style Guide

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2024-12-21  
**Subsystem**: CLI / Output  

---

## Summary

This RFC defines a comprehensive terminal UX style guide for Bengal's CLI output, establishing visual identity, component patterns, and implementation standards that align with Bengal's web design system.

**Implementation Note**: This style guide is implemented by the [Textual RFC](rfc-terminal-ux-textual.md) for interactive dashboards and the standard Rich-based output for static commands.

---

## Motivation

Bengal has a mature CSS design token system with 5 color palettes, semantic tokens, and strong brand identity (Bengal cat mascot, warm orange primary). However, the terminal output exists as a separate island with its own ad-hoc conventions. This creates:

1. **Visual inconsistency** between web output and CLI experience
2. **Limited theming** — web supports 5 palettes, terminal has one hardcoded palette
3. **No formal specification** — output styling decisions are scattered across code
4. **Unclear component patterns** — each feature reinvents output formatting

This RFC establishes a unified terminal design language.

---

## Goals

1. **Unify brand identity** across CLI and web output
2. **Establish reusable component patterns** for common output types
3. **Support palette-aware terminal theming**
4. **Document all conventions** in one authoritative source
5. **Maintain ASCII-first philosophy** with graceful enhancement

## Non-Goals

- Changing the web CSS token system
- Building a web-based terminal emulator (future work)
- Supporting non-TTY environments beyond basic fallback

---

## Design

### 1. Brand Identity

#### 1.1 Mascots

Bengal uses two Unicode mascots for personality and quick visual parsing:

| Symbol | Name | Usage | Context |
|--------|------|-------|---------|
| `ᓚᘏᗢ` | Bengal Cat | Success headers, help headers, completion | Positive outcomes |
| `ᘛ⁐̤ᕐᐷ` | Mouse | Error headers only | Errors (cat catches mice/bugs) |

**Rules**:
- Mascots appear at the **start of major headers only**
- Always followed by **2 spaces** before text
- Never used inline within paragraphs
- Always displayed regardless of emoji settings

```python
# ✅ CORRECT
cli.header("ᓚᘏᗢ  Build complete")
cli.error_header("ᘛ⁐̤ᕐᐷ  Build failed")

# ❌ WRONG - inline mascot
cli.info("Found ᓚᘏᗢ 245 pages")
```

#### 1.2 Status Icons

ASCII-first with optional emoji mode (`BENGAL_EMOJI=1`):

| Status | ASCII | Emoji | Rich Style |
|--------|-------|-------|------------|
| Success | `✓` | `✨` | `[success]` |
| Warning | `!` | `⚠️` | `[warning]` |
| Error | `x` | `❌` | `[error]` |
| Info | `-` | `ℹ️` | `[info]` |
| Tip | `*` | `💡` | `[tip]` |
| Pending | `·` | `⏳` | `[dim]` |

#### 1.3 Performance Grades

| Grade | ASCII | Emoji | Threshold |
|-------|-------|-------|-----------|
| Excellent | `++` | `🚀` | <100ms |
| Fast | `+` | `⚡` | <1000ms |
| Moderate | `~` | `📊` | <5000ms |
| Slow | `-` | `🐌` | ≥5000ms |

---

### 2. Color System

#### 2.1 Core Palette

The terminal palette derives from `bengal/utils/rich_console.py`:

```python
PALETTE = {
    # Brand
    "primary": "#FF9D00",      # Vivid Orange (Bengal)
    "secondary": "#3498DB",    # Bright Blue
    "accent": "#F1C40F",       # Sunflower Yellow

    # Semantic
    "success": "#2ECC71",      # Emerald Green
    "warning": "#E67E22",      # Carrot Orange
    "error": "#E74C3C",        # Alizarin Crimson
    "info": "#95A5A6",         # Silver
    "muted": "#7F8C8D",        # Grayish
}
```

#### 2.2 Rich Theme Tokens

Semantic tokens for Rich console styling:

| Token | Usage | Color | Style |
|-------|-------|-------|-------|
| `header` | Section headers | `#FF9D00` | bold |
| `success` | Success messages | `#2ECC71` | — |
| `warning` | Warning messages | `#E67E22` | — |
| `error` | Error messages | `#E74C3C` | bold |
| `bengal` | Cat mascot | `#FF9D00` | bold |
| `mouse` | Mouse mascot | `#E74C3C` | bold |
| `info` | Dim/secondary | `#95A5A6` | — |
| `tip` | Tips/hints | `#7F8C8D` | italic |
| `path` | File paths | `#3498DB` | — |
| `phase` | Build phases | — | bold |
| `link` | URLs | `#3498DB` | underline |
| `prompt` | User prompts | `#F1C40F` | — |
| `dim` | De-emphasized | — | dim |
| `highlight` | Emphasis | `#F1C40F` | bold |
| `metric_label` | Metric names | `#F1C40F` | bold |
| `metric_value` | Metric values | — | — |

#### 2.3 Palette-Aware Theming

Support switching terminal colors via design tokens. As defined in the [Textual RFC](rfc-terminal-ux-textual.md#3-shared-token-system), these tokens generate both web CSS and terminal `.tcss` variables.

**Palette mappings** (derive from CSS tokens):

| Palette | Primary | Accent | Success | Error |
|---------|---------|--------|---------|-------|
| Default | `#2196F3` | `#FF9800` | `#4CAF50` | `#F44336` |
| Blue Bengal | `#1976D2` | `#FF9800` | `#388E3C` | `#D32F2F` |
| Brown Bengal | `#6D4C41` | `#D4A574` | `#558B2F` | `#C62828` |
| Charcoal Bengal | `#1A1D21` | `#8B6914` | `#3D6B4A` | `#A63D3D` |
| Silver Bengal | `#607D8B` | `#78909C` | `#66BB6A` | `#EF5350` |
| Snow Lynx | `#4FA8A0` | `#5BB8AF` | `#2E7D5A` | `#C62828` |

---

### 3. Typography

#### 3.1 Casing Conventions

| Element | Case | Example |
|---------|------|---------|
| Headers | Sentence case | `Content statistics:` |
| Status messages | Sentence case | `Build complete` |
| Phase names | Title case | `Discovery`, `Rendering` |
| Options | Lowercase | `--verbose`, `--output` |
| Commands | Lowercase | `bengal build` |

**Never use**:
- ALL CAPS for headers (`BUILD COMPLETE`)
- Title Case for messages (`Build Is Complete`)

#### 3.2 Spacing & Indentation

```
[mascot]  [header text]                    [right-aligned metric]

   [section label]:
   ├─ [item]        [value]
   ├─ [item]        [value]
   └─ [item]        [value]

   [subsection]:
      [detail line with 3-space indent]
```

**Rules**:
- **2 spaces** after mascot
- **3 spaces** for section content indentation
- **6 spaces** for nested content (3 + 3)
- Right-align timing metrics
- One blank line between major sections

#### 3.3 Line Length

- **Maximum**: 80 characters (terminal-safe)
- **Wrap long paths**: Use `…` ellipsis for paths >50 chars
- **Wrap long messages**: Break at word boundaries

---

### 4. Component Library

#### 4.1 Headers

**Main Header** (with mascot):
```
ᓚᘏᗢ  Build complete                              0.82s
```

**Section Header**:
```
   Content statistics:
```

**Subheader** (with divider):
```
   === Options =========================================
```

#### 4.2 Tree Structure

For hierarchical data (content stats, file trees):

```
   Content statistics:
   ├─ Pages         245
   ├─ Sections       18
   ├─ Assets        134
   └─ Taxonomies      3
```

**Characters**:
- Branch: `├─` (U+251C U+2500)
- Last: `└─` (U+2514 U+2500)
- Continuation: `│ ` (U+2502 + space)

#### 4.3 Tables

Use box-drawing for formal tables:

```
   ┌──────────────┬─────────┬─────────┐
   │ Phase        │    Time │   % Tot │
   ├──────────────┼─────────┼─────────┤
   │ Discovery    │    45ms │   5.5%  │
   │ Rendering    │   501ms │  61.1%  │
   └──────────────┴─────────┴─────────┘
```

**Box-drawing characters**:
- Corners: `┌ ┐ └ ┘`
- Edges: `─ │`
- Junctions: `┬ ┴ ├ ┤ ┼`

Use Rich `Table` component with `box=box.ROUNDED` for consistency.

#### 4.4 Progress Bars

**Determinate progress**:
```
   Rendering     ███████░░░  65%  (159/245 pages)
```

**Indeterminate spinner**:
```
   Rendering     ⠹  processing...
```

**Characters**:
- Filled: `█` (U+2588)
- Empty: `░` (U+2591)
- Spinner: `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` (Braille pattern)

#### 4.5 Panels / Boxes

For important callouts (errors, tips):

```
   ┌─────────────────────────────────────────────────────────┐
   │  Template not found: blog/custom.html                   │
   │                                                         │
   │  Location: content/blog/my-post.md:1                    │
   │  Expected: themes/default/templates/blog/custom.html    │
   │                                                         │
   │  Tip: Create the template or use template: post.html    │
   └─────────────────────────────────────────────────────────┘
```

Use Rich `Panel` component with border style based on context:
- Error: `border_style="red"`
- Warning: `border_style="yellow"`
- Info: `border_style="blue"`
- Success: `border_style="green"`

#### 4.6 Key-Value Pairs

For configuration display:

```
   Build configuration:
      output_dir      public/
      baseurl         /
      parallel        true
      cache           enabled (95% hit rate)
```

**Alignment**: Keys left-padded, values aligned at column 20.

#### 4.7 Metrics Line

For performance/stats summary:

```
   Performance: A (94/100) ⚡  │  Cache: 95% hit  │  Output: 4.2MB
```

Use `│` to separate metric groups on same line.

---

### 5. Message Patterns

#### 5.1 Success Message

```
ᓚᘏᗢ  Build complete                              0.82s

   Content statistics:
   ├─ Pages         245
   ├─ Sections       18
   └─ Assets        134

   Output: public/ (4.2MB)
```

#### 5.2 Warning Message

```
ᓚᘏᗢ  Build complete (with warnings)              0.94s

   ! Missing title in content/blog/untitled.md
   ! Broken link: /docs/old-page in content/guide.md

   Output: public/ (4.2MB)
```

#### 5.3 Error Message

```
ᘛ⁐̤ᕐᐷ  Build failed                               1 error

   ┌─────────────────────────────────────────────────────────┐
   │  TemplateNotFound: blog/custom.html                     │
   │                                                         │
   │  File: content/blog/my-post.md:1                        │
   │  Template: blog/custom.html                             │
   │                                                         │
   │  Searched in:                                           │
   │    • themes/default/templates/                          │
   │    • site/templates/                                    │
   │                                                         │
   │  Tip: Use 'template: post.html' or create the template  │
   └─────────────────────────────────────────────────────────┘
```

**Error message structure**:
1. Error type and brief description
2. File location with line number
3. Context (what was searched, what was expected)
4. Actionable tip

#### 5.4 Help Display

```
ᓚᘏᗢ  bengal build

   Build your Bengal site to static HTML.

   Usage: bengal build [OPTIONS] [SOURCE]

   Options:
      --output, -o PATH         Output directory [default: public/]
      --config, -c PATH         Config file path
      --profile TEXT            Build profile (dev|writer|themer)
      --parallel/--no-parallel  Enable parallel rendering [default: true]
      --incremental, -i         Incremental build (skip unchanged)
      --verbose, -v             Verbose output
      --help                    Show this message and exit

   Examples:
      bengal build                    # Standard build
      bengal build -o dist/           # Custom output dir
      bengal build --profile writer   # Writer-friendly output
```

#### 5.5 Phase Progress

During build:

```
   ✓ Discovery      45ms   (245 pages)
   ✓ Taxonomies     12ms   (3 taxonomies)
   ⠹ Rendering     ███████░░░  65%
   · Assets        pending
   · Postprocess   pending
```

After completion:

```
   ✓ Discovery      45ms   (245 pages)
   ✓ Taxonomies     12ms   (3 taxonomies)
   ✓ Rendering     501ms   (245 pages, 489/sec)
   ✓ Assets        150ms   (134 files)
   ✓ Postprocess   112ms   (sitemap, rss)
```

---

### 6. User Profiles

Output adapts to user profile set via `--profile` or config:

#### 6.1 Writer Profile

Minimal, encouraging, action-focused:

```
ᓚᘏᗢ  Built 245 pages → public/

   ✓ Ready to preview at http://localhost:3000
```

#### 6.2 Theme Developer Profile

Focus on template/asset details:

```
ᓚᘏᗢ  Build complete                              0.82s

   Templates rendered:
   ├─ doc/single.html       187 uses
   ├─ blog/post.html         45 uses
   └─ home.html               1 use

   Assets processed:
   ├─ CSS                    12 files (45KB)
   ├─ JavaScript              8 files (120KB)
   └─ Images                114 files (2.1MB)

   Output: public/
```

#### 6.3 Developer Profile

Full statistics, performance metrics:

```
ᓚᘏᗢ  Build complete                              0.82s ⚡

   Content statistics:
   ├─ Pages         245 (12 changed, 233 cached)
   ├─ Sections       18
   ├─ Assets        134
   └─ Taxonomies      3

   Phase breakdown:
   ├─ Discovery      45ms   (5.5%)
   ├─ Taxonomies     12ms   (1.5%)
   ├─ Rendering     501ms  (61.1%)  ← bottleneck
   ├─ Assets        150ms  (18.3%)
   └─ Postprocess   112ms  (13.6%)

   Cache: 95% hit rate (233/245 pages), 2.3MB saved
   Throughput: 489 pages/sec

   Output: public/ (4.2MB)
```

#### 6.4 AI/Automation Profile

Machine-readable JSON:

```json
{
  "status": "success",
  "duration_ms": 820,
  "pages": 245,
  "sections": 18,
  "assets": 134,
  "output_dir": "public/",
  "output_size_bytes": 4404019,
  "cache_hit_rate": 0.95,
  "warnings": [],
  "errors": []
}
```

---

### 7. Accessibility

#### 7.1 Color Independence

Never rely solely on color to convey meaning:

```
# ✅ CORRECT - Icon + color
✓ Build complete    (green + checkmark)
x Build failed      (red + x symbol)

# ❌ WRONG - Color only
Build complete      (green text, no icon)
Build failed        (red text, no icon)
```

#### 7.2 Screen Reader Compatibility

- Use semantic status indicators (✓, x, !) not decorative symbols
- Provide text alternatives for progress bars
- Avoid ASCII art that doesn't convey meaning

#### 7.3 Contrast

All colors meet WCAG AA contrast ratio (4.5:1) against both:
- Dark terminal backgrounds (`#1a1a1a`)
- Light terminal backgrounds (`#fafafa`)

---

### 8. Environment Detection

#### 8.1 TTY Detection

```python
def should_use_rich() -> bool:
    """Determine if rich features should be enabled."""
    # Disable in CI
    if os.getenv("CI"):
        return False

    # Disable for dumb terminals
    if os.getenv("TERM", "").lower() == "dumb":
        return False

    # Check if stdout is a terminal
    return sys.stdout.isatty()
```

#### 8.2 Fallback Output

When Rich is disabled, use plain text:

```
[SUCCESS] Build complete (0.82s)

Content:
  Pages: 245
  Sections: 18
  Assets: 134

Output: public/
```

#### 8.3 Environment Variables

| Variable | Purpose | Values |
|----------|---------|--------|
| `BENGAL_EMOJI` | Enable emoji icons | `1` to enable |
| `BENGAL_PALETTE` | Terminal palette | Palette name |
| `NO_COLOR` | Disable all colors | Any value |
| `TERM` | Terminal type | `dumb` disables rich |
| `CI` | CI environment | Disables rich |

---

### 9. Implementation

#### 9.1 CLIOutput Class

Central output manager (existing in `bengal/output/core.py`):

```python
class CLIOutput:
    """Centralized CLI output manager."""

    def header(self, text: str) -> None:
        """Print main header with mascot."""

    def section(self, text: str) -> None:
        """Print section header."""

    def phase(self, name: str, duration_ms: int, details: str = "") -> None:
        """Print phase completion line."""

    def success(self, text: str) -> None:
        """Print success message."""

    def warning(self, text: str) -> None:
        """Print warning message."""

    def error(self, text: str) -> None:
        """Print error message."""

    def error_panel(self, error: Exception, context: dict) -> None:
        """Print boxed error with context."""

    def tree(self, items: list[tuple[str, str]]) -> None:
        """Print tree structure."""

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Print formatted table."""

    def progress(self, current: int, total: int, label: str) -> None:
        """Update progress bar."""
```

#### 9.2 Icon Set

```python
@dataclass(frozen=True)
class IconSet:
    # Branding (always shown)
    mascot: str = "ᓚᘏᗢ"
    error_mascot: str = "ᘛ⁐̤ᕐᐷ"

    # Status (ASCII or emoji)
    success: str = "✓"
    warning: str = "!"
    error: str = "x"
    info: str = "-"
    tip: str = "*"
    pending: str = "·"

    # Navigation
    arrow: str = "→"
    tree_branch: str = "├─"
    tree_end: str = "└─"

    # Performance
    grade_excellent: str = "++"
    grade_fast: str = "+"
    grade_moderate: str = "~"
    grade_slow: str = "-"
```

---

## Alternatives Considered

### Alternative 1: Full Emoji by Default

**Rejected**: Many terminal fonts don't render emoji well; ASCII provides universal baseline.

### Alternative 2: No Mascots

**Rejected**: The cat/mouse mascots provide unique brand identity and quick visual parsing of success/error states.

### Alternative 3: Minimal Output Only

**Rejected**: Developers need detailed stats; profiles solve this by adapting to audience.

---

## Migration Path

### Phase 1: Consolidate (Current)

1. Document existing conventions (this RFC)
2. Audit current output for consistency
3. Fix violations of this style guide

### Phase 2: Enhance

1. Add missing components (error panels, progress bars)
2. Implement profile-aware output
3. Add `--palette` flag support

### Phase 3: Extend

1. Web terminal preview component
2. Interactive terminal mode
3. Streaming output for long builds

---

## Open Questions

1. **Palette switching**: Should terminal palette match web palette automatically?
2. **Animation frequency**: How often should spinners update (50ms? 100ms?)?
3. **Log file format**: Should log files use ANSI codes or plain text?

---

## References

- [RFC: Bengal Terminal UX with Textual](rfc-terminal-ux-textual.md) — Technical implementation framework
- `bengal/utils/rich_console.py` - Current Rich theme definition
- `bengal/output/icons.py` - Icon set definitions
- `bengal/output/core.py` - CLIOutput implementation
- `bengal/output/README.md` - Current conventions
- `bengal/themes/default/assets/css/tokens/` - CSS design token system

---

## Appendix: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│  BENGAL TERMINAL STYLE QUICK REFERENCE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MASCOTS                                                    │
│    ᓚᘏᗢ  Success/help headers                               │
│    ᘛ⁐̤ᕐᐷ  Error headers only                                 │
│                                                             │
│  STATUS ICONS                                               │
│    ✓  Success    !  Warning    x  Error                     │
│    -  Info       *  Tip        ·  Pending                   │
│                                                             │
│  COLORS                                                     │
│    #FF9D00  Primary (Bengal Orange)                         │
│    #3498DB  Secondary (Blue)                                │
│    #2ECC71  Success (Green)                                 │
│    #E67E22  Warning (Orange)                                │
│    #E74C3C  Error (Red)                                     │
│                                                             │
│  SPACING                                                    │
│    2 spaces after mascot                                    │
│    3 spaces for section indent                              │
│    6 spaces for nested content                              │
│                                                             │
│  CASING                                                     │
│    Sentence case for headers: "Content statistics:"         │
│    Title case for phases: "Discovery", "Rendering"          │
│    Lowercase for commands: "bengal build"                   │
│                                                             │
│  TREE CHARACTERS                                            │
│    ├─  Branch    └─  Last    │   Continuation               │
│                                                             │
│  PROGRESS                                                   │
│    ███████░░░  Determinate                                  │
│    ⠹          Spinner                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
