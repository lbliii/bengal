"""
Command Provider for Bengal Dashboard.

Provides fuzzy search for commands and pages in the command palette.
Integrates with Textual's CommandPalette widget.

Usage:
    Press Ctrl+P in any dashboard to open command palette
    Type to filter commands and pages
    Press Enter to execute/navigate
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.command import Hit, Hits, Provider

if TYPE_CHECKING:
    from bengal.core.site import Site


class BengalCommandProvider(Provider):
    """
    Command provider for Bengal dashboards.

    Provides fuzzy search for:
    - Dashboard commands (rebuild, clear, open browser, etc.)
    - Site pages (quick navigation)
    - Configuration options

    The provider is registered with BengalApp and available
    in all screens via Ctrl+P.
    """

    # Command definitions
    COMMANDS: ClassVar[list[dict]] = [
        {
            "name": "Rebuild Site",
            "description": "Trigger a full site rebuild",
            "action": "rebuild",
            "keywords": ["build", "refresh", "regenerate"],
        },
        {
            "name": "Open in Browser",
            "description": "Open the site in your default browser",
            "action": "open_browser",
            "keywords": ["view", "preview", "browse"],
        },
        {
            "name": "Clear Log",
            "description": "Clear the output log",
            "action": "clear_log",
            "keywords": ["reset", "clean"],
        },
        {
            "name": "Toggle Help",
            "description": "Show keyboard shortcuts",
            "action": "toggle_help",
            "keywords": ["shortcuts", "keys", "bindings"],
        },
        {
            "name": "Quit",
            "description": "Exit the dashboard",
            "action": "quit",
            "keywords": ["exit", "close", "stop"],
        },
        {
            "name": "Switch to Build",
            "description": "Go to Build dashboard",
            "action": "goto_build",
            "keywords": ["dashboard", "screen"],
        },
        {
            "name": "Switch to Serve",
            "description": "Go to Serve dashboard",
            "action": "goto_serve",
            "keywords": ["dashboard", "screen", "dev", "server"],
        },
        {
            "name": "Switch to Health",
            "description": "Go to Health dashboard",
            "action": "goto_health",
            "keywords": ["dashboard", "screen", "check", "validate"],
        },
    ]

    async def search(self, query: str) -> Hits:
        """
        Search for commands matching the query.

        Args:
            query: Search query string

        Yields:
            Matching command hits
        """
        query_lower = query.lower()
        matcher = self.matcher(query)

        for cmd in self.COMMANDS:
            # Match against name and keywords
            name = cmd["name"]
            keywords = cmd.get("keywords", [])
            all_text = f"{name} {' '.join(keywords)}".lower()

            # Check for match
            match = matcher.match(name)
            if match > 0:
                yield Hit(
                    match,
                    matcher.highlight(name),
                    partial=self._create_action(cmd["action"]),
                    help=cmd["description"],
                )
            elif query_lower in all_text:
                # Keyword match
                yield Hit(
                    1,  # Lower score for keyword match
                    name,
                    partial=self._create_action(cmd["action"]),
                    help=cmd["description"],
                )

    def _create_action(self, action_name: str):
        """Create a callable that executes the action."""

        async def execute():
            """Execute the command action."""
            app = self.app
            if hasattr(app, f"action_{action_name}"):
                method = getattr(app, f"action_{action_name}")
                await method() if callable(method) else None

        return execute


class PageSearchProvider(Provider):
    """
    Provider for searching site pages.

    Enables quick navigation to any page in the site
    via the command palette.
    """

    def __init__(self, site: Site | None = None):
        """
        Initialize page search provider.

        Args:
            site: Site instance for page data
        """
        super().__init__()
        self._site = site

    async def search(self, query: str) -> Hits:
        """
        Search for pages matching the query.

        Args:
            query: Search query string

        Yields:
            Matching page hits
        """
        if not self._site or not hasattr(self._site, "pages"):
            return

        matcher = self.matcher(query)
        query_lower = query.lower()

        for page in self._site.pages[:100]:  # Limit results
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
                    partial=self._create_page_action(page),
                    help=url,
                )
            elif query_lower in search_text:
                yield Hit(
                    1,
                    title or url,
                    partial=self._create_page_action(page),
                    help=url,
                )

    def _create_page_action(self, page):
        """Create action to open/navigate to page."""

        async def open_page():
            """Open page in browser or show details."""
            app = self.app
            url = getattr(page, "url", "")
            if url and hasattr(app, "server_url"):
                import webbrowser

                full_url = f"{app.server_url}{url}"
                webbrowser.open(full_url)
                app.notify(f"Opening {url}", title="Page")

        return open_page
