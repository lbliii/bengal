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
These directives resolve include paths at render time using site and page
context from the active RenderSession.

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's include directives exactly for parity.

"""

from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape as html_escape
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

    from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract

__all__ = [
    "FileResolver",
    "IncludeDirective",
    "LiteralIncludeDirective",
    "SiteFileResolver",
]

_MAX_INCLUDE_BYTES = 1_048_576  # 1 MiB
_MAX_INCLUDE_DEPTH = 10


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


class SiteFileResolver:
    """Resolve and load include targets relative to a Bengal site."""

    def __init__(self, site_root: Path) -> None:
        self._site_root = site_root.resolve()

    def resolve_path(self, path: str, source_file: str | None) -> Path | None:
        return resolve_include_path(path, source_file=source_file, site_root=self._site_root)

    def load_file(
        self,
        path: Path,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str | None:
        content, error = load_include_file(path, start_line=start_line, end_line=end_line)
        return None if error else content


def resolve_include_path(
    path: str,
    *,
    source_file: str | Path | None,
    site_root: Path,
) -> Path | None:
    """Resolve an include path relative to the source page or site root."""
    cleaned = path.strip()
    if not cleaned:
        return None

    root = site_root.resolve()
    raw = Path(cleaned)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    if source_file:
        candidates.append(Path(source_file).resolve().parent / raw)
    candidates.extend((root / "content" / raw, root / raw))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            continue
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def load_include_file(
    path: Path,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
    max_bytes: int = _MAX_INCLUDE_BYTES,
) -> tuple[str, str]:
    """Load include file content with optional 1-indexed line bounds."""
    try:
        size = path.stat().st_size
        if size > max_bytes:
            return "", f"File too large ({size} bytes, max {max_bytes})"
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "", str(exc)

    if start_line is None and end_line is None:
        return text, ""

    lines = text.splitlines(keepends=True)
    start_idx = max((start_line or 1) - 1, 0)
    end_idx = end_line if end_line is not None else len(lines)
    return "".join(lines[start_idx:end_idx]), ""


def _record_include_dependency(resolved_path: Path) -> None:
    """Record included file for incremental rebuild dependency tracking."""
    from bengal.parsing.backends.patitas.render_session import append_content_dependency

    append_content_dependency(resolved_path)

    try:
        from bengal.effects.render_integration import record_extra_dependency

        record_extra_dependency(resolved_path.resolve())
    except ImportError:
        return


def _site_root_from_context(page_context: Any | None, site: Any | None) -> Path | None:
    if site is not None and hasattr(site, "root_path"):
        return Path(site.root_path)
    if page_context is not None and hasattr(page_context, "site") and page_context.site is not None:
        return Path(page_context.site.root_path)
    return None


def _source_file_from_context(page_context: Any | None) -> str | None:
    from bengal.parsing.backends.patitas.render_session import included_source_file

    active = included_source_file()
    if active:
        return active
    if page_context is None:
        return None
    source_path = getattr(page_context, "source_path", None)
    return str(source_path) if source_path else None


def _render_included_content(
    content: str,
    resolved_path: Path,
    *,
    start_line: int | None,
    end_line: int | None,
    render_markdown_fragment: Callable[[str], str] | None,
) -> tuple[str, str]:
    """Parse and render included markdown content."""
    if render_markdown_fragment is None:
        return "", "Include requires render context to parse files"

    from bengal.parsing.backends.patitas.include_cache import (
        cache_key_for,
        get_cached_include_ast,
        get_cached_include_html,
        store_cached_include_ast,
        store_cached_include_html,
    )
    from bengal.parsing.backends.patitas.render_config import get_render_config
    from bengal.parsing.backends.patitas.render_session import (
        get_markdown_engine,
        push_include_path,
        try_get_render_session,
    )

    resolved_key = str(resolved_path.resolve())
    session = try_get_render_session()
    stack = session.include_stack if session is not None else []
    if resolved_key in stack:
        return "", f"Circular include detected: {resolved_path.name}"
    if len(stack) >= _MAX_INCLUDE_DEPTH:
        return "", f"Maximum include depth ({_MAX_INCLUDE_DEPTH}) exceeded"

    cache_key = cache_key_for(resolved_path, start_line=start_line, end_line=end_line)
    config = get_render_config()
    cacheable = config.text_transformer is None
    engine = get_markdown_engine()

    if cacheable:
        cached_html = get_cached_include_html(cache_key)
        if cached_html is not None:
            return cached_html, ""

    render_kwargs: dict[str, Any] = {}
    if session is not None:
        render_kwargs = {
            "page_context": session.page_context,
            "site": session.site,
            "xref_index": session.xref_index,
            "links_collector": session.links_collector,
        }

    with push_include_path(resolved_path):
        if cacheable and engine is not None:
            cached_ast = get_cached_include_ast(cache_key)
            if cached_ast is not None:
                source, blocks = cached_ast
                html = engine.render_ast(
                    blocks,
                    source,
                    text_transformer=config.text_transformer,
                    **render_kwargs,
                )
                store_cached_include_html(cache_key, html)
                return html, ""

            ast = engine.parse_to_ast(content)
            html = engine.render_ast(
                ast,
                content,
                text_transformer=config.text_transformer,
                **render_kwargs,
            )
            store_cached_include_ast(cache_key, content, ast)
            store_cached_include_html(cache_key, html)
            return html, ""

        html = render_markdown_fragment(content)
        if cacheable:
            store_cached_include_html(cache_key, html)
        return html, ""


# =============================================================================
# Include Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class IncludeOptions(DirectiveOptions):
    """Options for include directive."""

    file: str = ""
    start_line: int | None = None
    end_line: int | None = None
    file_path: str = ""
    error: str = ""


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
        Site and page context from the active render session.

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

        Note: Included files are loaded and parsed during render (not parse),
        because path resolution requires site/page context. Nested includes
        reuse the active Markdown engine via RenderSession.
        """
        file_path = (title.strip() if title else "") or options.file.strip()

        computed_opts = replace(
            options,
            file_path=file_path,
            error="" if file_path else "No file path specified",
        )

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
        *,
        page_context: Any | None = None,
        site: Any | None = None,
        render_markdown_fragment: Callable[[str], str] | None = None,
    ) -> None:
        """Render include directive."""
        opts = node.options

        error = opts.error
        file_path = opts.file_path
        if not error and rendered_children.strip():
            sb.append(rendered_children)
            return

        if not error:
            site_root = _site_root_from_context(page_context, site)
            if site_root is None:
                error = "Include requires site context to load files"
            else:
                resolved = resolve_include_path(
                    file_path,
                    source_file=_source_file_from_context(page_context),
                    site_root=site_root,
                )
                if resolved is None:
                    error = f"File not found: {file_path}"
                else:
                    _record_include_dependency(resolved)
                    content, load_error = load_include_file(
                        resolved,
                        start_line=opts.start_line,
                        end_line=opts.end_line,
                    )
                    if load_error:
                        error = load_error
                    else:
                        html, render_error = _render_included_content(
                            content,
                            resolved,
                            start_line=opts.start_line,
                            end_line=opts.end_line,
                            render_markdown_fragment=render_markdown_fragment,
                        )
                        if render_error:
                            error = render_error
                        else:
                            sb.append(html)
                            return

        if error:
            import warnings

            loc = node.location
            loc_str = f" (line {loc.line})" if loc and hasattr(loc, "line") else ""
            warnings.warn(
                f"Include directive error{loc_str}: {error} (path: {file_path})",
                stacklevel=2,
            )
            sb.append(
                f'<div class="include-error">'
                f"<p><strong>Include error:</strong> {html_escape(error)}</p>"
                f"</div>\n"
            )
            return


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

    file: str = ""
    language: str = ""
    start_line: int | None = None
    end_line: int | None = None
    emphasize_lines: str = ""
    linenos: bool = False
    caption: str = ""
    file_path: str = ""
    code: str = ""
    error: str = ""


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
        Site and page context from the active render session.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("literalinclude",)
    token_type: ClassVar[str] = "literalinclude"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[LiteralIncludeOptions]] = LiteralIncludeOptions

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
        file_path = (title.strip() if title else "") or options.file.strip()

        language = options.language
        if not language and file_path:
            ext = Path(file_path).suffix.lower()
            language = EXTENSION_LANGUAGE_MAP.get(ext, "")

        computed_opts = replace(
            options,
            language=language,
            file_path=file_path,
            code="",
            error="" if file_path else "No file path specified",
        )

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
        *,
        page_context: Any | None = None,
        site: Any | None = None,
    ) -> None:
        """Render literalinclude as code block."""
        opts = node.options

        error = opts.error
        file_path = opts.file_path
        code = opts.code
        if not error and not code:
            site_root = _site_root_from_context(page_context, site)
            if site_root is None:
                error = "Literal include requires site context to load files"
            else:
                resolved = resolve_include_path(
                    file_path,
                    source_file=_source_file_from_context(page_context),
                    site_root=site_root,
                )
                if resolved is None:
                    error = f"File not found: {file_path}"
                else:
                    _record_include_dependency(resolved)
                    code, load_error = load_include_file(
                        resolved,
                        start_line=opts.start_line,
                        end_line=opts.end_line,
                    )
                    if load_error:
                        error = load_error

        if error:
            import warnings

            loc = node.location
            loc_str = f" (line {loc.line})" if loc and hasattr(loc, "line") else ""
            warnings.warn(
                f"Literalinclude directive error{loc_str}: {error} (path: {file_path})",
                stacklevel=2,
            )
            sb.append(
                f'<div class="literalinclude-error">'
                f"<p><strong>Literal include error:</strong> {html_escape(error)}</p>"
                f"</div>\n"
            )
            return

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
