"""
Directory-based configuration loader (internal helper).

Used by :mod:`bengal.config.unified_loader` to support directory-style configs
(`config/_default`, `config/environments`, `config/profiles`). Prefer importing
and using ``UnifiedConfigLoader`` from ``bengal.config``; this module remains
as the internal implementation for directory mode.

This module provides a loader for configuration files organized in a directory
structure, supporting multi-file configurations with environment-specific and
profile-specific overrides.

Directory Structure:
The expected directory layout is::

    config/
    ├── _default/           # Base configuration (multiple YAML files)
    │   ├── site.yaml       # Site metadata
    │   ├── build.yaml      # Build settings
    │   └── theme.yaml      # Theme configuration
    ├── environments/       # Environment-specific overrides
    │   ├── production.yaml
    │   ├── preview.yaml
    │   └── local.yaml
    └── profiles/           # User-defined profiles
        ├── writer.yaml
        └── developer.yaml

Merge Precedence (lowest to highest):
1. Bengal DEFAULTS from ``defaults.py`` - Built-in defaults
2. ``config/_default/*.yaml`` - Base configuration
3. ``config/environments/<env>.yaml`` - Environment overrides
4. ``config/profiles/<profile>.yaml`` - Profile settings

Features:
- Auto-detection of deployment environment (Netlify, Vercel, GitHub Actions)
- Feature group expansion (e.g., ``features.rss: true`` → detailed config)
- Origin tracking for debugging (``bengal config show --origin``)
- Automatic environment variable overrides for baseurl

Classes:
ConfigLoadError: Raised when configuration loading fails.
ConfigDirectoryLoader: Main loader class for directory-based configuration.

Example:
    >>> from bengal.config.directory_loader import ConfigDirectoryLoader
    >>> loader = ConfigDirectoryLoader(track_origins=True)
    >>> config = loader.load(Path("config"), environment="production")

See Also:
- :mod:`bengal.config.unified_loader`: Unified loader for all config modes.
- :mod:`bengal.config.environment`: Environment detection logic.

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.config.defaults import DEFAULTS
from bengal.config.environment import detect_environment
from bengal.config.feature_mappings import expand_features
from bengal.config.loader_utils import (
    extract_baseurl,
    flatten_config,
    load_environment_config,
    load_profile_config,
    load_yaml_file,
    warn_search_ui_without_index,
)
from bengal.config.merge import batch_deep_merge, deep_merge
from bengal.config.origin_tracker import ConfigWithOrigin
from bengal.config.utils import get_default_config
from bengal.errors import BengalConfigError, ErrorCode, format_suggestion
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class ConfigLoadError(BengalConfigError):
    """
    Raised when configuration loading fails.

    This exception is raised for various configuration loading failures
    including missing directories, invalid YAML syntax, or file permission
    errors. Extends :class:`~bengal.errors.BengalConfigError` for consistent
    error handling throughout the configuration system.

    Attributes:
        Inherited from BengalConfigError:
            message: Description of the error.
            file_path: Path to the problematic file or directory.
            line_number: Line number where the error occurred (if applicable).
            suggestion: Helpful suggestion for fixing the error.
            original_error: The underlying exception, if any.

    """


class ConfigDirectoryLoader:
    """
    Load configuration from a directory structure with layered overrides.

    This loader supports multi-file configurations organized in directories,
    with automatic environment detection and profile-based customization.
    It provides deterministic merging with clear precedence rules.

    Features:
        - **Multi-file configs**: Split configuration across multiple YAML files
          in ``_default/`` for better organization.
        - **Environment overrides**: Automatic detection of deployment environment
          with corresponding configuration overrides.
        - **Profile support**: User-defined profiles for different use cases
          (e.g., ``--profile writer``).
        - **Origin tracking**: Optional tracking of which file contributed each
          configuration key (for ``bengal config show --origin``).
        - **Feature expansion**: Simple feature toggles expanded to detailed config.

    Attributes:
        track_origins: Whether origin tracking is enabled.
        origin_tracker: The :class:`ConfigWithOrigin` instance if tracking is enabled.

    Example:
        Basic usage::

            loader = ConfigDirectoryLoader()
            config = loader.load(Path("config"))

        With origin tracking::

            loader = ConfigDirectoryLoader(track_origins=True)
            config = loader.load(Path("config"), environment="production")
            tracker = loader.get_origin_tracker()
            print(tracker.show_with_origin())

        With profile::

            config = loader.load(
                Path("config"),
                environment="local",
                profile="developer"
            )

    """

    def __init__(self, track_origins: bool = False) -> None:
        """
        Initialize the directory configuration loader.

        Args:
            track_origins: If ``True``, track which file contributed each
                configuration key. Use :meth:`get_origin_tracker` to access
                the tracking information after loading. Default is ``False``.
        """
        self.track_origins = track_origins
        self.origin_tracker: ConfigWithOrigin | None = None

    def load(
        self,
        config_dir: Path,
        environment: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        """
        Load config from directory with precedence.

        Precedence (lowest to highest):
        1. Bengal DEFAULTS from defaults.py (built-in defaults)
        2. config/_default/*.yaml (base user config)
        3. config/environments/<env>.yaml (environment overrides)
        4. config/profiles/<profile>.yaml (profile settings)

        Args:
            config_dir: Path to config directory
            environment: Environment name (auto-detected if None)
            profile: Profile name (optional)

        Returns:
            Merged configuration dictionary

        Raises:
            ConfigLoadError: If config loading fails
        """
        # Accept either a config directory or a site root containing config/
        if (
            config_dir.is_dir()
            and (config_dir / "config").exists()
            and not (config_dir / "_default").exists()
        ):
            config_dir = config_dir / "config"

        if not config_dir.exists():
            raise ConfigLoadError(
                f"Config directory not found: {config_dir}",
                code=ErrorCode.C005,  # config_defaults_missing
                file_path=config_dir,
                suggestion="Ensure config directory exists or run 'bengal init' to create site structure",
            )

        if not config_dir.is_dir():
            raise ConfigLoadError(
                f"Not a directory: {config_dir}",
                code=ErrorCode.C003,  # config_invalid_value
                file_path=config_dir,
                suggestion="Ensure path points to a directory, not a file",
            )

        # Initialize origin tracker if needed
        if self.track_origins:
            self.origin_tracker = ConfigWithOrigin()

        # Auto-detect environment if not specified
        if environment is None:
            environment = detect_environment()
            logger.debug("environment_detected", environment=environment)

        # Track whether user provided a baseurl (defaults should NOT count)
        explicit_baseurl = None

        # Layer 0: Start with Bengal DEFAULTS as base layer
        # This ensures all sites get sensible defaults (search, output_formats, etc.)
        # even if _default/ directory is missing or incomplete
        config: dict[str, Any] = get_default_config()
        if self.origin_tracker:
            self.origin_tracker.merge(DEFAULTS, "_bengal_defaults")

        # Layer 1: User defaults from _default/ (overrides DEFAULTS)
        defaults_dir = config_dir / "_default"
        if defaults_dir.exists():
            default_config = self._load_directory(defaults_dir, _origin_prefix="_default")
            detected_baseurl = extract_baseurl(default_config)
            if detected_baseurl is not None:
                explicit_baseurl = detected_baseurl
            config = deep_merge(config, default_config)
            if self.origin_tracker:
                self.origin_tracker.merge(default_config, "_default")
        else:
            suggestion = format_suggestion("config", "defaults_missing")
            logger.warning(
                "config_defaults_missing",
                config_dir=str(config_dir),
                suggestion=suggestion,
            )

        # Layer 2: Environment overrides from environments/<env>.yaml
        env_config = load_environment_config(config_dir, environment)
        if env_config:
            detected_baseurl = extract_baseurl(env_config)
            if detected_baseurl is not None:
                explicit_baseurl = detected_baseurl
            config = deep_merge(config, env_config)
            if self.origin_tracker:
                self.origin_tracker.merge(env_config, f"environments/{environment}")

        # Layer 3: Profile settings from profiles/<profile>.yaml
        if profile:
            profile_config = load_profile_config(config_dir, profile)
            if profile_config:
                detected_baseurl = extract_baseurl(profile_config)
                if detected_baseurl is not None:
                    explicit_baseurl = detected_baseurl
                config = deep_merge(config, profile_config)
                if self.origin_tracker:
                    self.origin_tracker.merge(profile_config, f"profiles/{profile}")

        # Expand feature groups (must happen after all merges)
        config = expand_features(config)

        # Warn about common theme.features vs features confusion
        warn_search_ui_without_index(config)

        # Normalize misplaced site keys (title/baseurl/etc. at root) into site section
        config = self._normalize_site_keys(config)

        # Flatten config (site.title → title, build.parallel → parallel)
        config = flatten_config(config)

        # Preserve whether baseurl was explicitly set in user config (including empty string)
        if explicit_baseurl is not None:
            config["_baseurl_explicit"] = True
            if explicit_baseurl == "":
                config["_baseurl_explicit_empty"] = True

        # BENGAL_ prefix overrides (Hugo-style) - before platform inference
        from bengal.config.env_config import apply_bengal_overrides

        config = apply_bengal_overrides(config)

        # Apply environment-based overrides (GitHub Actions, Netlify, Vercel)
        # Must happen after flattening so baseurl is at top level
        from bengal.config.env_overrides import apply_env_overrides

        config = apply_env_overrides(config)

        logger.debug(
            "config_loaded",
            environment=environment,
            profile=profile,
            sections=list(config.keys()),
        )

        return config

    def _load_directory(self, directory: Path, _origin_prefix: str = "") -> dict[str, Any]:
        """
        Load and merge all YAML files in a directory.

        Files are loaded in sorted order (alphabetically) for deterministic
        behavior. All files are collected first, then merged in a single batch
        operation for O(K × D) complexity instead of O(F × K × D).

        Args:
            directory: Directory containing YAML files to load.
            _origin_prefix: Reserved for future origin tracking (currently unused).

        Returns:
            Merged configuration dictionary from all files in the directory.

        Raises:
            ConfigLoadError: If any YAML file fails to load or parse.
                The error includes context about which file failed.
        """
        errors: list[tuple[Path, Exception]] = []

        # Load .yaml and .yml files in sorted order (deterministic)
        yaml_files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))

        from bengal.errors import BengalConfigError, ErrorContext, enrich_error

        # Collect all configs first, then batch merge (O(K×D) vs O(F×K×D))
        configs: list[dict[str, Any]] = []

        for yaml_file in yaml_files:
            try:
                file_config = load_yaml_file(yaml_file)
                configs.append(file_config)

                logger.debug(
                    "config_file_loaded",
                    file=str(yaml_file),
                    keys=list(file_config.keys()),
                )
            except ConfigLoadError:
                # Re-raise config errors immediately (critical)
                raise
            except Exception as e:
                # Enrich error with context for better error messages
                context = ErrorContext(
                    file_path=yaml_file,
                    operation="loading config file",
                    suggestion="Check YAML syntax and file encoding (must be UTF-8)",
                    original_error=e,
                )
                enriched = enrich_error(e, context, BengalConfigError)
                logger.warning(
                    "config_file_load_failed",
                    file=str(yaml_file),
                    error=str(enriched),
                    error_type=type(e).__name__,
                )
                errors.append((yaml_file, enriched))

        # If any errors occurred, raise with better context
        if errors:
            error_msg = "; ".join([f"{f}: {e}" for f, e in errors])
            # Use first error's file path for context
            first_file, first_error = errors[0]
            raise ConfigLoadError(
                message=f"Failed to load config files: {error_msg}",
                code=ErrorCode.C001,  # config_yaml_parse_error
                file_path=first_file,
                suggestion="Check YAML syntax and file encoding (must be UTF-8). Failed files were skipped.",
                original_error=first_error if isinstance(first_error, Exception) else None,
            )

        # Batch merge all configs in single pass - O(K×D) instead of O(F×K×D)
        return batch_deep_merge(configs)

    def _normalize_site_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Move common site keys placed at the root into the site section.

        Provides backward compatibility for configs that set title/baseurl/etc.
        at the root of _default/*.yaml instead of under [site].
        """
        site_keys = ("title", "baseurl", "description", "author", "language")
        site_section = config.get("site")
        if not isinstance(site_section, dict):
            site_section = {}
            config["site"] = site_section

        for key in site_keys:
            if key in config:
                # Prefer explicit root-level values (user provided) over existing defaults
                site_section[key] = config.pop(key)

        return config

    def get_origin_tracker(self) -> ConfigWithOrigin | None:
        """
        Get the origin tracker instance.

        Returns the origin tracker if tracking was enabled during initialization
        and :meth:`load` has been called. The tracker contains information about
        which configuration file contributed each key.

        Returns:
            The :class:`ConfigWithOrigin` instance if ``track_origins=True``
            was passed to the constructor and config has been loaded,
            otherwise ``None``.

        Example:
            >>> loader = ConfigDirectoryLoader(track_origins=True)
            >>> config = loader.load(Path("config"))
            >>> tracker = loader.get_origin_tracker()
            >>> tracker.get_origin("site.title")
            '_default/site.yaml'
        """
        return self.origin_tracker
