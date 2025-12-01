"""
Safe template rendering system with Hugo-style error boundaries.

This module provides error-safe template rendering that prevents silent failures
and provides graceful fallbacks when templates encounter errors.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, TemplateError, TemplateNotFound, UndefinedError

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateRenderingError(Exception):
    """Exception raised when template rendering fails."""

    def __init__(self, template_name: str, original_error: Exception, context: dict | None = None):
        self.template_name = template_name
        self.original_error = original_error
        self.context = context or {}
        super().__init__(f"Template {template_name} failed: {original_error}")


class SafeTemplateRenderer:
    """Hugo-style safe template rendering with error boundaries and fallbacks."""

    def __init__(self, environment: Environment):
        """
        Initialize safe template renderer.

        Args:
            environment: Jinja2 environment configured with templates
        """
        self.env = environment
        self.error_count = 0
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def render_with_boundaries(self, template_name: str, context: dict) -> str:
        """
        Render template with error boundaries and fallbacks.

        Args:
            template_name: Name of template to render
            context: Template context variables

        Returns:
            Rendered template content or fallback content if rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(context)

        except TemplateNotFound as e:
            self._record_error(template_name, e, context, "template_not_found")
            return self._render_not_found_fallback(template_name, context)

        except UndefinedError as e:
            self._record_error(template_name, e, context, "undefined_variable")
            return self._render_undefined_fallback(template_name, context, e)

        except TemplateError as e:
            self._record_error(template_name, e, context, "template_syntax_error")
            return self._render_syntax_fallback(template_name, context, e)

        except Exception as e:
            self._record_error(template_name, e, context, "unexpected_error")
            return self._render_emergency_fallback(template_name, context, e)

    def _record_error(
        self, template_name: str, error: Exception, context: dict, error_type: str
    ) -> None:
        """Record template error for reporting."""
        self.error_count += 1
        element = context.get("element")

        error_record = {
            "template": template_name,
            "error_type": error_type,
            "error": str(error),
            "element_name": element.name if element and hasattr(element, "name") else "Unknown",
            "element_type": (
                element.element_type if element and hasattr(element, "element_type") else "Unknown"
            ),
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc(),
        }

        self.errors.append(error_record)
        logger.error(
            "template_rendering_failed",
            template=template_name,
            error_type=error_type,
            error=str(error),
            element_name=error_record["element_name"],
        )

    def _render_not_found_fallback(self, template_name: str, context: dict) -> str:
        """Generate fallback when template file is not found."""
        element = context.get("element")
        if not element:
            return self._render_emergency_fallback(template_name, context, None)

        return f"""# {getattr(element, "name", "Unknown")}

```{{error}}
Template Not Found: {template_name}
```

## Basic Information

**Type:** {getattr(element, "element_type", "Unknown")}
**Source:** {getattr(element, "source_file", "Unknown")}

{getattr(element, "description", "*No description available.*")}

*Note: Template file missing. This is fallback content.*
"""

    def _render_undefined_fallback(
        self, template_name: str, context: dict, error: UndefinedError
    ) -> str:
        """Generate fallback when template has undefined variables."""
        element = context.get("element")
        if not element:
            return self._render_emergency_fallback(template_name, context, error)

        return f"""# {getattr(element, "name", "Unknown")}

```{{warning}}
Template Variable Error: {template_name}
Undefined variable: {str(error)}
```

## Basic Information

**Type:** {getattr(element, "element_type", "Unknown")}
**Source:** {getattr(element, "source_file", "Unknown")}

{getattr(element, "description", "*No description available.*")}

*Note: Template has undefined variables. This is fallback content.*
"""

    def _render_syntax_fallback(
        self, template_name: str, context: dict, error: TemplateError
    ) -> str:
        """Generate fallback when template has syntax errors."""
        element = context.get("element")
        if not element:
            return self._render_emergency_fallback(template_name, context, error)

        return f"""# {getattr(element, "name", "Unknown")}

```{{error}}
Template Syntax Error: {template_name}
Error: {str(error)}
```

## Basic Information

**Type:** {getattr(element, "element_type", "Unknown")}
**Source:** {getattr(element, "source_file", "Unknown")}

{getattr(element, "description", "*No description available.*")}

*Note: Template has syntax errors. This is fallback content.*
"""

    def _render_emergency_fallback(
        self, template_name: str, context: dict, error: Exception | None
    ) -> str:
        """Last resort fallback when everything fails."""
        element = context.get("element")
        element_name = getattr(element, "name", "Unknown") if element else "Unknown"

        error_info = f"Error: {str(error)}" if error else "Critical rendering failure"

        return f"""# {element_name}

```{{error}}
Critical Template Error: {template_name}
{error_info}
```

*This is emergency fallback content. Please report this issue.*

**Debug Info:**
- Template: {template_name}
- Element: {element_name}
- Context keys: {list(context.keys()) if context else "None"}
"""

    def get_error_summary(self) -> str:
        """Generate human-readable error summary."""
        if not self.errors and not self.warnings:
            return "✅ All templates rendered successfully"

        summary_parts = []

        if self.errors:
            summary_parts.append(f"❌ {len(self.errors)} template errors:")
            for error in self.errors[:5]:  # Show first 5 errors
                summary_parts.append(
                    f"  - {error['template']} ({error['element_name']}): {error['error']}"
                )
            if len(self.errors) > 5:
                summary_parts.append(f"  ... and {len(self.errors) - 5} more errors")

        if self.warnings:
            summary_parts.append(f"⚠️ {len(self.warnings)} template warnings:")
            for warning in self.warnings[:3]:  # Show first 3 warnings
                summary_parts.append(f"  - {warning['template']}: {warning['message']}")

        return "\n".join(summary_parts)

    def clear_errors(self) -> None:
        """Clear recorded errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
        self.error_count = 0


class TemplateValidator:
    """Validate template syntax and structure before rendering."""

    def __init__(self, environment: Environment):
        self.env = environment

    def validate_template(self, template_name: str) -> list[str]:
        """
        Validate template for common issues.

        Args:
            template_name: Name of template to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        try:
            # Try to load and parse template
            template = self.env.get_template(template_name)

            # Check for common issues
            # Get template source - try different methods
            source = None
            if hasattr(template, "source"):
                source = template.source
            elif hasattr(template, "get_source"):
                try:
                    source_info = template.get_source(self.env, template.name)
                    source = source_info[0] if source_info else None
                except Exception:
                    pass

            if source:
                issues.extend(self._check_whitespace_issues(source))
                issues.extend(self._check_variable_usage(source))
                issues.extend(self._check_block_structure(source))

        except TemplateNotFound:
            issues.append(f"Template file not found: {template_name}")
        except TemplateError as e:
            issues.append(f"Template syntax error: {e}")
        except Exception as e:
            issues.append(f"Unexpected validation error: {e}")

        return issues

    def _check_whitespace_issues(self, source: str) -> list[str]:
        """Check for common whitespace issues."""
        issues = []

        if source.endswith(" \n"):
            issues.append("Template ends with trailing whitespace")

        if "\t" in source:
            issues.append("Template contains tabs (use spaces for consistency)")

        lines = source.split("\n")
        for i, line in enumerate(lines, 1):
            if line.endswith(" "):
                issues.append(f"Line {i} has trailing whitespace")

        return issues

    def _check_variable_usage(self, source: str) -> list[str]:
        """Check for potentially undefined variables."""
        issues = []

        # Look for common undefined variable patterns
        if "{{ element." in source and "element" not in source[:50]:
            issues.append("Template uses 'element' variable but may not be passed in context")

        if "{{ config." in source and "config" not in source[:50]:
            issues.append("Template uses 'config' variable but may not be passed in context")

        return issues

    def _check_block_structure(self, source: str) -> list[str]:
        """Check for balanced blocks and proper structure."""
        issues = []

        # Count opening and closing blocks
        open_blocks = source.count("{% if")
        close_blocks = source.count("{% endif")

        if open_blocks != close_blocks:
            issues.append(f"Unbalanced if blocks: {open_blocks} opens, {close_blocks} closes")

        open_for = source.count("{% for")
        close_for = source.count("{% endfor")

        if open_for != close_for:
            issues.append(f"Unbalanced for blocks: {open_for} opens, {close_for} closes")

        return issues


def create_safe_environment(template_dirs: list[Path]) -> Environment:
    """
    Create Jinja2 environment configured for safe template rendering.

    Args:
        template_dirs: List of directories containing templates

    Returns:
        Configured Jinja2 environment
    """
    from jinja2 import FileSystemLoader

    # Create environment with safe defaults
    env = Environment(
        loader=FileSystemLoader([str(d) for d in template_dirs]),
        autoescape=False,  # We're generating Markdown, not HTML
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    # Add safe filters
    env.filters.update(_get_safe_filters())

    return env


def _get_safe_filters() -> dict[str, Any]:
    """Get dictionary of safe template filters."""

    def safe_description(text: str | None) -> str:
        """Safely format description text for YAML frontmatter."""
        if not text:
            return "Documentation"

        # Remove problematic characters for YAML
        lines = text.split("\n")
        clean_lines = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
        result = " ".join(clean_lines)

        # Truncate and escape
        if len(result) > 200:
            result = result[:200] + "..."

        # Escape quotes for YAML
        return result.replace('"', '\\"').replace("'", "\\'")

    def code_or_dash(value: Any) -> str:
        """Wrap in code backticks if not dash or empty."""
        if not value or str(value) in ["-", "None", ""]:
            return "-"
        return f"`{value}`"

    def safe_anchor(text: str | None) -> str:
        """Generate safe anchor links."""
        if not text:
            return ""
        return (
            text.lower()
            .replace(" ", "-")
            .replace(".", "-")
            .replace("_", "-")
            .replace("(", "")
            .replace(")", "")
        )

    def project_relative(path: Path | str | None) -> str:
        """Convert absolute or relative path to project-relative path."""
        if not path:
            return "Unknown"

        path_str = str(path)

        # Handle relative paths with ../ (e.g., ../bengal/core/site.py)
        # Strip leading ../ and normalize
        while path_str.startswith("../"):
            path_str = path_str[3:]
        while path_str.startswith("./"):
            path_str = path_str[2:]

        # Handle absolute paths - find project root by looking for markers
        try:
            path_obj = Path(path_str)
            if path_obj.is_absolute():
                # Walk up to find project root (directory with .git, pyproject.toml, etc.)
                for parent in path_obj.parents:
                    if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                        # Found project root, return path relative to it
                        try:
                            return str(path_obj.relative_to(parent))
                        except ValueError:
                            break
                
                # Fallback: look for common project directory markers
                parts = path_str.split("/")
                for i, part in enumerate(parts):
                    if part in ["bengal", "src", "lib", "project"]:
                        return "/".join(parts[i:])
        except (OSError, ValueError):
            pass

        return path_str

    def github_source_url(
        path: Path | str | None,
        github_repo: str | None = None,
        branch: str = "main",
        line_number: int | None = None,
    ) -> str:
        """
        Convert project-relative path to GitHub blob URL.

        Args:
            path: Project-relative path (e.g., 'bengal/core/site.py')
            github_repo: GitHub repository in 'owner/repo' format (from config)
            branch: Git branch name (default: 'main')
            line_number: Optional line number for anchor

        Returns:
            GitHub blob URL or fallback to relative path if no repo configured
        """
        if not path:
            return "Unknown"

        # Get project-relative path using the project_relative function
        rel_path = project_relative(path)
        if rel_path == "Unknown":
            return rel_path

        # If no GitHub repo configured, return relative path (backward compatible)
        if not github_repo:
            if line_number:
                return f"{rel_path}#L{line_number}"
            return rel_path

        # Build GitHub blob URL
        # Format: https://github.com/owner/repo/blob/branch/path#Lline
        url = f"https://github.com/{github_repo}/blob/{branch}/{rel_path}"
        if line_number:
            url += f"#L{line_number}"

        return url

    def safe_type(type_annotation: Any) -> str:
        """Safely format type annotations."""
        if not type_annotation:
            return "-"

        type_str = str(type_annotation)
        # Clean up common type annotation patterns
        type_str = type_str.replace("typing.", "").replace("<class '", "").replace("'>", "")

        if type_str in ["None", "NoneType"]:
            return "-"

        return f"`{type_str}`"

    def safe_default(default_value: Any) -> str:
        """Safely format default values."""
        if default_value is None or str(default_value) in ["None", ""]:
            return "-"

        # Handle special cases
        if isinstance(default_value, str):
            if default_value == "":
                return '`""`'
            return f'`"{default_value}"`'
        elif isinstance(default_value, bool | int | float):
            return f"`{default_value}`"
        else:
            return f"`{str(default_value)}`"

    def safe_text(text: Any) -> str:
        """Safely format text content."""
        if not text:
            return "*No description provided.*"

        text_str = str(text).strip()
        if not text_str:
            return "*No description provided.*"

        return text_str

    def truncate_text(text: str | None, length: int = 100, suffix: str = "...") -> str:
        """Safely truncate text to specified length."""
        if not text:
            return ""

        if len(text) <= length:
            return text

        return text[:length].rstrip() + suffix

    def format_list(items: list | None, separator: str = ", ", max_items: int = 5) -> str:
        """Safely format a list of items."""
        if not items:
            return ""

        if len(items) <= max_items:
            return separator.join(str(item) for item in items)
        else:
            shown_items = items[:max_items]
            remaining = len(items) - max_items
            return separator.join(str(item) for item in shown_items) + f" and {remaining} more"

    return {
        "safe_description": safe_description,
        "code_or_dash": code_or_dash,
        "safe_anchor": safe_anchor,
        "project_relative": project_relative,
        "github_source_url": github_source_url,
        "safe_type": safe_type,
        "safe_default": safe_default,
        "safe_text": safe_text,
        "truncate_text": truncate_text,
        "format_list": format_list,
    }
