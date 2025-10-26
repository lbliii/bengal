"""
Configuration loader supporting TOML and YAML formats.
"""

from __future__ import annotations

import difflib
import multiprocessing
import os
from pathlib import Path
from typing import Any

from bengal.utils.logger import get_logger


def pretty_print_config(config: dict[str, Any], title: str = "Configuration") -> None:
    """
    Pretty print configuration using Rich (if available) or fallback to pprint.

    Args:
        config: Configuration dictionary to display
        title: Title for the output
    """
    try:
        from rich.pretty import pprint as rich_pprint

        from bengal.utils.rich_console import get_console, should_use_rich

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
    Loads site configuration from bengal.toml or bengal.yaml.
    """

    # Section aliases for ergonomic config (accept common variations)
    SECTION_ALIASES = {
        "menus": "menu",  # Plural → singular
        "plugin": "plugins",  # Singular → plural (if we add plugins)
    }

    # Known valid section names
    KNOWN_SECTIONS = {
        "site",
        "build",
        "markdown",
        "features",
        "taxonomies",
        "menu",
        "params",
        "assets",
        "pagination",
        "dev",
        "output_formats",
        "health_check",
        "fonts",
        "theme",
    }

    def __init__(self, root_path: Path) -> None:
        """
        Initialize the config loader.

        Args:
            root_path: Root directory to look for config files
        """
        self.root_path = root_path
        self.warnings: list[str] = []
        self.logger = get_logger(__name__)

    def load(self, config_path: Path | None = None) -> dict[str, Any]:
        """
        Load configuration from file.

        Args:
            config_path: Optional explicit path to config file

        Returns:
            Configuration dictionary
        """
        if config_path:
            return self._apply_env_overrides(self._load_file(config_path))

        # Try to find config file automatically
        for filename in ["bengal.toml", "bengal.yaml", "bengal.yml"]:
            config_file = self.root_path / filename
            if config_file.exists():
                # Use debug level to avoid noise in normal output
                self.logger.debug(
                    "config_file_found", config_file=str(config_file), format=config_file.suffix
                )
                return self._load_file(config_file)

        # Return default config if no file found
        self.logger.warning(
            "config_file_not_found",
            search_path=str(self.root_path),
            tried_files=["bengal.toml", "bengal.yaml", "bengal.yml"],
            action="using_defaults",
        )
        return self._apply_env_overrides(self._default_config())

    def _load_file(self, config_path: Path) -> dict[str, Any]:
        """
        Load a specific config file with validation.

        Args:
            config_path: Path to config file

        Returns:
            Validated configuration dictionary

        Raises:
            ConfigValidationError: If validation fails
            ValueError: If config format is unsupported
            FileNotFoundError: If config file doesn't exist
        """
        from bengal.config.validators import ConfigValidationError, ConfigValidator

        suffix = config_path.suffix.lower()

        try:
            # Use debug level to avoid noise in normal output
            self.logger.debug("config_load_start", config_path=str(config_path), format=suffix)

            # Load raw config
            if suffix == ".toml":
                raw_config = self._load_toml(config_path)
            elif suffix in (".yaml", ".yml"):
                raw_config = self._load_yaml(config_path)
            else:
                raise ValueError(f"Unsupported config format: {suffix}")

            # Validate with lightweight validator
            validator = ConfigValidator()
            validated_config = validator.validate(raw_config, source_file=config_path)

            # Use debug level to avoid noise in normal output
            self.logger.debug(
                "config_load_complete",
                config_path=str(config_path),
                sections=list(validated_config.keys()),
                warnings=len(self.warnings),
            )

            return self._apply_env_overrides(validated_config)

        except ConfigValidationError:
            # Validation error already printed nice errors
            self.logger.error(
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
            self.logger.error(
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
        Load TOML configuration file.

        Uses bengal.utils.file_io.load_toml internally for robust loading.

        Args:
            config_path: Path to TOML file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            toml.TomlDecodeError: If TOML syntax is invalid
        """
        from bengal.utils.file_io import load_toml

        config = load_toml(config_path, on_error="raise", caller="config_loader")

        return self._flatten_config(config)

    def _load_yaml(self, config_path: Path) -> dict[str, Any]:
        """
        Load YAML configuration file.

        Uses bengal.utils.file_io.load_yaml internally for robust loading.

        Args:
            config_path: Path to YAML file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
            ImportError: If PyYAML is not installed
        """
        from bengal.utils.file_io import load_yaml

        config = load_yaml(config_path, on_error="raise", caller="config_loader")

        return self._flatten_config(config or {})

    def _flatten_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten nested config structure for easier access.

        Args:
            config: Nested configuration dictionary

        Returns:
            Flattened configuration (sections are preserved but accessible at top level too)
        """
        # First, normalize section names (accept aliases)
        normalized = self._normalize_sections(config)

        # Keep the original structure but also flatten for convenience
        flat = dict(normalized)

        # Extract common sections to top level
        if "site" in normalized:
            for key, value in normalized["site"].items():
                if key not in flat:
                    flat[key] = value

        if "build" in normalized:
            for key, value in normalized["build"].items():
                if key not in flat:
                    flat[key] = value

        # Preserve menu configuration (it's already in the right structure)
        # [[menu.main]] in TOML becomes {'menu': {'main': [...]}}
        if "menu" not in flat and "menu" in normalized:
            flat["menu"] = normalized["menu"]

        return flat

    def _normalize_sections(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize config section names using aliases.

        Accepts common variations like [menus] → [menu].
        Warns about unknown sections.

        Args:
            config: Raw configuration dictionary

        Returns:
            Normalized configuration with canonical section names
        """
        normalized = {}

        for key, value in config.items():
            # Check if this is an alias
            canonical = self.SECTION_ALIASES.get(key)

            if canonical:
                # Using an alias - normalize it
                if canonical in normalized:
                    # Both forms present - merge if possible
                    if isinstance(value, dict) and isinstance(normalized[canonical], dict):
                        normalized[canonical].update(value)
                        warning_msg = f"⚠️  Both [{key}] and [{canonical}] defined. Merging into [{canonical}]."
                        self.warnings.append(warning_msg)
                        self.logger.warning(
                            "config_section_duplicate",
                            alias=key,
                            canonical=canonical,
                            action="merging",
                        )
                    else:
                        warning_msg = (
                            f"⚠️  Both [{key}] and [{canonical}] defined. Using [{canonical}]."
                        )
                        self.warnings.append(warning_msg)
                        self.logger.warning(
                            "config_section_duplicate",
                            alias=key,
                            canonical=canonical,
                            action="using_canonical",
                        )
                else:
                    normalized[canonical] = value
                    warning_msg = f"💡 Config note: [{key}] works, but [{canonical}] is preferred for consistency"
                    self.warnings.append(warning_msg)
                    self.logger.debug(
                        "config_section_alias_used",
                        alias=key,
                        canonical=canonical,
                        suggestion=f"use [{canonical}] instead",
                    )
            elif key not in self.KNOWN_SECTIONS:
                # Unknown section - check for typos
                suggestions = difflib.get_close_matches(key, self.KNOWN_SECTIONS, n=1, cutoff=0.6)
                if suggestions:
                    warning_msg = f"⚠️  Unknown section [{key}]. Did you mean [{suggestions[0]}]?"
                    self.warnings.append(warning_msg)
                    self.logger.warning(
                        "config_section_unknown",
                        section=key,
                        suggestion=suggestions[0],
                        action="including_anyway",
                    )
                else:
                    self.logger.debug(
                        "config_section_custom", section=key, note="not in known sections"
                    )
                # Still include it (might be user-defined)
                normalized[key] = value
            else:
                # Known canonical section
                normalized[key] = value

        return normalized

    def get_warnings(self) -> list[str]:
        """Get configuration warnings (aliases used, unknown sections, etc)."""
        return self.warnings

    def print_warnings(self, verbose: bool = False) -> None:
        """Print configuration warnings if verbose mode is enabled."""
        if self.warnings and verbose:
            # Log and print warnings in verbose mode
            for warning in self.warnings:
                self.logger.warning("config_warning", note=warning)
                print(warning)

    def _default_config(self) -> dict[str, Any]:
        """
        Get default configuration.

        Returns:
            Default configuration dictionary
        """
        # Auto-detect optimal worker count based on CPU cores
        # Use CPU count - 1 to leave one core for OS/UI, minimum 4
        cpu_count = multiprocessing.cpu_count()
        default_workers = max(4, cpu_count - 1)

        return {
            "title": "Bengal Site",
            "baseurl": "",
            "output_dir": "public",
            "content_dir": "content",
            "assets_dir": "assets",
            "templates_dir": "templates",
            "parallel": True,
            "incremental": True,  # Fast incremental builds by default (18-42x faster)
            "minify_html": True,  # Minify HTML output by default (15-25% smaller)
            # HTML output formatting (advanced controls)
            "html_output": {
                "mode": "minify",  # minify | pretty | raw (overrides minify_html)
                "remove_comments": True,
                "collapse_blank_lines": True,
            },
            "max_workers": default_workers,  # Auto-detected based on CPU cores
            "pretty_urls": True,
            "minify_assets": True,
            "optimize_assets": True,
            "fingerprint_assets": True,
            "generate_sitemap": True,
            "generate_rss": True,
            "validate_links": True,
            # Debug and validation options
            "strict_mode": False,  # Fail on template errors instead of fallback
            "debug": False,  # Show verbose debug output and tracebacks
            "validate_build": True,  # Run post-build health checks
            "stable_section_references": True,  # Use path-based section references (rollback safety)
            "min_page_size": 1000,  # Minimum expected page size in bytes
            # Theme configuration
            "theme": {
                "name": "default",
                "default_appearance": "system",
                "default_palette": "",
            },
        }

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Apply environment-based overrides for deployment platforms.

        Delegates to shared utility function.
        Kept as method for backward compatibility.
        """
        from bengal.config.env_overrides import apply_env_overrides

        return apply_env_overrides(config)
