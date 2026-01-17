"""
Cross-reference index exporter for Bengal SSG.

Generates xref.json for cross-project documentation linking. Other Bengal sites
can import this index to enable [[ext:project:target]] syntax.

Output Format:
The xref.json contains:

    ```json
    {
      "version": "1",
      "generator": "bengal/0.2.0",
      "project": {
        "name": "My Project",
        "url": "https://docs.example.com/"
      },
      "generated": "2026-01-10T12:00:00Z",
      "entries": {
        "MyClass": {
          "type": "class",
          "path": "/api/python/myproject/#MyClass",
          "title": "MyClass",
          "summary": "Description from docstring"
        },
        "getting-started": {
          "type": "page",
          "path": "/docs/getting-started/",
          "title": "Getting Started"
        }
      }
    }
    ```

Entry Types:
- page: Content pages
- class: Python autodoc classes
- function: Python autodoc functions
- method: Python autodoc methods
- module: Python autodoc modules
- cli: CLI autodoc commands
- endpoint: OpenAPI autodoc endpoints

Configuration:
Enable in bengal.toml:

    ```toml
    [external_refs]
    export_index = true  # Generate xref.json on production builds
    ```

Example:
    >>> generator = XRefIndexGenerator(site)
    >>> path = generator.generate()
    >>> print(f"xref.json written to: {path}")

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.rendering.plugins.cross_references: CrossReferencePlugin
- plan/rfc-external-references.md: RFC for external references

See Also:
- https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal import __version__
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.autodoc import is_autodoc_page
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)

# xref.json format version
XREF_INDEX_VERSION = "1"


class XRefIndexGenerator:
    """
    Generates xref.json for cross-project documentation linking.
    
    Creates a JSON index that other Bengal sites can import to resolve
    [[ext:project:target]] references to pages, API docs, and CLI commands.
    
    Creation:
        Direct instantiation: XRefIndexGenerator(site)
            - Requires Site instance with rendered pages
            - Called during post-processing phase
    
    Attributes:
        site: Site instance with pages and configuration
    
    Entry Types:
        - page: Regular content pages
        - class: Python classes from autodoc
        - function: Python functions from autodoc
        - method: Python methods from autodoc
        - module: Python modules from autodoc
        - cli: CLI commands from autodoc
        - endpoint: REST API endpoints from autodoc
    
    Example:
            >>> generator = XRefIndexGenerator(site)
            >>> path = generator.generate()  # Returns Path to xref.json
        
    """

    def __init__(self, site: SiteLike) -> None:
        """
        Initialize the xref index generator.

        Args:
            site: Site instance with discovered pages
        """
        self.site = site

    def generate(self) -> Path:
        """
        Generate xref.json index file.

        Creates a JSON index containing all referenceable entries:
        - Content pages (by path and custom ID)
        - Autodoc entries (classes, functions, CLI commands, etc.)

        Returns:
            Path to the generated xref.json file
        """
        logger.info("generating_xref_index", page_count=len(self.site.pages))

        # Build project metadata
        project_url = self.site.baseurl or ""
        if not project_url.endswith("/"):
            project_url += "/"

        index_data: dict[str, Any] = {
            "version": XREF_INDEX_VERSION,
            "generator": f"bengal/{__version__}",
            "project": {
                "name": self.site.title or "Bengal Site",
                "url": project_url,
            },
            "generated": datetime.now(UTC).isoformat(),
            "entries": {},
        }

        # Add page entries
        for page in self.site.pages:
            self._add_page_entries(index_data["entries"], page)

        entry_count = len(index_data["entries"])
        logger.info(
            "xref_index_entries_collected",
            total_entries=entry_count,
            page_entries=sum(1 for e in index_data["entries"].values() if e["type"] == "page"),
            autodoc_entries=sum(1 for e in index_data["entries"].values() if e["type"] != "page"),
        )

        # Write to output directory
        output_path = self.site.output_dir / "xref.json"
        json_str = json.dumps(index_data, indent=2, ensure_ascii=False)

        with AtomicFile(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        logger.info(
            "xref_index_written",
            path=str(output_path),
            size_kb=round(output_path.stat().st_size / 1024, 2),
            entries=entry_count,
        )

        return output_path

    def _add_page_entries(self, entries: dict[str, Any], page: Page) -> None:
        """
        Add entries for a page to the index.

        Adds the page itself and any autodoc entries it contains.

        Args:
            entries: Dictionary to add entries to
            page: Page to process
        """
        # Skip draft pages
        if page.metadata.get("draft", False):
            return

        # Skip pages hidden from search
        if page.metadata.get("hidden", False):
            return

        visibility = page.metadata.get("visibility", {})
        if isinstance(visibility, dict) and not visibility.get("search", True):
            return

        # Get page URL
        page_url = page.href if hasattr(page, "href") else page.url

        # Determine entry type and key
        if is_autodoc_page(page):
            self._add_autodoc_entries(entries, page, page_url)
        else:
            self._add_content_page_entry(entries, page, page_url)

    def _add_content_page_entry(self, entries: dict[str, Any], page: Page, page_url: str) -> None:
        """
        Add a content page entry to the index.

        Args:
            entries: Dictionary to add entry to
            page: Page object
            page_url: URL for the page
        """
        # Use slug as primary key, fallback to path-based key
        entry_key = page.slug if hasattr(page, "slug") and page.slug else None

        if not entry_key:
            # Generate key from URL path
            entry_key = page_url.strip("/").replace("/", "-") or "index"

        # Build entry
        entry: dict[str, Any] = {
            "type": "page",
            "path": page_url,
            "title": page.title,
        }

        # Add summary from description or excerpt
        description = page.metadata.get("description", "")
        if description:
            entry["summary"] = description[:200]
        elif hasattr(page, "excerpt") and page.excerpt:
            entry["summary"] = page.excerpt[:200]

        entries[entry_key] = entry

        # Also add by custom ID if present
        if (custom_id := page.metadata.get("id")) and custom_id != entry_key:
            entries[custom_id] = entry

    def _add_autodoc_entries(self, entries: dict[str, Any], page: Page, page_url: str) -> None:
        """
        Add autodoc entries from a page to the index.

        Extracts classes, functions, methods, CLI commands, and API endpoints
        from autodoc pages.

        Args:
            entries: Dictionary to add entries to
            page: Autodoc page
            page_url: URL for the page
        """
        # Determine autodoc type from metadata
        autodoc_type = page.metadata.get("autodoc_type", "")

        if "api/python" in page_url or autodoc_type == "python":
            self._add_python_autodoc_entries(entries, page, page_url)
        elif "cli" in page_url or autodoc_type == "cli":
            self._add_cli_autodoc_entries(entries, page, page_url)
        elif "api/" in page_url or autodoc_type == "openapi":
            self._add_openapi_autodoc_entries(entries, page, page_url)
        else:
            # Fall back to content page entry
            self._add_content_page_entry(entries, page, page_url)

    def _add_python_autodoc_entries(
        self, entries: dict[str, Any], page: Page, page_url: str
    ) -> None:
        """
        Add Python autodoc entries (classes, functions, methods).

        Args:
            entries: Dictionary to add entries to
            page: Python autodoc page
            page_url: URL for the page
        """
        # Extract module name from metadata or URL
        module_name = page.metadata.get("api_module", "")
        if not module_name:
            # Try to extract from URL: /api/python/mypackage/module/
            parts = page_url.strip("/").split("/")
            if "python" in parts:
                idx = parts.index("python")
                module_name = ".".join(parts[idx + 1 :]) if idx + 1 < len(parts) else ""

        # Get documented items from metadata
        documented_items = page.metadata.get("documented_items", [])

        if documented_items:
            for item in documented_items:
                item_name = item.get("name", "")
                item_type = item.get("type", "function")
                item_summary = item.get("summary", "")

                if not item_name:
                    continue

                # Build fully qualified name
                fqn = f"{module_name}.{item_name}" if module_name else item_name

                entry: dict[str, Any] = {
                    "type": item_type,
                    "path": f"{page_url}#{item_name}",
                    "title": item_name,
                }

                if item_summary:
                    entry["summary"] = item_summary[:200]

                # Add by short name and fully qualified name
                entries[item_name] = entry
                if fqn != item_name:
                    entries[fqn] = entry
        else:
            # No documented_items metadata, add page as module entry
            if module_name:
                entries[module_name] = {
                    "type": "module",
                    "path": page_url,
                    "title": module_name,
                    "summary": page.metadata.get("description", "")[:200] or None,
                }

    def _add_cli_autodoc_entries(self, entries: dict[str, Any], page: Page, page_url: str) -> None:
        """
        Add CLI autodoc entries (commands, subcommands).

        Args:
            entries: Dictionary to add entries to
            page: CLI autodoc page
            page_url: URL for the page
        """
        # Get CLI command name from metadata
        cli_name = page.metadata.get("cli_name", "")
        if not cli_name:
            # Try to extract from title: "bengal build" -> "build"
            title_parts = page.title.split()
            if len(title_parts) > 1:
                cli_name = title_parts[-1]

        if cli_name:
            entry: dict[str, Any] = {
                "type": "cli",
                "path": page_url,
                "title": page.title,
            }

            if description := page.metadata.get("description", ""):
                entry["summary"] = description[:200]

            entries[cli_name] = entry

            # Also add full command if different
            if page.title and page.title != cli_name:
                entries[page.title.lower().replace(" ", "-")] = entry

    def _add_openapi_autodoc_entries(
        self, entries: dict[str, Any], page: Page, page_url: str
    ) -> None:
        """
        Add OpenAPI autodoc entries (endpoints).

        Args:
            entries: Dictionary to add entries to
            page: OpenAPI autodoc page
            page_url: URL for the page
        """
        # Get endpoint info from metadata
        endpoint_path = page.metadata.get("endpoint_path", "")
        endpoint_method = page.metadata.get("endpoint_method", "")
        operation_id = page.metadata.get("operation_id", "")

        if operation_id:
            entry: dict[str, Any] = {
                "type": "endpoint",
                "path": page_url,
                "title": page.title,
            }

            if description := page.metadata.get("description", ""):
                entry["summary"] = description[:200]

            # Add by operation_id
            entries[operation_id] = entry

            # Also add by method + path if available
            if endpoint_method and endpoint_path:
                endpoint_key = f"{endpoint_method.upper()} {endpoint_path}"
                entries[endpoint_key] = entry


def should_export_xref_index(site: SiteLike) -> bool:
    """
    Check if xref.json export is enabled.
    
    Args:
        site: Site instance
    
    Returns:
        True if external_refs.export_index is True
        
    """
    external_refs = site.config.get("external_refs", {})
    if isinstance(external_refs, bool):
        return False
    return bool(external_refs.get("export_index", False))
