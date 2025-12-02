"""
Directory-based configuration loader.

Loads config from directory structure:
    config/
    ├── _default/       # Base config
    ├── environments/   # Environment overrides
    └── profiles/       # Profile settings

Merge order: defaults → environment → profile
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bengal.config.deprecation import check_deprecated_keys
from bengal.config.environment import detect_environment, get_environment_file_candidates
from bengal.config.feature_mappings import expand_features
from bengal.config.merge import deep_merge
from bengal.config.origin_tracker import ConfigWithOrigin
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoadError(Exception):
    """Raised when config loading fails."""

    pass


class ConfigDirectoryLoader:
    """
    Load configuration from directory structure.

    Supports:
    - Multi-file configs in _default/
    - Environment-specific overrides
    - Profile-specific settings
    - Origin tracking for introspection

    Examples:
        >>> loader = ConfigDirectoryLoader()
        >>> config = loader.load(Path("config"), environment="production", profile="dev")
    """

    def __init__(self, track_origins: bool = False) -> None:
        """
        Initialize loader.

        Args:
            track_origins: Whether to track config origins for introspection
        """
        self.track_origins = track_origins
        self.origin_tracker: ConfigWithOrigin | None = None
        self.deprecated_keys: list[tuple[str, str, str]] = []

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
            raise ConfigLoadError(f"Config directory not found: {config_dir}")

        if not config_dir.is_dir():
            raise ConfigLoadError(f"Not a directory: {config_dir}")

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
            default_config = self._load_directory(defaults_dir, origin_prefix="_default")
            config = deep_merge(config, default_config)
            if self.origin_tracker:
                self.origin_tracker.merge(default_config, "_default")
        else:
            logger.warning("config_defaults_missing", config_dir=str(config_dir))

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

        # Flatten config for backward compatibility with old loader
        # (site.title → title, build.parallel → parallel)
        config = self._flatten_config(config)

        # Apply environment-based overrides (GitHub Actions, Netlify, Vercel)
        # Must happen after flattening so baseurl is at top level
        from bengal.config.env_overrides import apply_env_overrides

        config = apply_env_overrides(config)

        # Check for deprecated keys (don't warn yet, store for later)
        self.deprecated_keys = check_deprecated_keys(
            config,
            source="config/",
            warn=False,
        )

        logger.debug(
            "config_loaded",
            environment=environment,
            profile=profile,
            sections=list(config.keys()),
            deprecated_keys=len(self.deprecated_keys),
        )

        return config

    def get_deprecated_keys(self) -> list[tuple[str, str, str]]:
        """Get list of deprecated keys found (old_key, new_location, note)."""
        return self.deprecated_keys

    def print_deprecation_warnings(self) -> None:
        """Print deprecation warnings if any deprecated keys were found."""
        if self.deprecated_keys:
            from bengal.config.deprecation import print_deprecation_warnings

            print_deprecation_warnings(self.deprecated_keys)

    def _load_directory(self, directory: Path, origin_prefix: str = "") -> dict[str, Any]:
        """
        Load all YAML files in directory and merge.

        Args:
            directory: Directory to load from
            origin_prefix: Prefix for origin tracking

        Returns:
            Merged configuration from all files

        Raises:
            ConfigLoadError: If any YAML file fails to load
        """
        config: dict[str, Any] = {}
        errors = []

        # Load .yaml and .yml files in sorted order (deterministic)
        yaml_files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))

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
                # Re-raise config errors immediately
                raise
            except Exception as e:
                logger.warning(
                    "config_file_load_failed",
                    file=str(yaml_file),
                    error=str(e),
                )
                errors.append((yaml_file, e))

        # If any errors occurred, raise
        if errors:
            error_msg = "; ".join([f"{f}: {e}" for f, e in errors])
            raise ConfigLoadError(f"Failed to load config files: {error_msg}")

        return config

    def _load_environment(self, config_dir: Path, environment: str) -> dict[str, Any] | None:
        """
        Load environment-specific config.

        Args:
            config_dir: Root config directory
            environment: Environment name

        Returns:
            Environment config, or None if not found
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
        Load profile-specific config.

        Args:
            config_dir: Root config directory
            profile: Profile name

        Returns:
            Profile config, or None if not found
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
        Load single YAML file with error handling.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML as dict

        Raises:
            ConfigLoadError: If YAML parsing fails
        """
        try:
            with path.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content or {}
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML in {path}: {e}") from e
        except Exception as e:
            raise ConfigLoadError(f"Failed to load {path}: {e}") from e

    def get_origin_tracker(self) -> ConfigWithOrigin | None:
        """
        Get origin tracker if tracking is enabled.

        Returns:
            Origin tracker, or None if tracking disabled
        """
        return self.origin_tracker

    def _flatten_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten nested config for backward compatibility with old ConfigLoader.

        Extracts common sections to top level:
        - site.title → title
        - build.parallel → parallel

        Args:
            config: Nested configuration dictionary

        Returns:
            Flattened configuration (sections preserved, values also at top level)
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

        # Extract features section to top level (for backward compatibility)
        # Note: expand_features() runs before flattening, so this mainly handles
        # any remaining feature keys that weren't expanded
        if "features" in config and isinstance(config["features"], dict):
            for key, value in config["features"].items():
                if key not in flat:
                    flat[key] = value

        # Handle special asset fields (assets.minify -> minify_assets)
        # This ensures backward compatibility with code that expects flattened keys
        if "assets" in config and isinstance(config["assets"], dict):
            for k, v in config["assets"].items():
                flat[f"{k}_assets"] = v

        return flat
