"""
Health check report formatting and data structures.

Provides structured reporting of health check results with multiple output formats.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class CheckStatus(Enum):
    """Status of a health check."""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    """
    Result of a single health check.
    
    Attributes:
        status: Status level (success, info, warning, error)
        message: Human-readable description of the check result
        recommendation: Optional suggestion for how to fix/improve (shown for warnings/errors)
        details: Optional additional context (list of strings)
        validator: Name of validator that produced this result
    """
    status: CheckStatus
    message: str
    recommendation: Optional[str] = None
    details: Optional[List[str]] = None
    validator: str = ""
    
    @classmethod
    def success(cls, message: str, validator: str = "") -> 'CheckResult':
        """Create a success result."""
        return cls(CheckStatus.SUCCESS, message, validator=validator)
    
    @classmethod
    def info(cls, message: str, recommendation: Optional[str] = None, 
             details: Optional[List[str]] = None, validator: str = "") -> 'CheckResult':
        """Create an info result."""
        return cls(CheckStatus.INFO, message, recommendation, details, validator=validator)
    
    @classmethod
    def warning(cls, message: str, recommendation: Optional[str] = None, 
                details: Optional[List[str]] = None, validator: str = "") -> 'CheckResult':
        """Create a warning result."""
        return cls(CheckStatus.WARNING, message, recommendation, details, validator=validator)
    
    @classmethod
    def error(cls, message: str, recommendation: Optional[str] = None, 
              details: Optional[List[str]] = None, validator: str = "") -> 'CheckResult':
        """Create an error result."""
        return cls(CheckStatus.ERROR, message, recommendation, details, validator=validator)
    
    def is_problem(self) -> bool:
        """Check if this is a warning or error (vs success/info)."""
        return self.status in (CheckStatus.WARNING, CheckStatus.ERROR)


@dataclass
class ValidatorReport:
    """
    Report for a single validator's checks.
    
    Attributes:
        validator_name: Name of the validator
        results: List of check results from this validator
        duration_ms: How long the validator took to run
    """
    validator_name: str
    results: List[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    
    @property
    def passed_count(self) -> int:
        """Count of successful checks."""
        return sum(1 for r in self.results if r.status == CheckStatus.SUCCESS)
    
    @property
    def info_count(self) -> int:
        """Count of info messages."""
        return sum(1 for r in self.results if r.status == CheckStatus.INFO)
    
    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for r in self.results if r.status == CheckStatus.WARNING)
    
    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for r in self.results if r.status == CheckStatus.ERROR)
    
    @property
    def has_problems(self) -> bool:
        """Check if this validator found any warnings or errors."""
        return self.warning_count > 0 or self.error_count > 0
    
    @property
    def status_emoji(self) -> str:
        """Get emoji representing overall status."""
        if self.error_count > 0:
            return "❌"
        elif self.warning_count > 0:
            return "⚠️"
        elif self.info_count > 0:
            return "ℹ️"
        else:
            return "✅"


@dataclass
class HealthReport:
    """
    Complete health check report for a build.
    
    Attributes:
        validator_reports: Reports from each validator
        timestamp: When the health check was run
        build_stats: Optional build statistics
    """
    validator_reports: List[ValidatorReport] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    build_stats: Optional[Dict[str, Any]] = None
    
    @property
    def total_passed(self) -> int:
        """Total successful checks across all validators."""
        return sum(r.passed_count for r in self.validator_reports)
    
    @property
    def total_info(self) -> int:
        """Total info messages across all validators."""
        return sum(r.info_count for r in self.validator_reports)
    
    @property
    def total_warnings(self) -> int:
        """Total warnings across all validators."""
        return sum(r.warning_count for r in self.validator_reports)
    
    @property
    def total_errors(self) -> int:
        """Total errors across all validators."""
        return sum(r.error_count for r in self.validator_reports)
    
    @property
    def total_checks(self) -> int:
        """Total number of checks run."""
        return self.total_passed + self.total_info + self.total_warnings + self.total_errors
    
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return self.total_errors > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings were found."""
        return self.total_warnings > 0
    
    def has_problems(self) -> bool:
        """Check if any errors or warnings were found."""
        return self.has_errors() or self.has_warnings()
    
    def build_quality_score(self) -> int:
        """
        Calculate build quality score (0-100).
        
        Formula:
        - Each passed check: +1 point
        - Each info: +0.8 points
        - Each warning: +0.5 points
        - Each error: +0 points
        
        Returns:
            Score from 0-100 (100 = perfect)
        """
        if self.total_checks == 0:
            return 100
        
        points = (
            self.total_passed * 1.0 +
            self.total_info * 0.8 +
            self.total_warnings * 0.5 +
            self.total_errors * 0.0
        )
        
        return int((points / self.total_checks) * 100)
    
    def quality_rating(self) -> str:
        """Get quality rating based on score."""
        score = self.build_quality_score()
        
        if score >= 95:
            return "Excellent"
        elif score >= 85:
            return "Good"
        elif score >= 70:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def format_console(self, mode: str = "auto", verbose: bool = False) -> str:
        """
        Format report for console output.
        
        Args:
            mode: Display mode - "auto", "quiet", "normal", "verbose"
                  auto = quiet if no problems, normal if warnings/errors
            verbose: Legacy parameter, sets mode to "verbose"
            
        Returns:
            Formatted string ready to print
        """
        # Handle legacy verbose parameter
        if verbose:
            mode = "verbose"
        
        # Auto-detect mode based on results
        if mode == "auto":
            if not self.has_problems():
                mode = "quiet"
            else:
                mode = "normal"
        
        if mode == "quiet":
            return self._format_quiet()
        elif mode == "verbose":
            return self._format_verbose()
        else:  # normal
            return self._format_normal()
    
    def _format_quiet(self) -> str:
        """
        Minimal output - perfect builds get one line, problems shown clearly.
        """
        lines = []
        
        # Perfect build - just success message
        if not self.has_problems():
            score = self.build_quality_score()
            return f"✓ Build complete. All health checks passed (quality: {score}%)\n"
        
        # Has problems - show them
        lines.append("")
        
        # Group by validator, only show problems
        for vr in self.validator_reports:
            if not vr.has_problems:
                continue
            
            # Show validator name with problem count
            problem_count = vr.warning_count + vr.error_count
            emoji = "❌" if vr.error_count > 0 else "⚠️"
            lines.append(f"{emoji} {vr.validator_name} ({problem_count} issue(s)):")
            
            # Show problem messages
            for result in vr.results:
                if result.is_problem():
                    lines.append(f"   • {result.message}")
                    
                    # Show recommendation
                    if result.recommendation:
                        lines.append(f"     💡 {result.recommendation}")
                    
                    # Show first 3 details
                    if result.details:
                        for detail in result.details[:3]:
                            lines.append(f"        - {detail}")
                        if len(result.details) > 3:
                            remaining = len(result.details) - 3
                            lines.append(f"        ... and {remaining} more")
            
            lines.append("")  # Blank line between validators
        
        # Summary
        score = self.build_quality_score()
        rating = self.quality_rating()
        summary_parts = []
        
        if self.total_errors > 0:
            summary_parts.append(f"{self.total_errors} error(s)")
        if self.total_warnings > 0:
            summary_parts.append(f"{self.total_warnings} warning(s)")
        
        lines.append(f"Build Quality: {score}% ({rating}) · {', '.join(summary_parts)}")
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_normal(self) -> str:
        """
        Balanced output - show all validators but only problem details.
        """
        lines = []
        
        lines.append("\n🏥 Health Check Summary")
        lines.append("━" * 60)
        lines.append("")
        
        # Show all validators with status
        for vr in self.validator_reports:
            status_line = f"{vr.status_emoji} {vr.validator_name:<20}"
            
            if vr.error_count > 0:
                status_line += f" {vr.error_count} error(s)"
            elif vr.warning_count > 0:
                status_line += f" {vr.warning_count} warning(s)"
            elif vr.info_count > 0:
                status_line += f" {vr.info_count} info"
            else:
                status_line += " passed"
            
            lines.append(status_line)
            
            # Show problems only (not success messages)
            for result in vr.results:
                if result.is_problem():
                    lines.append(f"   • {result.message}")
                    if result.recommendation:
                        lines.append(f"     💡 {result.recommendation}")
                    if result.details:
                        for detail in result.details[:3]:
                            lines.append(f"        - {detail}")
                        if len(result.details) > 3:
                            lines.append(f"        ... and {len(result.details) - 3} more")
        
        # Summary
        lines.append("")
        lines.append("━" * 60)
        lines.append(f"Summary: {self.total_passed} passed, {self.total_warnings} warnings, {self.total_errors} errors")
        
        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append(f"Build Quality: {score}% ({rating})")
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_verbose(self) -> str:
        """
        Full audit trail - show everything including successes.
        """
        lines = []
        
        # Header
        lines.append("\n🏥 Health Check Report")
        lines.append("━" * 60)
        lines.append("")
        
        # Validator results
        for vr in self.validator_reports:
            # Status line
            status_line = f"{vr.status_emoji} {vr.validator_name:<20}"
            
            if vr.error_count > 0:
                status_line += f" {vr.error_count} error(s)"
            elif vr.warning_count > 0:
                status_line += f" {vr.warning_count} warning(s)"
            elif vr.info_count > 0:
                status_line += f" {vr.info_count} info"
            elif vr.passed_count > 0:
                status_line += f" {vr.passed_count} check(s) passed"
            
            lines.append(status_line)
            
            # Show all results in verbose mode
            for result in vr.results:
                # Indent the message
                lines.append(f"   • {result.message}")
                
                # Show recommendation if present
                if result.recommendation:
                    lines.append(f"     💡 {result.recommendation}")
                
                # Show details if present (limit to first 3)
                if result.details:
                    for detail in result.details[:3]:
                        lines.append(f"        - {detail}")
                    if len(result.details) > 3:
                        lines.append(f"        ... and {len(result.details) - 3} more")
        
        # Summary
        lines.append("")
        lines.append("━" * 60)
        lines.append(f"Summary: {self.total_passed} passed, {self.total_warnings} warnings, {self.total_errors} errors")
        
        score = self.build_quality_score()
        rating = self.quality_rating()
        lines.append(f"Build Quality: {score}% ({rating})")
        
        # Build stats if available
        if self.build_stats:
            build_time = self.build_stats.get('build_time_ms', 0) / 1000
            lines.append(f"Build Time: {build_time:.2f}s")
        
        lines.append("")
        
        return "\n".join(lines)
    
    def format_json(self) -> Dict[str, Any]:
        """
        Format report as JSON-serializable dictionary.
        
        Returns:
            Dictionary suitable for json.dumps()
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_checks": self.total_checks,
                "passed": self.total_passed,
                "info": self.total_info,
                "warnings": self.total_warnings,
                "errors": self.total_errors,
                "quality_score": self.build_quality_score(),
                "quality_rating": self.quality_rating(),
            },
            "validators": [
                {
                    "name": vr.validator_name,
                    "duration_ms": vr.duration_ms,
                    "summary": {
                        "passed": vr.passed_count,
                        "info": vr.info_count,
                        "warnings": vr.warning_count,
                        "errors": vr.error_count,
                    },
                    "results": [
                        {
                            "status": r.status.value,
                            "message": r.message,
                            "recommendation": r.recommendation,
                            "details": r.details,
                        }
                        for r in vr.results
                    ]
                }
                for vr in self.validator_reports
            ],
            "build_stats": self.build_stats,
        }

