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

import traceback
from typing import Any

from bengal.errors.template_callables import scan_template_for_callables

from .classifier import find_first_code_line
from .context import TemplateErrorContext


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


__all__ = [
    "SourceContextExtractor",
    "scan_template_for_callables",
]
