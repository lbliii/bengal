"""
Literal include directive for Mistune.

Allows including code files directly in content as code blocks.
Syntax:

    ```{literalinclude} path/to/file.py
    ```

Or with options:

    ```{literalinclude} path/to/file.py
    :language: python
    :start-line: 5
    :end-line: 20
    :emphasize-lines: 7,8,9
    :linenos: true
    ```

Robustness:
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

__all__ = ["LiteralIncludeDirective", "render_literalinclude"]

logger = get_logger(__name__)

# Robustness limits
MAX_INCLUDE_SIZE = 10 * 1024 * 1024  # 10 MB - prevent memory exhaustion


class LiteralIncludeDirective(DirectivePlugin):
    """
    Literal include directive for including code files as code blocks.

    Syntax:
        ```{literalinclude} path/to/file.py
        ```

    Or with options:
        ```{literalinclude} path/to/file.py
        :language: python
        :start-line: 5
        :end-line: 20
        :emphasize-lines: 7,8,9
        :linenos: true
        ```

    Paths are resolved relative to:
    1. Current page's directory (if source_path available in state)
    2. Site root (if root_path available in state)
    3. Current working directory (fallback)

    Security: Only allows paths within the site root to prevent path traversal.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["literalinclude"]

    def parse(self, block: BlockParser, m: Match[str], state: BlockState) -> dict[str, Any]:
        """
        Parse literalinclude directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state (may contain root_path, source_path)

        Returns:
            Token dict with type 'literalinclude'
        """
        # Get file path from title
        path = self.parse_title(m)
        if not path or not path.strip():
            logger.warning(
                "literalinclude_no_path",
                reason="literalinclude directive missing file path",
            )
            return {
                "type": "literalinclude",
                "attrs": {"error": "No file path specified"},
                "children": [],
            }

        # Parse options
        options = dict(self.parse_options(m))
        language = options.get("language")
        start_line_str = options.get("start-line")
        end_line_str = options.get("end-line")
        emphasize_lines = options.get("emphasize-lines")
        linenos = options.get("linenos", "false").lower() in ("true", "1", "yes")

        # Convert string line numbers to integers
        start_line: int | None = None
        end_line: int | None = None
        if start_line_str is not None:
            with contextlib.suppress(ValueError, TypeError):
                start_line = int(start_line_str)
        if end_line_str is not None:
            with contextlib.suppress(ValueError, TypeError):
                end_line = int(end_line_str)

        # Auto-detect language from file extension if not specified
        if not language:
            language = self._detect_language(path)

        # Resolve file path
        file_path = self._resolve_path(path, state)

        if not file_path:
            return {
                "type": "literalinclude",
                "attrs": {"error": f"File not found: {path}"},
                "children": [],
            }

        # Load file content
        content = self._load_file(file_path, start_line, end_line, emphasize_lines)

        if content is None:
            return {
                "type": "literalinclude",
                "attrs": {"error": f"Failed to read file: {path}"},
                "children": [],
            }

        return {
            "type": "literalinclude",
            "attrs": {
                "path": str(file_path),
                "language": language,
                "code": content,
                "start_line": int(start_line) if start_line else None,
                "end_line": int(end_line) if end_line else None,
                "emphasize_lines": emphasize_lines,
                "linenos": linenos,
            },
            "children": [],
        }

    def _detect_language(self, path: str) -> str | None:
        """
        Detect language from file extension.

        Args:
            path: File path

        Returns:
            Language name or None
        """
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".html": "html",
            ".css": "css",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".fish": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".sql": "sql",
            ".xml": "xml",
            ".r": "r",
            ".R": "r",
            ".m": "matlab",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".clj": "clojure",
            ".hs": "haskell",
            ".ml": "ocaml",
            ".fs": "fsharp",
            ".vb": "vbnet",
            ".cs": "csharp",
            ".dart": "dart",
            ".lua": "lua",
            ".pl": "perl",
            ".pm": "perl",
            ".vim": "vim",
            ".vimrc": "vim",
            ".dockerfile": "dockerfile",
            ".makefile": "makefile",
            ".mk": "makefile",
        }

        ext = Path(path).suffix.lower()
        return ext_map.get(ext)

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
                "literalinclude_missing_root_path",
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
            logger.warning("literalinclude_absolute_path_rejected", path=path)
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
                logger.warning("literalinclude_path_traversal_rejected", path=path)
                return None
            file_path = resolved
        else:
            file_path = base_dir / path

        # Check if file exists
        if not file_path.exists():
            return None

        # Security: Reject symlinks (could escape containment via symlink target)
        if file_path.is_symlink():
            logger.warning(
                "literalinclude_symlink_rejected",
                path=str(file_path),
                reason="symlinks_not_allowed_for_security",
            )
            return None

        # Ensure file is within site root (security check)
        try:
            file_path.resolve().relative_to(root_path.resolve())
        except ValueError:
            logger.warning("literalinclude_outside_site_root", path=str(file_path))
            return None

        return file_path

    def _load_file(
        self,
        file_path: Path,
        start_line: int | None,
        end_line: int | None,
        emphasize_lines: str | None,
    ) -> str | None:
        """
        Load file content, optionally with line range and emphasis.

        Security: Enforces file size limit to prevent memory exhaustion.

        Args:
            file_path: Path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed)
            emphasize_lines: Optional comma-separated line numbers to emphasize

        Returns:
            File content as string, or None on error
        """
        try:
            # Check file size before reading (security)
            file_size = file_path.stat().st_size
            if file_size > MAX_INCLUDE_SIZE:
                logger.warning(
                    "literalinclude_file_too_large",
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

            # Apply emphasis if specified
            if emphasize_lines:
                emphasize_set: set[int] = set()
                for part in emphasize_lines.split(","):
                    part = part.strip()
                    if "-" in part:
                        # Range: "7-9"
                        range_start, range_end = map(int, part.split("-"))
                        emphasize_set.update(range(range_start, range_end + 1))
                    else:
                        # Single line
                        emphasize_set.add(int(part))

                # Mark emphasized lines (we'll handle this in render)
                # For now, just return the content
                # The renderer will handle emphasis via CSS classes

            return "".join(lines).rstrip()

        except Exception as e:
            logger.warning("literalinclude_load_error", path=str(file_path), error=str(e))
            return None

    def __call__(self, directive: Any, md: Any) -> None:
        """Register literalinclude directive."""
        directive.register("literalinclude", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("literalinclude", render_literalinclude)


def render_literalinclude(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render literalinclude directive as code block.

    Args:
        renderer: Mistune renderer
        text: Not used (content is in attrs['code'])
        **attrs: Directive attributes

    Returns:
        HTML string
    """
    error = attrs.get("error")
    if error:
        return f'<div class="literalinclude-error"><p><strong>Literal include error:</strong> {error}</p></div>\n'

    code = attrs.get("code", "")
    language = attrs.get("language")
    linenos = attrs.get("linenos", False)
    emphasize_lines = attrs.get("emphasize_lines")

    # Use mistune's block_code renderer if available
    if hasattr(renderer, "block_code"):
        # Render as code block with syntax highlighting
        html: str = renderer.block_code(code, language)
    else:
        # Fallback: simple code block
        lang_attr = f' class="language-{language}"' if language else ""
        html = f"<pre><code{lang_attr}>{code}</code></pre>\n"

    # Add line numbers wrapper if requested
    if linenos:
        html = f'<div class="highlight-wrapper linenos">\n{html}</div>\n'

    # Add emphasis classes if specified
    if emphasize_lines:
        # Note: Full emphasis support would require client-side JS or server-side processing
        # For now, we just add a data attribute that themes can use
        emphasize_str = (
            emphasize_lines if isinstance(emphasize_lines, str) else str(emphasize_lines)
        )
        html = f'<div class="highlight-wrapper emphasize-lines" data-emphasize="{emphasize_str}">\n{html}</div>\n'

    return html
