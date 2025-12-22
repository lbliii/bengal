"""
Base validator interface for health checks.

This module defines BaseValidator, the abstract base class for all health check
validators. Each validator checks a specific aspect of the build and returns
structured results.

Architecture:
    Validators follow the single-responsibility principle. Each validator:
    - Has a clear name and description
    - Implements validate() returning CheckResult list
    - Targets <100ms execution (for fast feedback)
    - Operates independently (no cross-validator dependencies)

Related:
    - bengal.health.validators: Built-in validator implementations
    - bengal.health.report: CheckResult and status definitions
    - bengal.health.health_check: Orchestrator that runs validators
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.health.report import CheckResult
    from bengal.utils.build_context import BuildContext


class BaseValidator(ABC):
    """
    Abstract base class for all health check validators.

    Validators check specific aspects of a Bengal build and return structured
    results. Each validator runs independently and should complete quickly
    (<100ms target) to enable fast feedback during development.

    Class Attributes:
        name: Human-readable validator name (e.g., "Navigation", "Cache Integrity")
        description: Brief description of what this validator checks
        enabled_by_default: Whether validator runs unless explicitly disabled

    Subclass Requirements:
        1. Set ``name`` class attribute to a descriptive name
        2. Implement ``validate()`` method returning list of CheckResult
        3. Return only problems - if no issues, return empty list

    Example:
        >>> class MyValidator(BaseValidator):
        ...     name = "My System"
        ...     description = "Validates my system configuration"
        ...
        ...     def validate(self, site: Site, build_context=None) -> list[CheckResult]:
        ...         results = []
        ...         if something_wrong:
        ...             results.append(CheckResult.error(
        ...                 "Something is wrong",
        ...                 recommendation="Fix it like this"
        ...             ))
        ...         return results
    """

    # Validator name (override in subclass)
    name: str = "Unknown"

    # Validator description (override in subclass)
    description: str = ""

    # Whether this validator is enabled by default
    enabled_by_default: bool = True

    @abstractmethod
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """
        Run validation checks and return results.

        Args:
            site: The Site object being validated
            build_context: Optional BuildContext with cached artifacts (e.g., knowledge graph).
                          Use Any in type hint to avoid circular imports at runtime.

        Returns:
            List of CheckResult objects (errors, warnings, info, or success)

        Example:
            results = []

            if error_condition:
                results.append(CheckResult.error(
                    "Error message",
                    recommendation="How to fix"
                ))
            elif warning_condition:
                results.append(CheckResult.warning(
                    "Warning message",
                    recommendation="How to improve"
                ))
            # No success message - if no problems, silence is golden

            return results

        Note:
            Validators that need expensive artifacts like the knowledge graph
            should check build_context first before building their own:

            if build_context and getattr(build_context, "knowledge_graph", None):
                graph = build_context.knowledge_graph
            else:
                graph = KnowledgeGraph(site)
                graph.build()
        """
        pass

    def is_enabled(self, config: dict[str, Any]) -> bool:
        """
        Check if this validator is enabled in config.

        Args:
            config: Site configuration dictionary

        Returns:
            True if validator should run
        """
        from bengal.config.defaults import get_feature_config

        # Check if health checks are globally enabled
        if not config.get("validate_build", True):
            return False

        # Get normalized health_check config (handles bool or dict)
        health_config = get_feature_config(config, "health_check")
        if not health_config.get("enabled", True):
            return False

        # Check if this specific validator is enabled
        validators_config = health_config.get("validators", {})

        # Look for validator-specific config using lowercase name
        validator_key = self.name.lower().replace(" ", "_")
        return validators_config.get(validator_key, self.enabled_by_default)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
