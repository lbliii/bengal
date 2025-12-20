"""
Validation service protocol and implementations.

Provides protocol-based validation service interface with default implementation.
Enables decoupled validation logic that can be swapped for different validation
strategies or testing.

Key Concepts:
    - Validation protocol: Protocol-based interface for validation services
    - Template validation: Template rendering validation
    - Service pattern: Decoupled validation logic
    - Default implementation: DefaultTemplateValidationService adapter
    - Dependency injection: Engine factory and validator are injectable for testing

Related Modules:
    - bengal.health.validators.templates: Template validation implementation
    - bengal.rendering.template_engine: Template engine for validation
    - bengal.cli.commands.validate: CLI validation command

See Also:
    - bengal/services/validation.py:TemplateValidationService for validation protocol
    - bengal/services/validation.py:DefaultTemplateValidationService for default implementation
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
