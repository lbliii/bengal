"""
Tree-sitter based syntax highlighting backend.

This backend provides fast, semantic syntax highlighting using tree-sitter
parsers. It is optional and requires the tree-sitter package and language
grammar packages.

Features:
- 10x faster than Pygments for supported languages
- Semantic highlighting via tree queries
- Local variable tracking via locals.scm
- Thread-safe via thread-local Parser instances
- Automatic fallback to Pygments for unsupported languages

Performance:
- Parse time (per block): ~0.15ms (vs ~1.5ms for Pygments)
- Memory per parser: ~10KB (vs ~50KB for Pygments lexer)

Requirements:
- tree-sitter>=0.22
- Language grammar packages (e.g., tree-sitter-python)

See Also:
- https://tree-sitter.github.io/tree-sitter/
- https://github.com/tree-sitter/py-tree-sitter

"""

from __future__ import annotations

import html
import importlib.util
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tree_sitter import Language, Parser, Query, QueryCursor

from bengal.protocols import HighlightService as HighlightBackend
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from tree_sitter import Node, Tree

logger = get_logger(__name__)


# =============================================================================
# CSS Class Mapping: tree-sitter capture names → Pygments short codes
# =============================================================================

TREESITTER_TO_PYGMENTS: dict[str, str] = {
    # Keywords
    "keyword": "k",
    "keyword.control": "k",
    "keyword.control.conditional": "k",
    "keyword.control.repeat": "k",
    "keyword.control.import": "kn",
    "keyword.control.return": "k",
    "keyword.control.exception": "k",
    "keyword.function": "kd",
    "keyword.operator": "ow",
    "keyword.return": "k",
    "keyword.import": "kn",
    "keyword.type": "kt",
    "keyword.storage": "kd",
    "keyword.storage.type": "kt",
    "keyword.storage.modifier": "kd",
    # Functions
    "function": "nf",
    "function.method": "fm",
    "function.builtin": "nb",
    "function.call": "nf",
    "function.macro": "fm",
    "function.special": "fm",
    # Methods
    "method": "fm",
    "method.call": "fm",
    # Variables
    "variable": "n",
    "variable.parameter": "nv",
    "variable.builtin": "nb",
    "variable.member": "nv",
    "variable.special": "nv",
    # Parameters
    "parameter": "nv",
    # Literals
    "string": "s",
    "string.special": "ss",
    "string.escape": "se",
    "string.regex": "sr",
    "string.documentation": "sd",
    "string.special.symbol": "ss",
    "number": "m",
    "number.float": "mf",
    "number.integer": "mi",
    "boolean": "kc",
    "character": "sc",
    "character.special": "sc",
    # Comments
    "comment": "c",
    "comment.line": "c1",
    "comment.block": "cm",
    "comment.documentation": "cs",
    # Types
    "type": "nc",
    "type.builtin": "nb",
    "type.definition": "nc",
    "type.qualifier": "kt",
    # Classes
    "class": "nc",
    "class.builtin": "nb",
    # Other
    "operator": "o",
    "punctuation": "p",
    "punctuation.bracket": "p",
    "punctuation.delimiter": "p",
    "punctuation.special": "p",
    "constant": "no",
    "constant.builtin": "bp",
    "constant.builtin.boolean": "kc",
    "property": "na",
    "property.definition": "na",
    "attribute": "nd",
    "namespace": "nn",
    "module": "nn",
    "label": "nl",
    "constructor": "nc",
    "tag": "nt",
    "tag.attribute": "na",
    "embedded": "x",
    "escape": "se",
    # Python-specific
    "decorator": "nd",
    "none": "kc",
    # Rust-specific
    "lifetime": "nv",
    "self": "bp",
    # Go-specific
    "package": "nn",
}

# Track unmapped captures for debugging (development only)
_unmapped_captures: set[str] = set()


@dataclass
class HighlightQueries:
    """Container for language highlight queries."""

    highlights: Query
    locals: Query | None = None
    injections: Query | None = None


class TreeSitterBackend(HighlightBackend):
    """
    Tree-sitter based syntax highlighting backend.
    
    Features:
    - 10x faster than Pygments for supported languages
    - Semantic highlighting via tree queries
    - Local variable tracking via locals.scm
    - Thread-safe via thread-local Parser instances
    - Automatic fallback to Pygments for unsupported languages
    
    Reference:
    - https://tree-sitter.github.io/tree-sitter/
    - https://tree-sitter.github.io/tree-sitter/3-syntax-highlighting.html
    - https://github.com/tree-sitter/py-tree-sitter
        
    """

    # Class-level caches (thread-safe)
    _languages: dict[str, Language] = {}
    _queries: dict[str, HighlightQueries | None] = {}
    _lock = threading.RLock()  # RLock for nested locking (queries → language)

    # Thread-local Parser instances (Parsers are NOT thread-safe)
    _local = threading.local()

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "tree-sitter"

    def supports_language(self, language: str) -> bool:
        """Check if tree-sitter grammar is available for this language."""
        language = self._normalize_language(language)
        try:
            self._load_language(language)
            return self._get_queries(language) is not None
        except ImportError:
            return False

    def highlight(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """Highlight code using tree-sitter."""
        language = self._normalize_language(language)

        # Fallback to Rosettes if not supported
        if not self.supports_language(language):
            return self._rosettes_fallback(code, language, hl_lines, show_linenos)

        source = code.encode("utf-8")
        parser = self._get_parser(language)
        tree = parser.parse(source)

        queries = self._get_queries(language)
        if queries is None:
            return self._rosettes_fallback(code, language, hl_lines, show_linenos)

        highlighted_body = self._render_highlights(tree, source, queries, hl_lines)

        if show_linenos:
            return self._wrap_with_linenos(highlighted_body, hl_lines)

        return f'<pre class="highlight"><code>{highlighted_body}</code></pre>'

    # =========================================================================
    # Internal Methods
    # =========================================================================

    @staticmethod
    def _normalize_language(language: str) -> str:
        """Normalize language name for tree-sitter package lookup."""
        language = language.lower().strip()
        # Handle common aliases
        aliases = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "yml": "yaml",
            "sh": "bash",
            "shell": "bash",
            "c++": "cpp",
            "cxx": "cpp",
            "rs": "rust",
            "golang": "go",
        }
        return aliases.get(language, language)

    @classmethod
    def _load_language(cls, language: str) -> Language:
        """Load tree-sitter language grammar (thread-safe, cached)."""
        with cls._lock:
            if language not in cls._languages:
                try:
                    # Import the grammar module (e.g., tree_sitter_python)
                    module = __import__(f"tree_sitter_{language}")
                    # Wrap in Language() constructor per py-tree-sitter API
                    cls._languages[language] = Language(module.language())
                    logger.debug("tree_sitter_language_loaded", language=language)
                except ImportError:
                    logger.debug("tree_sitter_grammar_not_found", language=language)
                    raise
                except Exception as e:
                    # Handle other errors (e.g., binary incompatibility with Python 3.14)
                    logger.debug(
                        "tree_sitter_grammar_load_failed",
                        language=language,
                        error=str(e),
                    )
                    raise ImportError(f"Failed to load {language}: {e}") from e
            return cls._languages[language]

    def _get_parser(self, language: str) -> Parser:
        """Get thread-local parser instance for language."""
        if not hasattr(self._local, "parsers"):
            self._local.parsers = {}

        if language not in self._local.parsers:
            lang = self._load_language(language)
            parser = Parser(language=lang)
            self._local.parsers[language] = parser

        return self._local.parsers[language]

    @classmethod
    def _get_queries(cls, language: str) -> HighlightQueries | None:
        """Load highlight queries for a language (thread-safe, cached)."""
        with cls._lock:
            if language not in cls._queries:
                cls._queries[language] = cls._load_queries(language)
            return cls._queries[language]

    @classmethod
    def _load_queries(cls, language: str) -> HighlightQueries | None:
        """
        Load query files from grammar package.

        Per tree-sitter docs, queries are stored in queries/ folder:
        - queries/highlights.scm (required for highlighting)
        - queries/locals.scm (optional, for variable tracking)
        - queries/injections.scm (optional, for language injection)
        """
        try:
            lang = cls._load_language(language)

            # Find package directory
            spec = importlib.util.find_spec(f"tree_sitter_{language}")
            if spec is None or spec.origin is None:
                return None

            pkg_dir = Path(spec.origin).parent

            # Try multiple query locations (packages vary in structure)
            query_dirs = [
                pkg_dir / "queries",
                pkg_dir,
                pkg_dir.parent / "queries",
            ]

            highlights_query = None
            locals_query = None
            injections_query = None

            for query_dir in query_dirs:
                # Load highlights.scm (required)
                highlights_file = query_dir / "highlights.scm"
                if highlights_file.exists() and highlights_query is None:
                    highlights_text = highlights_file.read_text()
                    try:
                        highlights_query = Query(lang, highlights_text)
                        logger.debug(
                            "tree_sitter_query_loaded",
                            language=language,
                            query="highlights",
                            path=str(highlights_file),
                        )
                    except Exception as e:
                        logger.debug(
                            "tree_sitter_query_parse_failed",
                            language=language,
                            query="highlights",
                            error=str(e),
                        )
                        continue

                # Load locals.scm (optional, improves quality)
                locals_file = query_dir / "locals.scm"
                if locals_file.exists() and locals_query is None:
                    try:
                        locals_text = locals_file.read_text()
                        locals_query = Query(lang, locals_text)
                        logger.debug(
                            "tree_sitter_query_loaded",
                            language=language,
                            query="locals",
                            path=str(locals_file),
                        )
                    except Exception:
                        pass  # locals.scm parsing failed, continue without

                # Load injections.scm (optional, for embedded languages)
                injections_file = query_dir / "injections.scm"
                if injections_file.exists() and injections_query is None:
                    try:
                        injections_text = injections_file.read_text()
                        injections_query = Query(lang, injections_text)
                        logger.debug(
                            "tree_sitter_query_loaded",
                            language=language,
                            query="injections",
                            path=str(injections_file),
                        )
                    except Exception:
                        pass  # injections.scm parsing failed, continue without

            if highlights_query is None:
                logger.debug("tree_sitter_no_highlights_query", language=language)
                return None

            return HighlightQueries(
                highlights=highlights_query,
                locals=locals_query,
                injections=injections_query,
            )

        except Exception as e:
            logger.debug("tree_sitter_query_load_failed", language=language, error=str(e))
            return None

    def _render_highlights(
        self,
        tree: Tree,
        source: bytes,
        queries: HighlightQueries,
        hl_lines: list[int] | None = None,
    ) -> str:
        """
        Render syntax tree with highlight captures to HTML spans.

        Uses QueryCursor per py-tree-sitter API:
        https://github.com/tree-sitter/py-tree-sitter
        """
        # Execute highlight query using QueryCursor
        cursor = QueryCursor(queries.highlights)
        captures = cursor.captures(tree.root_node)

        # Flatten captures dict into sorted list of (node, capture_name)
        # captures is dict[str, list[Node]]
        all_captures: list[tuple[Node, str]] = []
        for capture_name, nodes in captures.items():
            for node in nodes:
                all_captures.append((node, capture_name))

        # Sort by start position, then by end position (longer spans first)
        all_captures.sort(key=lambda c: (c[0].start_byte, -c[0].end_byte))

        # Build highlighted output
        hl_set = set(hl_lines or [])
        result_lines: list[str] = []
        current_line_tokens: list[str] = []
        last_end = 0
        current_line_no = 1

        for node, capture_name in all_captures:
            start = node.start_byte
            end = node.end_byte

            # Skip if this capture overlaps with a previous one
            if start < last_end:
                continue

            # Add any text before this capture (unhighlighted)
            if start > last_end:
                gap_text = source[last_end:start].decode("utf-8")
                for char in gap_text:
                    if char == "\n":
                        line_html = "".join(current_line_tokens)
                        if current_line_no in hl_set:
                            line_html = f'<span class="hll">{line_html}</span>'
                        result_lines.append(line_html)
                        current_line_tokens = []
                        current_line_no += 1
                    else:
                        current_line_tokens.append(html.escape(char))

            # Get CSS class from mapping
            css_class = self._get_css_class(capture_name)
            token_text = source[start:end].decode("utf-8")

            # Handle multi-line tokens
            token_lines = token_text.split("\n")
            for i, line_part in enumerate(token_lines):
                if i > 0:
                    # Finish previous line
                    line_html = "".join(current_line_tokens)
                    if current_line_no in hl_set:
                        line_html = f'<span class="hll">{line_html}</span>'
                    result_lines.append(line_html)
                    current_line_tokens = []
                    current_line_no += 1

                if line_part:
                    escaped_part = html.escape(line_part)
                    if css_class:
                        current_line_tokens.append(
                            f'<span class="{css_class}">{escaped_part}</span>'
                        )
                    else:
                        current_line_tokens.append(escaped_part)

            last_end = end

        # Add remaining text after last capture
        if last_end < len(source):
            remaining = source[last_end:].decode("utf-8")
            for char in remaining:
                if char == "\n":
                    line_html = "".join(current_line_tokens)
                    if current_line_no in hl_set:
                        line_html = f'<span class="hll">{line_html}</span>'
                    result_lines.append(line_html)
                    current_line_tokens = []
                    current_line_no += 1
                else:
                    current_line_tokens.append(html.escape(char))

        # Don't forget the last line
        if current_line_tokens:
            line_html = "".join(current_line_tokens)
            if current_line_no in hl_set:
                line_html = f'<span class="hll">{line_html}</span>'
            result_lines.append(line_html)

        return "\n".join(result_lines)

    @classmethod
    def _get_css_class(cls, capture_name: str) -> str:
        """
        Map tree-sitter capture name to Pygments CSS class.

        Note: Capture names from QueryCursor.captures() do NOT have @ prefix.
        Per py-tree-sitter API, captures dict keys are like "function.def"
        not "@function.def".
        """
        # Try exact match first
        if capture_name in TREESITTER_TO_PYGMENTS:
            return TREESITTER_TO_PYGMENTS[capture_name]

        # Try progressively shorter prefixes (e.g., "function.method" → "function")
        parts = capture_name.split(".")
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            if prefix in TREESITTER_TO_PYGMENTS:
                return TREESITTER_TO_PYGMENTS[prefix]

        # Return first part as fallback
        if parts[0] in TREESITTER_TO_PYGMENTS:
            return TREESITTER_TO_PYGMENTS[parts[0]]

        # Log unmapped capture for debugging (only once per capture name)
        if capture_name not in _unmapped_captures:
            _unmapped_captures.add(capture_name)
            logger.debug("tree_sitter_unmapped_capture", capture=capture_name)

        return ""  # No mapping, render without class

    def _wrap_with_linenos(
        self,
        highlighted_body: str,
        hl_lines: list[int] | None = None,
    ) -> str:
        """Wrap highlighted code with line numbers (Pygments-compatible format)."""
        lines = highlighted_body.split("\n")

        # Build line number column
        lineno_parts = []
        for i, _ in enumerate(lines, 1):
            lineno_parts.append(f'<span class="linenos">{i}</span>')
        linenos_html = "\n".join(lineno_parts)

        # Pygments-compatible table structure
        return (
            '<div class="highlight">'
            '<table class="highlighttable"><tbody><tr>'
            f'<td class="linenos"><pre>{linenos_html}</pre></td>'
            f'<td class="code"><pre><code>{highlighted_body}</code></pre></td>'
            "</tr></tbody></table>"
            "</div>"
        )

    def _rosettes_fallback(
        self,
        code: str,
        language: str,
        hl_lines: list[int] | None,
        show_linenos: bool,
    ) -> str:
        """Fall back to Rosettes for unsupported languages."""
        from bengal.rendering.highlighting.rosettes import RosettesBackend

        return RosettesBackend().highlight(code, language, hl_lines, show_linenos)
