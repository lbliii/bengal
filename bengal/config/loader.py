"""
Configuration loader supporting TOML and YAML formats.

.. deprecated:: 0.2.0
This module is deprecated. Use :mod:`bengal.config.unified_loader` instead.
Import from ``bengal.config`` which provides ``UnifiedConfigLoader``::

    from bengal.config import UnifiedConfigLoader
    loader = UnifiedConfigLoader()
    config = loader.load(site_root)

This module provides the primary configuration loader for Bengal sites using
single-file configuration (``bengal.toml`` or ``bengal.yaml``). It handles
file discovery, format detection, validation, and environment overrides.

For multi-file directory-based configuration, see :mod:`bengal.config.directory_loader`.

Features:
- **Auto-discovery**: Automatically finds ``bengal.toml``, ``bengal.yaml``,
  or ``bengal.yml`` in the site root.
- **Format support**: Loads both TOML and YAML configuration files.
- **Section normalization**: Accepts common aliases (e.g., ``menus`` → ``menu``).
- **Validation**: Type checking, range validation, and dependency checking.
- **Flattening**: Nested sections (``site.title``) accessible at top level.
- **Environment overrides**: Automatic baseurl detection from platforms.

Classes:
ConfigLoader: Main loader class for single-file configuration.

Functions:
    pretty_print_config: Display configuration with Rich formatting.

Example:
    >>> from pathlib import Path
    >>> from bengal.config.loader import ConfigLoader
    >>> loader = ConfigLoader(Path("my-site"))
    >>> config = loader.load()
    >>> config["title"]
    'My Site'

See Also:
- :mod:`bengal.config.unified_loader`: Unified loader for all config modes.
- :mod:`bengal.config.defaults`: Default values for all configuration options.
- :mod:`bengal.config.validators`: Configuration validation logic.

"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from bengal.config.loader_utils import extract_baseurl, flatten_config, load_yaml_file
from bengal.config.utils import get_default_config
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


def pretty_print_config(config: dict[str, Any], title: str = "Configuration") -> None:
    """
    Pretty print configuration using Rich formatting.

    Displays the configuration dictionary with syntax highlighting and
    formatting. Falls back to standard ``pprint`` if Rich is unavailable
    or disabled.

    Args:
        config: Configuration dictionary to display.
        title: Title to display above the configuration output.

    Example:
            >>> config = {"title": "My Site", "baseurl": "/"}
            >>> pretty_print_config(config, title="Site Configuration")
        # Outputs formatted configuration with Rich or pprint

    """
    try:
        from rich.pretty import pprint as rich_pprint

        from bengal.utils.observability.rich_console import get_console, should_use_rich

        if should_use_rich():
            console = get_console()
            console.print()
            console.print(f"[bold cyan]{title}[/bold cyan]")
            console.print()

            # Use Rich pretty printing with syntax highlighting
            rich_pprint(config, console=console, expand_all=True)
            console.print()
        else:
            # Fallback to standard pprint
            import pprint

            print(f"\n{title}:\n")
            pprint.pprint(config, width=100, compact=False)
            print()
    except ImportError:
        # Ultimate fallback
        import pprint

        print(f"\n{title}:\n")
        pprint.pprint(config, width=100, compact=False)
        print()


class ConfigLoader:
    """
    Load site configuration from ``bengal.toml`` or ``bengal.yaml``.

    This is the primary configuration loader for single-file Bengal configurations.
    It auto-discovers configuration files, validates contents, and applies
    environment-based overrides.

    Attributes:
        root_path: Root directory to search for configuration files.
        warnings: List of configuration warnings accumulated during loading.

    Example:
            >>> loader = ConfigLoader(Path("my-site"))
            >>> config = loader.load()
            >>> config["title"]
            'My Site'

            >>> # Check for configuration warnings
            >>> for warning in loader.get_warnings():
            ...     print(warning)

    """

    def __init__(self, root_path: Path) -> None:
        """
        Initialize the configuration loader.

        Args:
            root_path: Root directory to search for configuration files.
                The loader will look for ``bengal.toml``, ``bengal.yaml``,
                or ``bengal.yml`` in this directory.
        """
        self.root_path = root_path
        self.warnings: list[str] = []

    def load(self, config_path: Path | None = None) -> dict[str, Any]:
        """
        Load configuration from file.

        If no explicit path is provided, searches for configuration files
        in the root directory in order: ``bengal.toml``, ``bengal.yaml``,
        ``bengal.yml``. If no file is found, returns default configuration.

        Args:
            config_path: Optional explicit path to a configuration file.
                If provided, loads only from this file.

        Returns:
            Validated and normalized configuration dictionary with
            environment overrides applied.
        """
        if config_path:
            return self._apply_env_overrides(self._load_file(config_path))

        # Try to find config file automatically
        for filename in ["bengal.toml", "bengal.yaml", "bengal.yml"]:
            config_file = self.root_path / filename
            if config_file.exists():
                # Use debug level to avoid noise in normal output
                logger.debug("config_file_found", config_file=filename, format=config_file.suffix)
                return self._load_file(config_file)

        # Return default config if no file found
        logger.warning(
            "config_file_not_found",
            search_path=self.root_path.name,
            tried_files=["bengal.toml", "bengal.yaml", "bengal.yml"],
            action="using_defaults",
        )
        return self._apply_env_overrides(self._default_config())

    def _load_file(self, config_path: Path) -> dict[str, Any]:
        """
        Load and validate a specific configuration file.

        Detects format from file extension, parses the file, validates
        the configuration, and applies environment overrides.

        Args:
            config_path: Path to the configuration file.

        Returns:
            Validated and normalized configuration dictionary.

        Raises:
            ConfigValidationError: If configuration validation fails.
            BengalConfigError: If the configuration format is unsupported.
            TomlDecodeError: If TOML syntax is invalid.
            YAMLError: If YAML syntax is invalid.
        """
        from bengal.config.validators import ConfigValidationError, ConfigValidator

        suffix = config_path.suffix.lower()

        try:
            # Use debug level to avoid noise in normal output
            logger.debug("config_load_start", config_path=str(config_path), format=suffix)

            # Load raw config
            if suffix == ".toml":
                raw_config = self._load_toml(config_path)
            elif suffix in (".yaml", ".yml"):
                raw_config = load_yaml_file(config_path)
            else:
                from bengal.errors import BengalConfigError, ErrorCode

                raise BengalConfigError(
                    f"Unsupported config format: {suffix}",
                    code=ErrorCode.C003,
                    file_path=config_path,
                    suggestion="Use .toml or .yaml/.yml extension for config files. "
                    "See: bengal init --help",
                )

            # Validate with lightweight validator
            validator = ConfigValidator()
            validated_config = validator.validate(raw_config, source_file=config_path)

            # Use debug level to avoid noise in normal output
            logger.debug(
                "config_load_complete",
                config_path=str(config_path),
                sections=list(validated_config.keys()),
                warnings=len(self.warnings),
            )

            return self._apply_env_overrides(validated_config)

        except ConfigValidationError:
            # Validation error already printed nice errors
            logger.error(
                "config_validation_failed", config_path=str(config_path), error="validation_error"
            )
            raise
        except Exception as e:
            # Propagate parsing errors so callers/tests can assert on invalid configuration.
            # Toml/YAML decoders typically raise ValueError/TomlDecodeError/YAMLError.
            err_name = type(e).__name__
            if err_name in {"TomlDecodeError", "YAMLError"} or isinstance(e, ValueError):
                # Re-raise with clearer context word included
                raise type(e)(f"Config parse error: {e}") from e
            # Otherwise, optionally propagate via env toggle, else fall back to defaults.
            logger.error(
                "config_load_failed",
                config_path=str(config_path),
                error=str(e),
                error_type=err_name,
                action="using_defaults",
            )
            if os.environ.get("BENGAL_RAISE_ON_CONFIG_ERROR") == "1":
                raise
            return self._default_config()

    def _load_toml(self, config_path: Path) -> dict[str, Any]:
        """
        Load a TOML configuration file.

        Uses :func:`bengal.utils.file_io.load_toml` internally for robust
        loading with proper error handling.

        Args:
            config_path: Path to the TOML file.

        Returns:
            Flattened configuration dictionary.

        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            TomlDecodeError: If TOML syntax is invalid.
        """
        from bengal.utils.io.file_io import load_toml

        config = load_toml(config_path, on_error="raise", caller="config_loader")
        if config is None:
            return {}

        return flatten_config(config)

    def get_warnings(self) -> list[str]:
        """
        Get configuration warnings accumulated during loading.

        Warnings include section alias usage, unknown section names, and
        duplicate section definitions.

        Returns:
            List of warning message strings.
        """
        return self.warnings

    def print_warnings(self, verbose: bool = False) -> None:
        """
        Print configuration warnings to the console.

        Args:
            verbose: If ``True``, prints warnings. If ``False``, does nothing.
        """
        if self.warnings and verbose:
            # Log and print warnings in verbose mode
            for warning in self.warnings:
                logger.warning("config_warning", note=warning)
                print(warning)

    def _default_config(self) -> dict[str, Any]:
        """
        Get the default configuration.

        Returns the complete DEFAULTS dictionary from :mod:`bengal.config.defaults`.
        This ensures consistency between single-file and directory-based config
        loading—both modes now inherit the same defaults.

        Returns:
            Default configuration dictionary with all settings from DEFAULTS.
        """
        # Use shared utility for consistent default config retrieval
        return get_default_config()

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Apply environment-based overrides for deployment platforms.

        Delegates to :func:`bengal.config.env_overrides.apply_env_overrides`
        for automatic baseurl detection from Netlify, Vercel, GitHub Pages, etc.

        Args:
            config: Configuration dictionary to enhance.

        Returns:
            Configuration with environment-based overrides applied.
        """
        from bengal.config.env_overrides import apply_env_overrides

        explicit_baseurl = extract_baseurl(config)
        if explicit_baseurl is not None:
            config["_baseurl_explicit"] = True
            if explicit_baseurl == "":
                config["_baseurl_explicit_empty"] = True

        return apply_env_overrides(config)
