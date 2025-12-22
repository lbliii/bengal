"""
Pluggable services for Bengal SSG.

This package provides protocol-based service interfaces with swappable
default implementations. Services enable decoupled logic that can be
replaced for different validation strategies, testing, or custom
integrations without modifying core Bengal components.

Design Pattern:
    Services follow a Protocol + Default Implementation pattern:
    - Protocol defines the interface contract
    - Default implementation provides standard behavior
    - Dependencies are injectable for testing without patches

Available Services:
    TemplateValidationService: Protocol defining template validation interface.
    DefaultTemplateValidationService: Default adapter using health.validators.

Example:
    Basic usage with default implementation::

        from bengal.services import DefaultTemplateValidationService

        service = DefaultTemplateValidationService(strict=True)
        error_count = service.validate(site)

    Custom implementation for testing::

        from bengal.services import TemplateValidationService

        class MockValidationService:
            def validate(self, site: Any) -> int:
                return 0  # Always pass

        # Use anywhere TemplateValidationService is expected
        service: TemplateValidationService = MockValidationService()

Related:
    bengal.health.validators: Concrete validation implementations.
    bengal.health.validators.templates: Template-specific validation.
    bengal.rendering.template_engine: TemplateEngine used by validators.
    bengal.cli.commands.validate: CLI command consuming these services.
"""

from __future__ import annotations

from bengal.services.validation import (
    DefaultTemplateValidationService,
    TemplateValidationService,
)

__all__ = [
    "DefaultTemplateValidationService",
    "TemplateValidationService",
]
