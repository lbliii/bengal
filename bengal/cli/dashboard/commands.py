"""
Command Provider for Bengal Dashboard.

Provides fuzzy search for commands and pages in the command palette.
Integrates with Textual's CommandPalette widget.

Inspired by Toad's ModeProvider pattern for discovery and search.

Usage:
    Press Ctrl+P in any dashboard to open command palette
    Type to filter commands and pages
    Press Enter to execute/navigate
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, ClassVar

from textual.command import DiscoveryHit, Hit, Hits, Provider

if TYPE_CHECKING:
    pass


class BengalCommandProvider(Provider):
    """
    Command provider for Bengal dashboards.

    Provides fuzzy search for:
    - Dashboard commands (rebuild, clear, open browser, etc.)
    - Screen navigation
    - Configuration options

    Includes discovery hits for common actions shown before typing.

    The provider is registered with BengalApp and available
    in all screens via Ctrl+P.
    """

    # Command definitions with keyboard shortcuts
    COMMANDS: ClassVar[list[dict]] = [
        {
            "name": "Rebuild Site",
            "description": "Trigger a full site rebuild",
            "action": "rebuild",
            "key": "r",
            "keywords": ["build", "refresh", "regenerate"],
        },
        {
            "name": "Open in Browser",
            "description": "Open the site in your default browser",
            "action": "open_browser",
            "key": "o",
            "keywords": ["view", "preview", "browse"],
        },
        {
            "name": "Clear Log",
            "description": "Clear the output log",
            "action": "clear_log",
            "key": "c",
            "keywords": ["reset", "clean"],
        },
        {
            "name": "Toggle Help",
            "description": "Show keyboard shortcuts",
            "action": "toggle_help",
            "key": "?",
            "keywords": ["shortcuts", "keys", "bindings"],
        },
        {
            "name": "Toggle Stats Panel",
            "description": "Show/hide statistics panel",
            "action": "toggle_stats",
            "key": "s",
            "keywords": ["stats", "panel", "hide", "show"],
        },
        {
            "name": "Quit",
            "description": "Exit the dashboard",
            "action": "quit",
            "key": "q",
            "keywords": ["exit", "close", "stop"],
        },
        {
            "name": "Switch to Build",
            "description": "Go to Build dashboard",
            "action": "goto_build",
            "key": "1",
            "keywords": ["dashboard", "screen"],
        },
        {
            "name": "Switch to Serve",
            "description": "Go to Serve dashboard",
            "action": "goto_serve",
            "key": "2",
            "keywords": ["dashboard", "screen", "dev", "server"],
        },
        {
            "name": "Switch to Health",
            "description": "Go to Health dashboard",
            "action": "goto_health",
            "key": "3",
            "keywords": ["dashboard", "screen", "check", "validate"],
        },
    ]

    async def discover(self) -> Hits:
        """
        Provide discovery hits shown before user types.

        Yields common actions for quick access.
        """
        # Show most common actions for quick discovery
        discovery_commands = [
            ("Rebuild Site", "rebuild", "Trigger a full site rebuild"),
            ("Open in Browser", "open_browser", "Open site in browser"),
            ("Check Health", "goto_health", "Go to health dashboard"),
            ("Toggle Stats", "toggle_stats", "Show/hide statistics"),
            ("Show Help", "toggle_help", "Show keyboard shortcuts"),
        ]

        for name, action, description in discovery_commands:
            yield DiscoveryHit(
                name,
                partial(self._execute_action, action),
                help=description,
            )

    async def search(self, query: str) -> Hits:
        """
        Search for commands matching the query.

        Args:
            query: Search query string

        Yields:
            Matching command hits with keyboard shortcut info
        """
        query_lower = query.lower()
        matcher = self.matcher(query)

        for cmd in self.COMMANDS:
            # Match against name and keywords
            name = cmd["name"]
            keywords = cmd.get("keywords", [])
            key = cmd.get("key", "")
            all_text = f"{name} {' '.join(keywords)}".lower()

            # Build help text with keyboard shortcut
            help_text = cmd["description"]
            if key:
                help_text = f"[{key}] {help_text}"

            # Check for match
            match = matcher.match(name)
            if match > 0:
                yield Hit(
                    match,
                    matcher.highlight(name),
                    partial(self._execute_action, cmd["action"]),
                    help=help_text,
                )
            elif query_lower in all_text:
                # Keyword match
                yield Hit(
                    1,  # Lower score for keyword match
                    name,
                    partial(self._execute_action, cmd["action"]),
                    help=help_text,
                )

    async def _execute_action(self, action_name: str) -> None:
        """Execute the command action."""
        app = self.app
        method_name = f"action_{action_name}"
        if hasattr(app, method_name):
            method = getattr(app, method_name)
            if callable(method):
                result = method()
                # Handle both sync and async methods
                if hasattr(result, "__await__"):
                    await result


class BengalPageProvider(Provider):
    """
    Provider for searching site pages.

    Enables quick navigation to any page in the site
    via the command palette. Opens page in browser.
    """

    async def discover(self) -> Hits:
        """
        Provide discovery hits for quick page access.

        Shows recently viewed or important pages.
        """
        # For discovery, we could show:
        # - Homepage
        # - Recently viewed pages (if tracked)
        # - Top-level section pages
        site = getattr(self.app, "site", None)
        if not site:
            return

        # Find homepage or first page
        pages = getattr(site, "pages", [])
        if pages:
            # Try to find index/homepage
            for page in pages[:5]:
                title = getattr(page, "title", "") or "Untitled"
                url = getattr(page, "url", "") or "/"
                yield DiscoveryHit(
                    f"📄 {title}",
                    partial(self._open_page, page),
                    help=url,
                )

    async def search(self, query: str) -> Hits:
        """
        Search for pages matching the query.

        Args:
            query: Search query string

        Yields:
            Matching page hits
        """
        site = getattr(self.app, "site", None)
        if not site or not hasattr(site, "pages"):
            return

        matcher = self.matcher(query)
        query_lower = query.lower()

        for page in site.pages[:50]:  # Limit for performance
            title = getattr(page, "title", "") or ""
            url = getattr(page, "url", "") or ""
            search_text = f"{title} {url}".lower()

            if not title and not url:
                continue

            # Match against title
            match = matcher.match(title) if title else 0
            if match > 0:
                yield Hit(
                    match,
                    matcher.highlight(title),
                    partial(self._open_page, page),
                    help=url,
                )
            elif query_lower in search_text:
                yield Hit(
                    1,
                    title or url,
                    partial(self._open_page, page),
                    help=url,
                )

    async def _open_page(self, page) -> None:
        """Open page in browser."""
        import webbrowser

        app = self.app
        url = getattr(page, "url", "")
        server_url = getattr(app, "server_url", "http://localhost:1313")

        if url:
            full_url = f"{server_url}{url}"
            webbrowser.open(full_url)
            app.notify(f"Opening {url}", title="Page")


# Backwards compatibility alias
PageSearchProvider = BengalPageProvider
