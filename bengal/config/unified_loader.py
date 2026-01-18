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

import yaml

from bengal.config.accessor import Config
from bengal.config.defaults import DEFAULTS
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.config.environment import detect_environment, get_environment_file_candidates
from bengal.config.feature_mappings import expand_features
from bengal.config.merge import batch_deep_merge, deep_merge
from bengal.config.origin_tracker import ConfigWithOrigin
from bengal.config.snapshot import ConfigSnapshot
from bengal.config.validation import validate_config
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
        # Layer 0: DEFAULTS
        config: dict[str, Any] = deep_merge({}, DEFAULTS)
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
            user_baseurl = self._extract_baseurl(user_config)
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
        config = self._flatten_config(config)

        # Preserve whether baseurl was explicitly set in user config (including empty string)
        if user_baseurl is not None:
            config["_baseurl_explicit"] = True
            if user_baseurl == "":
                config["_baseurl_explicit_empty"] = True

        # Warn about common theme.features vs features confusion
        self._warn_search_ui_without_index(config)

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
        from bengal.config.merge import deep_merge

        return deep_merge({}, DEFAULTS)

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

    def _flatten_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten nested configuration for uniform access and validation.

        Mirrors ConfigValidator behavior so callers can rely on both nested
        and flat access (config["title"], config["baseurl"], etc.).
        Nested values (site.*, build.*, etc.) take precedence over top-level
        values for consistency with Bengal's nested-first architecture.

        Args:
            config: Configuration dictionary (flat or nested).

        Returns:
            Flattened configuration dictionary.
        """
        flat = dict(config)

        # Extract values from known sections to top level
        # Specific nested values override general flat values
        for section in ("site", "build", "assets", "features", "dev"):
            if section in config and isinstance(config[section], dict):
                flat.update(config[section])

        return flat

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
                file_config = self._load_yaml(yaml_file)
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

    def _load_environment(self, config_dir: Path, environment: str) -> dict[str, Any] | None:
        """Load environment-specific configuration overrides."""
        env_dir = config_dir / "environments"
        if not env_dir.exists():
            return None

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
        """Load profile-specific configuration overrides."""
        profiles_dir = config_dir / "profiles"
        if not profiles_dir.exists():
            return None

        for ext in [".yaml", ".yml"]:
            profile_file = profiles_dir / f"{profile}{ext}"
            if profile_file.exists():
                logger.debug("profile_config_found", file=str(profile_file))
                return self._load_yaml(profile_file)

        logger.debug("profile_config_not_found", profile=profile)
        return None

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a single YAML file with error handling."""
        try:
            with path.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content or {}
        except yaml.YAMLError as e:
            line_number = getattr(e, "problem_mark", None)
            line_num = (
                (line_number.line + 1) if line_number and hasattr(line_number, "line") else None
            )

            error = ConfigLoadError(
                f"Invalid YAML in {path}: {e}",
                code=ErrorCode.C001,
                file_path=path,
                line_number=line_num,
                suggestion="Check YAML syntax, indentation, and ensure all quotes are properly closed",
                original_error=e,
            )
            record_error(error, file_path=str(path))
            raise error from e
        except Exception as e:
            error = ConfigLoadError(
                f"Failed to load {path}: {e}",
                code=ErrorCode.C003,
                file_path=path,
                suggestion="Check file permissions and encoding (must be UTF-8)",
                original_error=e if isinstance(e, Exception) else None,
            )
            record_error(error, file_path=str(path))
            raise error from e

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

    @staticmethod
    def _extract_baseurl(config: dict[str, Any] | None) -> Any:
        """
        Extract baseurl from a user config dict if explicitly provided.

        Returns the value if present (including empty string) or None if missing.
        """
        if not config or not isinstance(config, dict):
            return None

        # Prefer nested site.baseurl
        site_section = config.get("site")
        if isinstance(site_section, dict) and "baseurl" in site_section:
            return site_section.get("baseurl")

        # Fallback to flat baseurl
        if "baseurl" in config:
            return config.get("baseurl")

        return None

    def _warn_search_ui_without_index(self, config: dict[str, Any]) -> None:
        """Warn if theme.features has search but search index won't be generated."""
        theme = config.get("theme", {})
        if not isinstance(theme, dict):
            return

        theme_features = theme.get("features", [])
        if not isinstance(theme_features, list):
            return

        has_search_ui = any(
            f == "search" or (isinstance(f, str) and f.startswith("search."))
            for f in theme_features
        )

        if not has_search_ui:
            return

        output_formats = config.get("output_formats", {})
        if not isinstance(output_formats, dict):
            return

        site_wide = output_formats.get("site_wide", [])
        has_index_json = "index_json" in site_wide if isinstance(site_wide, list) else False

        if has_index_json:
            return

        logger.warning(
            "search_ui_without_index",
            theme_features=[f for f in theme_features if "search" in str(f)],
            site_wide_formats=site_wide,
            suggestion=(
                "Add 'features.search: true' to config/_default/features.yaml, "
                "or add 'index_json' to output_formats.site_wide"
            ),
        )
