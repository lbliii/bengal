"""Kida template listing, syntax validation, and static security analysis."""

from __future__ import annotations

from typing import Any

from kida.environment import (
    TemplateNotFoundError as KidaTemplateNotFoundError,
)
from kida.environment import (
    TemplateSyntaxError as KidaTemplateSyntaxError,
)

from bengal.rendering.engines.errors import TemplateError


def list_templates(engine: Any) -> list[str]:
    """List all available template names.

    Returns:
        Sorted list of template names
    """
    templates = set()

    for base in engine.template_dirs:
        if base.is_dir():
            for path in base.rglob("*.html"):
                templates.add(str(path.relative_to(base)))
            for path in base.rglob("*.xml"):
                templates.add(str(path.relative_to(base)))

    return sorted(templates)


def validate(
    engine: Any,
    patterns: list[str] | None = None,
) -> list[TemplateError]:
    """Validate templates for syntax errors.

    Args:
        patterns: Optional glob patterns to filter

    Returns:
        List of TemplateError for invalid templates
    """
    errors = []

    for name in engine.list_templates():
        # Filter by patterns if provided
        if patterns:
            from fnmatch import fnmatch

            if not any(fnmatch(name, p) for p in patterns):
                continue

        try:
            engine._env.get_template(name)
        except Exception as e:
            # Determine error type from exception class name
            exc_name = type(e).__name__.lower()
            if "syntax" in exc_name:
                error_type = "syntax"
            elif "undefined" in exc_name:
                error_type = "undefined"
            elif "runtime" in exc_name:
                error_type = "runtime"
            elif "notfound" in exc_name:
                error_type = "not_found"
            else:
                error_type = "other"
            errors.append(
                TemplateError(
                    template=name,
                    message=str(e),
                    line=getattr(e, "lineno", None),
                    error_type=error_type,
                )
            )

    return errors


def validate_security(
    engine: Any,
    patterns: list[str] | None = None,
) -> list[TemplateError]:
    """Run Kida static escape and privacy analysis for templates.

    This intentionally reports only warning/error findings, not every
    escaped output site, so authors get actionable trust-boundary feedback
    without a dump of normal autoescape facts.
    """
    from fnmatch import fnmatch

    from kida.analysis import audit_escaping, lint_privacy

    findings: list[TemplateError] = []

    for name in engine.list_templates():
        if patterns and not any(fnmatch(name, p) for p in patterns):
            continue

        try:
            template = engine._env.get_template(name)
        except KidaTemplateSyntaxError, KidaTemplateNotFoundError:
            # Syntax validation reports compile failures. Static analysis
            # only runs on templates Kida can parse.
            continue
        except Exception as e:
            findings.append(
                TemplateError(
                    template=name,
                    message=f"Kida static analysis failed: {e}",
                    error_type="kida_static_analysis",
                    severity="error",
                    original_exception=e,
                )
            )
            continue

        raw_findings = [
            *audit_escaping(template, include_output_sites=False),
            *lint_privacy(template),
        ]
        for finding in raw_findings:
            severity = getattr(finding, "severity", "warning")
            if severity == "info":
                continue
            findings.append(
                TemplateError(
                    template=getattr(finding, "template_name", name) or name,
                    message=getattr(finding, "message", str(finding)),
                    line=getattr(finding, "lineno", None),
                    column=getattr(finding, "col_offset", None),
                    error_type=getattr(finding, "kind", "kida_static_analysis"),
                    severity=severity,
                    suggestion=getattr(finding, "suggestion", None),
                    diagnostic_code=getattr(finding, "code", None),
                )
            )

    return findings
