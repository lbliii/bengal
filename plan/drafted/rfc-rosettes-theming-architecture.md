# RFC: Rosettes Theming Architecture — Semantic Token System

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0003 |
| **Title** | Rosettes Theming: Semantic Token System for Syntax Highlighting |
| **Status** | Draft |
| **Created** | 2025-12-24 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Modern theming architecture for Rosettes with semantic color roles |
| **Why** | Pygments themes are verbose, non-adaptive, and lack semantic meaning |
| **Effort** | 1-2 weeks for core palette system + 5 built-in themes |
| **Risk** | Low — Pygments CSS compatibility maintained for fallback |
| **Dependencies** | Rosettes core (RFC-0002), optionally Bengal design tokens |

**Key Design Goals:**
1. ✅ Semantic roles (why a color, not just which color)
2. ✅ Immutable, thread-safe palettes (frozen dataclasses)
3. ✅ CSS custom properties for runtime theming
4. ✅ Dark/light adaptive themes from single definition
5. ✅ WCAG AA contrast validation
6. ✅ Pygments CSS class compatibility (drop-in migration)

---

## Motivation

### Problem: Pygments Theming Was Designed in 2006

Pygments themes have architectural patterns that don't align with modern CSS or accessibility requirements:

| Pygments Pattern | Problem | Modern Alternative |
|------------------|---------|-------------------|
| Token → Color direct mapping | No semantic layer, 100+ lines per theme | Role → Color with inheritance |
| Hardcoded hex values | No runtime customization | CSS custom properties |
| Separate dark/light themes | 2x maintenance, no adaptation | Adaptive palettes |
| Class-level mutable state | Not thread-safe | Frozen dataclasses |
| No contrast validation | Accessibility issues | WCAG AA enforcement |
| `StyleMeta` metaclass | Complex, hard to understand | Simple dataclasses |

**Example: Pygments Monokai Theme (113 lines)**

```python
# Most lines are empty strings for inheritance
styles = {
    Token:                     "#f8f8f2",
    Whitespace:                "",        # Empty
    Error:                     "#ed007e bg:#1e0010",
    Comment:                   "#959077",
    Comment.Multiline:         "",        # Empty
    Comment.Preproc:           "",        # Empty  
    Comment.Single:            "",        # Empty
    Comment.Special:           "",        # Empty
    # ... 80+ more lines, mostly empty
}
```

### Why Semantic Theming?

| Current State | Semantic Approach |
|---------------|-------------------|
| `KEYWORD → #e74c3c` | `KEYWORD → control_flow → var(--syntax-control)` |
| "Keywords are red" | "Control flow is emphasized with primary accent" |
| No design rationale | Intent is explicit |
| Hard to maintain consistency | Roles ensure visual coherence |

**The Insight**: Syntax highlighting colors aren't arbitrary—they communicate **meaning**:

- Control flow keywords (`if`, `for`, `return`) → **Draw attention** (usually bold/bright)
- Declarations (`def`, `class`) → **Structure** (distinct from control)
- Strings → **Data** (often green/warm)
- Comments → **De-emphasized** (muted/italic)

By capturing this semantic layer, themes become:
1. **Easier to create** (define 12 roles, not 100+ tokens)
2. **More consistent** (roles ensure visual hierarchy)
3. **Easier to adapt** (dark/light mode changes role colors, not token mappings)

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

    # Semantic syntax colors (the 12 core roles)
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

ROLE_MAPPING: dict[TokenType, SyntaxRole] = {
    # Keywords → Control/Declaration
    TokenType.KEYWORD: SyntaxRole.CONTROL_FLOW,
    TokenType.KEYWORD_CONSTANT: SyntaxRole.BOOLEAN,
    TokenType.KEYWORD_DECLARATION: SyntaxRole.DECLARATION,
    TokenType.KEYWORD_NAMESPACE: SyntaxRole.IMPORT,
    TokenType.KEYWORD_TYPE: SyntaxRole.TYPE,

    # Names → Identity
    TokenType.NAME_CLASS: SyntaxRole.TYPE,
    TokenType.NAME_FUNCTION: SyntaxRole.FUNCTION,
    TokenType.NAME_FUNCTION_MAGIC: SyntaxRole.FUNCTION,
    TokenType.NAME_BUILTIN: SyntaxRole.FUNCTION,
    TokenType.NAME_CONSTANT: SyntaxRole.CONSTANT,
    TokenType.NAME_VARIABLE: SyntaxRole.VARIABLE,
    TokenType.NAME_DECORATOR: SyntaxRole.DECLARATION,

    # Literals → Data
    TokenType.STRING: SyntaxRole.STRING,
    TokenType.STRING_DOC: SyntaxRole.DOCSTRING,
    TokenType.NUMBER: SyntaxRole.NUMBER,

    # Comments → Documentation
    TokenType.COMMENT: SyntaxRole.COMMENT,
    TokenType.COMMENT_SINGLE: SyntaxRole.COMMENT,
    TokenType.COMMENT_MULTILINE: SyntaxRole.COMMENT,

    # Generic → Feedback
    TokenType.GENERIC_DELETED: SyntaxRole.REMOVED,
    TokenType.GENERIC_INSERTED: SyntaxRole.ADDED,
    TokenType.ERROR: SyntaxRole.ERROR,

    # Default
    TokenType.TEXT: SyntaxRole.TEXT,
    TokenType.PUNCTUATION: SyntaxRole.TEXT,
    TokenType.OPERATOR: SyntaxRole.CONTROL_FLOW,
}
```

### 4. CSS Custom Property Output

Generate CSS that uses custom properties for runtime theming:

```css
/* Generated by rosettes - theme: monokai */
:root {
  /* Rosettes Syntax Palette */
  --syntax-bg: #272822;
  --syntax-bg-hl: #49483e;
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

/* Token classes map to semantic variables */
.highlight { background: var(--syntax-bg); color: var(--syntax-text); }
.highlight .hll { background: var(--syntax-bg-hl); }

/* Keywords */
.highlight .k { color: var(--syntax-control); font-weight: bold; }
.highlight .kd { color: var(--syntax-declaration); }
.highlight .kn { color: var(--syntax-import); }

/* Strings */
.highlight .s, .highlight .s1, .highlight .s2 { color: var(--syntax-string); }
.highlight .sd { color: var(--syntax-docstring); font-style: italic; }

/* Names */
.highlight .nf, .highlight .fm { color: var(--syntax-function); }
.highlight .nc { color: var(--syntax-type); }
.highlight .no { color: var(--syntax-constant); }

/* Comments */
.highlight .c, .highlight .c1, .highlight .cm { color: var(--syntax-comment); font-style: italic; }

/* Numbers */
.highlight .m, .highlight .mi, .highlight .mf { color: var(--syntax-number); }

/* Diff */
.highlight .gi { color: var(--syntax-added); }
.highlight .gd { color: var(--syntax-removed); }
```

**Benefits:**
- Runtime theme switching without regenerating HTML
- Integration with external design systems (just override `--syntax-*` vars)
- Smaller CSS footprint (variables vs inline values)

### 5. Dark/Light Adaptive Palettes

Single theme definition adapts to color scheme:

```python
@dataclass(frozen=True, slots=True)
class AdaptivePalette:
    """Theme that adapts to light/dark mode preference."""

    name: str
    light: SyntaxPalette
    dark: SyntaxPalette

    def to_css(self) -> str:
        return f"""
/* {self.name} - Adaptive Theme */
:root {{
{self.light.to_css_vars(indent=2)}
}}

@media (prefers-color-scheme: dark) {{
  :root {{
{self.dark.to_css_vars(indent=4)}
  }}
}}

[data-theme="dark"] {{
{self.dark.to_css_vars(indent=2)}
}}

[data-theme="light"] {{
{self.light.to_css_vars(indent=2)}
}}
"""
```

### 6. WCAG Contrast Validation

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
│   │   ├── _mapping.py           # TokenType → SyntaxRole mapping
│   │   ├── _validation.py        # WCAG contrast validation
│   │   ├── _css.py               # CSS generation
│   │   ├── _pygments_compat.py   # Pygments theme import
│   │   └── palettes/
│   │       ├── __init__.py
│   │       ├── monokai.py        # Classic dark theme
│   │       ├── dracula.py        # Popular dark theme
│   │       ├── github.py         # GitHub light/dark
│   │       ├── one_dark.py       # Atom One Dark
│   │       ├── vs_dark.py        # VS Code Dark+
│   │       ├── bengal.py         # Bengal-native palettes
│   │       └── solarized.py      # Solarized light/dark
```

### Public API

```python
# rosettes/themes/__init__.py

from ._roles import SyntaxRole
from ._palette import SyntaxPalette, AdaptivePalette
from ._mapping import ROLE_MAPPING, get_role
from ._validation import validate_palette, contrast_ratio
from ._css import generate_css, generate_css_vars

# Built-in palettes
from .palettes import (
    MONOKAI,
    DRACULA,
    GITHUB_LIGHT,
    GITHUB_DARK,
    GITHUB,  # Adaptive
    ONE_DARK,
    VS_DARK,
    BENGAL_TIGER,
    BENGAL_SNOW_LYNX,
    SOLARIZED_LIGHT,
    SOLARIZED_DARK,
    SOLARIZED,  # Adaptive
)

# Registry
_PALETTES: dict[str, SyntaxPalette | AdaptivePalette] = {}

def register_palette(palette: SyntaxPalette | AdaptivePalette) -> None:
    """Register a custom palette."""
    _PALETTES[palette.name] = palette

def get_palette(name: str) -> SyntaxPalette | AdaptivePalette:
    """Get a registered palette by name."""
    return _PALETTES[name]

def list_palettes() -> list[str]:
    """List all registered palette names."""
    return list(_PALETTES.keys())
```

### Integration with HtmlFormatter

```python
# rosettes/formatters/html.py

from rosettes.themes import get_palette, generate_css

class HtmlFormatter:
    def __init__(
        self,
        config: FormatConfig = FormatConfig(),
        palette: str | SyntaxPalette | None = None,
    ):
        self.config = config
        self._palette = (
            get_palette(palette) if isinstance(palette, str)
            else palette
        )

    def get_stylesheet(self) -> str:
        """Generate CSS stylesheet for the current palette."""
        if self._palette is None:
            return ""  # Use Pygments-compatible classes only
        return generate_css(self._palette)

    def format(self, tokens: Iterator[Token]) -> Iterator[str]:
        """Format tokens as HTML."""
        # Uses semantic classes that map to CSS variables
        ...
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

## Bengal Design Token Integration

Rosettes can optionally inherit colors from Bengal's design token system:

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

**CSS Integration**:

```css
/* Bengal site can override Rosettes tokens with design system tokens */
:root {
  /* Map Rosettes syntax tokens to Bengal semantic tokens */
  --syntax-control: var(--color-primary);
  --syntax-declaration: var(--color-secondary);
  --syntax-string: var(--color-success);
  --syntax-error: var(--color-error);
  --syntax-comment: var(--color-text-muted);
  /* ... */
}
```

---

## Pygments Compatibility

### Import Pygments Themes

Convert existing Pygments themes to Rosettes palettes:

```python
# rosettes/themes/_pygments_compat.py

from pygments.styles import get_style_by_name
from pygments.token import Token

def import_pygments_style(name: str) -> SyntaxPalette:
    """Import a Pygments style as a Rosettes palette."""
    style = get_style_by_name(name)

    # Extract key colors from style
    def get_color(token) -> str:
        info = style.style_for_token(token)
        return f"#{info['color']}" if info['color'] else "#808080"

    return SyntaxPalette(
        name=f"pygments-{name}",
        background=style.background_color or "#ffffff",
        background_highlight=style.highlight_color or "#ffffcc",
        control_flow=get_color(Token.Keyword),
        declaration=get_color(Token.Keyword.Declaration),
        import_=get_color(Token.Keyword.Namespace),
        string=get_color(Token.String),
        number=get_color(Token.Number),
        boolean=get_color(Token.Keyword.Constant),
        type_=get_color(Token.Name.Class),
        function=get_color(Token.Name.Function),
        variable=get_color(Token.Name),
        constant=get_color(Token.Name.Constant),
        comment=get_color(Token.Comment),
        docstring=get_color(Token.String.Doc),
        error=get_color(Token.Error),
        warning=get_color(Token.Generic.Error),
        added=get_color(Token.Generic.Inserted),
        removed=get_color(Token.Generic.Deleted),
        text=get_color(Token),
        muted=get_color(Token.Comment),
    )
```

### Export to Pygments CSS

Generate Pygments-compatible CSS from Rosettes palette:

```python
def to_pygments_css(palette: SyntaxPalette, selector: str = ".highlight") -> str:
    """Generate Pygments-compatible CSS from a Rosettes palette."""
    lines = [
        f"{selector} {{ background: {palette.background}; }}",
        f"{selector} .hll {{ background: {palette.background_highlight}; }}",
        "",
        "/* Keywords */",
        f"{selector} .k {{ color: {palette.control_flow}; font-weight: bold; }}",
        f"{selector} .kd {{ color: {palette.declaration}; }}",
        f"{selector} .kn {{ color: {palette.import_}; }}",
        f"{selector} .kc {{ color: {palette.boolean}; }}",
        # ... all token classes
    ]
    return "\n".join(lines)
```

---

## Implementation Plan

### Phase 1: Core Types (Days 1-2)

- [ ] Define `SyntaxRole` enum with all semantic roles
- [ ] Define `SyntaxPalette` frozen dataclass
- [ ] Define `AdaptivePalette` frozen dataclass
- [ ] Implement `ROLE_MAPPING` from TokenType → SyntaxRole
- [ ] Write unit tests for types

### Phase 2: CSS Generation (Days 3-4)

- [ ] Implement `generate_css_vars()` for custom properties
- [ ] Implement `generate_css()` for complete stylesheet
- [ ] Implement `to_pygments_css()` for compatibility
- [ ] Support both semantic (`.syntax-*`) and Pygments (`.k`, `.s`) class names
- [ ] Write CSS generation tests

### Phase 3: Validation (Day 5)

- [ ] Implement WCAG contrast ratio calculation
- [ ] Implement `validate_palette()` with warnings
- [ ] Add validation to `SyntaxPalette.__post_init__`
- [ ] Write accessibility tests

### Phase 4: Built-in Palettes (Days 6-8)

- [ ] Port Monokai
- [ ] Port Dracula
- [ ] Port GitHub (adaptive)
- [ ] Port One Dark
- [ ] Port VS Dark
- [ ] Create Bengal Tiger
- [ ] Create Bengal Snow Lynx
- [ ] Port Solarized (adaptive)
- [ ] Validate all palettes pass WCAG AA

### Phase 5: Integration (Days 9-10)

- [ ] Integrate with `HtmlFormatter`
- [ ] Add `palette` parameter to `highlight()` function
- [ ] Implement palette registry
- [ ] Write integration tests
- [ ] Implement Pygments theme import

### Phase 6: Bengal Integration (Days 11-12)

- [ ] Create `create_bengal_palette()` function
- [ ] Generate Bengal variant palettes
- [ ] Document CSS variable mapping for Bengal themes
- [ ] Test with Bengal site build

---

## API Examples

### Basic Usage

```python
from rosettes import highlight
from rosettes.themes import MONOKAI, BENGAL_TIGER

# Use built-in palette
html = highlight("def foo(): pass", "python", palette=MONOKAI)

# Get stylesheet for embedding
from rosettes.themes import generate_css
css = generate_css(MONOKAI)
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

# Validate accessibility
warnings = validate_palette(MY_THEME)
if warnings:
    for w in warnings:
        print(f"Warning: {w}")
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
```

### Import Pygments Theme

```python
from rosettes.themes import import_pygments_style

# Convert existing Pygments theme
native_theme = import_pygments_style("native")
nord_theme = import_pygments_style("nord")
```

---

## Success Criteria

### Must Have (MVP)

| Criterion | Validation |
|-----------|------------|
| SyntaxRole enum with 15+ semantic roles | Type tests |
| SyntaxPalette frozen dataclass | Immutability tests |
| 5+ built-in palettes | Unit tests per palette |
| CSS custom property output | CSS generation tests |
| Pygments CSS class compatibility | Visual regression tests |
| WCAG AA contrast validation | All built-in palettes pass |

### Should Have

| Criterion | Target |
|-----------|--------|
| Adaptive palette support | 2+ adaptive themes |
| Pygments theme import | `import_pygments_style()` works |
| Bengal token integration | `create_bengal_palette()` works |
| Documentation | README with examples |

### Nice to Have (Post-MVP)

- [ ] Theme builder CLI
- [ ] VSCode theme import
- [ ] Real-time theme preview
- [ ] Palette editor web UI

---

## Comparison: Before vs After

### Defining a Theme

**Pygments (113 lines)**:
```python
class MonokaiStyle(Style):
    background_color = "#272822"
    styles = {
        Token: "#f8f8f2",
        Whitespace: "",
        Error: "#ed007e bg:#1e0010",
        Comment: "#959077",
        Comment.Multiline: "",
        Comment.Preproc: "",
        Comment.Single: "",
        # ... 100+ more entries
    }
```

**Rosettes (25 lines)**:
```python
MONOKAI = SyntaxPalette(
    name="monokai",
    background="#272822",
    background_highlight="#49483e",
    control_flow="#f92672",
    declaration="#66d9ef",
    string="#e6db74",
    number="#ae81ff",
    type_="#a6e22e",
    function="#a6e22e",
    comment="#75715e",
    # ... 15 more semantic fields
)
```

### CSS Output

**Pygments**: Inline hex values, no runtime customization
```css
.highlight .k { color: #f92672; }
.highlight .s { color: #e6db74; }
```

**Rosettes**: CSS custom properties, runtime theming possible
```css
:root { --syntax-control: #f92672; --syntax-string: #e6db74; }
.highlight .k { color: var(--syntax-control); }
.highlight .s { color: var(--syntax-string); }
```

---

## Alternatives Considered

### 1. Extend Pygments Style System

**Rejected**: Would require maintaining compatibility with legacy patterns, still no CSS custom properties.

### 2. Use TextMate/VSCode Scopes Directly

**Rejected**: Different model (nested scopes vs flat tokens), complex mapping, limited to editor themes.

### 3. No Theme System (CSS Only)

**Rejected**: Loses ability to validate palettes, no Python-side introspection, harder to share themes.

---

## References

- [RFC-0002: Rosettes Syntax Highlighter](./rfc-rosettes-syntax-highlighter.md)
- [Bengal Design Tokens](../../bengal/themes/tokens.py)
- [WCAG 2.1 Contrast Requirements](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Pygments Style System](https://pygments.org/docs/styles/)

---

## Quick Reference

### Key Types

| Type | Purpose |
|------|---------|
| `SyntaxRole` | Semantic meaning of code elements |
| `SyntaxPalette` | Immutable theme with 20 color slots |
| `AdaptivePalette` | Light/dark adaptive theme |
| `ROLE_MAPPING` | TokenType → SyntaxRole static mapping |

### Built-in Palettes

| Palette | Type | Style |
|---------|------|-------|
| `MONOKAI` | Dark | Classic Monokai |
| `DRACULA` | Dark | Dracula theme |
| `GITHUB` | Adaptive | GitHub light/dark |
| `ONE_DARK` | Dark | Atom One Dark |
| `VS_DARK` | Dark | VS Code Dark+ |
| `BENGAL_TIGER` | Dark | Bengal brand colors |
| `SOLARIZED` | Adaptive | Solarized light/dark |

### CSS Variables

```css
--syntax-bg, --syntax-bg-hl
--syntax-control, --syntax-declaration, --syntax-import
--syntax-string, --syntax-number, --syntax-boolean
--syntax-type, --syntax-function, --syntax-variable, --syntax-constant
--syntax-comment, --syntax-docstring
--syntax-error, --syntax-warning, --syntax-added, --syntax-removed
--syntax-text, --syntax-muted
```
