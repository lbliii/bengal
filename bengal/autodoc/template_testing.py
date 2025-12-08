"""
Template testing framework for automated template validation and regression testing.

Provides comprehensive testing capabilities for template safety, rendering accuracy,
and performance regression detection.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bengal.autodoc.base import DocElement
from bengal.autodoc.dev_tools import SampleDataGenerator
from bengal.autodoc.template_safety import SafeTemplateRenderer, TemplateValidator
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TemplateTestCase:
    """Test case for template rendering."""

    name: str
    template_name: str
    element_data: dict[str, Any]
    config_data: dict[str, Any]
    expected_content: str | None = None
    expected_errors: list[str] | None = None
    should_fail: bool = False
    performance_threshold_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateTestCase:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TemplateTestResult:
    """Result of template test execution."""

    test_case_name: str
    template_name: str
    passed: bool
    render_time_ms: float
    content_length: int
    errors: list[str]
    warnings: list[str]
    failure_reason: str | None = None
    content_preview: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class TemplateTestSuite:
    """Test suite for template validation and regression testing."""

    def __init__(
        self,
        renderer: SafeTemplateRenderer,
        validator: TemplateValidator,
        sample_generator: SampleDataGenerator | None = None,
    ):
        self.renderer = renderer
        self.validator = validator
        self.sample_generator = sample_generator or SampleDataGenerator()
        self.test_cases: list[TemplateTestCase] = []
        self.results: list[TemplateTestResult] = []

    def add_test_case(self, test_case: TemplateTestCase) -> None:
        """Add a test case to the suite."""
        self.test_cases.append(test_case)

    def generate_standard_test_cases(self) -> None:
        """Generate standard test cases for all template types."""
        # Python module tests
        module_element = self.sample_generator.generate_python_module("test_module")
        self.add_test_case(
            TemplateTestCase(
                name="python_module_basic",
                template_name="python/module.md.jinja2",
                element_data=module_element.to_dict(),
                config_data=self.sample_generator.generate_sample_config(),
                performance_threshold_ms=100.0,
            )
        )

        # CLI command tests
        command_element = self.sample_generator.generate_cli_command("test-cmd")
        self.add_test_case(
            TemplateTestCase(
                name="cli_command_basic",
                template_name="cli/command.md.jinja2",
                element_data=command_element.to_dict(),
                config_data=self.sample_generator.generate_sample_config(),
                performance_threshold_ms=50.0,
            )
        )

        # OpenAPI endpoint tests
        endpoint_element = self.sample_generator.generate_openapi_endpoint("/test", "POST")
        self.add_test_case(
            TemplateTestCase(
                name="openapi_endpoint_basic",
                template_name="openapi/endpoint.md.jinja2",
                element_data=endpoint_element.to_dict(),
                config_data=self.sample_generator.generate_sample_config(),
                performance_threshold_ms=75.0,
            )
        )

        # Error handling tests
        self._add_error_handling_tests()

    def _add_error_handling_tests(self) -> None:
        """Add test cases for error handling scenarios."""
        # Test with missing element data
        self.add_test_case(
            TemplateTestCase(
                name="missing_element_data",
                template_name="python/module.md.jinja2",
                element_data={},  # Empty element data
                config_data=self.sample_generator.generate_sample_config(),
                should_fail=False,  # Should not fail due to safe rendering
                expected_errors=["undefined_variable"],
            )
        )

        # Test with malformed element data
        malformed_element = {
            "name": "test",
            "element_type": "module",
            "children": "not_a_list",  # Should be a list
            "metadata": None,
        }
        self.add_test_case(
            TemplateTestCase(
                name="malformed_element_data",
                template_name="python/module.md.jinja2",
                element_data=malformed_element,
                config_data=self.sample_generator.generate_sample_config(),
                should_fail=False,  # Should handle gracefully
            )
        )

        # Test with non-existent template
        self.add_test_case(
            TemplateTestCase(
                name="nonexistent_template",
                template_name="nonexistent/template.md.jinja2",
                element_data=self.sample_generator.generate_python_module().to_dict(),
                config_data=self.sample_generator.generate_sample_config(),
                should_fail=False,  # SafeTemplateRenderer should handle this
                expected_errors=["template_not_found"],
            )
        )

    def run_test_case(self, test_case: TemplateTestCase) -> TemplateTestResult:
        """
        Run a single test case.

        Args:
            test_case: Test case to execute

        Returns:
            Test result
        """
        logger.debug(
            "running_template_test", test_case=test_case.name, template=test_case.template_name
        )

        # Create element from data
        element = DocElement.from_dict(test_case.element_data) if test_case.element_data else None

        # Create context
        context = {"element": element, "config": test_case.config_data}

        # Clear previous errors
        self.renderer.clear_errors()

        # Execute test
        start_time = time.time()
        errors = []
        warnings = []
        content = ""
        failure_reason = None

        try:
            # Validate template first
            validation_issues = self.validator.validate_template(test_case.template_name)
            if validation_issues:
                warnings.extend([f"Validation: {issue}" for issue in validation_issues])

            # Render template
            content = self.renderer.render_with_boundaries(test_case.template_name, context)

            # Check for renderer errors
            if self.renderer.errors:
                errors.extend([error["error"] for error in self.renderer.errors])

        except Exception as e:
            failure_reason = f"Unexpected error: {str(e)}"
            errors.append(str(e))

        render_time = (time.time() - start_time) * 1000

        # Evaluate test result
        passed = self._evaluate_test_result(test_case, content, errors, render_time, failure_reason)

        result = TemplateTestResult(
            test_case_name=test_case.name,
            template_name=test_case.template_name,
            passed=passed,
            render_time_ms=render_time,
            content_length=len(content),
            errors=errors,
            warnings=warnings,
            failure_reason=failure_reason,
            content_preview=content[:200] + "..." if len(content) > 200 else content,
        )

        self.results.append(result)
        return result

    def _evaluate_test_result(
        self,
        test_case: TemplateTestCase,
        content: str,
        errors: list[str],
        render_time: float,
        failure_reason: str | None,
    ) -> bool:
        """Evaluate whether a test case passed."""
        # Check for unexpected failure
        if failure_reason and not test_case.should_fail:
            return False

        # Check for expected failure
        if test_case.should_fail and not failure_reason and not errors:
            return False

        # Check expected content
        if test_case.expected_content and test_case.expected_content not in content:
            return False

        # Check expected errors
        if test_case.expected_errors:
            for expected_error in test_case.expected_errors:
                if not any(expected_error in error for error in errors):
                    return False

        # Check performance threshold
        if test_case.performance_threshold_ms and render_time > test_case.performance_threshold_ms:
            return False

        # Check that content was generated (unless expecting failure)
        return not (not test_case.should_fail and len(content.strip()) == 0)

    def run_all_tests(self) -> dict[str, Any]:
        """
        Run all test cases in the suite.

        Returns:
            Test suite results summary
        """
        logger.info("running_template_test_suite", test_count=len(self.test_cases))

        self.results.clear()

        for test_case in self.test_cases:
            try:
                self.run_test_case(test_case)
            except Exception as e:
                # Record critical test failure
                self.results.append(
                    TemplateTestResult(
                        test_case_name=test_case.name,
                        template_name=test_case.template_name,
                        passed=False,
                        render_time_ms=0.0,
                        content_length=0,
                        errors=[str(e)],
                        warnings=[],
                        failure_reason=f"Critical test failure: {str(e)}",
                    )
                )

        return self.get_test_summary()

    def get_test_summary(self) -> dict[str, Any]:
        """Get summary of test results."""
        if not self.results:
            return {"message": "No test results available"}

        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]

        total_render_time = sum(r.render_time_ms for r in self.results)
        avg_render_time = total_render_time / len(self.results)

        return {
            "total_tests": len(self.results),
            "passed": len(passed_tests),
            "failed": len(failed_tests),
            "pass_rate": len(passed_tests) / len(self.results) * 100,
            "total_render_time_ms": total_render_time,
            "avg_render_time_ms": avg_render_time,
            "templates_tested": len(set(r.template_name for r in self.results)),
            "failed_tests": [
                {
                    "name": r.test_case_name,
                    "template": r.template_name,
                    "reason": r.failure_reason or "Test conditions not met",
                    "errors": r.errors,
                }
                for r in failed_tests
            ],
        }

    def export_results(self, output_path: Path) -> None:
        """Export test results to JSON file."""
        data = {
            "summary": self.get_test_summary(),
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "results": [r.to_dict() for r in self.results],
            "exported_at": time.time(),
        }

        output_path.write_text(json.dumps(data, indent=2))
        logger.info(
            "template_test_results_exported", path=str(output_path), test_count=len(self.results)
        )

    def load_test_cases(self, input_path: Path) -> None:
        """Load test cases from JSON file."""
        data = json.loads(input_path.read_text())

        self.test_cases.clear()
        for tc_data in data.get("test_cases", []):
            self.test_cases.append(TemplateTestCase.from_dict(tc_data))

        logger.info("template_test_cases_loaded", path=str(input_path), count=len(self.test_cases))


class RegressionTester:
    """Detect performance and output regressions in templates."""

    def __init__(self, baseline_path: Path | None = None):
        self.baseline_path = baseline_path
        self.baseline_data: dict[str, Any] | None = None

        if baseline_path and baseline_path.exists():
            self.load_baseline()

    def load_baseline(self) -> None:
        """Load baseline test results."""
        if self.baseline_path and self.baseline_path.exists():
            self.baseline_data = json.loads(self.baseline_path.read_text())
            logger.info("regression_baseline_loaded", path=str(self.baseline_path))

    def save_baseline(self, test_results: dict[str, Any]) -> None:
        """Save current results as new baseline."""
        if self.baseline_path:
            self.baseline_path.write_text(json.dumps(test_results, indent=2))
            self.baseline_data = test_results
            logger.info("regression_baseline_saved", path=str(self.baseline_path))

    def detect_regressions(self, current_results: dict[str, Any]) -> dict[str, Any]:
        """
        Detect regressions compared to baseline.

        Args:
            current_results: Current test results

        Returns:
            Regression analysis report
        """
        if not self.baseline_data:
            return {"message": "No baseline data available for regression testing"}

        regressions: dict[str, Any] = {
            "performance_regressions": [],
            "new_failures": [],
            "fixed_tests": [],
            "summary": {},
        }

        # Compare performance
        baseline_results = {r["test_case_name"]: r for r in self.baseline_data.get("results", [])}
        current_results_map = {r["test_case_name"]: r for r in current_results.get("results", [])}

        for test_name, current_result in current_results_map.items():
            baseline_result = baseline_results.get(test_name)

            if baseline_result:
                # Check performance regression (>20% slower)
                baseline_time = baseline_result["render_time_ms"]
                current_time = current_result["render_time_ms"]

                if baseline_time > 0 and current_time > baseline_time * 1.2:
                    regressions["performance_regressions"].append(
                        {
                            "test_name": test_name,
                            "template": current_result["template_name"],
                            "baseline_time_ms": baseline_time,
                            "current_time_ms": current_time,
                            "slowdown_percent": ((current_time - baseline_time) / baseline_time)
                            * 100,
                        }
                    )

                # Check for new failures
                if baseline_result["passed"] and not current_result["passed"]:
                    regressions["new_failures"].append(
                        {
                            "test_name": test_name,
                            "template": current_result["template_name"],
                            "failure_reason": current_result.get("failure_reason", "Unknown"),
                            "errors": current_result.get("errors", []),
                        }
                    )

                # Check for fixed tests
                if not baseline_result["passed"] and current_result["passed"]:
                    regressions["fixed_tests"].append(
                        {"test_name": test_name, "template": current_result["template_name"]}
                    )

        # Summary
        regressions["summary"] = {
            "performance_regressions": len(regressions["performance_regressions"]),
            "new_failures": len(regressions["new_failures"]),
            "fixed_tests": len(regressions["fixed_tests"]),
            "baseline_pass_rate": self.baseline_data.get("summary", {}).get("pass_rate", 0),
            "current_pass_rate": current_results.get("summary", {}).get("pass_rate", 0),
        }

        return regressions


def create_template_test_suite(
    renderer: SafeTemplateRenderer,
    validator: TemplateValidator,
    include_standard_tests: bool = True,
) -> TemplateTestSuite:
    """
    Create a comprehensive template test suite.

    Args:
        renderer: Safe template renderer
        validator: Template validator
        include_standard_tests: Whether to include standard test cases

    Returns:
        Configured test suite
    """
    suite = TemplateTestSuite(renderer, validator)

    if include_standard_tests:
        suite.generate_standard_test_cases()

    return suite
