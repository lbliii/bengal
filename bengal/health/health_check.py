"""
Main health check orchestrator.

Coordinates all validators and produces unified health reports.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import HealthReport, ValidatorReport

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.profile import BuildProfile


class HealthCheck:
    """
    Orchestrates health check validators and produces unified health reports.

    By default, registers all standard validators. You can disable auto-registration
    by passing auto_register=False, then manually register validators.

    Usage:
        # Default: auto-registers all validators
        health = HealthCheck(site)
        report = health.run()
        print(report.format_console())

        # Manual registration:
        health = HealthCheck(site, auto_register=False)
        health.register(ConfigValidator())
        health.register(OutputValidator())
        report = health.run()
    """

    def __init__(self, site: Site, auto_register: bool = True):
        """
        Initialize health check system.

        Args:
            site: The Site object to validate
            auto_register: Whether to automatically register all default validators
        """
        self.site = site
        self.validators: list[BaseValidator] = []

        if auto_register:
            self._register_default_validators()

    def _register_default_validators(self) -> None:
        """Register all default validators."""
        from bengal.health.validators import (
            AssetValidator,
            CacheValidator,
            ConfigValidatorWrapper,
            ConnectivityValidator,
            DirectiveValidator,
            FontValidator,
            LinkValidatorWrapper,
            MenuValidator,
            NavigationValidator,
            OutputValidator,
            PerformanceValidator,
            RenderingValidator,
            RSSValidator,
            SitemapValidator,
            TaxonomyValidator,
            TrackValidator,
        )

        # Register in logical order (fast validators first)
        # Phase 1: Basic validation
        self.register(ConfigValidatorWrapper())
        self.register(OutputValidator())

        # Phase 2: Content validation
        self.register(RenderingValidator())
        self.register(DirectiveValidator())
        self.register(NavigationValidator())
        self.register(MenuValidator())
        self.register(TaxonomyValidator())
        self.register(TrackValidator())
        self.register(LinkValidatorWrapper())

        # Phase 3: Advanced validation
        self.register(CacheValidator())
        self.register(PerformanceValidator())

        # Phase 4: Production-ready validation
        self.register(RSSValidator())
        self.register(SitemapValidator())
        self.register(FontValidator())
        self.register(AssetValidator())

        # Phase 5: Knowledge graph validation
        self.register(ConnectivityValidator())

    def register(self, validator: BaseValidator) -> None:
        """
        Register a validator to be run.

        Args:
            validator: Validator instance to register
        """
        self.validators.append(validator)

    def run(
        self,
        build_stats: dict | None = None,
        verbose: bool = False,
        profile: BuildProfile = None,
        incremental: bool = False,
        context: list[Path] | None = None,
        cache: Any = None,
    ) -> HealthReport:
        """
        Run all registered validators and produce a health report.

        Args:
            build_stats: Optional build statistics to include in report
            verbose: Whether to show verbose output during validation
            profile: Build profile to use for filtering validators
            incremental: If True, only validate changed files (requires cache)
            context: Optional list of specific file paths to validate (overrides incremental)
            cache: Optional BuildCache instance for incremental validation and result caching

        Returns:
            HealthReport with results from all validators
        """
        from pathlib import Path

        from bengal.utils.profile import is_validator_enabled

        report = HealthReport(build_stats=build_stats)

        # Determine which files to validate (for file-specific validators)
        files_to_validate: set[Path] | None = None
        if context:
            # Explicit context provided - validate only these files
            files_to_validate = set(Path(p) for p in context)
        elif incremental and cache:
            # Incremental mode - find changed files
            from pathlib import Path

            files_to_validate = set()
            for page in self.site.pages:
                if page.source_path and cache.is_changed(page.source_path):
                    files_to_validate.add(page.source_path)

        # File-specific validators that can benefit from incremental validation
        FILE_SPECIFIC_VALIDATORS = {"Directives", "Links"}

        for validator in self.validators:
            # Profile-based filtering (if profile is set)
            if profile:
                # Check if profile allows this validator (uses global profile state)
                profile_allows = is_validator_enabled(validator.name)

                # Check config for explicit override (normalized to handle bool/dict)
                from bengal.config.defaults import get_feature_config

                health_config = get_feature_config(self.site.config, "health_check")
                validators_config = health_config.get("validators", {})
                validator_key = validator.name.lower().replace(" ", "_")
                config_explicit = validator_key in validators_config
                config_value = validators_config.get(validator_key) if config_explicit else None

                if profile_allows:
                    # Profile allows it - check if config explicitly disables
                    if config_explicit and config_value is False:
                        if verbose:
                            print(f"  Skipping {validator.name} (disabled in config)")
                        continue
                    # Profile allows and config doesn't disable - run it
                else:
                    # Profile disables it - only run if config explicitly enables (True)
                    if config_explicit and config_value is True:
                        # Config explicitly enables - override profile
                        pass
                    else:
                        # Profile disables and config doesn't override - skip
                        if verbose:
                            print(f"  Skipping {validator.name} (disabled by profile)")
                        continue
            else:
                # No profile - use config/default
                if not validator.is_enabled(self.site.config):
                    if verbose:
                        print(f"  Skipping {validator.name} (disabled in config)")
                    continue

            # Check if we can use cached results (for file-specific validators)
            use_cache = (
                cache is not None
                and validator.name in FILE_SPECIFIC_VALIDATORS
                and files_to_validate is not None
                and len(files_to_validate) < len(self.site.pages)  # Only cache if subset
            )

            cached_results: list[Any] = []
            if use_cache:
                # Try to get cached results for unchanged files
                from bengal.health.report import CheckResult

                for page in self.site.pages:
                    if not page.source_path or page.source_path in files_to_validate:
                        continue  # Skip changed files or pages without source

                    cached = cache.get_cached_validation_results(page.source_path, validator.name)
                    if cached:
                        # Deserialize cached results
                        cached_results.extend([CheckResult.from_cache_dict(r) for r in cached])

            # Run validator and time it
            start_time = time.time()

            try:
                # For file-specific validators with context, we could optimize further
                # but for now, validators still validate entire site
                # Future: Pass files_to_validate to validator.validate() for optimization
                results = validator.validate(self.site)

                # Set validator name on all results
                for result in results:
                    if not result.validator:
                        result.validator = validator.name

                # Cache results for file-specific validators
                if use_cache and cache:
                    for page in self.site.pages:
                        if page.source_path and page.source_path in files_to_validate:
                            # Cache results for changed files
                            # Note: This is simplified - in reality, we'd need to filter
                            # results by file. For Phase 1, we cache all results per validator.
                            pass
                    # For now, cache all results (simplified approach)
                    # Future: Filter results by file for per-file caching

            except Exception as e:
                # If validator crashes, record as error
                from bengal.health.report import CheckResult

                results = [
                    CheckResult.error(
                        f"Validator crashed: {e}",
                        recommendation="This is a bug in the health check system. Please report it.",
                        validator=validator.name,
                    )
                ]

            duration_ms = (time.time() - start_time) * 1000

            # Add to report
            validator_report = ValidatorReport(
                validator_name=validator.name, results=results, duration_ms=duration_ms
            )
            report.validator_reports.append(validator_report)

            if verbose:
                status = "✅" if not validator_report.has_problems else "⚠️"
                print(f"  {status} {validator.name}: {len(results)} checks in {duration_ms:.1f}ms")

        return report

    def run_and_print(self, build_stats: dict | None = None, verbose: bool = False) -> HealthReport:
        """
        Run health checks and print console output.

        Args:
            build_stats: Optional build statistics
            verbose: Whether to show all checks (not just problems)

        Returns:
            HealthReport
        """
        report = self.run(build_stats=build_stats, verbose=verbose)
        print(report.format_console(verbose=verbose))
        return report

    def __repr__(self) -> str:
        return f"<HealthCheck: {len(self.validators)} validators>"
