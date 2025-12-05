"""
Main health check orchestrator.

Coordinates all validators and produces unified health reports.
Supports parallel execution of validators for improved performance.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, HealthReport, ValidatorReport

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext
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

    # Threshold for parallel execution - avoid thread overhead for small workloads
    PARALLEL_THRESHOLD = 3
    # Maximum worker threads for parallel execution
    MAX_WORKERS = 4

    def run(
        self,
        build_stats: dict | None = None,
        verbose: bool = False,
        profile: BuildProfile = None,
        incremental: bool = False,
        context: list[Path] | None = None,
        cache: Any = None,
        build_context: Any = None,
    ) -> HealthReport:
        """
        Run all registered validators and produce a health report.

        Validators run in parallel when there are 3+ enabled validators,
        falling back to sequential execution for smaller workloads.

        Args:
            build_stats: Optional build statistics to include in report
            verbose: Whether to show verbose output during validation
            profile: Build profile to use for filtering validators
            incremental: If True, only validate changed files (requires cache)
            context: Optional list of specific file paths to validate (overrides incremental)
            cache: Optional BuildCache instance for incremental validation and result caching
            build_context: Optional BuildContext with cached artifacts (e.g., knowledge graph)
                          that validators can use to avoid redundant computation

        Returns:
            HealthReport with results from all validators
        """
        report = HealthReport(build_stats=build_stats)

        # Filter to enabled validators only
        enabled_validators = [
            v for v in self.validators if self._is_validator_enabled(v, profile, verbose)
        ]

        # Determine which files to validate (for file-specific validators)
        files_to_validate = self._get_files_to_validate(context, incremental, cache)

        # Choose execution strategy based on validator count
        if len(enabled_validators) >= self.PARALLEL_THRESHOLD:
            self._run_validators_parallel(
                enabled_validators, report, build_context, verbose, cache, files_to_validate
            )
        else:
            self._run_validators_sequential(
                enabled_validators, report, build_context, verbose, cache, files_to_validate
            )

        return report

    def _is_validator_enabled(
        self, validator: BaseValidator, profile: BuildProfile | None, verbose: bool
    ) -> bool:
        """
        Check if a validator should run based on profile and config.

        Args:
            validator: The validator to check
            profile: Optional build profile for filtering
            verbose: Whether to show skip messages

        Returns:
            True if validator should run
        """
        from bengal.utils.profile import is_validator_enabled

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
                    return False
                # Profile allows and config doesn't disable - run it
                return True
            else:
                # Profile disables it - only run if config explicitly enables (True)
                if config_explicit and config_value is True:
                    # Config explicitly enables - override profile
                    return True
                else:
                    # Profile disables and config doesn't override - skip
                    if verbose:
                        print(f"  Skipping {validator.name} (disabled by profile)")
                    return False
        else:
            # No profile - use config/default
            if not validator.is_enabled(self.site.config):
                if verbose:
                    print(f"  Skipping {validator.name} (disabled in config)")
                return False
            return True

    def _get_files_to_validate(
        self, context: list[Path] | None, incremental: bool, cache: Any
    ) -> set[Path] | None:
        """
        Determine which files to validate for incremental/context modes.

        Args:
            context: Optional explicit file list
            incremental: Whether incremental mode is enabled
            cache: BuildCache instance

        Returns:
            Set of paths to validate, or None for full validation
        """
        if context:
            # Explicit context provided - validate only these files
            return set(Path(p) for p in context)
        elif incremental and cache:
            # Incremental mode - find changed files
            files_to_validate: set[Path] = set()
            for page in self.site.pages:
                if page.source_path and cache.is_changed(page.source_path):
                    files_to_validate.add(page.source_path)
            return files_to_validate
        return None

    def _run_single_validator(
        self,
        validator: BaseValidator,
        build_context: BuildContext | Any | None,
        cache: Any,
        files_to_validate: set[Path] | None,
    ) -> ValidatorReport:
        """
        Run a single validator and return its report.

        This method is used by both sequential and parallel execution.

        Args:
            validator: The validator to run
            build_context: Optional BuildContext with cached artifacts
            cache: Optional BuildCache for result caching
            files_to_validate: Set of files to validate (for incremental mode)

        Returns:
            ValidatorReport with results and timing
        """
        # File-specific validators that can benefit from incremental validation
        FILE_SPECIFIC_VALIDATORS = {"Directives", "Links"}

        # Check if we can use cached results (for file-specific validators)
        use_cache = (
            cache is not None
            and validator.name in FILE_SPECIFIC_VALIDATORS
            and files_to_validate is not None
            and len(files_to_validate) < len(self.site.pages)  # Only cache if subset
        )

        cached_results: list[CheckResult] = []
        if use_cache:
            # Try to get cached results for unchanged files
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
            # Pass build_context so validators can use cached artifacts
            results = validator.validate(self.site, build_context=build_context)

            # Set validator name on all results
            for result in results:
                if not result.validator:
                    result.validator = validator.name

        except Exception as e:
            # If validator crashes, record as error
            results = [
                CheckResult.error(
                    f"Validator crashed: {e}",
                    recommendation="This is a bug in the health check system. Please report it.",
                    validator=validator.name,
                )
            ]

        duration_ms = (time.time() - start_time) * 1000

        return ValidatorReport(
            validator_name=validator.name, results=results, duration_ms=duration_ms
        )

    def _run_validators_sequential(
        self,
        validators: list[BaseValidator],
        report: HealthReport,
        build_context: BuildContext | Any | None,
        verbose: bool,
        cache: Any,
        files_to_validate: set[Path] | None,
    ) -> None:
        """
        Run validators sequentially (for small workloads).

        Args:
            validators: List of validators to run
            report: HealthReport to add results to
            build_context: Optional BuildContext with cached artifacts
            verbose: Whether to show per-validator output
            cache: Optional BuildCache for result caching
            files_to_validate: Set of files to validate (for incremental mode)
        """
        for validator in validators:
            validator_report = self._run_single_validator(
                validator, build_context, cache, files_to_validate
            )
            report.validator_reports.append(validator_report)

            if verbose:
                status = "✅" if not validator_report.has_problems else "⚠️"
                print(
                    f"  {status} {validator.name}: "
                    f"{len(validator_report.results)} checks in {validator_report.duration_ms:.1f}ms"
                )

    def _run_validators_parallel(
        self,
        validators: list[BaseValidator],
        report: HealthReport,
        build_context: BuildContext | Any | None,
        verbose: bool,
        cache: Any,
        files_to_validate: set[Path] | None,
    ) -> None:
        """
        Run validators in parallel using ThreadPoolExecutor.

        Uses as_completed() to process results as they finish, providing
        better UX for verbose mode. Output is printed in the main thread
        to prevent garbled console output.

        Args:
            validators: List of validators to run
            report: HealthReport to add results to
            build_context: Optional BuildContext with cached artifacts
            verbose: Whether to show per-validator output
            cache: Optional BuildCache for result caching
            files_to_validate: Set of files to validate (for incremental mode)
        """
        # Use up to MAX_WORKERS threads (balance parallelism vs overhead)
        max_workers = min(self.MAX_WORKERS, len(validators))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all validators for parallel execution
            futures = {
                executor.submit(
                    self._run_single_validator, v, build_context, cache, files_to_validate
                ): v
                for v in validators
            }

            # Process results as they complete
            for future in as_completed(futures):
                validator = futures[future]
                try:
                    validator_report = future.result()
                    report.validator_reports.append(validator_report)

                    if verbose:
                        status = "✅" if not validator_report.has_problems else "⚠️"
                        print(
                            f"  {status} {validator.name}: "
                            f"{len(validator_report.results)} checks in "
                            f"{validator_report.duration_ms:.1f}ms"
                        )
                except Exception as e:
                    # Future itself failed (shouldn't happen with our error handling)
                    validator_report = ValidatorReport(
                        validator_name=validator.name,
                        results=[CheckResult.error(f"Validator execution failed: {e}")],
                        duration_ms=0,
                    )
                    report.validator_reports.append(validator_report)

                    if verbose:
                        print(f"  ❌ {validator.name}: execution failed - {e}")

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
