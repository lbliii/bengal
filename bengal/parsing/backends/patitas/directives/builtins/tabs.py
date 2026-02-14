"""Tab directives for tabbed content.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.

Supports two rendering modes:
- "enhanced" (default): JavaScript-based tabs with data-tab-target
- "css_state_machine": URL-driven tabs using :target CSS selector

Tab-Item Options:
:selected: - Whether this tab is initially selected
:icon: - Icon name to show next to tab label
:badge: - Badge text (e.g., "New", "Beta", "Pro")
:disabled: - Mark tab as disabled/unavailable

Example:
:::{tab-set}
:sync: language

:::{tab-item} Python
:icon: python
:selected:

Content for Python tab.
:::

:::{tab-item} JavaScript
:badge: Popular

Content for JavaScript tab.
:::

:::

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's tabs directive exactly.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from html import unescape as html_unescape
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import (
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    DirectiveContract,
)
from bengal.parsing.backends.patitas.directives.options import StyledOptions
from bengal.utils.primitives.text import slugify_id

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder


# Import hash utility for stable IDs
try:
    from bengal.utils.primitives.hashing import hash_str
except ImportError:
    import hashlib

    def hash_str(content: str, truncate: int | None = None, algorithm: str = "sha256") -> str:
        """Fallback hash function."""
        return hashlib.md5(content.encode()).hexdigest()[: truncate or 12]


@dataclass(frozen=True, slots=True)
class TabItemOptions(StyledOptions):
    """Options for tab-item directive.

    Attributes:
        selected: Whether this tab is initially selected
        icon: Icon name to show next to tab label
        badge: Badge text (e.g., "New", "Beta", "Pro")
        disabled: Mark tab as disabled/unavailable

    """

    selected: bool = False
    icon: str | None = None
    badge: str | None = None
    disabled: bool = False
    sync: str | None = None


@dataclass(frozen=True, slots=True)
class TabSetOptions(StyledOptions):
    """Options for tab-set directive.

    Attributes:
        id: Unique ID for the tab set
        sync: Sync key for synchronizing tabs across multiple tab-sets
        mode: Rendering mode - "enhanced" (JS) or "css_state_machine" (URL-driven)

    """

    id: str | None = None
    sync: str | None = None
    mode: str | None = None


@dataclass
class TabItemData:
    """Data extracted from a rendered tab-item div."""

    title: str
    selected: str
    icon: str
    badge: str
    disabled: str
    content: str


class TabItemDirective:
    """Handler for tab-item directive.

    Must be inside a tab-set container.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("tab-item", "tab")
    token_type: ClassVar[str] = "tab_item"
    contract: ClassVar[DirectiveContract | None] = TAB_ITEM_CONTRACT
    options_class: ClassVar[type[TabItemOptions]] = TabItemOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: TabItemOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build tab-item AST node."""
        return Directive(
            location=location,
            name=name,
            title=title or "Tab",
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[TabItemOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render tab-item to HTML.

        Creates a wrapper div with metadata that the parent tab-set
        will parse to build the navigation and panels.
        """
        opts = node.options  # Direct typed access!
        title = node.title or "Tab"
        selected = "true" if opts.selected else "false"
        icon = opts.icon or ""
        badge = opts.badge or ""
        disabled = "true" if opts.disabled else "false"

        sb.append(
            f'<div class="tab-item" '
            f'data-title="{html_escape(title)}" '
            f'data-selected="{selected}" '
            f'data-icon="{html_escape(icon)}" '
            f'data-badge="{html_escape(badge)}" '
            f'data-disabled="{disabled}">'
        )
        sb.append(rendered_children)
        sb.append("</div>")


class TabSetDirective:
    """Handler for tab-set container directive.

    Contains tab-item children that form a tabbed interface.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("tab-set", "tabs")
    token_type: ClassVar[str] = "tab_set"
    contract: ClassVar[DirectiveContract | None] = TAB_SET_CONTRACT
    options_class: ClassVar[type[TabSetOptions]] = TabSetOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: TabSetOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build tab-set AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[TabSetOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render tab-set to HTML.

        Extracts tab items from rendered children and builds
        navigation + content panels.

        Supports two modes:
        - "enhanced" (default): JavaScript-based tabs with data-tab-target
        - "css_state_machine": URL-driven tabs using :target CSS selector
        """
        opts = node.options  # Direct typed access!

        # Stable IDs are critical for deterministic builds
        tab_id = opts.id or f"tabs-{hash_str(rendered_children or '', truncate=12)}"
        sync_key = opts.sync or ""
        mode = opts.mode or "enhanced"

        # Extract tab items from rendered HTML
        matches = _extract_tab_items(rendered_children)

        if not matches:
            sb.append(f'<div class="tabs" id="{html_escape(tab_id)}" data-bengal="tabs">\n')
            sb.append(rendered_children)
            sb.append("</div>\n")
            return

        # Route to appropriate renderer
        if mode == "css_state_machine":
            self._render_css_state_machine(tab_id, sync_key, matches, sb)
        else:
            self._render_enhanced(tab_id, sync_key, matches, sb)

    def _render_enhanced(
        self, tab_id: str, sync_key: str, matches: list[TabItemData], sb: StringBuilder
    ) -> None:
        """Render JavaScript-enhanced tabs (default mode)."""
        # Build tab navigation
        sb.append(f'<div class="tabs" id="{html_escape(tab_id)}" data-bengal="tabs"')
        if sync_key:
            sb.append(f' data-sync="{html_escape(sync_key)}"')
        sb.append('>\n  <ul class="tab-nav">\n')

        for i, tab_data in enumerate(matches):
            # Determine active state
            is_first_unselected = i == 0 and not any(t.selected == "true" for t in matches)
            is_active = tab_data.selected == "true" or is_first_unselected
            is_disabled = tab_data.disabled == "true"

            # Build classes
            li_classes = []
            if is_active and not is_disabled:
                li_classes.append("active")
            if is_disabled:
                li_classes.append("disabled")
            class_attr = f' class="{" ".join(li_classes)}"' if li_classes else ""

            # Build tab label with optional icon and badge
            label_parts = []
            if tab_data.icon:
                label_parts.append(
                    f'<span class="tab-icon" data-icon="{html_escape(tab_data.icon)}"></span>'
                )
            label_parts.append(html_escape(tab_data.title))
            if tab_data.badge:
                label_parts.append(f'<span class="tab-badge">{html_escape(tab_data.badge)}</span>')
            label = "".join(label_parts)

            # Build link attributes
            disabled_attr = ' aria-disabled="true" tabindex="-1"' if is_disabled else ""
            sb.append(
                f'    <li{class_attr}><a href="#" data-tab-target="{html_escape(tab_id)}-{i}"{disabled_attr}>{label}</a></li>\n'
            )
        sb.append("  </ul>\n")

        # Build content panes
        sb.append('  <div class="tab-content">\n')
        for i, tab_data in enumerate(matches):
            is_first_unselected = i == 0 and not any(t.selected == "true" for t in matches)
            is_active = tab_data.selected == "true" or is_first_unselected
            is_disabled = tab_data.disabled == "true"

            pane_classes = ["tab-pane"]
            if is_active and not is_disabled:
                pane_classes.append("active")
            class_str = " ".join(pane_classes)

            sb.append(
                f'    <div id="{html_escape(tab_id)}-{i}" class="{class_str}">\n{tab_data.content}    </div>\n'
            )
        sb.append("  </div>\n</div>\n")

    def _render_css_state_machine(
        self, tab_id: str, sync_key: str, matches: list[TabItemData], sb: StringBuilder
    ) -> None:
        """Render CSS state machine tabs (URL-driven, no JS required).

        Uses :target CSS selector for tab state. Tab URLs become:
        /page#tabset-id-tabname
        """
        # Build tab navigation using proper ARIA roles
        sb.append(f'<div class="tabs tabs--native" id="{html_escape(tab_id)}"')
        if sync_key:
            sb.append(f' data-sync="{html_escape(sync_key)}"')
        sb.append('>\n  <nav class="tab-nav" role="tablist">\n')

        for tab_data in matches:
            is_disabled = tab_data.disabled == "true"

            # Generate slug from title for readable URLs
            tab_slug = self._make_tab_id(tab_data.title)
            pane_id = f"{tab_id}-{tab_slug}"

            # Build tab label with optional icon and badge
            label_parts = []
            if tab_data.icon:
                label_parts.append(
                    f'<span class="tab-icon" data-icon="{html_escape(tab_data.icon)}"></span>'
                )
            label_parts.append(f"<span>{html_escape(tab_data.title)}</span>")
            if tab_data.badge:
                label_parts.append(f'<span class="tab-badge">{html_escape(tab_data.badge)}</span>')
            label = "".join(label_parts)

            # ARIA attributes for accessibility
            aria_attrs = f'role="tab" aria-controls="{html_escape(pane_id)}"'
            if is_disabled:
                aria_attrs += ' aria-disabled="true" tabindex="-1"'

            # Use data-pane for CSS pairing
            sb.append(
                f'    <a href="#{html_escape(pane_id)}" {aria_attrs} data-pane="{html_escape(pane_id)}">{label}</a>\n'
            )
        sb.append("  </nav>\n")

        # Build content panes with proper roles
        sb.append('  <div class="tab-content">\n')
        for tab_data in matches:
            tab_slug = self._make_tab_id(tab_data.title)
            pane_id = f"{tab_id}-{tab_slug}"

            sb.append(
                f'    <section id="{html_escape(pane_id)}" role="tabpanel" class="tab-pane">\n'
                f"{tab_data.content}"
                f"    </section>\n"
            )
        sb.append("  </div>\n</div>\n")

    def _make_tab_id(self, text: str) -> str:
        """Convert tab title to URL-safe anchor ID."""
        return slugify_id(text, default="tab")


def _extract_tab_items(text: str) -> list[TabItemData]:
    """Extract tab-item divs from rendered HTML, handling nested divs correctly.

    Args:
        text: Rendered HTML containing tab-item divs

    Returns:
        List of TabItemData with extracted attributes

    """
    matches: list[TabItemData] = []
    pattern = re.compile(
        r'<div class="tab-item" '
        r'data-title="([^"]*)" '
        r'data-selected="([^"]*)" '
        r'data-icon="([^"]*)" '
        r'data-badge="([^"]*)" '
        r'data-disabled="([^"]*)">',
        re.DOTALL,
    )

    pos = 0
    while True:
        match = pattern.search(text, pos)
        if not match:
            break

        # Unescape: values were html_escape'd when written to data-* attrs
        title = html_unescape(match.group(1))
        selected = match.group(2)
        icon = html_unescape(match.group(3))
        badge = html_unescape(match.group(4))
        disabled = match.group(5)
        start = match.end()

        # Find matching closing </div> by counting nesting levels
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            # Check for opening div tag
            if i + 4 < len(text) and text[i : i + 4] == "<div":
                depth += 1
                # Find the closing '>' of this tag
                tag_end = text.find(">", i)
                if tag_end != -1:
                    i = tag_end + 1
                else:
                    i += 1
            elif i + 6 <= len(text) and text[i : i + 6] == "</div>":
                depth -= 1
                if depth == 0:
                    content = text[start:i]
                    matches.append(
                        TabItemData(
                            title=title,
                            selected=selected,
                            icon=icon,
                            badge=badge,
                            disabled=disabled,
                            content=content,
                        )
                    )
                    pos = i + 6
                    break
                i += 6
            else:
                i += 1
        else:
            pos = match.end()

    return matches
