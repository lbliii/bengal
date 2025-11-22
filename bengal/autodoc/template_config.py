"""
Configuration system for template safety features.

Provides configuration options for controlling template rendering behavior,
error handling, and safety features.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TemplateSafetyConfig:
    """Configuration for template safety features."""

    # Error handling
    error_boundaries: bool = True
    """Enable error boundary protection around template sections."""

    fallback_content: bool = True
    """Generate fallback content when templates fail to render."""

    validate_templates: bool = True
    """Validate template syntax before rendering."""

    # Debugging and development
    debug_mode: bool = False
    """Show detailed error information in rendered output."""

    show_template_names: bool = False
    """Include template names in HTML comments for debugging."""

    strict_undefined: bool = False
    """Raise errors for undefined variables instead of using fallbacks."""

    # Performance
    cache_templates: bool = True
    """Cache compiled templates for better performance."""

    cache_rendered_content: bool = False
    """Cache rendered content (use with caution - may use lots of memory)."""

    # Error reporting
    collect_errors: bool = True
    """Collect detailed error information for reporting."""

    max_errors_per_template: int = 10
    """Maximum number of errors to collect per template."""

    export_error_reports: bool = False
    """Export detailed error reports to files."""

    # Template validation
    check_whitespace: bool = True
    """Check for whitespace issues in templates."""

    check_undefined_vars: bool = True
    """Check for potentially undefined variables."""

    check_block_structure: bool = True
    """Check for balanced template blocks."""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> TemplateSafetyConfig:
        """
        Create configuration from dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            TemplateSafetyConfig instance
        """
        # Get template safety config section
        safety_config = config.get("autodoc", {}).get("template_safety", {})

        # Create instance with defaults, then update with provided values
        instance = cls()

        for key, value in safety_config.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        return instance

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "error_boundaries": self.error_boundaries,
            "fallback_content": self.fallback_content,
            "validate_templates": self.validate_templates,
            "debug_mode": self.debug_mode,
            "show_template_names": self.show_template_names,
            "strict_undefined": self.strict_undefined,
            "cache_templates": self.cache_templates,
            "cache_rendered_content": self.cache_rendered_content,
            "collect_errors": self.collect_errors,
            "max_errors_per_template": self.max_errors_per_template,
            "export_error_reports": self.export_error_reports,
            "check_whitespace": self.check_whitespace,
            "check_undefined_vars": self.check_undefined_vars,
            "check_block_structure": self.check_block_structure,
        }

    def is_development_mode(self) -> bool:
        """Check if running in development mode (debug features enabled)."""
        return self.debug_mode or self.show_template_names or self.export_error_reports

    def should_fail_fast(self) -> bool:
        """Check if should fail fast on errors (strict mode)."""
        return self.strict_undefined and not self.fallback_content


def get_default_config() -> TemplateSafetyConfig:
    """Get default template safety configuration."""
    return TemplateSafetyConfig()


def validate_config(config: TemplateSafetyConfig) -> list[str]:
    """
    Validate template safety configuration.

    Args:
        config: Configuration to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    # Check for conflicting settings
    if config.strict_undefined and config.fallback_content:
        issues.append(
            "Conflicting settings: strict_undefined=True with fallback_content=True. "
            "Strict mode should disable fallbacks."
        )

    if not config.error_boundaries and config.fallback_content:
        issues.append("Inconsistent settings: fallback_content=True requires error_boundaries=True")

    # Check reasonable limits
    if config.max_errors_per_template < 1:
        issues.append("max_errors_per_template must be at least 1")

    if config.max_errors_per_template > 100:
        issues.append("max_errors_per_template is very high (>100). This may impact performance.")

    # Warn about performance implications
    if config.cache_rendered_content and not config.cache_templates:
        issues.append(
            "Performance warning: cache_rendered_content=True without cache_templates=True "
            "may not provide expected benefits"
        )

    return issues
