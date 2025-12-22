"""
Template validation service protocol and default implementation.

This module defines the TemplateValidationService protocol and provides
DefaultTemplateValidationService as the standard implementation. The service
pattern decouples CLI commands and other consumers from concrete validation
internals, enabling easy testing and alternative implementations.

Architecture:
    The validation service follows a dependency injection pattern:

    1. TemplateValidationService defines the contract (Protocol)
    2. DefaultTemplateValidationService adapts bengal.health.validators
    3. Dependencies (engine factory, validator) are injectable

    This allows tests to inject mock factories/validators without patching.

Example:
    Using the default service::

        from bengal.services.validation import DefaultTemplateValidationService

        service = DefaultTemplateValidationService(strict=True)
        errors = service.validate(site)
        if errors > 0:
            print(f"Found {errors} template validation errors")

    Custom validator for testing::

        def mock_validator(engine: Any) -> int:
            return 0  # No errors

        service = DefaultTemplateValidationService(validator=mock_validator)

Related:
    bengal.health.validators.templates: Concrete validate_templates implementation.
    bengal.rendering.template_engine: TemplateEngine created by default factory.
    bengal.cli.commands.validate: CLI command that consumes this service.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from bengal.rendering.template_engine import TemplateEngine


class TemplateValidationService(Protocol):
    """
    Protocol defining the template validation service interface.

    Implementations validate templates for a given site and return the count
    of validation errors found. This protocol enables dependency injection
    and makes validation logic easily swappable for testing.

    Any class implementing this protocol must provide a `validate` method
    that accepts a Site and returns an integer error count.

    Example:
        Custom implementation::

            class StrictValidator:
                def validate(self, site: Any) -> int:
                    # Custom validation logic
                    return count_errors(site)

            validator: TemplateValidationService = StrictValidator()
    """

    def validate(self, site: Any) -> int:
        """
        Validate templates for the given site.

        Args:
            site: The Site instance to validate templates for.

        Returns:
            Number of validation errors found. Zero indicates success.
        """
        ...


def _default_engine_factory(site: Any) -> TemplateEngine:
    """
    Create a TemplateEngine instance from a site.

    This is the default factory used by DefaultTemplateValidationService.
    It performs a lazy import to avoid circular dependencies at module load.

    Args:
        site: The Site instance to create the engine for.

    Returns:
        Configured TemplateEngine for the given site.
    """
    from bengal.rendering.template_engine import TemplateEngine

    return TemplateEngine(site)


def _default_validator(engine: Any) -> int:
    """
    Validate templates using the health.validators.templates module.

    This is the default validator used by DefaultTemplateValidationService.
    It delegates to the concrete validate_templates function.

    Args:
        engine: The TemplateEngine instance to validate.

    Returns:
        Number of validation errors found.
    """
    from bengal.health.validators.templates import validate_templates

    return validate_templates(engine)


@dataclass
class DefaultTemplateValidationService:
    """
    Default implementation of TemplateValidationService.

    Adapts bengal.health.validators.templates for use via the service interface.
    This keeps CLI commands and other consumers decoupled from concrete rendering
    internals while preserving all validation behavior.

    Dependencies are injectable via constructor, enabling testing without patches
    or mocks. Pass custom `engine_factory` or `validator` callables to override
    the default behavior.

    Attributes:
        strict: Enable strict validation mode (reserved for future use).
        engine_factory: Callable that creates a TemplateEngine from a Site.
        validator: Callable that validates templates and returns error count.

    Example:
        Default usage::

            service = DefaultTemplateValidationService()
            errors = service.validate(site)

        With custom validator for testing::

            service = DefaultTemplateValidationService(
                validator=lambda engine: 0  # Always passes
            )

        With strict mode::

            service = DefaultTemplateValidationService(strict=True)
    """

    strict: bool = False
    engine_factory: Callable[[Any], Any] = field(default=_default_engine_factory)
    validator: Callable[[Any], int] = field(default=_default_validator)

    def validate(self, site: Any) -> int:
        """
        Validate templates for the given site.

        Creates a TemplateEngine via the configured factory, then runs the
        configured validator against it.

        Args:
            site: The Site instance containing templates to validate.

        Returns:
            Number of validation errors found. Zero indicates all templates
            are valid.

        Example:
            >>> service = DefaultTemplateValidationService()
            >>> error_count = service.validate(site)
            >>> if error_count == 0:
            ...     print("All templates valid")
        """
        engine = self.engine_factory(site)
        return self.validator(engine)
