"""
NotionSource - Content source for Notion databases.

Fetches pages from Notion databases and converts them to markdown.

Requires: pip install bengal[notion] (installs aiohttp)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

try:
    import aiohttp
except ImportError as e:
    raise ImportError(
        "NotionSource requires aiohttp.\nInstall with: pip install bengal[notion]"
    ) from e

from bengal.content_layer.entry import ContentEntry
from bengal.content_layer.source import ContentSource
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class NotionSource(ContentSource):
    """
    Content source for Notion databases.

    Fetches pages from a Notion database and converts them to markdown.
    Requires a Notion integration token with read access to the database.

    Configuration:
        database_id: str - Notion database ID (required)
        token: str - Notion integration token (or NOTION_TOKEN env var)
        property_mapping: dict - Map Notion properties to frontmatter fields
            Defaults: {"title": "Name", "date": "Date", "tags": "Tags"}
        filter: dict - Notion filter object (optional)
        sorts: list - Notion sorts array (optional)

    Setup:
        1. Create a Notion integration at https://www.notion.so/my-integrations
        2. Share your database with the integration
        3. Set NOTION_TOKEN environment variable or pass token in config

    Example:
        >>> source = NotionSource("blog", {
        ...     "database_id": "abc123...",
        ...     "property_mapping": {
        ...         "title": "Name",
        ...         "date": "Published",
        ...         "tags": "Tags",
        ...         "author": "Author",
        ...     },
        ... })
    """

    source_type = "notion"

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """
        Initialize Notion source.

        Args:
            name: Source name
            config: Configuration with 'database_id' required
        """
        super().__init__(name, config)

        from bengal.errors import BengalConfigError

        if "database_id" not in config:
            raise BengalConfigError(
                f"NotionSource '{name}' requires 'database_id' in config",
                suggestion="Add 'database_id' to NotionSource configuration",
            )

        self.database_id = config["database_id"]
        self.token = config.get("token") or os.environ.get("NOTION_TOKEN")
        self.property_mapping: dict[str, str] = config.get(
            "property_mapping",
            {"title": "Name", "date": "Date", "tags": "Tags"},
        )
        self.filter = config.get("filter")
        self.sorts = config.get("sorts")

        if not self.token:
            from bengal.errors import BengalConfigError

            raise BengalConfigError(
                f"NotionSource '{name}' requires a token.\n"
                "Set NOTION_TOKEN environment variable or pass 'token' in config.\n"
                "Create an integration at https://www.notion.so/my-integrations",
                suggestion="Set NOTION_TOKEN environment variable or add 'token' to config",
            )

        self.api_base = "https://api.notion.com/v1"
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all pages from the database.

        Handles pagination automatically.

        Yields:
            ContentEntry for each page
        """
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/databases/{self.database_id}/query"
            has_more = True
            start_cursor: str | None = None

            while has_more:
                body: dict[str, Any] = {}
                if start_cursor:
                    body["start_cursor"] = start_cursor
                if self.filter:
                    body["filter"] = self.filter
                if self.sorts:
                    body["sorts"] = self.sorts

                async with session.post(url, json=body) as resp:
                    if resp.status == 404:
                        logger.error(f"Database not found: {self.database_id}")
                        return
                    if resp.status == 401:
                        logger.error("Invalid Notion token or database not shared with integration")
                        return
                    resp.raise_for_status()
                    data = await resp.json()

                for page in data.get("results", []):
                    entry = await self._page_to_entry(session, page)
                    if entry:
                        yield entry

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """
        Fetch a single page by ID.

        Args:
            id: Notion page ID

        Returns:
            ContentEntry if found, None otherwise
        """
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/pages/{id}"

            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                page = await resp.json()

            return await self._page_to_entry(session, page)

    async def _page_to_entry(
        self,
        session: aiohttp.ClientSession,
        page: dict[str, Any],
    ) -> ContentEntry | None:
        """
        Convert Notion page to ContentEntry.

        Args:
            session: aiohttp session
            page: Notion page object

        Returns:
            ContentEntry or None
        """
        page_id = page["id"]

        # Get page content (blocks)
        content = await self._get_page_content(session, page_id)

        # Extract properties as frontmatter
        frontmatter = self._extract_properties(page)

        # Generate slug from title or ID
        title = frontmatter.get("title", "")
        slug = self._title_to_slug(title) if title else page_id.replace("-", "")

        # Parse last edited time
        last_modified = None
        if page.get("last_edited_time"):
            last_modified = datetime.fromisoformat(page["last_edited_time"].replace("Z", "+00:00"))

        return ContentEntry(
            id=page_id,
            slug=slug,
            content=content,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=page.get("url"),
            last_modified=last_modified,
        )

    async def _get_page_content(
        self,
        session: aiohttp.ClientSession,
        page_id: str,
    ) -> str:
        """
        Fetch and convert page blocks to markdown.

        Args:
            session: aiohttp session
            page_id: Notion page ID

        Returns:
            Markdown content string
        """
        url = f"{self.api_base}/blocks/{page_id}/children"
        blocks: list[dict[str, Any]] = []

        # Fetch all blocks (with pagination)
        has_more = True
        start_cursor: str | None = None

        while has_more:
            params: dict[str, Any] = {}
            if start_cursor:
                params["start_cursor"] = start_cursor

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to fetch blocks for page {page_id}")
                    break
                data = await resp.json()

            blocks.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        return self._blocks_to_markdown(blocks)

    def _blocks_to_markdown(self, blocks: list[dict[str, Any]]) -> str:
        """
        Convert Notion blocks to markdown.

        Args:
            blocks: List of Notion block objects

        Returns:
            Markdown string
        """
        lines: list[str] = []

        for block in blocks:
            block_type = block.get("type")
            block_data = block.get(str(block_type) if block_type else "", {})

            if block_type == "paragraph":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(text)

            elif block_type == "heading_1":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"# {text}")

            elif block_type == "heading_2":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"## {text}")

            elif block_type == "heading_3":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"### {text}")

            elif block_type == "bulleted_list_item":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"- {text}")

            elif block_type == "numbered_list_item":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"1. {text}")

            elif block_type == "to_do":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                checked = "x" if block_data.get("checked") else " "
                lines.append(f"- [{checked}] {text}")

            elif block_type == "toggle":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"<details><summary>{text}</summary>")
                # Note: nested blocks not handled in this simple implementation
                lines.append("</details>")

            elif block_type == "code":
                code = self._rich_text_to_md(block_data.get("rich_text", []))
                lang = block_data.get("language", "")
                lines.append(f"```{lang}")
                lines.append(code)
                lines.append("```")

            elif block_type == "quote":
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"> {text}")

            elif block_type == "callout":
                icon = block_data.get("icon", {}).get("emoji", "💡")
                text = self._rich_text_to_md(block_data.get("rich_text", []))
                lines.append(f"> {icon} {text}")

            elif block_type == "divider":
                lines.append("---")

            elif block_type == "image":
                image_data = block_data
                url = image_data.get("external", {}).get("url") or image_data.get("file", {}).get(
                    "url"
                )
                caption = self._rich_text_to_md(image_data.get("caption", []))
                if url:
                    lines.append(f"![{caption}]({url})")

            elif block_type == "bookmark":
                url = block_data.get("url", "")
                caption = self._rich_text_to_md(block_data.get("caption", []))
                lines.append(f"[{caption or url}]({url})")

            elif block_type == "equation":
                expression = block_data.get("expression", "")
                lines.append(f"$$\n{expression}\n$$")

            # Add blank line between blocks
            lines.append("")

        return "\n".join(lines).strip()

    def _rich_text_to_md(self, rich_text: list[dict[str, Any]]) -> str:
        """
        Convert Notion rich text to markdown.

        Args:
            rich_text: List of rich text objects

        Returns:
            Markdown string
        """
        parts: list[str] = []

        for item in rich_text:
            text = item.get("plain_text", "")
            annotations = item.get("annotations", {})

            # Apply formatting
            if annotations.get("code"):
                text = f"`{text}`"
            if annotations.get("bold"):
                text = f"**{text}**"
            if annotations.get("italic"):
                text = f"*{text}*"
            if annotations.get("strikethrough"):
                text = f"~~{text}~~"
            if annotations.get("underline"):
                text = f"<u>{text}</u>"

            # Handle links
            href = item.get("href")
            if href:
                text = f"[{text}]({href})"

            parts.append(text)

        return "".join(parts)

    def _extract_properties(self, page: dict[str, Any]) -> dict[str, Any]:
        """
        Extract Notion properties as frontmatter.

        Args:
            page: Notion page object

        Returns:
            Frontmatter dictionary
        """
        frontmatter: dict[str, Any] = {}
        properties = page.get("properties", {})

        for fm_key, notion_prop in self.property_mapping.items():
            if notion_prop not in properties:
                continue

            prop = properties[notion_prop]
            prop_type = prop.get("type")

            if prop_type == "title":
                frontmatter[fm_key] = self._rich_text_to_md(prop.get("title", []))

            elif prop_type == "rich_text":
                frontmatter[fm_key] = self._rich_text_to_md(prop.get("rich_text", []))

            elif prop_type == "date":
                date_obj = prop.get("date")
                if date_obj:
                    frontmatter[fm_key] = date_obj.get("start")

            elif prop_type == "multi_select":
                frontmatter[fm_key] = [opt["name"] for opt in prop.get("multi_select", [])]

            elif prop_type == "select":
                select_obj = prop.get("select")
                if select_obj:
                    frontmatter[fm_key] = select_obj.get("name")

            elif prop_type == "checkbox":
                frontmatter[fm_key] = prop.get("checkbox", False)

            elif prop_type == "number":
                frontmatter[fm_key] = prop.get("number")

            elif prop_type == "url":
                frontmatter[fm_key] = prop.get("url")

            elif prop_type == "email":
                frontmatter[fm_key] = prop.get("email")

            elif prop_type == "phone_number":
                frontmatter[fm_key] = prop.get("phone_number")

            elif prop_type == "people":
                people = prop.get("people", [])
                frontmatter[fm_key] = [p.get("name", p.get("id")) for p in people]

            elif prop_type == "files":
                files = prop.get("files", [])
                urls = []
                for f in files:
                    url = f.get("external", {}).get("url") or f.get("file", {}).get("url")
                    if url:
                        urls.append(url)
                frontmatter[fm_key] = urls

            elif prop_type == "status":
                status_obj = prop.get("status")
                if status_obj:
                    frontmatter[fm_key] = status_obj.get("name")

        return frontmatter

    def _title_to_slug(self, title: str) -> str:
        """
        Convert title to URL-friendly slug.

        Args:
            title: Page title

        Returns:
            URL-friendly slug
        """
        import re

        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")
