"""
Unified configuration loader for all config modes.

This module provides a single loader that handles both single-file and
directory-based configuration. It replaces the previous ConfigLoader and
ConfigDirectoryLoader classes with a unified implementation.

Precedence (lowest to highest):
1. DEFAULTS (nested structure)
2. User config (single file or directory)
3. Environment overrides (optional)
4. Profile overrides (optional)

See Also:
- :mod:`bengal.config.accessor`: Config and ConfigSection classes.
- :mod:`bengal.config.defaults`: Default configuration values.
- :mod:`bengal.config.validation`: Configuration validation.

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.config.accessor import Config
from bengal.config.defaults import DEFAULTS
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.config.environment import detect_environment
from bengal.config.feature_mappings import expand_features
from bengal.config.loader_utils import (
    extract_baseurl,
    flatten_config,
    load_yaml_file,
    warn_search_ui_without_index,
)
from bengal.config.merge import batch_deep_merge, deep_merge
from bengal.config.origin_tracker import ConfigWithOrigin
from bengal.config.snapshot import ConfigSnapshot
from bengal.config.utils import get_default_config
from bengal.config.validators import validate_config
from bengal.errors import ErrorCode, format_suggestion, record_error
from bengal.utils.io.file_io import load_toml, load_yaml
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class UnifiedConfigLoader:
    """
    Single loader for all config modes.

    Precedence (lowest to highest):
        1. DEFAULTS (nested structure)
        2. User config (single file or directory)
        3. Environment overrides (optional)
        4. Profile overrides (optional)

    """

    def __init__(self, track_origins: bool = False) -> None:
        """
        Initialize the unified configuration loader.

        Args:
            track_origins: If True, track which file contributed each config key.
        """
        self.track_origins = track_origins
        self.origin_tracker: ConfigWithOrigin | None = None

    def load(
        self,
        site_root: Path,
        environment: str | None = None,
        profile: str | None = None,
    ) -> Config:
        """
        Load configuration from site root.

        Auto-detects config mode:
            - config/ directory exists → directory mode
            - bengal.toml/yaml exists → single-file mode
            - Neither → DEFAULTS only

        Args:
            site_root: Root directory of the site.
            environment: Environment name (auto-detected if None).
            profile: Profile name (optional).

        Returns:
            Config object with structured access.

        Raises:
            ConfigLoadError: If configuration loading fails.
        """
        site_root = Path(site_root)

        # Validate path early to match directory loader semantics
        if not site_root.exists():
            raise ConfigLoadError(
                f"Config directory not found: {site_root}",
                code=ErrorCode.C005,
                file_path=site_root,
                suggestion="Ensure site root or config directory exists",
            )

        # Determine config source
        config_dir: Path | None = None
        single_file: Path | None = None
        # Allow passing config directory directly (has _default/)
        if site_root.is_dir() and (site_root / "_default").exists():
            config_dir = site_root
        elif site_root.is_dir() and (site_root / "config").exists():
            config_dir = site_root / "config"
        elif site_root.is_file():
            # Allow direct single-file configs; otherwise, reject
            if site_root.name in ("bengal.toml", "bengal.yaml", "bengal.yml"):
                single_file = site_root
                site_root = site_root.parent
            else:
                raise ConfigLoadError(
                    f"Not a directory: {site_root}",
                    code=ErrorCode.C003,
                    file_path=site_root,
                    suggestion="Provide a site root directory or config/ directory",
                )
        else:
            single_file = self._find_config_file(site_root)

        if self.track_origins:
            self.origin_tracker = ConfigWithOrigin()

        # Directory mode: delegate to ConfigDirectoryLoader for parity with legacy loader
        if config_dir:
            dir_loader = ConfigDirectoryLoader(track_origins=self.track_origins)
            config_dict = dir_loader.load(config_dir, environment=environment, profile=profile)
            if self.track_origins:
                self.origin_tracker = dir_loader.get_origin_tracker()
            # Directory loader handles normalization/flattening; adopt any warnings if exposed
            if hasattr(dir_loader, "warnings"):
                self.warnings = getattr(dir_loader, "warnings", [])
            config_obj = Config(config_dict)
            return config_obj

        # Single-file or defaults mode
        # Layer 0: DEFAULTS (use shared utility for consistent copy)
        config: dict[str, Any] = get_default_config()
        if self.origin_tracker:
            self.origin_tracker.merge(DEFAULTS, "_bengal_defaults")

        # Track whether user explicitly set baseurl (including empty)
        user_baseurl = None

        # Layer 1: User config (single file)
        if single_file:
            try:
                user_config = self._load_file(single_file)
            except Exception as e:
                # Add context so callers/tests can assert on config parse errors
                raise type(e)(f"Config parse error: {e}") from e
            user_baseurl = extract_baseurl(user_config)
            config = deep_merge(config, user_config)
            if self.origin_tracker:
                self.origin_tracker.merge(user_config, single_file.name)

        # Layer 2: Environment (auto-detect or explicit)
        if environment is None:
            environment = detect_environment()

        # For single-file mode, environment/profile overrides are not applied (no directories)

        # Feature expansion
        config = expand_features(config)

        # Flatten site/build keys for backward compatibility (config["title"], etc.)
        config = flatten_config(config)

        # Preserve whether baseurl was explicitly set in user config (including empty string)
        if user_baseurl is not None:
            config["_baseurl_explicit"] = True
            if user_baseurl == "":
                config["_baseurl_explicit_empty"] = True

        # Warn about common theme.features vs features confusion
        warn_search_ui_without_index(config)

        # BENGAL_ prefix overrides (Hugo-style) - before platform inference
        from bengal.config.env_config import apply_bengal_overrides

        config = apply_bengal_overrides(config)

        # Platform env vars (Netlify, Vercel, GitHub)
        from bengal.config.env_overrides import apply_env_overrides

        config = apply_env_overrides(config)

        # Validation
        validate_config(config)  # Check required keys

        from bengal.config.validators import ConfigValidator

        validator = ConfigValidator()
        config = validator.validate(config)  # Type/range check and normalization

        # Pre-flight access to warm cache (thread-safety)
        # Access core properties before returning to ensure they're cached
        # in single-threaded context
        config_obj = Config(config)
        _ = config_obj.site  # Warm cache
        _ = config_obj.build  # Warm cache
        _ = config_obj.dev  # Warm cache

        logger.debug(
            "config_loaded",
            environment=environment,
            profile=profile,
            sections=list(config.keys()),
        )

        return config_obj

    def _default_config(self) -> dict[str, Any]:
        """
        Return a deep copy of DEFAULTS for single-file parity with directory loader.
        """
        return get_default_config()

    def _find_config_file(self, site_root: Path) -> Path | None:
        """Find single config file (bengal.toml, bengal.yaml, bengal.yml)."""
        for name in ("bengal.toml", "bengal.yaml", "bengal.yml"):
            path = site_root / name
            if path.exists():
                return path
        return None

    def _load_file(self, path: Path) -> dict[str, Any]:
        """Load a single config file (TOML or YAML)."""
        if path.suffix == ".toml":
            return load_toml(path, on_error="raise", caller="config_loader") or {}
        return load_yaml(path, on_error="raise", caller="config_loader") or {}

    def _load_directory(self, config_dir: Path) -> dict[str, Any]:
        """Load all YAML files from config/_default/ directory."""
        defaults_dir = config_dir / "_default"
        if not defaults_dir.exists():
            suggestion = format_suggestion("config", "defaults_missing")
            logger.warning(
                "config_defaults_missing",
                config_dir=str(config_dir),
                suggestion=suggestion,
            )
            return {}

        yaml_files = sorted(defaults_dir.glob("*.yaml")) + sorted(defaults_dir.glob("*.yml"))
        configs: list[dict[str, Any]] = []

        for yaml_file in yaml_files:
            try:
                file_config = load_yaml_file(yaml_file)
                configs.append(file_config)
            except Exception as e:
                error = ConfigLoadError(
                    f"Failed to load {yaml_file}: {e}",
                    code=ErrorCode.C001,
                    file_path=yaml_file,
                    suggestion="Check YAML syntax and file encoding (must be UTF-8)",
                    original_error=e if isinstance(e, Exception) else None,
                )
                record_error(error, file_path=str(yaml_file))
                raise error from e

        return batch_deep_merge(configs)

    def get_origin_tracker(self) -> ConfigWithOrigin | None:
        """Get the origin tracker instance if tracking is enabled."""
        return self.origin_tracker

    def load_snapshot(
        self,
        site_root: Path,
        environment: str | None = None,
        profile: str | None = None,
    ) -> ConfigSnapshot:
        """
        Load configuration and return a frozen ConfigSnapshot.

        This is the preferred entry point for RFC: Snapshot-Enabled v2.
        Returns a frozen, typed configuration that is thread-safe by construction.

        Args:
            site_root: Root directory of the site.
            environment: Environment name (auto-detected if None).
            profile: Profile name (optional).

        Returns:
            Frozen ConfigSnapshot with typed sections.

        Example:
            >>> loader = UnifiedConfigLoader()
            >>> snapshot = loader.load_snapshot(site_root)
            >>> snapshot.site.title
            'My Site'
            >>> snapshot.build.parallel
            True
        """
        config = self.load(site_root, environment=environment, profile=profile)
        return ConfigSnapshot.from_dict(config.raw)
