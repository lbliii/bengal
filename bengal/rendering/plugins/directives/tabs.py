"""
Tabs directive for Mistune.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.

Architecture:
    Migrated to BengalDirective base class with DirectiveContract validation.
    - TabSetDirective: requires_children=["tab_item"]
    - TabItemDirective: requires_parent=["tab_set", "legacy_tabs"]

Modern MyST syntax:
    ::::{tab-set}
    :::{tab-item} Python
    Content here
    :::
    :::{tab-item} JavaScript
    Content here
    :::
    ::::
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Match
from typing import Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.contracts import (
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

__all__ = [
    "TabItemDirective",
    "TabSetDirective",
    "TabsDirective",
    "TabItemOptions",
    "TabSetOptions",
]

logger = get_logger(__name__)

# Pre-compiled regex patterns
_TAB_SPLIT_PATTERN = re.compile(r"^### Tab: (.+)$", re.MULTILINE)


# =============================================================================
# Tab Item Directive (must be nested in tab-set)
# =============================================================================


@dataclass
class TabItemOptions(DirectiveOptions):
    """
    Options for tab-item directive.

    Attributes:
        selected: Whether this tab is initially selected

    Example:
        :::{tab-item} Python
        :selected:
        Content here
        :::
    """

    selected: bool = False


class TabItemDirective(BengalDirective):
    """
    Individual tab directive (nested in tab-set).

    Syntax:
        :::{tab-item} Tab Title
        :selected:
        Tab content with full **markdown** support.
        :::

    Contract:
        MUST be nested inside a :::{tab-set} or legacy {tabs} directive.
    """

    # Support both "tab-item" and shorter "tab" alias
    NAMES: ClassVar[list[str]] = ["tab-item", "tab"]
    TOKEN_TYPE: ClassVar[str] = "tab_item"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = TabItemOptions

    # Contract: tab-item MUST be inside tab-set or legacy_tabs
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

        return (
            f'<div class="tab-item" '
            f'data-title="{self.escape_html(title)}" '
            f'data-selected="{selected}">'
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

    NAMES: ClassVar[list[str]] = ["tab-set"]
    TOKEN_TYPE: ClassVar[str] = "tab_set"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = TabSetOptions

    # Contract: tab-set REQUIRES tab_item children
    CONTRACT: ClassVar[DirectiveContract] = TAB_SET_CONTRACT

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["tab-set"]

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
        tab_id = attrs.get("id") or f"tabs-{id(text)}"
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

        for i, (title, selected, _) in enumerate(matches):
            active = (
                ' class="active"'
                if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
                else ""
            )
            nav_html += f'    <li{active}><a href="#" data-tab-target="{tab_id}-{i}">{self.escape_html(title)}</a></li>\n'
        nav_html += "  </ul>\n"

        # Build content panes
        content_html = '  <div class="tab-content">\n'
        for i, (_, selected, tab_content) in enumerate(matches):
            active = (
                " active"
                if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
                else ""
            )
            content_html += (
                f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n{tab_content}    </div>\n'
            )
        content_html += "  </div>\n</div>\n"

        return nav_html + content_html


# =============================================================================
# Legacy Tabs Directive (backward compatibility)
# =============================================================================


class TabsDirective(DirectivePlugin):
    """
    Legacy tabs directive for backward compatibility.

    Syntax:
        ```{tabs}
        :id: my-tabs

        ### Tab: First
        Content in first tab.

        ### Tab: Second
        Content in second tab.
        ```

    This uses ### Tab: markers to split content into tabs.
    For new code, prefer the modern {tab-set}/{tab-item} syntax.

    Note: Not migrated to BengalDirective because it uses a different
    parsing pattern (content splitting vs. nested directives).
    """

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["tabs"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse legacy tabs directive."""
        options = dict(self.parse_options(m))
        content = self.parse_content(m)

        # Split by tab markers
        parts = _TAB_SPLIT_PATTERN.split(content)

        tabs = []
        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    title = parts[i].strip()
                    tab_content = parts[i + 1].strip()
                    children = self.parse_tokens(block, tab_content, state)

                    tabs.append(
                        {
                            "type": "legacy_tab_item",
                            "attrs": {
                                "title": title,
                                "selected": i == start_idx,
                            },
                            "children": children,
                        }
                    )

        return {
            "type": "legacy_tabs",
            "attrs": options,
            "children": tabs,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("tabs", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("legacy_tabs", render_tabs)
            md.renderer.register("legacy_tab_item", render_legacy_tab_item)


# =============================================================================
# HTML Extraction Helpers
# =============================================================================


def _extract_tab_items(text: str) -> list[tuple[str, str, str]]:
    """
    Extract tab-item divs from rendered HTML, handling nested divs correctly.

    Args:
        text: Rendered HTML containing tab-item divs

    Returns:
        List of (title, selected, content) tuples
    """
    matches = []
    pattern = re.compile(
        r'<div class="tab-item" data-title="([^"]*)" data-selected="([^"]*)">', re.DOTALL
    )

    pos = 0
    while True:
        match = pattern.search(text, pos)
        if not match:
            break

        title = match.group(1)
        selected = match.group(2)
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
                    matches.append((title, selected, content))
                    pos = i + 6
                    break
                i += 6
            else:
                i += 1
        else:
            pos = match.end()

    return matches


def _extract_legacy_tab_items(text: str) -> list[tuple[str, str, str]]:
    """Extract legacy-tab-item divs from rendered HTML."""
    matches = []
    pattern = re.compile(
        r'<div class="legacy-tab-item" data-title="([^"]*)" data-selected="([^"]*)">', re.DOTALL
    )

    pos = 0
    while True:
        match = pattern.search(text, pos)
        if not match:
            break

        title = match.group(1)
        selected = match.group(2)
        start = match.end()

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
                    matches.append((title, selected, content))
                    pos = i + 6
                    break
                i += 6
            else:
                i += 1
        else:
            pos = match.end()

    return matches


# =============================================================================
# Backward Compatibility Render Functions
# =============================================================================


def render_tab_item(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return TabItemDirective().render(renderer, text, **attrs)


def render_tab_set(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return TabSetDirective().render(renderer, text, **attrs)


def render_legacy_tab_item(renderer: Any, text: str, **attrs: Any) -> str:
    """Render legacy tab item wrapper."""
    title = attrs.get("title", "Tab")
    selected = "true" if attrs.get("selected", False) else "false"

    return (
        f'<div class="legacy-tab-item" '
        f'data-title="{_escape_html(title)}" '
        f'data-selected="{selected}">'
        f"{text}"
        f"</div>"
    )


def render_tabs(renderer: Any, text: str, **attrs: Any) -> str:
    """Render legacy tabs directive to HTML."""
    tab_id = attrs.get("id", f"tabs-{id(text)}")

    matches = _extract_legacy_tab_items(text)

    if not matches:
        return f'<div class="tabs" id="{tab_id}" data-bengal="tabs">\n{text}</div>\n'

    nav_html = f'<div class="tabs" id="{tab_id}" data-bengal="tabs">\n  <ul class="tab-nav">\n'

    for i, (title, selected, _) in enumerate(matches):
        active = (
            ' class="active"'
            if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
            else ""
        )
        nav_html += f'    <li{active}><a href="#" data-tab-target="{tab_id}-{i}">{title}</a></li>\n'
    nav_html += "  </ul>\n"

    content_html = '  <div class="tab-content">\n'
    for i, (title, selected, content) in enumerate(matches):
        active = (
            " active"
            if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
            else ""
        )
        content_html += f'    <div id="{tab_id}-{i}" class="tab-pane{active}" data-tab-title="{title}">\n{content}    </div>\n'
    content_html += "  </div>\n</div>\n"

    return nav_html + content_html


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
