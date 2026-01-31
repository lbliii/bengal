"""File I/O directives for documentation.

Provides:
- include: Include markdown files directly in content
- literalinclude: Include code files as code blocks

Security:
- Maximum include depth to prevent stack overflow
- Cycle detection to prevent infinite loops
- File size limits to prevent memory exhaustion
- Symlink rejection to prevent path traversal attacks
- Path containment within site root

Context Requirements:
These directives require a FileResolver to be provided by the renderer.
The resolver handles path resolution and file loading with security checks.

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's include directives exactly for parity.

"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from html import escape as html_escape
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = [
    "FileResolver",
    "IncludeDirective",
    "LiteralIncludeDirective",
]


# =============================================================================
# File Resolver Protocol
# =============================================================================


class FileResolver(Protocol):
    """Protocol for file resolution and loading.

    Implementations must handle:
    - Path resolution relative to current file or site root
    - Security validation (containment, symlinks, size limits)
    - File loading with encoding support

    """

    def resolve_path(self, path: str, source_file: str | None) -> Path | None:
        """Resolve a path relative to source file or site root.

        Args:
            path: Relative path to resolve
            source_file: Current source file path (for relative resolution)

        Returns:
            Resolved absolute Path, or None if not found/invalid
        """
        ...

    def load_file(
        self,
        path: Path,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str | None:
        """Load file content with optional line range.

        Args:
            path: Absolute path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed)

        Returns:
            File content, or None on error
        """
        ...


# =============================================================================
# Include Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class IncludeOptions(DirectiveOptions):
    """Options for include directive."""

    start_line: int | None = None
    end_line: int | None = None


class IncludeDirective:
    """
    Include markdown files directly in content.

    Syntax:
        :::{include} path/to/file.md
        :::

        :::{include} path/to/file.md
        :start-line: 5
        :end-line: 20
        :::

    Requires:
        FileResolver for path resolution and file loading.

    Security:
        - Maximum include depth of 10 (stack overflow protection)
        - Cycle detection (infinite loop protection)
        - File size limits (memory exhaustion protection)
        - Symlink rejection (path traversal protection)
        - Path containment within site root

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("include",)
    token_type: ClassVar[str] = "include"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[IncludeOptions]] = IncludeOptions
    preserves_raw_content: ClassVar[bool] = True  # Need raw content for parsing

    # File resolver - set by renderer/parser during registration
    file_resolver: FileResolver | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: IncludeOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build include AST node.

        Note: For include, the actual file loading and recursive parsing
        happens in a separate integration step, not during parse.
        The parse method just captures the configuration.
        """
        file_path = title.strip() if title else ""

        # Store configuration in options
        computed_opts = replace(
            options,
            start_line=options.start_line,
            end_line=options.end_line,
        )
        # Add file path as attribute
        object.__setattr__(computed_opts, "file_path", file_path)
        object.__setattr__(computed_opts, "error", "" if file_path else "No file path specified")

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,
            children=tuple(children),  # May be populated by integration layer
            raw_content=content,
        )

    def render(
        self,
        node: Directive[IncludeOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render include directive."""
        opts = node.options

        error = getattr(opts, "error", "")
        if error:
            sb.append(
                f'<div class="include-error">'
                f"<p><strong>Include error:</strong> {html_escape(error)}</p>"
                f"</div>\n"
            )
            return

        # rendered_children contains the rendered included markdown content
        sb.append(rendered_children)


# =============================================================================
# LiteralInclude Directive
# =============================================================================


# Extension to language mapping
EXTENSION_LANGUAGE_MAP = {
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


@dataclass(frozen=True, slots=True)
class LiteralIncludeOptions(DirectiveOptions):
    """Options for literalinclude directive."""

    language: str = ""
    start_line: int | None = None
    end_line: int | None = None
    emphasize_lines: str = ""
    linenos: bool = False
    caption: str = ""


class LiteralIncludeDirective:
    """
    Include code files as syntax-highlighted code blocks.

    Syntax:
        :::{literalinclude} path/to/file.py
        :::

        :::{literalinclude} path/to/file.py
        :language: python
        :start-line: 5
        :end-line: 20
        :emphasize-lines: 7,8,9
        :linenos:
        :::

    Requires:
        FileResolver for path resolution and file loading.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("literalinclude",)
    token_type: ClassVar[str] = "literalinclude"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[LiteralIncludeOptions]] = LiteralIncludeOptions

    # File resolver - set by renderer/parser during registration
    file_resolver: FileResolver | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: LiteralIncludeOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build literalinclude AST node."""
        file_path = title.strip() if title else ""

        # Auto-detect language from extension if not specified
        language = options.language
        if not language and file_path:
            ext = Path(file_path).suffix.lower()
            language = EXTENSION_LANGUAGE_MAP.get(ext, "")

        # Store configuration in options
        computed_opts = replace(
            options,
            language=language,
        )
        # Add computed attributes
        object.__setattr__(computed_opts, "file_path", file_path)
        object.__setattr__(computed_opts, "code", "")  # Will be populated by integration
        object.__setattr__(computed_opts, "error", "" if file_path else "No file path specified")

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,
            children=(),
        )

    def render(
        self,
        node: Directive[LiteralIncludeOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render literalinclude as code block."""
        opts = node.options

        error = getattr(opts, "error", "")
        if error:
            sb.append(
                f'<div class="literalinclude-error">'
                f"<p><strong>Literal include error:</strong> {html_escape(error)}</p>"
                f"</div>\n"
            )
            return

        code = getattr(opts, "code", "")
        language = opts.language
        linenos = opts.linenos
        emphasize_lines = opts.emphasize_lines
        caption = opts.caption

        # Build language class
        lang_class = f' class="language-{language}"' if language else ""

        # Build wrapper classes
        wrapper_classes = ["highlight-wrapper"]
        if linenos:
            wrapper_classes.append("linenos")
        if emphasize_lines:
            wrapper_classes.append("emphasize-lines")

        # Add caption if present
        if caption:
            sb.append(f'<div class="{" ".join(wrapper_classes)}">\n')
            sb.append(f'<div class="code-caption">{html_escape(caption)}</div>\n')
        elif linenos or emphasize_lines:
            sb.append(f'<div class="{" ".join(wrapper_classes)}"')
            if emphasize_lines:
                sb.append(f' data-emphasize="{html_escape(emphasize_lines)}"')
            sb.append(">\n")

        # Render code block
        sb.append(f"<pre><code{lang_class}>{html_escape(code)}</code></pre>\n")

        # Close wrapper if opened
        if caption or linenos or emphasize_lines:
            sb.append("</div>\n")
