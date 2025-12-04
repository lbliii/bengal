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

Related Modules:
    - bengal.rendering.validator: Template validation implementation
    - bengal.rendering.template_engine: Template engine for validation
    - bengal.cli.commands.validate: CLI validation command

See Also:
    - bengal/services/validation.py:TemplateValidationService for validation protocol
    - bengal/services/validation.py:DefaultTemplateValidationService for default implementation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class TemplateValidationService(Protocol):
    def validate(self, site: Any) -> int:  # returns number of errors
        ...


@dataclass
class DefaultTemplateValidationService:
    """Adapter around bengal.rendering.validator with current TemplateEngine.

    Keeps CLI decoupled from concrete rendering internals while preserving behavior.
    """

    strict: bool = False

    def validate(self, site: Any) -> int:
        from bengal.rendering.template_engine import TemplateEngine
        from bengal.rendering.validator import validate_templates

        engine = TemplateEngine(site)
        return validate_templates(engine)
