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
    def validate(self, site: Any) -> int:  # returns number of errors
        ...


def _default_engine_factory(site: Any) -> TemplateEngine:
    """Default factory that creates a TemplateEngine from a site."""
    from bengal.rendering.template_engine import TemplateEngine

    return TemplateEngine(site)


def _default_validator(engine: Any) -> int:
    """Default validator that uses health.validators.templates."""
    from bengal.health.validators.templates import validate_templates

    return validate_templates(engine)


@dataclass
class DefaultTemplateValidationService:
    """Adapter around bengal.health.validators.templates with current TemplateEngine.

    Keeps CLI decoupled from concrete rendering internals while preserving behavior.
    Dependencies are injectable for testing without patches.

    Args:
        strict: Whether to use strict validation mode.
        engine_factory: Factory function to create TemplateEngine from site.
        validator: Function to validate templates given an engine.
    """

    strict: bool = False
    engine_factory: Callable[[Any], Any] = field(default=_default_engine_factory)
    validator: Callable[[Any], int] = field(default=_default_validator)

    def validate(self, site: Any) -> int:
        engine = self.engine_factory(site)
        return self.validator(engine)
