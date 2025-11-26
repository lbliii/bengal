"""
Include directive for Mistune.

Allows including markdown files directly in content.
Syntax:
    ```{include} path/to/file.md
    ```

Or with options:
    ```{include} path/to/file.md
    :start-line: 5
    :end-line: 20
    ```

Paths are resolved relative to the site root or the current page's directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from re import Match

    from mistune.block_parser import BlockParser
    from mistune.core import BlockState

__all__ = ["IncludeDirective", "render_include"]

logger = get_logger(__name__)


class IncludeDirective(DirectivePlugin):
    """
    Include directive for including markdown files.

    Syntax:
        ```{include} path/to/file.md
        ```

    Or with line range:
        ```{include} path/to/file.md
        :start-line: 5
        :end-line: 20
        ```

    Paths are resolved relative to:
    1. Current page's directory (if source_path available in state)
    2. Site root (if root_path available in state)
    3. Current working directory (fallback)

    Security: Only allows paths within the site root to prevent path traversal.
    """

    def parse(self, block: BlockParser, m: Match, state: BlockState) -> dict[str, Any]:
        """
        Parse include directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state (may contain root_path, source_path)

        Returns:
            Token dict with type 'include'
        """
        # Get file path from title
        path = self.parse_title(m)
        if not path or not path.strip():
            logger.warning(
                "include_no_path",
                reason="include directive missing file path",
            )
            return {
                "type": "include",
                "attrs": {"error": "No file path specified"},
                "children": [],
            }

        # Parse options
        options = dict(self.parse_options(m))
        start_line = options.get("start-line")
        end_line = options.get("end-line")

        # Resolve file path
        file_path = self._resolve_path(path, state)

        if not file_path:
            return {
                "type": "include",
                "attrs": {"error": f"File not found: {path}"},
                "children": [],
            }

        # Load file content
        content = self._load_file(file_path, start_line, end_line)

        if content is None:
            return {
                "type": "include",
                "attrs": {"error": f"Failed to read file: {path}"},
                "children": [],
            }

        # Parse included content as markdown
        # Use parse_tokens to allow nested directives in included content
        children = self.parse_tokens(block, content, state)

        return {
            "type": "include",
            "attrs": {
                "path": str(file_path),
                "start_line": int(start_line) if start_line else None,
                "end_line": int(end_line) if end_line else None,
            },
            "children": children,
        }

    def _resolve_path(self, path: str, state: BlockState) -> Path | None:
        """
        Resolve file path relative to current page or site root.

        Args:
            path: Relative or absolute path to file
            state: Parser state (may contain root_path, source_path)

        Returns:
            Resolved Path object, or None if not found or outside site root
        """
        # Try to get root_path from state (set by rendering pipeline)
        root_path = getattr(state, "root_path", None)
        root_path = Path(root_path) if root_path else Path.cwd()

        # Try to get source_path from state (current page being parsed)
        source_path = getattr(state, "source_path", None)
        if source_path:
            source_path = Path(source_path)
            # Use current page's directory as base for relative paths
            base_dir = source_path.parent
        else:
            # Fall back to content directory
            content_dir = root_path / "content"
            base_dir = content_dir if content_dir.exists() else root_path

        # Resolve path relative to base directory
        if Path(path).is_absolute():
            # Reject absolute paths (security)
            logger.warning("include_absolute_path_rejected", path=path)
            return None

        # Check for path traversal attempts
        normalized_path = path.replace("\\", "/")
        if "../" in normalized_path or normalized_path.startswith("../"):
            # Allow relative paths, but validate they stay within site root
            resolved = (base_dir / path).resolve()
            # Ensure resolved path is within site root
            try:
                resolved.relative_to(root_path.resolve())
            except ValueError:
                logger.warning("include_path_traversal_rejected", path=path)
                return None
            file_path = resolved
        else:
            file_path = base_dir / path

        # Check if file exists
        if not file_path.exists():
            # Try with .md extension
            if not path.endswith(".md"):
                file_path = base_dir / f"{path}.md"
                if not file_path.exists():
                    return None
            else:
                return None

        # Ensure file is within site root (security check)
        try:
            file_path.resolve().relative_to(root_path.resolve())
        except ValueError:
            logger.warning("include_outside_site_root", path=str(file_path))
            return None

        return file_path

    def _load_file(
        self, file_path: Path, start_line: int | None, end_line: int | None
    ) -> str | None:
        """
        Load file content, optionally with line range.

        Args:
            file_path: Path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed)

        Returns:
            File content as string, or None on error
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Apply line range if specified
            if start_line is not None or end_line is not None:
                start = int(start_line) - 1 if start_line else 0
                end = int(end_line) if end_line else len(lines)
                # Clamp to valid range
                start = max(0, min(start, len(lines)))
                end = max(start, min(end, len(lines)))
                lines = lines[start:end]

            return "".join(lines)

        except Exception as e:
            logger.warning("include_load_error", path=str(file_path), error=str(e))
            return None

    def __call__(self, directive, md):
        """Register include directive."""
        directive.register("include", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("include", render_include)


def render_include(renderer, text: str, **attrs) -> str:
    """
    Render include directive.

    Args:
        renderer: Mistune renderer
        text: Rendered children (included markdown content)
        **attrs: Directive attributes

    Returns:
        HTML string
    """
    error = attrs.get("error")

    if error:
        return f'<div class="include-error"><p><strong>Include error:</strong> {error}</p></div>\n'

    # text contains the rendered included markdown content
    return text
