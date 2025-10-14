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
