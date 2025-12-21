"""
Tabs directive for Mistune.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.

Architecture:
    Built on BengalDirective base class with DirectiveContract validation.
    - TabSetDirective: requires_children=["tab_item"]
    - TabItemDirective: requires_parent=["tab_set"]

MyST syntax (with named closers):
    :::{tab-set}
    :::{tab-item} Python
    :icon: python
    :badge: Recommended
    Content here
    :::{/tab-item}
    :::{tab-item} JavaScript
    Content here
    :::{/tab-item}
    :::{/tab-set}

Tab-Item Options:
    :selected: - Whether this tab is initially selected
    :icon: - Icon name to show next to tab label
    :badge: - Badge text (e.g., "New", "Beta", "Pro")
    :disabled: - Mark tab as disabled/unavailable
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.contracts import (
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    DirectiveContract,
)
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

__all__ = [
    "TabItemDirective",
    "TabSetDirective",
    "TabItemOptions",
    "TabSetOptions",
]

logger = get_logger(__name__)


# =============================================================================
# Tab Item Directive (must be nested in tab-set)
# =============================================================================


@dataclass
class TabItemOptions(DirectiveOptions):
    """
    Options for tab-item directive.

    Attributes:
        selected: Whether this tab is initially selected
        icon: Icon name to show next to tab label
        badge: Badge text (e.g., "New", "Beta", "Pro")
        disabled: Mark tab as disabled/unavailable

    Example:
        :::{tab-item} Python
        :selected:
        :icon: python
        :badge: Recommended
        Content here
        :::{/tab-item}
    """

    selected: bool = False
    icon: str = ""
    badge: str = ""
    disabled: bool = False


class TabItemDirective(BengalDirective):
    """
    Individual tab directive (nested in tab-set).

    Syntax:
        :::{tab-item} Tab Title
        :selected:
        Tab content with full **markdown** support.
        :::

    Contract:
        MUST be nested inside a :::{tab-set} directive.
    """

    # Support both "tab-item" and shorter "tab" alias
    NAMES: ClassVar[list[str]] = ["tab-item", "tab"]
    TOKEN_TYPE: ClassVar[str] = "tab_item"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = TabItemOptions

    # Contract: tab-item MUST be inside tab-set
    CONTRACT: ClassVar[DirectiveContract] = TAB_ITEM_CONTRACT

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["tab-item", "tab"]

    def parse_directive(
        self,
        title: str,
        options: TabItemOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build tab-item token from parsed components."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "Tab",
                "selected": options.selected,
                "icon": options.icon,
                "badge": options.badge,
                "disabled": options.disabled,
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render individual tab item to HTML.

        Creates a wrapper div with metadata that the parent tab-set
        will parse to build the navigation and panels.
        """
        title = attrs.get("title", "Tab")
        selected = "true" if attrs.get("selected", False) else "false"
        icon = attrs.get("icon", "")
        badge = attrs.get("badge", "")
        disabled = "true" if attrs.get("disabled", False) else "false"

        return (
            f'<div class="tab-item" '
            f'data-title="{self.escape_html(title)}" '
            f'data-selected="{selected}" '
            f'data-icon="{self.escape_html(icon)}" '
            f'data-badge="{self.escape_html(badge)}" '
            f'data-disabled="{disabled}">'
            f"{text}"
            f"</div>"
        )


# =============================================================================
# Tab Set Container Directive
# =============================================================================


@dataclass
class TabSetOptions(DirectiveOptions):
    """
    Options for tab-set directive.

    Attributes:
        id: Unique ID for the tab set
        sync: Sync key for synchronizing tabs across multiple tab-sets

    Example:
        ::::{tab-set}
        :id: my-tabs
        :sync: language
        ...
        ::::
    """

    id: str = ""
    sync: str = ""


class TabSetDirective(BengalDirective):
    """
    Modern MyST-style tab container directive.

    Syntax:
        ::::{tab-set}
        :sync: my-key

        :::{tab-item} Python
        Python content with **markdown** support.
        :::

        :::{tab-item} JavaScript
        JavaScript content here.
        :::
        ::::

    Contract:
        REQUIRES at least one :::{tab-item} child directive.
    """

    NAMES: ClassVar[list[str]] = ["tab-set", "tabs"]
    TOKEN_TYPE: ClassVar[str] = "tab_set"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = TabSetOptions

    # Contract: tab-set REQUIRES tab_item children
    CONTRACT: ClassVar[DirectiveContract] = TAB_SET_CONTRACT

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["tab-set", "tabs"]

    def parse_directive(
        self,
        title: str,
        options: TabSetOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build tab-set token from parsed components."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "id": options.id,
                "sync": options.sync,
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render tab-set container to HTML.

        Extracts tab items from rendered children and builds
        navigation + content panels.
        """
        # Stable IDs are critical for deterministic builds and output diffs.
        # Previous behavior used `id(text)` which varies between runs/processes.
        tab_id = attrs.get("id") or f"tabs-{hash_str(text or '', truncate=12)}"
        sync_key = attrs.get("sync", "")

        # Extract tab items from rendered HTML
        matches = _extract_tab_items(text)

        if not matches:
            return f'<div class="tabs" id="{tab_id}" data-bengal="tabs">\n{text}</div>\n'

        # Build tab navigation
        nav_html = f'<div class="tabs" id="{tab_id}" data-bengal="tabs"'
        if sync_key:
            nav_html += f' data-sync="{self.escape_html(sync_key)}"'
        nav_html += '>\n  <ul class="tab-nav">\n'

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
                    f'<span class="tab-icon" data-icon="{self.escape_html(tab_data.icon)}"></span>'
                )
            label_parts.append(self.escape_html(tab_data.title))
            if tab_data.badge:
                label_parts.append(
                    f'<span class="tab-badge">{self.escape_html(tab_data.badge)}</span>'
                )
            label = "".join(label_parts)

            # Build link attributes
            disabled_attr = ' aria-disabled="true" tabindex="-1"' if is_disabled else ""
            nav_html += f'    <li{class_attr}><a href="#" data-tab-target="{tab_id}-{i}"{disabled_attr}>{label}</a></li>\n'
        nav_html += "  </ul>\n"

        # Build content panes
        content_html = '  <div class="tab-content">\n'
        for i, tab_data in enumerate(matches):
            is_first_unselected = i == 0 and not any(t.selected == "true" for t in matches)
            is_active = tab_data.selected == "true" or is_first_unselected
            is_disabled = tab_data.disabled == "true"

            pane_classes = ["tab-pane"]
            if is_active and not is_disabled:
                pane_classes.append("active")
            class_str = " ".join(pane_classes)

            content_html += (
                f'    <div id="{tab_id}-{i}" class="{class_str}">\n{tab_data.content}    </div>\n'
            )
        content_html += "  </div>\n</div>\n"

        return nav_html + content_html


# =============================================================================
# HTML Extraction Helpers
# =============================================================================


@dataclass
class TabItemData:
    """Data extracted from a rendered tab-item div."""

    title: str
    selected: str
    icon: str
    badge: str
    disabled: str
    content: str


def _extract_tab_items(text: str) -> list[TabItemData]:
    """
    Extract tab-item divs from rendered HTML, handling nested divs correctly.

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

        title = match.group(1)
        selected = match.group(2)
        icon = match.group(3)
        badge = match.group(4)
        disabled = match.group(5)
        start = match.end()

        # Find matching closing </div> by counting nesting levels
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i : i + 5] == "<div " or text[i : i + 5] == "<div>":
                depth += 1
                i += 5
            elif text[i : i + 6] == "</div>":
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
