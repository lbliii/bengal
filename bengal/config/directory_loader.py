"""
Directory-based configuration loader.

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
    1. ``config/_default/*.yaml`` - Base configuration
    2. ``config/environments/<env>.yaml`` - Environment overrides
    3. ``config/profiles/<profile>.yaml`` - Profile settings

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
    - :mod:`bengal.config.loader`: Single-file configuration loader.
    - :mod:`bengal.config.environment`: Environment detection logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bengal.config.environment import detect_environment, get_environment_file_candidates
from bengal.config.feature_mappings import expand_features
from bengal.config.merge import deep_merge
from bengal.config.origin_tracker import ConfigWithOrigin
from bengal.errors import BengalConfigError, format_suggestion
from bengal.utils.logger import get_logger

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

    pass


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
        1. config/_default/*.yaml (base)
        2. config/environments/<env>.yaml (environment overrides)
        3. config/profiles/<profile>.yaml (profile settings)

        Args:
            config_dir: Path to config directory
            environment: Environment name (auto-detected if None)
            profile: Profile name (optional)

        Returns:
            Merged configuration dictionary

        Raises:
            ConfigLoadError: If config loading fails
        """
        if not config_dir.exists():
            raise ConfigLoadError(
                f"Config directory not found: {config_dir}",
                file_path=config_dir,
                suggestion="Ensure config directory exists or run 'bengal init' to create site structure",
            )

        if not config_dir.is_dir():
            raise ConfigLoadError(
                f"Not a directory: {config_dir}",
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

        config: dict[str, Any] = {}

        # Layer 1: Base defaults from _default/
        defaults_dir = config_dir / "_default"
        if defaults_dir.exists():
            default_config = self._load_directory(defaults_dir, _origin_prefix="_default")
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
        env_config = self._load_environment(config_dir, environment)
        if env_config:
            config = deep_merge(config, env_config)
            if self.origin_tracker:
                self.origin_tracker.merge(env_config, f"environments/{environment}")

        # Layer 3: Profile settings from profiles/<profile>.yaml
        if profile:
            profile_config = self._load_profile(config_dir, profile)
            if profile_config:
                config = deep_merge(config, profile_config)
                if self.origin_tracker:
                    self.origin_tracker.merge(profile_config, f"profiles/{profile}")

        # Expand feature groups (must happen after all merges)
        config = expand_features(config)

        # Flatten config (site.title → title, build.parallel → parallel)
        config = self._flatten_config(config)

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
        behavior. Each file's contents are deep-merged with previous files,
        with later files taking precedence for conflicting keys.

        Args:
            directory: Directory containing YAML files to load.
            _origin_prefix: Reserved for future origin tracking (currently unused).

        Returns:
            Merged configuration dictionary from all files in the directory.

        Raises:
            ConfigLoadError: If any YAML file fails to load or parse.
                The error includes context about which file failed.
        """
        config: dict[str, Any] = {}
        errors = []

        # Load .yaml and .yml files in sorted order (deterministic)
        yaml_files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))

        from bengal.errors import BengalConfigError, ErrorContext, enrich_error

        for yaml_file in yaml_files:
            try:
                file_config = self._load_yaml(yaml_file)
                config = deep_merge(config, file_config)

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
                file_path=first_file,
                suggestion="Check YAML syntax and file encoding (must be UTF-8). Failed files were skipped.",
                original_error=first_error if isinstance(first_error, Exception) else None,
            )

        return config

    def _load_environment(self, config_dir: Path, environment: str) -> dict[str, Any] | None:
        """
        Load environment-specific configuration overrides.

        Searches for environment configuration in ``config_dir/environments/``
        using multiple filename candidates (e.g., ``production.yaml``,
        ``prod.yaml``).

        Args:
            config_dir: Root configuration directory.
            environment: Environment name (e.g., ``"production"``, ``"preview"``).

        Returns:
            Environment configuration dictionary, or ``None`` if no matching
            file is found.
        """
        env_dir = config_dir / "environments"
        if not env_dir.exists():
            return None

        # Try candidates (production.yaml, prod.yaml, etc.)
        candidates = get_environment_file_candidates(environment)

        for candidate in candidates:
            env_file = env_dir / candidate
            if env_file.exists():
                logger.debug("environment_config_found", file=str(env_file))
                return self._load_yaml(env_file)

        logger.debug(
            "environment_config_not_found",
            environment=environment,
            tried=candidates,
        )
        return None

    def _load_profile(self, config_dir: Path, profile: str) -> dict[str, Any] | None:
        """
        Load profile-specific configuration overrides.

        Searches for profile configuration in ``config_dir/profiles/`` with
        both ``.yaml`` and ``.yml`` extensions.

        Args:
            config_dir: Root configuration directory.
            profile: Profile name (e.g., ``"writer"``, ``"developer"``).

        Returns:
            Profile configuration dictionary, or ``None`` if no matching
            file is found.
        """
        profiles_dir = config_dir / "profiles"
        if not profiles_dir.exists():
            return None

        # Try .yaml and .yml
        for ext in [".yaml", ".yml"]:
            profile_file = profiles_dir / f"{profile}{ext}"
            if profile_file.exists():
                logger.debug("profile_config_found", file=str(profile_file))
                return self._load_yaml(profile_file)

        logger.debug("profile_config_not_found", profile=profile)
        return None

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """
        Load a single YAML file with comprehensive error handling.

        Parses the YAML file and returns its contents as a dictionary.
        Provides detailed error messages with line numbers for syntax errors.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed YAML content as a dictionary. Returns an empty dict
            if the file is empty or contains only ``null``.

        Raises:
            ConfigLoadError: If YAML parsing fails (with line number if available)
                or if the file cannot be read (permissions, encoding, etc.).
        """
        try:
            with path.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content or {}
        except yaml.YAMLError as e:
            # Extract line number from YAML error if available
            line_number = getattr(e, "problem_mark", None)
            if line_number and hasattr(line_number, "line"):
                line_num = line_number.line + 1  # YAML line numbers are 0-based
            else:
                line_num = None

            raise ConfigLoadError(
                f"Invalid YAML in {path}: {e}",
                file_path=path,
                line_number=line_num,
                suggestion="Check YAML syntax, indentation, and ensure all quotes are properly closed",
                original_error=e,
            ) from e
        except Exception as e:
            raise ConfigLoadError(
                f"Failed to load {path}: {e}",
                file_path=path,
                suggestion="Check file permissions and encoding (must be UTF-8)",
                original_error=e,
            ) from e

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

    def _flatten_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten nested configuration for easier access.

        Extracts values from common sections to the top level while preserving
        the original section structure. This allows both flat access
        (``config["title"]``) and section access (``config["site"]["title"]``).

        Sections flattened:
            - ``site.*`` → top level (title, baseurl, etc.)
            - ``build.*`` → top level (parallel, incremental, etc.)
            - ``dev.*`` → top level (cache_templates, watch_backend, etc.)
            - ``features.*`` → top level (rss, sitemap, etc.)
            - ``assets.*`` → top level with ``_assets`` suffix (minify_assets, etc.)

        Args:
            config: Nested configuration dictionary.

        Returns:
            Flattened configuration dictionary. Original sections are preserved
            and values are also accessible at the top level.
        """
        flat = dict(config)

        # Extract site section to top level
        if "site" in config and isinstance(config["site"], dict):
            for key, value in config["site"].items():
                if key not in flat:
                    flat[key] = value

        # Extract build section to top level
        if "build" in config and isinstance(config["build"], dict):
            for key, value in config["build"].items():
                if key not in flat:
                    flat[key] = value

        # Extract dev section to top level (for cache_templates, watch_backend, etc.)
        if "dev" in config and isinstance(config["dev"], dict):
            for key, value in config["dev"].items():
                if key not in flat:
                    flat[key] = value

        # Extract features section to top level
        # Note: expand_features() runs before flattening, so this mainly handles
        # any remaining feature keys that weren't expanded
        if "features" in config and isinstance(config["features"], dict):
            for key, value in config["features"].items():
                if key not in flat:
                    flat[key] = value

        # Extract assets section to top level with _assets suffix (for backward compatibility)
        # assets.minify → minify_assets, assets.optimize → optimize_assets, etc.
        if "assets" in config and isinstance(config["assets"], dict):
            for key, value in config["assets"].items():
                flat_key = f"{key}_assets"
                if flat_key not in flat:
                    flat[flat_key] = value

        return flat
