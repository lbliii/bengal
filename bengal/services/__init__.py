"""
Pluggable services for Bengal SSG.

Provides protocol-based service interfaces with default implementations.
Services enable decoupled logic that can be swapped for different strategies
or testing.

Services:
    - TemplateValidationService: Protocol for template validation
    - DefaultTemplateValidationService: Default validation implementation

Related:
    - bengal.health.validators: Validation implementations
    - bengal.rendering: Template engine
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
