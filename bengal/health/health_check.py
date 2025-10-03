"""
Main health check orchestrator.

Coordinates all validators and produces unified health reports.
"""

import time
from typing import List, TYPE_CHECKING

from bengal.health.base import BaseValidator
from bengal.health.report import HealthReport, ValidatorReport

if TYPE_CHECKING:
    from bengal.core.site import Site


class HealthCheck:
    """
    Orchestrates health check validators and produces unified reports.
    
    Usage:
        health = HealthCheck(site)
        
        # Add validators
        health.register(ConfigValidator())
        health.register(OutputValidator())
        
        # Run all validators
        report = health.run()
        
        # Display report
        print(report.format_console())
        
        # Or get JSON
        import json
        print(json.dumps(report.format_json(), indent=2))
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize health check system.
        
        Args:
            site: The Site object to validate
        """
        self.site = site
        self.validators: List[BaseValidator] = []
    
    def register(self, validator: BaseValidator) -> None:
        """
        Register a validator to be run.
        
        Args:
            validator: Validator instance to register
        """
        self.validators.append(validator)
    
    def run(self, build_stats: dict = None, verbose: bool = False) -> HealthReport:
        """
        Run all registered validators and produce a health report.
        
        Args:
            build_stats: Optional build statistics to include in report
            verbose: Whether to show verbose output during validation
            
        Returns:
            HealthReport with results from all validators
        """
        report = HealthReport(build_stats=build_stats)
        
        for validator in self.validators:
            # Check if validator is enabled
            if not validator.is_enabled(self.site.config):
                if verbose:
                    print(f"  Skipping {validator.name} (disabled in config)")
                continue
            
            # Run validator and time it
            start_time = time.time()
            
            try:
                results = validator.validate(self.site)
                
                # Set validator name on all results
                for result in results:
                    if not result.validator:
                        result.validator = validator.name
                
            except Exception as e:
                # If validator crashes, record as error
                from bengal.health.report import CheckResult
                results = [
                    CheckResult.error(
                        f"Validator crashed: {e}",
                        recommendation="This is a bug in the health check system. Please report it.",
                        validator=validator.name
                    )
                ]
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Add to report
            validator_report = ValidatorReport(
                validator_name=validator.name,
                results=results,
                duration_ms=duration_ms
            )
            report.validator_reports.append(validator_report)
            
            if verbose:
                status = "✅" if not validator_report.has_problems else "⚠️"
                print(f"  {status} {validator.name}: {len(results)} checks in {duration_ms:.1f}ms")
        
        return report
    
    def run_and_print(self, build_stats: dict = None, verbose: bool = False) -> HealthReport:
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

