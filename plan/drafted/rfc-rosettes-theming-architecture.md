# RFC: Rosettes Theming Architecture — Semantic Token System

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0003 |
| **Title** | Rosettes Theming: Semantic Token System for Syntax Highlighting |
| **Status** | Draft |
| **Created** | 2025-12-24 |
| **Revised** | 2025-12-24 |
| **Revision** | v4 — Added code.css migration plan, semantic classes as default, CSS variable strategy |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Modern theming architecture for Rosettes with semantic color roles |
| **Why** | Clean-slate design for the future—no legacy baggage |
| **Effort** | 3-4 weeks for core palette system + 8 built-in themes + Bengal integration + CSS migration |
| **Risk** | Low — standalone system, Bengal design token integration |
| **Dependencies** | Rosettes core (RFC-0002), optionally Bengal design tokens |

**Key Design Goals:**
1. ✅ Semantic roles (why a color, not just which color)
2. ✅ Immutable, thread-safe palettes (frozen dataclasses)
3. ✅ CSS custom properties for runtime theming
4. ✅ Dark/light adaptive themes from single definition
5. ✅ WCAG AA contrast validation
6. ✅ **Dual class output**: Semantic (`.syntax-keyword`) or Pygments-compatible (`.k`)
7. ✅ Modern CSS: `@layer`, `color-mix()`, `light-dark()`, container queries
8. ✅ Bengal design system integration
9. ✅ Terminal (ANSI) palette support
10. ✅ **Zero-config experience**: Syntax theme auto-inherits from site palette

---

## Relationship with RFC-0002

RFC-0002 states Rosettes will be "Pygments CSS compatible" with cryptic class names (`.k`, `.nf`). This RFC introduces semantic class names (`.syntax-keyword`, `.syntax-function`) as the **default** while maintaining backward compatibility.

**Resolution**: Dual output mode via `css_class_style` parameter:

| Mode | Class Names | Use Case |
|------|-------------|----------|
| `"semantic"` (default) | `.syntax-keyword`, `.syntax-function` | New projects, modern CSS |
| `"pygments"` | `.k`, `.nf` | Drop-in Pygments theme compatibility |

This preserves RFC-0002's compatibility promise while enabling the modern semantic approach by default.

---

## Motivation

### Philosophy: Embrace the Future

Rosettes is a clean-slate syntax highlighter. Its theming system should be equally forward-looking:

| Legacy Approach | Rosettes Approach |
|-----------------|-------------------|
| Token → Color direct | Token → Role → Color (semantic layer) |
| Cryptic class names (`.k`, `.nf`) | Readable classes (`.syntax-keyword`, `.syntax-function`) |
| Hardcoded hex values | CSS custom properties |
| Separate dark/light themes | Single adaptive palette |
| Mutable class state | Frozen dataclasses |
| No accessibility | WCAG AA validation built-in |
| Web only | Web + Terminal (ANSI) |

### Why Semantic Theming?

Syntax highlighting colors aren't arbitrary—they communicate **meaning**:

| Code Element | Semantic Role | Visual Intent |
|--------------|---------------|---------------|
| `if`, `for`, `return` | Control flow | Draw attention (bold/bright) |
| `def`, `class`, `fn` | Declaration | Structure (distinct) |
| `"hello"`, `'world'` | String literal | Data (warm colors) |
| `# comment` | Comment | De-emphasized (muted/italic) |
| `MyClass`, `int` | Type | Identity (distinct hue) |

**The Insight**: Instead of mapping 100+ token types to colors, map them to ~18 semantic roles. Themes define colors for roles, not tokens.

| Approach | Theme Definition |
|----------|------------------|
| Traditional | 100+ token → color mappings |
| Semantic | 18 role → color mappings |

Benefits:
1. **Easier to create** (define 18 roles, not 100+ tokens)
2. **More consistent** (roles ensure visual hierarchy)
3. **Easier to adapt** (dark/light mode changes role colors, not token mappings)
4. **Self-documenting** (role names explain intent)

---

## Design Goals

### 1. Semantic Role Layer

Introduce a semantic layer between tokens and colors:

```
TokenType → SyntaxRole → Color
```

```python
class SyntaxRole(StrEnum):
    """Why code elements are colored, not just which color."""

    # Control & Structure
    CONTROL_FLOW = "control"      # if, for, while, return, break
    DECLARATION = "declaration"    # def, class, let, const, fn
    IMPORT = "import"             # import, from, require, use

    # Data & Literals  
    STRING = "string"             # "hello", 'world', `template`
    NUMBER = "number"             # 42, 3.14, 0xFF
    BOOLEAN = "boolean"           # true, false, True, False

    # Identifiers
    TYPE = "type"                 # Class names, type annotations
    FUNCTION = "function"         # Function/method names
    VARIABLE = "variable"         # Variable names
    CONSTANT = "constant"         # ALL_CAPS constants

    # Documentation
    COMMENT = "comment"           # # comment, // comment
    DOCSTRING = "docstring"       # """docstring""", /** */

    # Feedback
    ERROR = "error"               # Syntax errors
    WARNING = "warning"           # Deprecation, lint warnings
    ADDED = "added"               # Diff: added lines
    REMOVED = "removed"           # Diff: removed lines

    # Base
    TEXT = "text"                 # Default text, punctuation
    MUTED = "muted"               # De-emphasized elements
```

### 2. Immutable Palette Definition

Themes are frozen dataclasses with semantic color slots:

```python
@dataclass(frozen=True, slots=True)
class SyntaxPalette:
    """Immutable syntax highlighting palette. Thread-safe by design."""

    name: str

    # Background
    background: str
    background_highlight: str  # For hl_lines

    # Semantic syntax colors (the 18 core roles)
    control_flow: str     # Keywords that control execution
    declaration: str      # def, class, let, const
    import_: str          # import statements

    string: str
    number: str
    boolean: str

    type_: str            # Type names
    function: str         # Function names
    variable: str         # Variable names (optional styling)
    constant: str         # ALL_CAPS constants

    comment: str
    docstring: str

    error: str
    warning: str
    added: str
    removed: str

    # Base text
    text: str             # Default text/punctuation
    muted: str            # De-emphasized

    # Style modifiers
    bold_control: bool = True
    bold_declaration: bool = True
    italic_comment: bool = True

    def __post_init__(self):
        """Validate WCAG contrast ratios."""
        # Implemented in validation section
        pass
```

**Comparison: 20 fields vs 100+ Pygments style entries**

### 3. Token → Role Mapping

Static mapping from TokenType to SyntaxRole:

```python
# rosettes/themes/_mapping.py
from rosettes._types import TokenType
from rosettes.themes._roles import SyntaxRole

ROLE_MAPPING: dict[TokenType, SyntaxRole] = {
    # Keywords → Control/Declaration
    # TokenType values are StrEnum with Pygments-compatible string values
    TokenType.KEYWORD: SyntaxRole.CONTROL_FLOW,           # "k"
    TokenType.KEYWORD_CONSTANT: SyntaxRole.BOOLEAN,       # "kc"
    TokenType.KEYWORD_DECLARATION: SyntaxRole.DECLARATION, # "kd"
    TokenType.KEYWORD_NAMESPACE: SyntaxRole.IMPORT,       # "kn"
    TokenType.KEYWORD_TYPE: SyntaxRole.TYPE,              # "kt"

    # Names → Identity
    TokenType.NAME_CLASS: SyntaxRole.TYPE,                # "nc"
    TokenType.NAME_FUNCTION: SyntaxRole.FUNCTION,         # "nf"
    TokenType.NAME_FUNCTION_MAGIC: SyntaxRole.FUNCTION,   # "fm"
    TokenType.NAME_BUILTIN: SyntaxRole.FUNCTION,          # "nb"
    TokenType.NAME_CONSTANT: SyntaxRole.CONSTANT,         # "no"
    TokenType.NAME_VARIABLE: SyntaxRole.VARIABLE,         # "nv"
    TokenType.NAME_DECORATOR: SyntaxRole.DECLARATION,     # "nd"

    # Literals → Data
    TokenType.STRING: SyntaxRole.STRING,                  # "s"
    TokenType.STRING_DOC: SyntaxRole.DOCSTRING,           # "sd"
    TokenType.NUMBER: SyntaxRole.NUMBER,                  # "m"

    # Comments → Documentation
    TokenType.COMMENT: SyntaxRole.COMMENT,                # "c"
    TokenType.COMMENT_SINGLE: SyntaxRole.COMMENT,         # "c1"
    TokenType.COMMENT_MULTILINE: SyntaxRole.COMMENT,      # "cm"

    # Generic → Feedback
    TokenType.GENERIC_DELETED: SyntaxRole.REMOVED,        # "gd"
    TokenType.GENERIC_INSERTED: SyntaxRole.ADDED,         # "gi"
    TokenType.ERROR: SyntaxRole.ERROR,                    # "err"

    # Default
    TokenType.TEXT: SyntaxRole.TEXT,                      # ""
    TokenType.PUNCTUATION: SyntaxRole.TEXT,               # "p"
    TokenType.OPERATOR: SyntaxRole.CONTROL_FLOW,          # "o"
}

# Reverse mapping for Pygments-compatible class output
PYGMENTS_CLASS_MAP: dict[SyntaxRole, str] = {
    SyntaxRole.CONTROL_FLOW: "k",
    SyntaxRole.DECLARATION: "kd",
    SyntaxRole.IMPORT: "kn",
    SyntaxRole.STRING: "s",
    SyntaxRole.DOCSTRING: "sd",
    SyntaxRole.NUMBER: "m",
    SyntaxRole.BOOLEAN: "kc",
    SyntaxRole.TYPE: "nc",
    SyntaxRole.FUNCTION: "nf",
    SyntaxRole.VARIABLE: "nv",
    SyntaxRole.CONSTANT: "no",
    SyntaxRole.COMMENT: "c",
    SyntaxRole.ERROR: "err",
    SyntaxRole.WARNING: "w",
    SyntaxRole.ADDED: "gi",
    SyntaxRole.REMOVED: "gd",
    SyntaxRole.TEXT: "",
    SyntaxRole.MUTED: "x",
}
```

### 4. Dual CSS Class Output

Support both semantic and Pygments-compatible class names:

```python
# rosettes/themes/_css.py
from typing import Literal

CssClassStyle = Literal["semantic", "pygments"]

def get_css_class(role: SyntaxRole, style: CssClassStyle = "semantic") -> str:
    """Get CSS class name for a role."""
    if style == "semantic":
        return f"syntax-{role.value}"  # e.g., "syntax-function"
    else:
        return PYGMENTS_CLASS_MAP.get(role, "")  # e.g., "nf"
```

#### Semantic CSS Output (Default)

```css
/* Generated by rosettes - theme: monokai, style: semantic */
:root {
  /* Rosettes Syntax Palette */
  --syntax-bg: #272822;
  --syntax-bg-highlight: #49483e;
  --syntax-control: #f92672;
  --syntax-declaration: #66d9ef;
  --syntax-import: #f92672;
  --syntax-string: #e6db74;
  --syntax-number: #ae81ff;
  --syntax-boolean: #ae81ff;
  --syntax-type: #a6e22e;
  --syntax-function: #a6e22e;
  --syntax-variable: #f8f8f2;
  --syntax-constant: #ae81ff;
  --syntax-comment: #75715e;
  --syntax-docstring: #75715e;
  --syntax-error: #f92672;
  --syntax-warning: #e6db74;
  --syntax-added: #a6e22e;
  --syntax-removed: #f92672;
  --syntax-text: #f8f8f2;
  --syntax-muted: #75715e;
}

/* Base container */
.rosettes {
  background: var(--syntax-bg);
  color: var(--syntax-text);
  font-family: var(--font-mono, ui-monospace, monospace);
}
.rosettes .line-highlight { background: var(--syntax-bg-highlight); }

/* Semantic token classes - self-documenting! */
.rosettes .syntax-control { color: var(--syntax-control); font-weight: 600; }
.rosettes .syntax-declaration { color: var(--syntax-declaration); font-weight: 600; }
.rosettes .syntax-import { color: var(--syntax-import); }

.rosettes .syntax-string { color: var(--syntax-string); }
.rosettes .syntax-docstring { color: var(--syntax-docstring); font-style: italic; }
.rosettes .syntax-number { color: var(--syntax-number); }
.rosettes .syntax-boolean { color: var(--syntax-boolean); }

.rosettes .syntax-type { color: var(--syntax-type); }
.rosettes .syntax-function { color: var(--syntax-function); }
.rosettes .syntax-variable { color: var(--syntax-variable); }
.rosettes .syntax-constant { color: var(--syntax-constant); }

.rosettes .syntax-comment { color: var(--syntax-comment); font-style: italic; }

.rosettes .syntax-error { color: var(--syntax-error); text-decoration: wavy underline; }
.rosettes .syntax-warning { color: var(--syntax-warning); }
.rosettes .syntax-added { color: var(--syntax-added); }
.rosettes .syntax-removed { color: var(--syntax-removed); }

.rosettes .syntax-punctuation { color: var(--syntax-muted); }
.rosettes .syntax-operator { color: var(--syntax-control); }
```

#### Pygments-Compatible CSS Output

```css
/* Generated by rosettes - theme: monokai, style: pygments */
/* Compatible with existing Pygments themes */

.highlight {
  background: #272822;
  color: #f8f8f2;
}
.highlight .hll { background: #49483e; }

.highlight .k { color: #f92672; font-weight: 600; }
.highlight .kd { color: #66d9ef; font-weight: 600; }
.highlight .kn { color: #f92672; }

.highlight .s { color: #e6db74; }
.highlight .sd { color: #75715e; font-style: italic; }
.highlight .m { color: #ae81ff; }
.highlight .kc { color: #ae81ff; }

.highlight .nc { color: #a6e22e; }
.highlight .nf { color: #a6e22e; }
.highlight .nv { color: #f8f8f2; }
.highlight .no { color: #ae81ff; }

.highlight .c { color: #75715e; font-style: italic; }

.highlight .err { color: #f92672; text-decoration: wavy underline; }
.highlight .gi { color: #a6e22e; }
.highlight .gd { color: #f92672; }
```

**Benefits:**
- **Self-documenting**: `.syntax-function` is readable; `.nf` is cryptic
- **Backward compatible**: Pygments mode for existing themes
- **Runtime theme switching**: Override `--syntax-*` vars without regenerating HTML
- **Design system integration**: Map to external tokens (`--syntax-control: var(--color-primary)`)
- **Scoped**: `.rosettes` namespace prevents conflicts

### 5. Dark/Light Adaptive Palettes

Single theme definition adapts to color scheme using modern CSS:

```python
@dataclass(frozen=True, slots=True)
class AdaptivePalette:
    """Theme that adapts to light/dark mode preference."""

    name: str
    light: SyntaxPalette
    dark: SyntaxPalette

    def to_css(self, css_class_style: CssClassStyle = "semantic") -> str:
        return f"""
/* {self.name} - Adaptive Theme */
/* Uses modern light-dark() function with fallback */

:root {{
  color-scheme: light dark;

  /* Modern: light-dark() function (Chrome 123+, Firefox 120+, Safari 17.5+) */
  --syntax-bg: light-dark({self.light.background}, {self.dark.background});
  --syntax-control: light-dark({self.light.control_flow}, {self.dark.control_flow});
  --syntax-string: light-dark({self.light.string}, {self.dark.string});
  /* ... all tokens ... */
}}

/* Fallback for older browsers (Safari < 17.5, older Chrome/Firefox) */
@supports not (color: light-dark(white, black)) {{
  :root {{
{self.light.to_css_vars(indent=4)}
  }}

  @media (prefers-color-scheme: dark) {{
    :root {{
{self.dark.to_css_vars(indent=6)}
    }}
  }}
}}

/* Explicit overrides via data attribute */
[data-theme="dark"] {{
{self.dark.to_css_vars(indent=2)}
}}

[data-theme="light"] {{
{self.light.to_css_vars(indent=2)}
}}
"""
```

### 6. Modern CSS Architecture

Rosettes embraces modern web platform features, aligned with Bengal's CSS architecture:

#### CSS Layers

Rosettes styles live in a dedicated layer for cascade control:

```css
/* Rosettes declares its own layer */
@layer rosettes {
  .rosettes { /* container styles */ }
  .rosettes .syntax-keyword { /* token styles */ }
}

/* Bengal can easily override */
@layer rosettes, bengal-overrides;

@layer bengal-overrides {
  .rosettes .syntax-control { color: var(--color-primary); }
}
```

#### `color-mix()` for Dynamic Variants

Generate hover states and variants without hardcoding:

```css
.rosettes {
  /* Base background */
  --syntax-bg: #1e1e1e;

  /* Dynamic variants via color-mix() */
  --syntax-bg-hover: color-mix(in oklch, var(--syntax-bg) 90%, white);
  --syntax-bg-highlight: color-mix(in oklch, var(--syntax-bg) 85%, var(--syntax-control));

  /* Muted variants for less important tokens */
  --syntax-comment: color-mix(in oklch, var(--syntax-text) 60%, transparent);
}

.rosettes .line-highlight {
  background: var(--syntax-bg-highlight);
}
```

#### `light-dark()` for Native Adaptation

Use the CSS `light-dark()` function for truly adaptive colors:

```css
:root {
  color-scheme: light dark;

  /* Single declaration, adapts automatically */
  --syntax-bg: light-dark(#ffffff, #1e1e1e);
  --syntax-text: light-dark(#24292e, #c9d1d9);
  --syntax-control: light-dark(#d73a49, #ff7b72);
  --syntax-string: light-dark(#032f62, #a5d6ff);
}
```

#### Container Queries for Responsive Code Blocks

Code blocks adapt to their container, not just viewport:

```css
.rosettes {
  container-type: inline-size;
  container-name: code-block;
}

/* Responsive font size based on container width */
@container code-block (max-width: 400px) {
  .rosettes code {
    font-size: var(--text-xs);
  }
}

@container code-block (min-width: 800px) {
  .rosettes code {
    font-size: var(--text-sm);
  }
}

/* Hide line numbers on narrow containers */
@container code-block (max-width: 300px) {
  .rosettes .line-numbers {
    display: none;
  }
}
```

#### CSS Nesting (With Fallback)

Modern browsers support native CSS nesting. We provide both nested and flat CSS:

**Modern (nested) — 88%+ browser support:**

```css
.rosettes {
  background: var(--syntax-bg);
  color: var(--syntax-text);

  & code {
    font-family: var(--font-mono);
  }

  & .syntax-keyword {
    color: var(--syntax-control);
    font-weight: 600;

    &.declaration {
      color: var(--syntax-declaration);
    }
  }

  & .line-highlight {
    background: var(--syntax-bg-highlight);
  }
}
```

**Fallback (flat) — 100% browser support:**

```css
/* Equivalent flat CSS for older browsers */
.rosettes {
  background: var(--syntax-bg);
  color: var(--syntax-text);
}

.rosettes code {
  font-family: var(--font-mono);
}

.rosettes .syntax-keyword {
  color: var(--syntax-control);
  font-weight: 600;
}

.rosettes .syntax-keyword.declaration {
  color: var(--syntax-declaration);
}

.rosettes .line-highlight {
  background: var(--syntax-bg-highlight);
}
```

**Implementation**: The `generate_css()` function accepts a `use_nesting: bool = True` parameter. When `False`, outputs flat CSS.

#### View Transitions for Theme Switching

Smooth transitions when switching themes (progressive enhancement):

```css
/* Enable view transitions for theme changes */
@supports (view-transition-name: syntax-theme) {
  ::view-transition-old(syntax-theme),
  ::view-transition-new(syntax-theme) {
    animation-duration: 200ms;
    animation-timing-function: ease-out;
  }

  .rosettes {
    view-transition-name: syntax-theme;
  }
}
```

```javascript
// Theme switch with view transition
async function switchTheme(newPalette) {
  if (!document.startViewTransition) {
    applyPalette(newPalette);
    return;
  }

  await document.startViewTransition(() => {
    applyPalette(newPalette);
  }).finished;
}
```

#### OKLCH Color Space

Use perceptually uniform OKLCH for better color relationships:

```css
:root {
  /* Define base colors in OKLCH */
  --syntax-hue-control: 0;      /* Red */
  --syntax-hue-string: 140;     /* Green */
  --syntax-hue-type: 280;       /* Purple */

  /* Generate consistent lightness across hues */
  --syntax-control: oklch(65% 0.25 var(--syntax-hue-control));
  --syntax-string: oklch(65% 0.2 var(--syntax-hue-string));
  --syntax-type: oklch(65% 0.2 var(--syntax-hue-type));

  /* Automatic variants */
  --syntax-control-dim: oklch(from var(--syntax-control) calc(l * 0.8) c h);
}
```

---

### 7. Terminal (ANSI) Palette Support

Rosettes supports terminal output via ANSI color codes, mapped from semantic roles:

```python
@dataclass(frozen=True, slots=True)
class TerminalPalette:
    """ANSI color palette for terminal output."""

    name: str

    # Map semantic roles to ANSI codes
    # Standard ANSI: 30-37 (fg), 40-47 (bg), 90-97 (bright fg)
    # 256-color: 38;5;N or 48;5;N
    # True color: 38;2;R;G;B or 48;2;R;G;B

    control_flow: str = "1;35"      # Bold magenta
    declaration: str = "1;34"       # Bold blue
    import_: str = "35"             # Magenta

    string: str = "32"              # Green
    number: str = "33"              # Yellow
    boolean: str = "33"             # Yellow

    type_: str = "36"               # Cyan
    function: str = "34"            # Blue
    variable: str = "0"             # Default
    constant: str = "1;33"          # Bold yellow

    comment: str = "2;37"           # Dim white (gray)
    docstring: str = "2;32"         # Dim green

    error: str = "1;31"             # Bold red
    warning: str = "33"             # Yellow
    added: str = "32"               # Green
    removed: str = "31"             # Red

    text: str = "0"                 # Default
    muted: str = "2;37"             # Dim white

    @classmethod
    def from_syntax_palette(
        cls,
        palette: SyntaxPalette,
        color_mode: Literal["16", "256", "truecolor"] = "256"
    ) -> "TerminalPalette":
        """Convert a SyntaxPalette to ANSI codes."""
        if color_mode == "truecolor":
            return cls._from_truecolor(palette)
        elif color_mode == "256":
            return cls._from_256(palette)
        else:
            return cls._from_16()  # Use defaults

    @staticmethod
    def _hex_to_ansi_truecolor(hex_color: str) -> str:
        """Convert #RRGGBB to 38;2;R;G;B"""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return f"38;2;{r};{g};{b}"


# Built-in terminal palettes
TERMINAL_MONOKAI = TerminalPalette(
    name="monokai-terminal",
    control_flow="38;5;197",    # Pink
    declaration="38;5;81",      # Cyan
    string="38;5;186",          # Yellow
    number="38;5;141",          # Purple
    type_="38;5;148",           # Green
    function="38;5;148",        # Green
    comment="38;5;102",         # Gray
)
```

**Usage in Terminal Formatter:**

```python
# rosettes/formatters/terminal.py

class TerminalFormatter:
    def __init__(
        self,
        palette: TerminalPalette = TERMINAL_MONOKAI,
        color_mode: Literal["16", "256", "truecolor"] = "256",
    ):
        self.palette = palette
        self.color_mode = color_mode

    def format(self, tokens: Iterator[Token]) -> Iterator[str]:
        for token in tokens:
            role = ROLE_MAPPING.get(token.type, SyntaxRole.TEXT)
            ansi_code = getattr(self.palette, role.value, "0")

            if ansi_code and ansi_code != "0":
                yield f"\033[{ansi_code}m{token.value}\033[0m"
            else:
                yield token.value
```

---

### 8. WCAG Contrast Validation

Built-in accessibility checking:

```python
def _relative_luminance(hex_color: str) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)

    def adjust(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """Calculate WCAG contrast ratio between foreground and background."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def validate_palette(palette: SyntaxPalette) -> list[str]:
    """Validate palette meets WCAG AA contrast requirements."""
    warnings = []
    min_ratio = 4.5  # WCAG AA for normal text

    roles_to_check = [
        ('control_flow', palette.control_flow),
        ('declaration', palette.declaration),
        ('string', palette.string),
        ('number', palette.number),
        ('comment', palette.comment),
        ('text', palette.text),
    ]

    for role_name, color in roles_to_check:
        ratio = contrast_ratio(color, palette.background)
        if ratio < min_ratio:
            warnings.append(
                f"{role_name}: {color} has contrast {ratio:.1f}:1 "
                f"(needs {min_ratio}:1 for WCAG AA)"
            )

    return warnings
```

---

## Architecture

### Package Structure Extension

```
rosettes/
├── rosettes/
│   ├── themes/
│   │   ├── __init__.py           # Public theme API
│   │   ├── _roles.py             # SyntaxRole enum
│   │   ├── _palette.py           # SyntaxPalette, AdaptivePalette
│   │   ├── _terminal.py          # TerminalPalette for ANSI output
│   │   ├── _mapping.py           # TokenType → SyntaxRole mapping
│   │   ├── _validation.py        # WCAG contrast validation
│   │   ├── _css.py               # CSS generation (semantic + pygments)
│   │   └── palettes/
│   │       ├── __init__.py
│   │       ├── monokai.py        # Classic dark theme
│   │       ├── dracula.py        # Popular dark theme
│   │       ├── github.py         # GitHub light/dark (adaptive)
│   │       ├── one_dark.py       # Atom One Dark
│   │       ├── catppuccin.py     # Catppuccin (adaptive)
│   │       ├── bengal.py         # Bengal-native palettes
│   │       └── nord.py           # Nord theme (adaptive)
```

### Public API

```python
# rosettes/themes/__init__.py

from ._roles import SyntaxRole
from ._palette import SyntaxPalette, AdaptivePalette
from ._terminal import TerminalPalette
from ._mapping import ROLE_MAPPING, PYGMENTS_CLASS_MAP, get_role
from ._validation import validate_palette, contrast_ratio
from ._css import generate_css, generate_css_vars, CssClassStyle

# Built-in palettes
from .palettes import (
    # Dark themes
    MONOKAI,
    DRACULA,
    ONE_DARK,

    # Adaptive themes (light/dark)
    GITHUB,
    CATPPUCCIN,
    NORD,

    # Bengal-native themes
    BENGAL_TIGER,
    BENGAL_SNOW_LYNX,
    BENGAL_CHARCOAL,

    # Terminal palettes
    TERMINAL_MONOKAI,
    TERMINAL_DRACULA,
)

# Type alias
Palette = SyntaxPalette | AdaptivePalette

# Registry (auto-populated with built-ins)
_PALETTES: dict[str, Palette] = {}

def register_palette(palette: Palette) -> None:
    """Register a custom palette."""
    _PALETTES[palette.name] = palette

def get_palette(name: str) -> Palette:
    """Get a registered palette by name."""
    if name not in _PALETTES:
        raise KeyError(f"Unknown palette: {name!r}. Available: {list_palettes()}")
    return _PALETTES[name]

def list_palettes() -> list[str]:
    """List all registered palette names."""
    return sorted(_PALETTES.keys())
```

### Integration with HtmlFormatter

```python
# rosettes/formatters/html.py

from rosettes.themes import (
    get_palette, generate_css, get_role,
    ROLE_MAPPING, PYGMENTS_CLASS_MAP, CssClassStyle
)

class HtmlFormatter:
    def __init__(
        self,
        config: FormatConfig = FormatConfig(),
        palette: str | SyntaxPalette | None = None,
        css_class_style: CssClassStyle = "semantic",  # or "pygments"
    ):
        self.config = config
        self._palette = (
            get_palette(palette) if isinstance(palette, str)
            else palette
        )
        self._css_class_style = css_class_style

    def get_stylesheet(self) -> str:
        """Generate CSS stylesheet for the current palette."""
        if self._palette is None:
            return generate_css(css_class_style=self._css_class_style)
        return generate_css(self._palette, css_class_style=self._css_class_style)

    def format(self, tokens: Iterator[Token]) -> Iterator[str]:
        """Format tokens as HTML with configurable class names."""
        container_class = "rosettes" if self._css_class_style == "semantic" else "highlight"
        yield f'<pre class="{container_class}"><code>'

        for token in tokens:
            role = ROLE_MAPPING.get(token.type, SyntaxRole.TEXT)

            if self._css_class_style == "semantic":
                css_class = f"syntax-{role.value}"  # e.g., "syntax-function"
            else:
                css_class = PYGMENTS_CLASS_MAP.get(role, "")  # e.g., "nf"

            escaped = html_escape(token.value)
            if css_class:
                yield f'<span class="{css_class}">{escaped}</span>'
            else:
                yield escaped

        yield '</code></pre>'
```

---

## Built-in Palettes

### Monokai (Classic Dark)

```python
MONOKAI = SyntaxPalette(
    name="monokai",
    background="#272822",
    background_highlight="#49483e",
    control_flow="#f92672",      # Pink
    declaration="#66d9ef",       # Cyan
    import_="#f92672",           # Pink
    string="#e6db74",            # Yellow
    number="#ae81ff",            # Purple
    boolean="#ae81ff",           # Purple
    type_="#a6e22e",             # Green
    function="#a6e22e",          # Green
    variable="#f8f8f2",          # White
    constant="#ae81ff",          # Purple
    comment="#75715e",           # Gray
    docstring="#75715e",         # Gray
    error="#f92672",             # Pink
    warning="#e6db74",           # Yellow
    added="#a6e22e",             # Green
    removed="#f92672",           # Pink
    text="#f8f8f2",              # White
    muted="#75715e",             # Gray
)
```

### Bengal Tiger (Brand Theme)

```python
BENGAL_TIGER = SyntaxPalette(
    name="bengal-tiger",
    background="#1a1a1a",
    background_highlight="#2d2d2d",
    control_flow="#FF9D00",      # Bengal orange (primary)
    declaration="#3498DB",       # Blue (secondary)
    import_="#FF9D00",           # Bengal orange
    string="#2ECC71",            # Emerald green
    number="#E67E22",            # Carrot orange
    boolean="#E67E22",           # Carrot orange
    type_="#9b59b6",             # Purple
    function="#3498DB",          # Blue
    variable="#e0e0e0",          # Light gray
    constant="#F1C40F",          # Yellow (accent)
    comment="#757575",           # Muted gray
    docstring="#9e9e9e",         # Secondary gray
    error="#E74C3C",             # Alizarin red
    warning="#F1C40F",           # Yellow
    added="#2ECC71",             # Green
    removed="#E74C3C",           # Red
    text="#e0e0e0",              # Light gray
    muted="#757575",             # Muted
    bold_control=True,
    italic_comment=True,
)
```

### GitHub (Adaptive)

```python
GITHUB = AdaptivePalette(
    name="github",
    light=SyntaxPalette(
        name="github-light",
        background="#ffffff",
        background_highlight="#fffbdd",
        control_flow="#d73a49",      # Red
        declaration="#6f42c1",       # Purple
        import_="#d73a49",           # Red
        string="#032f62",            # Dark blue
        number="#005cc5",            # Blue
        boolean="#005cc5",           # Blue
        type_="#6f42c1",             # Purple
        function="#6f42c1",          # Purple
        variable="#24292e",          # Dark
        constant="#005cc5",          # Blue
        comment="#6a737d",           # Gray
        docstring="#6a737d",         # Gray
        error="#cb2431",             # Error red
        warning="#b08800",           # Warning yellow
        added="#22863a",             # Green
        removed="#cb2431",           # Red
        text="#24292e",              # Dark
        muted="#6a737d",             # Gray
    ),
    dark=SyntaxPalette(
        name="github-dark",
        background="#0d1117",
        background_highlight="#161b22",
        control_flow="#ff7b72",      # Coral
        declaration="#d2a8ff",       # Light purple
        import_="#ff7b72",           # Coral
        string="#a5d6ff",            # Light blue
        number="#79c0ff",            # Blue
        boolean="#79c0ff",           # Blue
        type_="#d2a8ff",             # Light purple
        function="#d2a8ff",          # Light purple
        variable="#c9d1d9",          # Light gray
        constant="#79c0ff",          # Blue
        comment="#8b949e",           # Gray
        docstring="#8b949e",         # Gray
        error="#f85149",             # Error red
        warning="#d29922",           # Warning yellow
        added="#3fb950",             # Green
        removed="#f85149",           # Red
        text="#c9d1d9",              # Light gray
        muted="#8b949e",             # Gray
    ),
)
```

---

## Bengal Design System Integration

Rosettes is designed for deep integration with Bengal's design token system.

### Python: Inherit from Bengal Tokens

```python
# rosettes/themes/palettes/bengal.py

from bengal.themes.tokens import BENGAL_PALETTE, get_palette

def create_bengal_palette(variant: str = "default") -> SyntaxPalette:
    """Create a syntax palette from Bengal's design tokens."""
    tokens = get_palette(variant)

    return SyntaxPalette(
        name=f"bengal-{variant}",
        background=tokens.background,
        background_highlight=tokens.surface_light,
        control_flow=tokens.primary,        # Bengal orange
        declaration=tokens.secondary,       # Blue
        import_=tokens.primary,
        string=tokens.success,              # Green
        number=tokens.warning,              # Orange
        boolean=tokens.warning,
        type_=tokens.accent if hasattr(tokens, 'accent') else "#9b59b6",
        function=tokens.secondary,
        variable=tokens.foreground,
        constant=tokens.accent if hasattr(tokens, 'accent') else tokens.warning,
        comment=tokens.text_muted,
        docstring=tokens.text_secondary,
        error=tokens.error,
        warning=tokens.warning,
        added=tokens.success,
        removed=tokens.error,
        text=tokens.foreground,
        muted=tokens.text_muted,
    )

# Pre-built Bengal variants
BENGAL_TIGER = create_bengal_palette("default")
BENGAL_BLUE = create_bengal_palette("blue-bengal")
BENGAL_CHARCOAL = create_bengal_palette("charcoal-bengal")
BENGAL_SNOW_LYNX = create_bengal_palette("snow-lynx")
```

### CSS: Zero-Config Integration

When used in Bengal, Rosettes can inherit design tokens directly:

```css
/* rosettes/themes/bengal-integration.css */

/* Use Bengal's layer system */
@layer rosettes {
  .rosettes {
    /* Inherit from Bengal's semantic tokens */
    --syntax-bg: var(--color-bg-code);
    --syntax-bg-highlight: color-mix(in oklch, var(--color-bg-code) 90%, var(--color-primary));

    /* Map semantic roles to Bengal tokens */
    --syntax-control: var(--color-primary);
    --syntax-declaration: var(--color-secondary);
    --syntax-string: var(--color-success);
    --syntax-number: var(--color-warning);
    --syntax-type: var(--color-accent);
    --syntax-function: var(--color-secondary);
    --syntax-comment: var(--color-text-muted);
    --syntax-error: var(--color-error);
    --syntax-added: var(--color-success);
    --syntax-removed: var(--color-error);
    --syntax-text: var(--color-text-primary);
    --syntax-muted: var(--color-text-tertiary);

    /* Inherit Bengal's font stack */
    font-family: var(--font-mono);
    font-size: var(--text-code);
    line-height: var(--line-height-relaxed);

    /* Inherit Bengal's border radius */
    border-radius: var(--radius-2xl);
  }
}
```

### HTML Output: Modern Semantic Structure

```html
<!-- Rosettes output (semantic mode) -->
<pre class="rosettes" data-language="python">
  <code>
    <span class="line" data-line="1">
      <span class="syntax-declaration">def</span>
      <span class="syntax-function">hello</span>
      <span class="syntax-punctuation">(</span>
      <span class="syntax-variable">name</span>
      <span class="syntax-punctuation">:</span>
      <span class="syntax-type">str</span>
      <span class="syntax-punctuation">)</span>
      <span class="syntax-punctuation">:</span>
    </span>
    <span class="line" data-line="2">
      <span class="syntax-docstring">"""Greet someone."""</span>
    </span>
    <span class="line line-highlight" data-line="3">
      <span class="syntax-keyword">return</span>
      <span class="syntax-string">f"Hello, {name}!"</span>
    </span>
  </code>
</pre>

<!-- Rosettes output (pygments mode) -->
<pre class="highlight">
  <code>
    <span class="kd">def</span>
    <span class="nf">hello</span>
    <span class="p">(</span>
    <span class="nv">name</span>
    <span class="p">:</span>
    <span class="nc">str</span>
    <span class="p">)</span>
    <span class="p">:</span>
    ...
  </code>
</pre>
```

**Features:**
- Semantic line wrapping with `data-line` attributes
- Native CSS line highlighting via `.line-highlight`
- `data-language` for styling hooks
- Clean, inspectable DOM structure
- Pygments-compatible mode for existing themes

### Bengal Configuration

Bengal needs to know which syntax theme to use. This is configured in `theme.yaml`:

#### Why Bengal Uses Semantic Output by Default

Bengal defaults to `css_class_style: "semantic"` for modern, self-documenting output:

| Pygments (legacy) | Semantic (Bengal default) |
|-------------------|---------------------------|
| `<span class="k">def</span>` | `<span class="syntax-declaration">def</span>` |
| `<span class="nf">hello</span>` | `<span class="syntax-function">hello</span>` |
| `<span class="s">"world"</span>` | `<span class="syntax-string">"world"</span>` |

**Benefits for Bengal:**
- CSS is self-documenting (no guessing what `.nf` means)
- CSS variables enable runtime theme switching
- Integrates with Bengal's design token system
- Container class `.rosettes` avoids conflicts with other `.highlight` uses

**Pygments mode** is available for users migrating from existing Pygments themes.

#### Config Schema

```yaml
# site/config/_default/theme.yaml

theme:
  name: "default"
  default_palette: "snow-lynx"    # Site-wide color palette

  # Syntax highlighting configuration (NEW)
  syntax_highlighting:
    theme: "auto"                 # Which syntax palette to use
    css_class_style: "semantic"   # "semantic" (default) or "pygments"

# Available syntax themes:
#   "auto"           - Inherit from default_palette (recommended)
#   "bengal-tiger"   - Bengal brand (orange accent, dark)
#   "bengal-snow-lynx" - Bengal brand (teal accent, light)
#   "monokai"        - Classic dark theme
#   "github"         - GitHub adaptive (light/dark)
#   "dracula"        - Popular dark theme
#   "one-dark"       - Atom One Dark
#   "catppuccin"     - Warm adaptive theme
#   "nord"           - Arctic color system
```

#### Theme Inheritance Logic

When `theme: "auto"` (the default), syntax highlighting inherits from the site palette:

```python
# bengal/rendering/highlighting/_theme_resolver.py

from rosettes.themes import get_palette, create_bengal_palette

# Mapping from site palette to syntax palette
PALETTE_INHERITANCE = {
    "default": "bengal-tiger",
    "snow-lynx": "bengal-snow-lynx",
    "brown-bengal": "bengal-tiger",
    "silver-bengal": "bengal-charcoal",
    "charcoal-bengal": "bengal-charcoal",
    "blue-bengal": "bengal-blue",
}

def resolve_syntax_theme(config: dict) -> SyntaxPalette:
    """Resolve which syntax palette to use based on config."""
    theme_config = config.get("theme", {})
    syntax_config = theme_config.get("syntax_highlighting", {})

    theme_name = syntax_config.get("theme", "auto")

    if theme_name == "auto":
        # Inherit from site palette
        site_palette = theme_config.get("default_palette", "default")
        theme_name = PALETTE_INHERITANCE.get(site_palette, "bengal-tiger")

    return get_palette(theme_name)
```

#### Defaults

```python
# bengal/config/defaults.py (additions)

DEFAULTS = {
    # ... existing defaults ...

    "theme": {
        # ... existing theme defaults ...

        "syntax_highlighting": {
            "theme": "auto",              # Inherit from default_palette
            "css_class_style": "semantic", # "semantic" or "pygments"
        },
    },
}
```

#### Integration with RosettesBackend

```python
# bengal/rendering/highlighting/rosettes.py

from rosettes.themes import get_palette, generate_css

class RosettesBackend(HighlightBackend):
    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._palette = resolve_syntax_theme(self._config)
        self._css_class_style = (
            self._config
            .get("theme", {})
            .get("syntax_highlighting", {})
            .get("css_class_style", "semantic")
        )

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        formatter = HtmlFormatter(
            palette=self._palette,
            css_class_style=self._css_class_style,
        )
        # ... formatting logic

    def get_stylesheet(self) -> str:
        """Generate CSS for the configured theme."""
        return generate_css(
            self._palette,
            css_class_style=self._css_class_style
        )
```

#### code.css Migration

Bengal's `code.css` will be updated to use semantic classes with CSS variables:

**Before** (Pygments classes, hardcoded colors):
```css
.highlight .k { color: #e74c3c; }
.highlight .nf { color: #3498db; }
.highlight .s { color: #2ecc71; }

[data-theme="dark"] .highlight .k { color: #ff6b6b; }
```

**After** (Semantic classes, CSS variables):
```css
/* Rosettes semantic classes - self-documenting */
.rosettes {
  /* Inherit from palette or Bengal tokens */
  --syntax-control: var(--color-primary, #e74c3c);
  --syntax-function: var(--color-secondary, #3498db);
  --syntax-string: var(--color-success, #2ecc71);
  --syntax-comment: var(--color-text-muted, #6c757d);
  /* ... all 18 semantic tokens ... */
}

.rosettes .syntax-control { color: var(--syntax-control); font-weight: 600; }
.rosettes .syntax-function { color: var(--syntax-function); }
.rosettes .syntax-string { color: var(--syntax-string); }
.rosettes .syntax-comment { color: var(--syntax-comment); font-style: italic; }

/* Dark mode: just update the variables */
[data-theme="dark"] .rosettes {
  --syntax-control: #ff7b72;
  --syntax-function: #d2a8ff;
  --syntax-string: #a5d6ff;
}

/* Legacy Pygments support (migration period) */
.highlight .k { color: var(--syntax-control, #e74c3c); }
.highlight .nf { color: var(--syntax-function, #3498db); }
```

**Benefits**:
- Theme switching = update CSS variables (no class changes)
- Dark mode = one block of variable overrides
- Self-documenting (`.syntax-function` vs `.nf`)
- Integrates with Bengal's `--color-*` design tokens

#### Zero-Config Experience

With these defaults, Bengal "just works":

| Site Palette | Syntax Theme | Result |
|--------------|--------------|--------|
| `snow-lynx` | `bengal-snow-lynx` | Light theme with teal accents |
| `charcoal-bengal` | `bengal-charcoal` | Dark minimal theme |
| `blue-bengal` | `bengal-blue` | Dark theme with blue accents |
| (not set) | `bengal-tiger` | Default dark theme with orange |

Users who want a specific syntax theme (e.g., Monokai regardless of site palette) can override:

```yaml
theme:
  default_palette: "snow-lynx"  # Light site
  syntax_highlighting:
    theme: "monokai"            # But dark code blocks
```

---

## Implementation Plan

### Phase 1: Core Types (Days 1-3)

- [ ] Define `SyntaxRole` enum with all 18 semantic roles
- [ ] Define `SyntaxPalette` frozen dataclass
- [ ] Define `AdaptivePalette` frozen dataclass
- [ ] Define `TerminalPalette` frozen dataclass
- [ ] Implement `ROLE_MAPPING` from TokenType → SyntaxRole
- [ ] Implement `PYGMENTS_CLASS_MAP` for backward compatibility
- [ ] Write unit tests for types

### Phase 2: CSS Generation (Days 4-6)

- [ ] Implement `generate_css_vars()` for custom properties
- [ ] Implement `generate_css()` with:
  - Dual class style support (`semantic` / `pygments`)
  - `@layer rosettes` for cascade control
  - `color-mix()` for dynamic variants
  - `light-dark()` for adaptive colors (with fallback)
  - Native CSS nesting (with flat fallback option)
  - Container queries for responsive code blocks
- [ ] Update `HtmlFormatter` to support `css_class_style` parameter
- [ ] Write CSS generation tests
- [ ] Generate Bengal integration CSS

### Phase 3: Validation (Days 7-8)

- [ ] Implement WCAG contrast ratio calculation
- [ ] Implement `validate_palette()` with warnings
- [ ] Add validation to `SyntaxPalette.__post_init__`
- [ ] Write accessibility tests

### Phase 4: Built-in Palettes (Days 9-12)

- [ ] Create Monokai (+ terminal variant)
- [ ] Create Dracula (+ terminal variant)
- [ ] Create GitHub (adaptive)
- [ ] Create One Dark
- [ ] Create Catppuccin (adaptive)
- [ ] Create Nord (adaptive)
- [ ] Create Bengal Tiger
- [ ] Create Bengal Snow Lynx
- [ ] Validate all palettes pass WCAG AA
- [ ] Visual regression tests

### Phase 5: Terminal Support (Days 13-14)

- [ ] Implement `TerminalPalette` with ANSI codes
- [ ] Implement `TerminalFormatter`
- [ ] Support 16, 256, and truecolor modes
- [ ] Add `from_syntax_palette()` converter
- [ ] Test terminal output

### Phase 6: Integration (Days 15-16)

- [ ] Integrate with `HtmlFormatter` (dual class output)
- [ ] Add `palette` and `css_class_style` params to `highlight()`
- [ ] Implement palette registry
- [ ] Write integration tests
- [ ] Update RFC-0002 to reference theming

### Phase 7: Bengal Integration (Days 17-22)

- [ ] Create `create_bengal_palette()` function
- [ ] Generate Bengal variant palettes from design tokens
- [ ] Implement `resolve_syntax_theme()` for config-based theme selection
- [ ] Add `syntax_highlighting` to Bengal config schema
- [ ] Update `bengal/config/defaults.py` with syntax highlighting defaults
- [ ] Update `RosettesBackend` to use config-based palette selection
- [ ] Add `PALETTE_INHERITANCE` mapping (site palette → syntax palette)
- [ ] **Migrate `code.css` to semantic classes**:
  - Replace `.highlight` with `.rosettes` container
  - Replace `.k`, `.nf`, `.s` with `.syntax-control`, `.syntax-function`, `.syntax-string`
  - Use CSS variables (`--syntax-*`) for all colors
  - Keep Pygments selectors with fallback for migration period
- [ ] Document CSS variable mapping for Bengal themes
- [ ] Test with Bengal site build
- [ ] Verify "auto" theme inheritance works correctly
- [ ] Visual regression test all 8 syntax palettes

---

## API Examples

### Basic Usage

```python
from rosettes import highlight
from rosettes.themes import MONOKAI, BENGAL_TIGER

# Use built-in palette (semantic classes by default)
html = highlight("def foo(): pass", "python", palette=MONOKAI)

# Use Pygments-compatible classes for existing themes
html = highlight(
    "def foo(): pass",
    "python",
    palette=MONOKAI,
    css_class_style="pygments"
)

# Get stylesheet for embedding
from rosettes.themes import generate_css
css = generate_css(MONOKAI)  # Semantic classes
css = generate_css(MONOKAI, css_class_style="pygments")  # Pygments classes

# Output (semantic):
# <pre class="rosettes"><code>
#   <span class="syntax-declaration">def</span>
#   <span class="syntax-function">foo</span>
#   <span class="syntax-punctuation">()</span>:
#   <span class="syntax-keyword">pass</span>
# </code></pre>
```

### Create Custom Palette

```python
from rosettes.themes import SyntaxPalette, validate_palette

MY_THEME = SyntaxPalette(
    name="my-theme",
    background="#1e1e1e",
    background_highlight="#2d2d2d",
    control_flow="#c586c0",
    declaration="#569cd6",
    import_="#c586c0",
    string="#ce9178",
    number="#b5cea8",
    boolean="#569cd6",
    type_="#4ec9b0",
    function="#dcdcaa",
    variable="#9cdcfe",
    constant="#4fc1ff",
    comment="#6a9955",
    docstring="#6a9955",
    error="#f44747",
    warning="#cca700",
    added="#4ec9b0",
    removed="#f44747",
    text="#d4d4d4",
    muted="#808080",
)

# Validate accessibility (WCAG AA)
warnings = validate_palette(MY_THEME)
if warnings:
    for w in warnings:
        print(f"⚠️  {w}")
# Output: ⚠️  comment: #6a9955 has contrast 4.2:1 (needs 4.5:1 for WCAG AA)
```

### Terminal Output

```python
from rosettes import highlight
from rosettes.themes import TERMINAL_MONOKAI
from rosettes.formatters import TerminalFormatter

# Highlight for terminal
formatter = TerminalFormatter(palette=TERMINAL_MONOKAI, color_mode="256")
print(highlight("def foo(): pass", "python", formatter=formatter))

# Auto-convert web palette to terminal
from rosettes.themes import TerminalPalette, MONOKAI
terminal_palette = TerminalPalette.from_syntax_palette(MONOKAI, color_mode="truecolor")
```

### Adaptive Theme

```python
from rosettes.themes import AdaptivePalette, SyntaxPalette

MY_ADAPTIVE = AdaptivePalette(
    name="my-adaptive",
    light=SyntaxPalette(name="my-light", background="#ffffff", ...),
    dark=SyntaxPalette(name="my-dark", background="#1e1e1e", ...),
)

# Generates CSS with @media (prefers-color-scheme) and [data-theme] selectors
css = MY_ADAPTIVE.to_css()

# Respects user preference automatically
# Also works with: <html data-theme="dark">
```

### Integration with Bengal Design Tokens

```python
from rosettes.themes import create_bengal_palette

# Create palette from Bengal's design token system
tiger = create_bengal_palette("default")      # Orange accent
snow = create_bengal_palette("snow-lynx")     # Teal accent  
charcoal = create_bengal_palette("charcoal-bengal")  # Minimal

# These palettes inherit Bengal's WCAG-compliant colors
```

---

## Success Criteria

### Must Have (MVP)

| Criterion | Validation |
|-----------|------------|
| SyntaxRole enum with 18 semantic roles | Type tests |
| SyntaxPalette frozen dataclass | Immutability tests |
| 8+ built-in palettes | Unit tests per palette |
| CSS custom property output | CSS generation tests |
| **Dual class output** | `css_class_style` param works |
| Modern CSS architecture | `@layer`, `color-mix()`, fallbacks work |
| WCAG AA contrast validation | All built-in palettes pass |
| Bengal design token integration | `--syntax-*` maps to `--color-*` |
| **Bengal config integration** | `theme.syntax_highlighting` works |
| **Theme auto-inheritance** | `theme: "auto"` inherits from site palette |

### Should Have

| Criterion | Target |
|-----------|--------|
| Adaptive palette support | 3+ adaptive themes (GitHub, Catppuccin, Nord) |
| Bengal token integration | `create_bengal_palette()` works |
| Terminal palette support | `TerminalPalette` + formatter |
| Documentation | README with examples |
| Dark/light preference detection | `@media (prefers-color-scheme)` in CSS |

### Nice to Have (Post-MVP)

- [ ] Theme builder CLI
- [ ] VSCode/TextMate theme import
- [ ] Real-time theme preview
- [ ] Palette editor web UI
- [ ] Pygments theme import utility

---

## Browser Support Matrix

| Feature | Support | Fallback |
|---------|---------|----------|
| `@layer` | 95%+ | None needed (graceful degradation) |
| `color-mix()` | 93%+ | Pre-computed values in palette |
| `light-dark()` | 85%+ | `@media (prefers-color-scheme)` |
| `@container` | 91%+ | Viewport-based media queries |
| CSS Nesting | 88%+ | Flat CSS option (`use_nesting=False`) |
| `oklch()` | 93%+ | Hex fallback in palette |
| View Transitions | 75%+ | Instant switch (progressive) |

**Strategy**: Modern features with explicit fallbacks. All fallbacks are automatically generated by `generate_css()`.

---

## The Rosettes Advantage

### Defining a Theme

**Traditional approach (100+ lines)**:
```python
styles = {
    Token: "#f8f8f2",
    Whitespace: "",
    Error: "#ed007e",
    Comment: "#959077",
    Comment.Multiline: "",  # Empty for inheritance
    Comment.Preproc: "",    # Empty for inheritance  
    Comment.Single: "",     # Empty for inheritance
    # ... 100+ more entries, most empty
}
```

**Rosettes (25 lines, semantic)**:
```python
MONOKAI = SyntaxPalette(
    name="monokai",
    background="#272822",
    background_highlight="#49483e",
    control_flow="#f92672",    # if, for, return
    declaration="#66d9ef",      # def, class
    string="#e6db74",
    number="#ae81ff",
    type_="#a6e22e",
    function="#a6e22e",
    comment="#75715e",
    # ... each field is meaningful
)
```

### CSS Output

**Traditional**: Cryptic classes, hardcoded values
```css
.highlight .k { color: #f92672; }
.highlight .s { color: #e6db74; }
.highlight .nf { color: #a6e22e; }
```

**Rosettes**: Semantic classes, CSS custom properties
```css
:root {
  --syntax-control: #f92672;
  --syntax-string: #e6db74;
  --syntax-function: #a6e22e;
}
.rosettes .syntax-keyword { color: var(--syntax-control); }
.rosettes .syntax-string { color: var(--syntax-string); }
.rosettes .syntax-function { color: var(--syntax-function); }
```

### HTML Output

**Traditional**: Meaningless classes
```html
<span class="k">def</span> <span class="nf">hello</span>
```

**Rosettes**: Self-documenting classes
```html
<span class="syntax-declaration">def</span> <span class="syntax-function">hello</span>
```

---

## Alternatives Considered

### 1. Semantic Classes Only (No Pygments Compatibility)

**Rejected**: Would break RFC-0002's promise of Pygments theme compatibility. The dual output mode preserves backward compatibility while enabling modern styling.

### 2. Use TextMate/VSCode Scopes Directly

**Rejected**: Different model (nested scopes vs flat tokens), complex mapping, limited to editor themes. May add as import option post-MVP.

### 3. No Theme System (CSS Only)

**Rejected**: Loses ability to validate palettes, no Python-side introspection, harder to share themes.

### 4. Copy Pygments Theme Format

**Rejected**: 100+ line theme definitions with inheritance boilerplate. Semantic roles are more maintainable.

### 5. No Terminal Support

**Rejected**: Terminal output is valuable for CLI tools, debugging, and print statements. ANSI mapping is straightforward from semantic roles.

---

## Migration Guide

### From Pygments Themes

Existing Pygments themes can be used with Rosettes in two ways:

**Option 1: Use Pygments-compatible output**
```python
# Your existing Pygments CSS works as-is
html = highlight(code, "python", css_class_style="pygments")
```

**Option 2: Convert to SyntaxPalette**
```python
# Extract colors from Pygments style and map to roles
from rosettes.themes import SyntaxPalette

MY_CONVERTED = SyntaxPalette(
    name="my-converted",
    # Map Pygments Token.Keyword → control_flow
    control_flow=pygments_style.style_for_token(Token.Keyword)["color"],
    # Map Token.Name.Function → function
    function=pygments_style.style_for_token(Token.Name.Function)["color"],
    # ... etc
)
```

**Future**: A `convert_pygments_style()` utility will automate this (post-MVP).

---

## References

- [RFC-0002: Rosettes Syntax Highlighter](./rfc-rosettes-syntax-highlighter.md)
- [Bengal Design Tokens](../../bengal/themes/tokens.py)
- [Bengal CSS Architecture](../../bengal/themes/default/assets/css/README.md)
- [WCAG 2.1 Contrast Requirements](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)

### Modern CSS References

- [CSS Cascade Layers (`@layer`)](https://developer.mozilla.org/en-US/docs/Web/CSS/@layer)
- [`color-mix()` Function](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/color-mix)
- [`light-dark()` Function](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/light-dark)
- [CSS Container Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries)
- [CSS Nesting](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_nesting)
- [OKLCH Color Space](https://oklch.com/)
- [View Transitions API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transitions_API)

### Theme Inspiration

- [Catppuccin](https://catppuccin.com/) — Warm adaptive theming
- [Nord](https://www.nordtheme.com/) — Cohesive arctic color system
- [Dracula](https://draculatheme.com/) — Dark theme with strong contrast

---

## Quick Reference

### Key Types

| Type | Purpose |
|------|---------|
| `SyntaxRole` | Semantic meaning of code elements (18 roles) |
| `SyntaxPalette` | Immutable theme with ~20 color slots |
| `AdaptivePalette` | Light/dark adaptive theme |
| `TerminalPalette` | ANSI color codes for terminal |
| `ROLE_MAPPING` | TokenType → SyntaxRole static mapping |
| `PYGMENTS_CLASS_MAP` | SyntaxRole → Pygments class mapping |

### CSS Class Styles

| Style | Container | Classes | Use Case |
|-------|-----------|---------|----------|
| `"semantic"` | `.rosettes` | `.syntax-keyword`, `.syntax-function` | New projects |
| `"pygments"` | `.highlight` | `.k`, `.nf` | Existing themes |

### Built-in Palettes

| Palette | Type | Style |
|---------|------|-------|
| `MONOKAI` | Dark | Classic Monokai |
| `DRACULA` | Dark | Dracula theme |
| `ONE_DARK` | Dark | Atom One Dark |
| `GITHUB` | Adaptive | GitHub light/dark |
| `CATPPUCCIN` | Adaptive | Catppuccin (Latte/Mocha) |
| `NORD` | Adaptive | Nord light/dark |
| `BENGAL_TIGER` | Dark | Bengal brand (orange accent) |
| `BENGAL_SNOW_LYNX` | Light | Bengal brand (teal accent) |

### CSS Variables

```css
/* Background */
--syntax-bg, --syntax-bg-highlight

/* Control & Structure */
--syntax-control, --syntax-declaration, --syntax-import

/* Literals */
--syntax-string, --syntax-number, --syntax-boolean

/* Identifiers */
--syntax-type, --syntax-function, --syntax-variable, --syntax-constant

/* Documentation */
--syntax-comment, --syntax-docstring

/* Feedback */
--syntax-error, --syntax-warning, --syntax-added, --syntax-removed

/* Base */
--syntax-text, --syntax-muted
```

### CSS Class Names (Semantic)

```css
/* Semantic, self-documenting */
.syntax-control, .syntax-declaration, .syntax-import
.syntax-string, .syntax-number, .syntax-boolean
.syntax-type, .syntax-function, .syntax-variable, .syntax-constant
.syntax-comment, .syntax-docstring
.syntax-error, .syntax-added, .syntax-removed
.syntax-punctuation, .syntax-operator
```

### Modern CSS Features Used

| Feature | Purpose | Browser Support | Fallback |
|---------|---------|-----------------|----------|
| `@layer rosettes` | Cascade control | 95%+ | Graceful degradation |
| `color-mix()` | Dynamic variants | 93%+ | Pre-computed values |
| `light-dark()` | Native dark mode | 85%+ | `@media (prefers-color-scheme)` |
| `@container` | Responsive code blocks | 91%+ | Viewport media queries |
| CSS Nesting | Cleaner stylesheets | 88%+ | Flat CSS option |
| `oklch()` | Perceptual color space | 93%+ | Hex fallback |
| View Transitions | Theme switching | 75%+ | Instant switch |
