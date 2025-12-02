"""
Base validator interface for health checks.

All validators should inherit from BaseValidator and implement the validate() method.
"""


from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.health.report import CheckResult


class BaseValidator(ABC):
    """
    Base class for all health check validators.

    Each validator should:
    1. Have a clear name (e.g., "Navigation", "Cache Integrity")
    2. Implement validate() to return a list of CheckResult objects
    3. Be fast (target: < 100ms for most validators)
    4. Be independent (no dependencies on other validators)

    Example:
        class MyValidator(BaseValidator):
            name = "My System"

            def validate(self, site: Site) -> List[CheckResult]:
                results = []

                if something_wrong:
                    results.append(CheckResult.error(
                        "Something is wrong",
                        recommendation="Fix it like this"
                    ))
                else:
                    results.append(CheckResult.success("Everything OK"))

                return results
    """

    # Validator name (override in subclass)
    name: str = "Unknown"

    # Validator description (override in subclass)
    description: str = ""

    # Whether this validator is enabled by default
    enabled_by_default: bool = True

    @abstractmethod
    def validate(self, site: Site) -> list[CheckResult]:
        """
        Run validation checks and return results.

        Args:
            site: The Site object being validated

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
            else:
                results.append(CheckResult.success("Check passed"))

            return results
        """
        pass

    def is_enabled(self, config: dict) -> bool:
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
