# Bengal Directive System (v2)

The directive system provides MyST-style fenced directives for rich content authoring in Bengal documentation.

## Named Closers (New!)

Bengal supports **named closers** as an alternative to fence-depth counting:

```markdown
<!-- Traditional fence-depth counting (still works) -->
::::{tab-set}
:::{tab-item} First
Content
:::
:::{tab-item} Second
Content
:::
::::

<!-- Named closers (new - no counting!) -->
:::{tab-set}
:::{tab-item} First
Content
:::{/tab-item}
:::{tab-item} Second
Content
:::{/tab-item}
:::{/tab-set}
```

### Benefits

- **No mental counting** — Use `:::{/name}` to close any directive
- **Deeply nested structures** — Works at any nesting depth without adding colons
- **Mixed syntax** — Combine named closers with fence-depth as needed
- **Backward compatible** — Traditional fence-depth counting still works

### When to Use Named Closers

| Scenario | Recommendation |
|----------|----------------|
| Simple admonition | Fence-depth (concise) |
| Tabs with 2 items | Either works |
| 3+ levels of nesting | Named closers (clearer) |
| Tabs > Cards > Tips | Named closers (essential) |

### Example: Deep Nesting Made Simple

```markdown
:::{tab-set}
:::{tab-item} Overview
:::{cards}
:::{card} Getting Started
:::{tip}
This would require 6+ colons with fence-depth counting!
:::{/tip}
:::{/card}
:::{/cards}
:::{/tab-item}
:::{/tab-set}
```

## Architecture Overview

Bengal's directive system is built on four core components:

```
┌─────────────────────────────────────────────────────────────────┐
│                       BengalDirective                            │
│                     (base class for all)                         │
├─────────────────────────────────────────────────────────────────┤
│  DirectiveToken      │  DirectiveOptions   │  DirectiveContract  │
│  (typed AST tokens)  │  (typed options)    │  (nesting rules)    │
├─────────────────────────────────────────────────────────────────┤
│                        utils.py                                  │
│              (shared HTML utilities)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start: Creating a New Directive

### 1. Define Options (if needed)

```python
from dataclasses import dataclass
from bengal.rendering.plugins.directives.options import DirectiveOptions

@dataclass
class MyOptions(DirectiveOptions):
    """Options for my custom directive."""
    title: str = ""
    color: str = "default"
    show_icon: bool = True
```

### 2. Create the Directive Class

```python
from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.rendering.plugins.directives.utils import escape_html

class MyDirective(BengalDirective):
    """My custom directive."""
    
    DIRECTIVE_NAMES = frozenset({"my-directive"})
    
    def parse_directive(
        self, block: Any, m: re.Match, state: Any
    ) -> DirectiveToken:
        """Parse the directive from markdown."""
        info = self.parse_info(m)
        options = self.parse_options(m, MyOptions)
        
        return DirectiveToken(
            directive_type="my_directive",
            raw_info=info,
            title=options.title or info,
            attrs={"color": options.color},
            children=block.parse(m.group("text") or "", state),
        )
    
    def render(
        self, renderer: Any, text: str, title: str = "", **attrs
    ) -> str:
        """Render the directive to HTML."""
        color = attrs.get("color", "default")
        return f'<div class="my-directive {color}">{text}</div>'
```

### 3. Register the Directive

Add your directive to `__init__.py`:

1. Add to `DIRECTIVE_CLASSES` list
2. Add to `create_documentation_directives()` function

## Core Components

### DirectiveToken

Typed dataclass for AST tokens:

```python
@dataclass
class DirectiveToken:
    directive_type: str      # e.g., "admonition", "tabs"
    raw_info: str           # e.g., "note", "warning"
    children: list          # Child tokens (parsed markdown)
    title: str = ""         # Optional title
    attrs: dict = field(default_factory=dict)  # Custom attributes
```

### DirectiveOptions

Base class for typed option parsing with automatic coercion:

```python
@dataclass
class DirectiveOptions:
    css_class: str = ""     # Most directives support css_class

# Pre-built option classes:
# - StyledOptions: css_class
# - TitledOptions: title, css_class
# - ContainerOptions: columns, gap, style, css_class
```

Options are parsed from the directive body:
```markdown
:::{my-directive}
:title: My Title
:color: blue
:show_icon: true

Content here
:::
```

### DirectiveContract

Defines valid parent-child nesting relationships:

```python
@dataclass
class DirectiveContract:
    required_parent: list[str] | None = None  # Must be inside these
    allowed_children: list[str] | None = None  # Can contain these
    disallowed_children: list[str] | None = None  # Cannot contain these
    min_children: int | None = None
    max_children: int | None = None

# Example: step must be inside steps
STEP_CONTRACT = DirectiveContract(
    required_parent=["steps"]
)

# Example: steps can only contain step children
STEPS_CONTRACT = DirectiveContract(
    allowed_children=["step"]
)
```

## Available Directives

### Content Blocks

| Directive | Description | Example |
|-----------|-------------|---------|
| `admonition` | Callout boxes (note, tip, warning, etc.) | `:::{note}` |
| `dropdown` | Collapsible sections | `:::{dropdown} Title` |
| `container` | Generic wrapper div | `:::{container} my-class` |
| `rubric` | Pseudo-heading (not in TOC) | `:::{rubric} API Reference` |
| `example-label` | Lightweight example section label | `:::{example-label} Basic Usage` |

### Navigation

| Directive | Description | Example |
|-----------|-------------|---------|
| `tabs` / `tab-set` | Tabbed content | `:::{tab-set}` |
| `tab-item` | Individual tab | `:::{tab-item} Label` |
| `steps` | Step-by-step guide | `:::{steps}` |
| `step` | Individual step | `:::{step} Title` |

#### Tabs Example (with named closers)

```markdown
:::{tab-set}
:sync: language

:::{tab-item} Python
:icon: python
:badge: Recommended
Python code example here.
:::{/tab-item}

:::{tab-item} JavaScript
:icon: javascript
JavaScript code example here.
:::{/tab-item}

:::{tab-item} Legacy API
:disabled:
:badge: Deprecated
This tab is disabled.
:::{/tab-item}
:::{/tab-set}
```

**Tab-Set Options:**
- `:id:` — Unique ID for the tab set
- `:sync:` — Sync key for synchronizing tabs across multiple tab-sets

**Tab-Item Options:**
- `:selected:` — Mark this tab as initially selected
- `:icon:` — Icon name to display next to tab label
- `:badge:` — Badge text (e.g., "New", "Beta", "Pro")
- `:disabled:` — Mark tab as disabled/unavailable

#### Steps Example (with named closers)

```markdown
:::{steps}
:start: 1

:::{step} Install Dependencies
:description: First, set up your environment with required packages.
:duration: 2 min
Run the installation command:
\`\`\`bash
pip install bengal
\`\`\`
:::{/step}

:::{step} Configure Your Site
:description: Customize Bengal's behavior for your project.
:duration: 5 min
Edit `bengal.toml` to add your settings.
:::{/step}

:::{step} Advanced Configuration
:optional:
:description: These settings are for power users.
Optional advanced configuration here.
:::{/step}
:::{/steps}
```

**Steps Container Options:**
- `:class:` — Custom CSS class for the container
- `:style:` — Visual style (`default`, `compact`)
- `:start:` — Start numbering from this value (default: 1)

**Step Options:**
- `:class:` — Custom CSS class for the step
- `:description:` — Lead-in text with special typography (rendered before main content)
- `:optional:` — Mark step as optional/skippable (adds visual indicator)
- `:duration:` — Estimated time for the step (e.g., "2 min", "1 hour")

#### Example Labels

Lightweight semantic labels for example sections - a "soft header" that doesn't appear in TOC:

```markdown
:::{example-label} Basic Usage
:::

Here's how you use it:
\`\`\`python
print("hello")
\`\`\`
```

**Example Label Options:**
- `:class:` — Custom CSS class (e.g., `featured`, `compact`)
- `:prefix:` — Custom prefix text (default: "Example")
- `:no-prefix:` — Omit the prefix entirely

```markdown
<!-- Custom prefix -->
:::{example-label} API Call
:prefix: Demo
:::

<!-- No prefix (just the title) -->
:::{example-label} Simple
:no-prefix:
:::

<!-- Featured styling -->
:::{example-label} Production Setup
:class: featured
:::
```

### Cards and Grids

| Directive | Description | Example |
|-----------|-------------|---------|
| `cards` | Card grid container | `::::{cards}` |
| `card` | Individual card | `:::{card} Title` |
| `child-cards` | Auto-generate from children | `:::{child-cards}` |

#### Cards Example (with named closers)

```markdown
:::{cards}
:columns: 3
:gap: medium

:::{card} Getting Started
:icon: rocket
:link: /docs/quickstart/
:description: Everything you need to get up and running
:badge: Updated
Detailed content explaining how to get started.
:::{/card}

:::{card} API Reference
:icon: book
:link: /docs/api/
:description: Complete API documentation
:color: blue
Technical API documentation.
:::{/card}
:::{/cards}
```

**Cards Container Options:**
- `:columns:` — Column layout (`auto`, `1-6`, or responsive `1-2-3`)
- `:gap:` — Grid gap (`small`, `medium`, `large`)
- `:style:` — Visual style (`default`, `minimal`, `bordered`)
- `:variant:` — Card variant (`navigation`, `info`, `concept`)
- `:layout:` — Card layout (`default`, `horizontal`, `portrait`, `compact`)

**Card Options:**
- `:icon:` — Icon name displayed in card header
- `:link:` — URL or page reference (makes card clickable)
- `:description:` — Brief summary shown below the title
- `:badge:` — Badge text (e.g., "New", "Beta", "Pro")
- `:color:` — Color theme (`blue`, `green`, `red`, `yellow`, etc.)
- `:image:` — Header image URL
- `:footer:` — Footer content
- `:pull:` — Fields to pull from linked page (`title`, `description`, `icon`, `badge`)
- `:layout:` — Layout override

### Code and Data

| Directive | Description | Example |
|-----------|-------------|---------|
| `code-tabs` | Multi-language code tabs | `:::{code-tabs}` |
| `list-table` | Table from nested list | `:::{list-table}` |
| `data-table` | Interactive data table | `:::{data-table}` |
| `literalinclude` | Include code file | `:::{literalinclude} file.py` |

### UI Elements

| Directive | Description | Example |
|-----------|-------------|---------|
| `button` | Styled link button | `:::{button} URL` |
| `badge` | Inline badge | `:::{badge} Label` |
| `icon` | Inline SVG icon | `:::{icon} star` |
| `checklist` | Styled checklist | `:::{checklist}` |

#### Checklist Example

```markdown
:::{checklist} Prerequisites
:style: numbered
:show-progress:
:compact:
- [x] Python 3.14+ installed
- [x] Bengal package installed
- [ ] Git configured
- [ ] IDE with Python support
:::{/checklist}
```

**Checklist Options:**
- `:style:` — Visual style (`default`, `numbered`, `minimal`)
- `:show-progress:` — Display completion percentage bar for task lists
- `:compact:` — Tighter spacing for dense lists
- `:class:` — Custom CSS class

## Nesting Validation

The contract system validates parent-child relationships at parse time:

```markdown
<!-- ✅ Valid: step inside steps (named closers - preferred) -->
:::{steps}
:start: 1

:::{step} First Step
:description: This is the lead-in text.
:duration: 3 min
Step content here.
:::{/step}

:::{step} Optional Step
:optional:
This step is skippable.
:::{/step}
:::{/steps}

<!-- ✅ Valid: fence-depth counting (still works) -->
::::{steps}
:::{step}
First step
:::
::::

<!-- ⚠️ Warning: orphaned step (will still render) -->
:::{step}
Orphaned step
:::
```

When a contract violation is detected, Bengal logs a warning but continues rendering. This provides gradual enforcement without breaking existing content.

### Contracts Defined

| Parent | Children | Contract |
|--------|----------|----------|
| `steps` | `step` | Required |
| `tab-set` | `tab-item` | Required |
| `cards` | `card` | Soft (recommended) |

## Migration from Legacy Directives

### Before (ad-hoc rendering)

```python
class OldDirective(DirectivePlugin):
    def parse(self, block, m, state):
        # Manual option parsing
        options = self.parse_directive_options(m)
        # Manual token creation
        return {"type": "old_directive", ...}
    
    def __call__(self, directive, md):
        directive.register(...)
        md.renderer.old_directive = render_old_directive
```

### After (BengalDirective)

```python
class NewDirective(BengalDirective):
    DIRECTIVE_NAMES = frozenset({"new-directive"})
    
    def parse_directive(self, block, m, state) -> DirectiveToken:
        options = self.parse_options(m, MyOptions)
        return DirectiveToken(...)
    
    def render(self, renderer, text, **attrs) -> str:
        return f'<div>{text}</div>'
```

### Migration Checklist

- [ ] Create options dataclass (if directive has options)
- [ ] Inherit from `BengalDirective` instead of `DirectivePlugin`
- [ ] Add `DIRECTIVE_NAMES` class attribute
- [ ] Implement `parse_directive()` returning `DirectiveToken`
- [ ] Implement `render()` method
- [ ] Add `CONTRACT` if directive has nesting requirements
- [ ] Update `__init__.py` exports

## Utility Functions

```python
from bengal.rendering.plugins.directives.utils import (
    escape_html,        # HTML escape
    build_class_string, # Build class attribute
    bool_attr,          # Boolean HTML attribute
    data_attrs,         # Data attribute dictionary
    attr_str,           # Format attribute string
    class_attr,         # Format class attribute
)
```

## Testing Directives

```python
from bengal.rendering.parsers.mistune import MistuneParser

def test_my_directive():
    parser = MistuneParser()
    markdown = """
:::{my-directive}
:color: blue
Content
:::
"""
    result = parser.parse(markdown, {})
    assert 'class="my-directive blue"' in result
    assert "Content" in result
```

## File Structure

```
bengal/rendering/plugins/directives/
├── __init__.py          # Package exports, registry
├── base.py              # BengalDirective base class
├── tokens.py            # DirectiveToken dataclass
├── options.py           # DirectiveOptions + presets
├── contracts.py         # DirectiveContract + validator
├── utils.py             # Shared utilities
├── fenced.py            # FencedDirective parser
├── cache.py             # Directive caching
├── errors.py            # Error handling
├── validator.py         # Syntax validation
│
├── admonitions.py       # note, tip, warning, etc.
├── badge.py             # badge, bdg
├── button.py            # button
├── cards.py             # cards, card, child-cards, grid
├── checklist.py         # checklist
├── code_tabs.py         # code-tabs
├── container.py         # container, div
├── data_table.py        # data-table
├── dropdown.py          # dropdown, details
├── example_label.py     # example-label (lightweight example headers)
├── glossary.py          # glossary
├── icon.py              # icon, svg-icon
├── include.py           # include
├── list_table.py        # list-table
├── literalinclude.py    # literalinclude
├── marimo.py            # marimo (optional)
├── navigation.py        # breadcrumbs, siblings, prev-next, related
├── rubric.py            # rubric
├── steps.py             # steps, step
├── tabs.py              # tabs, tab-set, tab-item
└── README.md            # This file
```

## See Also

- [RFC: Directive System v2](../../../../plan/active/rfc-directive-system-v2.md) - Design rationale
- [Plan: Directive System v2](../../../../plan/active/plan-directive-system-v2.md) - Implementation plan
- [MyST Directive Syntax](https://myst-parser.readthedocs.io/en/latest/syntax/directives.html) - Syntax reference

