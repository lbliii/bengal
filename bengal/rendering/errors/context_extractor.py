"""
SourceContextExtractor — read template source and build error context.

Extracted from ``TemplateRenderError._extract_context`` (Sprint A1.2) per
``plan/rfc-template-error-codes.md``. The extractor performs the I/O
work the classifier deliberately avoids: it reads the template file,
slices the surrounding lines, and packages a
:class:`TemplateErrorContext` for downstream display.

Related Modules:
- bengal.rendering.errors.classifier:    ErrorClassifier (pure, no I/O)
- bengal.rendering.errors.context:       TemplateErrorContext dataclass
- bengal.rendering.errors.exceptions:    Legacy TemplateRenderError (delegates here)
"""

from __future__ import annotations

import re
import traceback
from typing import TYPE_CHECKING, Any

from .classifier import find_first_code_line
from .context import TemplateErrorContext

if TYPE_CHECKING:
    from pathlib import Path

# Identifiers that are commonly registered globals/builtins — excluded from
# the "suspect callables" list so we don't flag obvious safe names like
# ``len``, ``range``, or Jinja control-flow keywords.
_KNOWN_SAFE_CALLABLES: frozenset[str] = frozenset(
    {
        # Builtins
        "range",
        "len",
        "dict",
        "list",
        "str",
        "int",
        "float",
        "bool",
        "set",
        "tuple",
        "enumerate",
        "zip",
        "sorted",
        "reversed",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "type",
        "isinstance",
        "getattr",
        "hasattr",
        "callable",
        "print",
        "super",
        # Jinja/template builtins
        "loop",
        "self",
        "caller",
        # Control flow
        "if",
        "else",
        "elif",
        "for",
        "endfor",
        "endif",
        "block",
        "endblock",
        "macro",
        "endmacro",
        "call",
        "endcall",
        "include",
        "import",
        "from",
        "extends",
        "with",
        "endwith",
    }
)

# {{ func( ... }} — function calls inside expression delimiters.
_FUNC_CALL_PATTERN = re.compile(r"\{\{[^}]*\b(\w+)\s*\([^}]*\}\}")
# | filter — filter applications anywhere on a line.
_FILTER_PATTERN = re.compile(r"\|\s*(\w+)")


class SourceContextExtractor:
    """Read template source and build a :class:`TemplateErrorContext`.

    Performs file I/O and traceback inspection. Stateless and reusable
    — a single instance can extract context for any number of errors.
    """

    def extract(
        self, error: Exception, template_name: str, template_engine: Any
    ) -> TemplateErrorContext:
        """Build context for ``error`` raised while rendering ``template_name``.

        Mirrors the behaviour of the legacy
        ``TemplateRenderError._extract_context`` static method: pulls
        ``lineno``/``filename`` from the exception when present, falls
        back to traceback walking for ``TypeError``, then reads the
        template file (when discoverable) and slices ±3 surrounding
        lines.
        """
        line_number = getattr(error, "lineno", None)
        filename = getattr(error, "filename", None) or template_name

        if isinstance(error, TypeError) and line_number is None:
            line_number, filename = self._refine_typeerror_location(error, filename)

        template_path = template_engine._find_template_path(filename)

        source_line: str | None = None
        surrounding_lines: list[tuple[int, str]] = []

        if template_path and template_path.exists():
            try:
                with open(template_path, encoding="utf-8") as fh:
                    lines = fh.readlines()

                # If the engine reports line 1 but the file starts with a
                # comment, the line info was lost in compilation — re-find.
                if line_number == 1 and lines:
                    first_line = lines[0].strip()
                    if first_line.startswith(("{#", "#")):
                        line_number = find_first_code_line(lines, error)

                if line_number and 1 <= line_number <= len(lines):
                    source_line = lines[line_number - 1].rstrip()
                    start = max(0, line_number - 4)
                    end = min(len(lines), line_number + 3)
                    surrounding_lines.extend((i + 1, lines[i].rstrip()) for i in range(start, end))
            except OSError, IndexError:
                pass

        return TemplateErrorContext(
            template_name=filename,
            line_number=line_number,
            column=None,
            source_line=source_line,
            surrounding_lines=surrounding_lines,
            template_path=template_path,
        )

    @staticmethod
    def _refine_typeerror_location(
        error: TypeError, fallback_filename: str
    ) -> tuple[int | None, str]:
        """Walk a TypeError traceback for the most-recent template frame."""
        line_number: int | None = None
        filename = fallback_filename

        tb = traceback.extract_tb(error.__traceback__)
        for frame in reversed(tb):
            if "templates/" in frame.filename or frame.filename.endswith(".html"):
                line_number = frame.lineno
                if "templates/" in frame.filename:
                    parts = frame.filename.split("templates/")
                    if len(parts) > 1:
                        filename = parts[-1]
                break
            # Jinja/Kida internal frames carry no useful line info — skip
            # past them and keep looking.
            if "jinja2" in frame.filename.lower() or "kida" in frame.filename.lower():
                continue

        return line_number, filename


def scan_template_for_callables(template_path: Path) -> list[str]:
    """Scan a template file for likely-None callable suspects.

    Returns the list of `function 'name'` / `filter 'name'` strings that
    appear in the template and are *not* in the known-safe set. Used by
    the suggestion engine to enrich `TypeError: 'NoneType' is not
    callable` messages.

    Free function rather than a class method — scanning is a one-shot
    string operation with no instance state to share.
    """
    try:
        with open(template_path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return []

    suspects: list[str] = []

    for match in _FUNC_CALL_PATTERN.finditer(content):
        func_name = match.group(1)
        if func_name.lower() not in _KNOWN_SAFE_CALLABLES:
            suspects.append(f"function '{func_name}'")

    for match in _FILTER_PATTERN.finditer(content):
        filter_name = match.group(1)
        if filter_name.lower() not in _KNOWN_SAFE_CALLABLES:
            suspects.append(f"filter '{filter_name}'")

    return suspects


__all__ = [
    "SourceContextExtractor",
    "scan_template_for_callables",
]
