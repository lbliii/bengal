"""
Tabs directive for Mistune.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.

Modern MyST syntax:
    :::{tab-set}
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
from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = [
    "TabItemDirective",  # Modern MyST syntax
    "TabSetDirective",  # Modern MyST syntax
    "TabsDirective",  # Legacy/backward compatibility
    "render_tab_item",
    "render_tab_set",
    "render_tabs",
]

logger = get_logger(__name__)

# Pre-compiled regex patterns
_TAB_SPLIT_PATTERN = re.compile(r"^### Tab: (.+)$", re.MULTILINE)


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
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["tabs"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse legacy tabs directive."""
        options = dict(self.parse_options(m))
        content = self.parse_content(m)

        # Split by tab markers
        parts = _TAB_SPLIT_PATTERN.split(content)

        tabs = []
        if len(parts) > 1:
            # Skip first part if it's just whitespace before first tab
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    title = parts[i].strip()
                    tab_content = parts[i + 1].strip()

                    # Parse the tab content as markdown
                    children = self.parse_tokens(block, tab_content, state)

                    tabs.append(
                        {
                            "type": "legacy_tab_item",
                            "attrs": {
                                "title": title,
                                "selected": i == start_idx,  # First tab selected
                            },
                            "children": children,
                        }
                    )

        return {
            "type": "legacy_tabs",
            "attrs": options,
            "children": tabs,
        }

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("tabs", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("legacy_tabs", render_tabs)
            md.renderer.register("legacy_tab_item", render_legacy_tab_item)


class TabSetDirective(DirectivePlugin):
    """
    Modern MyST-style tab container directive.

    Syntax:
        :::{tab-set}
        :sync: my-key  # Optional: sync tabs across multiple tab-sets

        :::{tab-item} Python
        Python content with **markdown** support.
        :::

        :::{tab-item} JavaScript
        JavaScript content here.
        :::
        ::::

    Each tab-item is a nested directive inside the tab-set.
    This is cleaner and more consistent with MyST Markdown.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["tab-set"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse tab-set directive."""
        options = dict(self.parse_options(m))

        # Parse nested tab-item directives
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        return {
            "type": "tab_set",
            "attrs": options,
            "children": children,
        }

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("tab-set", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("tab_set", render_tab_set)


class TabItemDirective(DirectivePlugin):
    """
    Individual tab directive (nested in tab-set).

    Syntax:
        :::{tab-item} Tab Title
        :selected:  # Optional: mark this tab as initially selected

        Tab content with full **markdown** support.
        :::

    Supports all markdown features including nested directives.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["tab-item"]

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """Parse tab-item directive."""
        title = self.parse_title(m)
        options = dict(self.parse_options(m))

        # Parse tab content
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        return {
            "type": "tab_item",
            "attrs": {
                "title": title,
                "selected": "selected" in options,
            },
            "children": children,
        }

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("tab-item", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("tab_item", render_tab_item)


# Render functions


def _extract_tab_items(text: str) -> list[tuple[str, str, str]]:
    """
    Extract tab-item divs from rendered HTML, handling nested divs correctly.

    This function properly matches opening and closing div tags by counting
    nesting levels, which is necessary because tab content may contain
    nested divs (e.g., code blocks, admonitions).

    Args:
        text: Rendered HTML containing tab-item divs

    Returns:
        List of (title, selected, content) tuples
    """
    import re

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

        # Find the matching closing </div> by counting nesting levels
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
            # No matching closing tag found, skip this match
            pos = match.end()

    return matches


def _extract_legacy_tab_items(text: str) -> list[tuple[str, str, str]]:
    """
    Extract legacy-tab-item divs from rendered HTML, handling nested divs correctly.

    Args:
        text: Rendered HTML containing legacy-tab-item divs

    Returns:
        List of (title, selected, content) tuples
    """
    import re

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

        # Find the matching closing </div> by counting nesting levels
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
            # No matching closing tag found, skip this match
            pos = match.end()

    return matches


def render_tab_set(renderer, text: str, **attrs) -> str:
    """
    Render tab-set container to HTML.

    The text contains rendered tab-item children. We need to extract
    titles and contents to build the tab navigation and panels.

    Args:
        renderer: Mistune renderer
        text: Rendered children (tab items)
        attrs: Tab set attributes (id, sync, etc.)

    Returns:
        HTML string for tab set
    """
    tab_id = attrs.get("id", f"tabs-{id(text)}")
    sync_key = attrs.get("sync", "")

    # Extract tab items from rendered HTML
    # Pattern: <div class="tab-item" data-title="..." data-selected="...">content</div>
    # NOTE: Cannot use simple regex because content may contain nested divs.
    #       Use proper HTML parsing via _extract_tab_items() to handle nesting correctly.
    matches = _extract_tab_items(text)

    if not matches:
        # Fallback: just wrap the content
        return f'<div class="tabs" id="{tab_id}">\n{text}</div>\n'

    # Build tab navigation
    nav_html = f'<div class="tabs" id="{tab_id}"'
    if sync_key:
        nav_html += f' data-sync="{_escape_html(sync_key)}"'
    nav_html += '>\n  <ul class="tab-nav">\n'

    for i, (title, selected, _) in enumerate(matches):
        active = (
            ' class="active"'
            if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
            else ""
        )
        nav_html += f'    <li{active}><a href="#" data-tab-target="{tab_id}-{i}">{_escape_html(title)}</a></li>\n'
    nav_html += "  </ul>\n"

    # Build content panes
    content_html = '  <div class="tab-content">\n'
    for i, (_, selected, content) in enumerate(matches):
        active = (
            " active"
            if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
            else ""
        )
        content_html += (
            f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n{content}    </div>\n'
        )
    content_html += "  </div>\n</div>\n"

    return nav_html + content_html


def render_tab_item(renderer, text: str, **attrs) -> str:
    """
    Render individual tab item to HTML.

    This creates a wrapper div with metadata that the parent tab-set
    will parse to build the navigation and panels.

    Args:
        renderer: Mistune renderer
        text: Rendered tab content
        attrs: Tab attributes (title, selected)

    Returns:
        HTML string for tab item (wrapper for tab-set to parse)
    """
    title = attrs.get("title", "Tab")
    selected = "true" if attrs.get("selected", False) else "false"

    # Return wrapper div that tab-set will parse
    # We escape the attributes but not the content (already rendered HTML)
    return (
        f'<div class="tab-item" '
        f'data-title="{_escape_html(title)}" '
        f'data-selected="{selected}">'
        f"{text}"
        f"</div>"
    )


def render_legacy_tab_item(renderer, text: str, **attrs) -> str:
    """
    Render legacy tab item to HTML.

    Similar to render_tab_item, creates a wrapper div with metadata
    that the parent legacy_tabs will parse.

    Args:
        renderer: Mistune renderer
        text: Rendered tab content
        attrs: Tab attributes (title, selected)

    Returns:
        HTML string for tab item (wrapper for legacy_tabs to parse)
    """
    title = attrs.get("title", "Tab")
    selected = "true" if attrs.get("selected", False) else "false"

    return (
        f'<div class="legacy-tab-item" '
        f'data-title="{_escape_html(title)}" '
        f'data-selected="{selected}">'
        f"{text}"
        f"</div>"
    )


def render_tabs(renderer, text: str, **attrs) -> str:
    """
    Render legacy tabs directive to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered children (tab items as wrapper divs)
        attrs: Tab attributes (id, etc.)

    Returns:
        HTML string for tabs
    """
    tab_id = attrs.get("id", f"tabs-{id(text)}")

    # Extract tab items from rendered HTML
    # Pattern: <div class="legacy-tab-item" data-title="..." data-selected="...">content</div>
    # NOTE: Cannot use simple regex because content may contain nested divs.
    #       Use proper HTML parsing via _extract_legacy_tab_items() to handle nesting correctly.
    matches = _extract_legacy_tab_items(text)

    if not matches:
        # Fallback: just wrap the content
        return f'<div class="tabs" id="{tab_id}">\n{text}</div>\n'

    # Build tab navigation
    nav_html = f'<div class="tabs" id="{tab_id}">\n  <ul class="tab-nav">\n'

    for i, (title, selected, _) in enumerate(matches):
        active = (
            ' class="active"'
            if selected == "true" or (i == 0 and not any(s == "true" for _, s, _ in matches))
            else ""
        )
        nav_html += f'    <li{active}><a href="#" data-tab-target="{tab_id}-{i}">{title}</a></li>\n'
    nav_html += "  </ul>\n"

    # Build content panes
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
    """
    Escape HTML special characters in attributes.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    if not text:
        return ""

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
