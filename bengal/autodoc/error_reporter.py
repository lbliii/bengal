"""
Template error reporting and diagnostics system.

Provides comprehensive error reporting for template rendering failures
with detailed context and debugging information.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateErrorReporter:
    """Collect, analyze, and report template rendering errors."""

    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.stats: dict[str, int] = {
            "total_renders": 0,
            "successful_renders": 0,
            "failed_renders": 0,
            "fallback_renders": 0,
        }

    def record_success(self, template_name: str, element_name: str = "Unknown") -> None:
        """Record successful template render."""
        self.stats["total_renders"] += 1
        self.stats["successful_renders"] += 1

        logger.debug("template_render_success", template=template_name, element=element_name)

    def record_error(
        self,
        template_name: str,
        error: Exception,
        context: dict[str, Any],
        error_type: str = "unknown",
        used_fallback: bool = True,
    ) -> None:
        """
        Record template rendering error.

        Args:
            template_name: Name of template that failed
            error: Exception that occurred
            context: Template context at time of failure
            error_type: Category of error (syntax, undefined, etc.)
            used_fallback: Whether fallback content was generated
        """
        self.stats["total_renders"] += 1
        self.stats["failed_renders"] += 1
        if used_fallback:
            self.stats["fallback_renders"] += 1

        element = context.get("element")
        error_record = {
            "template": template_name,
            "error_type": error_type,
            "error_message": str(error),
            "error_class": type(error).__name__,
            "element_name": getattr(element, "name", "Unknown") if element else "Unknown",
            "element_type": (getattr(element, "element_type", "Unknown") if element else "Unknown"),
            "source_file": (
                str(getattr(element, "source_file", "Unknown")) if element else "Unknown"
            ),
            "context_keys": list(context.keys()),
            "used_fallback": used_fallback,
            "timestamp": datetime.now().isoformat(),
        }

        self.errors.append(error_record)

        logger.error(
            "template_render_error",
            template=template_name,
            error_type=error_type,
            error=str(error),
            element=error_record["element_name"],
            fallback=used_fallback,
        )

    def record_warning(
        self, template_name: str, message: str, context: dict[str, Any] | None = None
    ) -> None:
        """
        Record template rendering warning.

        Args:
            template_name: Name of template
            message: Warning message
            context: Optional template context
        """
        element = context.get("element") if context else None
        warning_record = {
            "template": template_name,
            "message": message,
            "element_name": getattr(element, "name", "Unknown") if element else "Unknown",
            "timestamp": datetime.now().isoformat(),
        }

        self.warnings.append(warning_record)

        logger.warning(
            "template_render_warning",
            template=template_name,
            warning_message=message,
            element=warning_record["element_name"],
        )

    def get_summary_report(self) -> str:
        """Generate human-readable summary report."""
        if not self.errors and not self.warnings:
            return f"✅ All {self.stats['total_renders']} templates rendered successfully"

        lines = []

        # Overall stats
        success_rate = (
            (self.stats["successful_renders"] / self.stats["total_renders"] * 100)
            if self.stats["total_renders"] > 0
            else 0
        )

        lines.append("📊 Template Rendering Summary:")
        lines.append(f"   Total renders: {self.stats['total_renders']}")
        lines.append(f"   Successful: {self.stats['successful_renders']}")
        lines.append(f"   Failed: {self.stats['failed_renders']}")
        lines.append(f"   Fallbacks used: {self.stats['fallback_renders']}")
        lines.append(f"   Success rate: {success_rate:.1f}%")
        lines.append("")

        # Error details
        if self.errors:
            lines.append(f"❌ {len(self.errors)} Template Errors:")

            # Group errors by type
            error_types: dict[str, list[dict[str, Any]]] = {}
            for error in self.errors:
                error_type = error["error_type"]
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append(error)

            for error_type, type_errors in error_types.items():
                lines.append(f"   {error_type}: {len(type_errors)} errors")
                for error in type_errors[:3]:  # Show first 3 of each type
                    lines.append(
                        f"     - {error['template']} ({error['element_name']}): {error['error_message'][:80]}..."
                    )
                if len(type_errors) > 3:
                    lines.append(f"     ... and {len(type_errors) - 3} more")
            lines.append("")

        # Warning details
        if self.warnings:
            lines.append(f"⚠️ {len(self.warnings)} Template Warnings:")
            for warning in self.warnings[:5]:  # Show first 5 warnings
                lines.append(f"   - {warning['template']}: {warning['message']}")
            if len(self.warnings) > 5:
                lines.append(f"   ... and {len(self.warnings) - 5} more warnings")

        return "\n".join(lines)

    def get_detailed_report(self) -> str:
        """Generate detailed error report for debugging."""
        if not self.errors:
            return "No template errors to report."

        lines = []
        lines.append("🔍 Detailed Template Error Report")
        lines.append("=" * 50)
        lines.append("")

        for i, error in enumerate(self.errors, 1):
            lines.append(f"Error #{i}: {error['template']}")
            lines.append(f"  Element: {error['element_name']} ({error['element_type']})")
            lines.append(f"  Source: {error['source_file']}")
            lines.append(f"  Error Type: {error['error_type']}")
            lines.append(f"  Error Class: {error['error_class']}")
            lines.append(f"  Message: {error['error_message']}")
            lines.append(f"  Context Keys: {', '.join(error['context_keys'])}")
            lines.append(f"  Fallback Used: {error['used_fallback']}")
            lines.append(f"  Timestamp: {error['timestamp']}")
            lines.append("")

        return "\n".join(lines)

    def export_errors_json(self, output_path: Path) -> None:
        """
        Export errors to JSON file for analysis.

        Args:
            output_path: Path to write JSON report
        """
        report_data = {
            "summary": self.stats,
            "errors": self.errors,
            "warnings": self.warnings,
            "generated_at": datetime.now().isoformat(),
        }

        output_path.write_text(json.dumps(report_data, indent=2))
        logger.info("template_error_report_exported", path=str(output_path))

    def get_most_common_errors(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get most common error types and templates.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of error summaries sorted by frequency
        """
        # Count errors by template
        template_errors = {}
        for error in self.errors:
            template = error["template"]
            if template not in template_errors:
                template_errors[template] = {
                    "template": template,
                    "count": 0,
                    "error_types": set(),
                    "elements": set(),
                }
            template_errors[template]["count"] += 1
            template_errors[template]["error_types"].add(error["error_type"])
            template_errors[template]["elements"].add(error["element_name"])

        # Convert sets to lists and sort by count
        result = []
        for template_data in template_errors.values():
            template_data["error_types"] = list(template_data["error_types"])
            template_data["elements"] = list(template_data["elements"])
            result.append(template_data)

        return sorted(result, key=lambda x: x["count"], reverse=True)[:limit]

    def clear(self) -> None:
        """Clear all recorded errors, warnings, and stats."""
        self.errors.clear()
        self.warnings.clear()
        self.stats = {
            "total_renders": 0,
            "successful_renders": 0,
            "failed_renders": 0,
            "fallback_renders": 0,
        }

    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings have been recorded."""
        return len(self.warnings) > 0

    def get_error_count(self) -> int:
        """Get total number of errors recorded."""
        return len(self.errors)

    def get_success_rate(self) -> float:
        """Get success rate as percentage (0-100)."""
        if self.stats["total_renders"] == 0:
            return 100.0
        return (self.stats["successful_renders"] / self.stats["total_renders"]) * 100
