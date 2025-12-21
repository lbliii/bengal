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

Robustness:
    - Maximum include depth of 10 to prevent stack overflow
    - Cycle detection to prevent infinite loops (a.md → b.md → a.md)
    - File size limits to prevent memory exhaustion (10MB default)
    - Symlink rejection to prevent path traversal attacks
"""

from __future__ import annotations

import contextlib
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

# Robustness limits
MAX_INCLUDE_DEPTH = 10  # Prevent stack overflow from deeply nested includes
MAX_INCLUDE_SIZE = 10 * 1024 * 1024  # 10 MB - prevent memory exhaustion


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

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["include"]

    def parse(self, block: BlockParser, m: Match[str], state: BlockState) -> dict[str, Any]:
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
        start_line_str = options.get("start-line")
        end_line_str = options.get("end-line")

        # Convert string line numbers to integers
        start_line: int | None = None
        end_line: int | None = None
        if start_line_str is not None:
            with contextlib.suppress(ValueError, TypeError):
                start_line = int(start_line_str)
        if end_line_str is not None:
            with contextlib.suppress(ValueError, TypeError):
                end_line = int(end_line_str)

        # Resolve file path
        file_path = self._resolve_path(path, state)

        if not file_path:
            return {
                "type": "include",
                "attrs": {"error": f"File not found: {path}"},
                "children": [],
            }

        # --- Robustness: Check depth limit ---
        current_depth = getattr(state, "_include_depth", 0)
        if current_depth >= MAX_INCLUDE_DEPTH:
            logger.warning(
                "include_max_depth_exceeded",
                path=path,
                depth=current_depth,
                max_depth=MAX_INCLUDE_DEPTH,
            )
            return {
                "type": "include",
                "attrs": {
                    "error": f"Maximum include depth ({MAX_INCLUDE_DEPTH}) exceeded. "
                    f"Check for deeply nested includes."
                },
                "children": [],
            }

        # --- Robustness: Check for include cycles ---
        included_files: set[str] = getattr(state, "_included_files", set())
        canonical_path = str(file_path.resolve())
        if canonical_path in included_files:
            logger.warning(
                "include_cycle_detected",
                path=path,
                canonical_path=canonical_path,
            )
            return {
                "type": "include",
                "attrs": {
                    "error": f"Include cycle detected: {path} was already included. "
                    f"Check for circular includes (a.md → b.md → a.md)."
                },
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

        # --- Update state for nested includes ---
        # Track this file to detect cycles
        new_included_files = included_files | {canonical_path}
        state._included_files = new_included_files  # type: ignore[attr-defined]
        state._include_depth = current_depth + 1  # type: ignore[attr-defined]

        # Parse included content as markdown
        # Use parse_tokens to allow nested directives in included content
        children = self.parse_tokens(block, content, state)

        # Restore depth after parsing (allows sibling includes at same depth)
        state._include_depth = current_depth  # type: ignore[attr-defined]

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

        Security:
            - Rejects absolute paths
            - Rejects paths outside site root
            - Rejects symlinks (could escape containment)

        Path Resolution:
            - root_path MUST be provided via state (set by rendering pipeline)
            - No fallback to Path.cwd() - eliminates CWD-dependent behavior
            - See: plan/active/rfc-path-resolution-architecture.md

        Args:
            path: Relative or absolute path to file
            state: Parser state (must contain root_path, may contain source_path)

        Returns:
            Resolved Path object, or None if not found, outside site root,
            or if root_path is not available in state
        """
        # Get root_path from state (MUST be set by rendering pipeline)
        # No CWD fallback - path resolution must be explicit
        root_path = getattr(state, "root_path", None)
        if not root_path:
            logger.warning(
                "include_missing_root_path",
                path=path,
                action="skipping",
                hint="Ensure rendering pipeline passes root_path in state",
            )
            return None
        root_path = Path(root_path)

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
            file_path: Path | None = resolved
        else:
            file_path = base_dir / path

        # Check if file exists
        if file_path is None or not file_path.exists():
            # Try with .md extension
            if not path.endswith(".md"):
                file_path = base_dir / f"{path}.md"
                if not file_path.exists():
                    file_path = None
            else:
                file_path = None

        # Fallback: try content directory if file not found relative to page
        # This allows global snippets to be used from any page location
        if file_path is None and source_path:
            content_dir = root_path / "content"
            if content_dir.exists():
                fallback_path = content_dir / path
                if fallback_path.exists():
                    file_path = fallback_path
                elif not path.endswith(".md"):
                    fallback_path = content_dir / f"{path}.md"
                    if fallback_path.exists():
                        file_path = fallback_path

        if file_path is None:
            return None

        # Security: Reject symlinks (could escape containment via symlink target)
        if file_path.is_symlink():
            logger.warning(
                "include_symlink_rejected",
                path=str(file_path),
                reason="symlinks_not_allowed_for_security",
            )
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

        Security: Enforces file size limit to prevent memory exhaustion.

        Args:
            file_path: Path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed)

        Returns:
            File content as string, or None on error
        """
        try:
            # Check file size before reading (security)
            file_size = file_path.stat().st_size
            if file_size > MAX_INCLUDE_SIZE:
                logger.warning(
                    "include_file_too_large",
                    path=str(file_path),
                    size_bytes=file_size,
                    limit_bytes=MAX_INCLUDE_SIZE,
                    size_mb=f"{file_size / (1024 * 1024):.2f}",
                    limit_mb=f"{MAX_INCLUDE_SIZE / (1024 * 1024):.0f}",
                )
                return None

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

            # Join lines and strip trailing whitespace (including trailing newline)
            # This prevents extra blank lines when embedding content
            return "".join(lines).rstrip()

        except Exception as e:
            logger.warning("include_load_error", path=str(file_path), error=str(e))
            return None

    def __call__(self, directive: Any, md: Any) -> None:
        """Register include directive."""
        directive.register("include", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("include", render_include)


def render_include(renderer: Any, text: str, **attrs: Any) -> str:
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
