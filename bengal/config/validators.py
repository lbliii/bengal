"""
Configuration validation without external dependencies.

This module provides type-safe configuration validation with helpful error
messages for Bengal sites. It validates configuration values for type
correctness, acceptable ranges, and logical dependencies.

The validator follows Bengal's minimal dependencies principle by avoiding
external validation libraries in favor of straightforward Python validation.

Validation Categories:
    - **Type validation**: Ensures boolean, integer, and string fields have
      correct types. Performs sensible coercion where appropriate (e.g.,
      ``"true"`` → ``True``).
    - **Range validation**: Checks numeric fields are within acceptable bounds
      (e.g., ``max_workers >= 0``, ``port`` between 1-65535).
    - **Dependency validation**: Validates logical consistency between related
      configuration options (reserved for future use).

Classes:
    ConfigValidationError: Raised when validation fails.
    ConfigValidator: Main validator class.

Example:
    >>> from bengal.config.validators import ConfigValidator
    >>> validator = ConfigValidator()
    >>> config = {"parallel": "yes", "max_workers": 8}
    >>> validated = validator.validate(config)
    >>> validated["parallel"]
    True

See Also:
    - :mod:`bengal.config.loader`: Uses validator during configuration loading.
    - :mod:`bengal.errors`: Base error classes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.errors import BengalConfigError
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidationError(BengalConfigError, ValueError):
    """
    Raised when configuration validation fails.

    This exception is raised when one or more configuration values fail
    validation. It extends both :class:`~bengal.errors.BengalConfigError`
    for consistent error handling and :class:`ValueError` for backward
    compatibility with code that catches standard value errors.

    The error message includes the count of validation errors found.
    Detailed error messages are printed to the console before the
    exception is raised.
    """

    pass


class ConfigValidator:
    """
    Validate configuration with helpful error messages.

    This validator checks configuration values for type correctness, valid
    ranges, and logical consistency. It performs sensible type coercion
    where appropriate (e.g., string ``"true"`` → boolean ``True``).

    Validation Checks:
        - **Type correctness**: Boolean, integer, and string fields.
        - **Range validation**: Numeric bounds (min/max workers, port numbers).
        - **Dependency validation**: Related field consistency (future).

    Class Attributes:
        BOOLEAN_FIELDS: Set of field names expected to be boolean.
        INTEGER_FIELDS: Set of field names expected to be integers.
        STRING_FIELDS: Set of field names expected to be strings.

    Example:
        >>> validator = ConfigValidator()
        >>> config = {"parallel": "yes", "max_workers": 8}
        >>> validated = validator.validate(config)
        >>> validated["parallel"]
        True
    """

    # Define expected types for known fields
    BOOLEAN_FIELDS = {
        "parallel",
        "incremental",
        "pretty_urls",
        "minify",
        "optimize",
        "fingerprint",
        "minify_assets",
        "optimize_assets",
        "fingerprint_assets",
        "generate_sitemap",
        "generate_rss",
        "validate_links",
        "strict_mode",
        "debug",
        "validate_build",
        "validate_templates",  # Proactive template syntax validation
        "stable_section_references",  # Path-based section references
        "expose_metadata_json",  # Opt-in JSON bootstrap in head
    }

    INTEGER_FIELDS = {"max_workers", "min_page_size", "port"}

    STRING_FIELDS = {
        "title",
        "baseurl",
        "description",
        "author",
        "language",
        # Note: "theme" removed - now a [theme] section with nested config
        "output_dir",
        "content_dir",
        "assets_dir",
        "templates_dir",
        "host",
        "expose_metadata",  # minimal|standard|extended
        "default_appearance",  # light|dark|system
        "default_palette",  # palette key or empty string
    }

    def validate(self, config: dict[str, Any], source_file: Path | None = None) -> dict[str, Any]:
        """
        Validate configuration and return a normalized version.

        Performs type validation, range checking, and dependency validation
        on the provided configuration. Type coercion is applied where sensible
        (e.g., string ``"true"`` to boolean ``True``).

        Args:
            config: Raw configuration dictionary to validate.
            source_file: Optional source file path for error context in messages.

        Returns:
            Validated and normalized configuration dictionary. Type coercion
            has been applied where appropriate.

        Raises:
            ConfigValidationError: If any validation errors are found.
                Error messages are printed to the console before raising.
        """
        errors = []

        # Flatten nested config if present (support both flat and nested)
        flat_config = self._flatten_config(config)

        # Validate and coerce types
        errors.extend(self._validate_types(flat_config))

        # Validate ranges
        errors.extend(self._validate_ranges(flat_config))

        # Validate dependencies
        errors.extend(self._validate_dependencies(flat_config))

        if errors:
            self._print_errors(errors, source_file)
            raise ConfigValidationError(f"{len(errors)} validation error(s)")

        return flat_config

    def _flatten_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten nested configuration for validation.

        Extracts values from known sections (``site``, ``build``, ``assets``,
        ``features``, ``dev``) to the top level for uniform validation.

        Supports both formats:
            - Flat: ``{parallel: true, title: "Site"}``
            - Nested: ``{build: {parallel: true}, site: {title: "Site"}}``

        Args:
            config: Configuration dictionary (flat or nested).

        Returns:
            Flattened configuration dictionary.
        """
        flat = {}

        for key, value in config.items():
            if key in ("site", "build", "assets", "features", "dev") and isinstance(value, dict):
                # Nested section - merge to root
                flat.update(value)
            else:
                # Already flat or special key (menu, etc)
                flat[key] = value

        # Handle special asset fields (assets.minify -> minify_assets)
        if "assets" in config and isinstance(config["assets"], dict):
            for k, v in config["assets"].items():
                flat[f"{k}_assets"] = v

        # Handle pagination
        if "pagination" in config and isinstance(config["pagination"], dict):
            flat["pagination"] = config["pagination"]

        return flat

    def _validate_types(self, config: dict[str, Any]) -> list[str]:
        """
        Validate and coerce configuration value types.

        Checks that known fields have the expected types and performs
        sensible coercion where possible (e.g., ``"true"`` → ``True``).

        Args:
            config: Configuration dictionary (mutated for coercion).

        Returns:
            List of error messages for type violations that couldn't be coerced.
        """
        errors = []

        # Boolean fields
        for key in self.BOOLEAN_FIELDS:
            if key in config:
                value = config[key]

                match value:
                    case bool():
                        continue  # Already correct
                    case str() as s:
                        # Coerce string to boolean
                        match s.lower():
                            case "true" | "yes" | "1" | "on":
                                config[key] = True
                            case "false" | "no" | "0" | "off":
                                config[key] = False
                            case _:
                                errors.append(
                                    f"'{key}': expected boolean or 'true'/'false', got '{value}'"
                                )
                    case int():
                        # Coerce int to boolean (0=False, non-zero=True)
                        config[key] = bool(value)
                    case _:
                        errors.append(f"'{key}': expected boolean, got {type(value).__name__}")

        # Integer fields
        for key in self.INTEGER_FIELDS:
            if key in config:
                value = config[key]

                match value:
                    case int():
                        continue  # Already correct
                    case str():
                        # Try to coerce string to int
                        try:
                            config[key] = int(value)
                        except ValueError:
                            errors.append(
                                f"'{key}': expected integer, got non-numeric string '{value}'"
                            )
                    case _:
                        errors.append(f"'{key}': expected integer, got {type(value).__name__}")

        # String fields (mostly for type checking, less coercion needed)
        for key in self.STRING_FIELDS:
            if key in config:
                value = config[key]
                if not isinstance(value, str):
                    # Coerce to string if not already
                    config[key] = str(value)

        return errors

    def _validate_ranges(self, config: dict[str, Any]) -> list[str]:
        """
        Validate numeric configuration values are within acceptable ranges.

        Checks fields like ``max_workers``, ``min_page_size``, ``port``,
        and ``pagination.per_page`` for valid bounds.

        Args:
            config: Configuration dictionary.

        Returns:
            List of error messages for out-of-range values.
        """
        errors = []

        # max_workers: must be >= 0
        max_workers = config.get("max_workers")
        if max_workers is not None and isinstance(max_workers, int):
            if max_workers < 0:
                errors.append("'max_workers': must be >= 0 (0 = auto-detect)")
            elif max_workers > 100:
                errors.append("'max_workers': value > 100 seems excessive, is this intentional?")

        # min_page_size: must be >= 0
        min_page_size = config.get("min_page_size")
        if min_page_size is not None and isinstance(min_page_size, int) and min_page_size < 0:
            errors.append("'min_page_size': must be >= 0")

        # Pagination per_page
        pagination = config.get("pagination", {})
        if isinstance(pagination, dict):
            per_page = pagination.get("per_page")
            if per_page is not None:
                if not isinstance(per_page, int):
                    errors.append("'pagination.per_page': must be integer")
                elif per_page < 1:
                    errors.append("'pagination.per_page': must be >= 1")
                elif per_page > 1000:
                    errors.append("'pagination.per_page': value > 1000 seems excessive")

        # Port number
        port = config.get("port")
        if port is not None and isinstance(port, int) and (port < 1 or port > 65535):
            errors.append("'port': must be between 1 and 65535")

        return errors

    def _validate_dependencies(self, config: dict[str, Any]) -> list[str]:
        """
        Validate logical dependencies between configuration fields.

        Reserved for future validation of field interdependencies
        (e.g., incremental builds require valid cache settings).

        Args:
            config: Configuration dictionary.

        Returns:
            List of error messages for dependency violations (currently empty).
        """
        errors: list[str] = []

        # Future: Add dependency validation here
        # Example: if incremental, ensure cache location is valid

        return errors

    def _print_errors(self, errors: list[str], source_file: Path | None = None) -> None:
        """
        Print formatted validation errors to the console.

        Outputs a numbered list of validation errors with contextual
        information about the source file.

        Args:
            errors: List of error message strings.
            source_file: Optional source file path for context.
        """
        source_info = f" in {source_file}" if source_file else ""

        # Log for observability
        logger.error(
            "config_validation_failed",
            error_count=len(errors),
            source_file=str(source_file) if source_file else None,
            errors=errors,
        )

        # Print for user visibility (part of CLI UX)
        print(f"\n❌ Configuration validation failed{source_info}:")
        print()

        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

        print()
        print("Please fix the configuration errors and try again.")
        print("See documentation for valid configuration options.")
        print()
