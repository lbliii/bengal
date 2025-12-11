"""
Tests for health check report formatting.
"""

from bengal.health.report import CheckResult, CheckStatus, HealthReport, ValidatorReport


class TestCheckResult:
    """Test CheckResult class."""

    def test_create_success(self):
        """Test creating success result."""
        result = CheckResult.success("All good")
        assert result.status == CheckStatus.SUCCESS
        assert result.message == "All good"
        assert result.recommendation is None

    def test_create_info(self):
        """Test creating info result."""
        result = CheckResult.info("FYI", recommendation="Check this")
        assert result.status == CheckStatus.INFO
        assert result.message == "FYI"
        assert result.recommendation == "Check this"

    def test_create_warning(self):
        """Test creating warning result."""
        result = CheckResult.warning(
            "Problem found", recommendation="Fix it", details=["detail1", "detail2"]
        )
        assert result.status == CheckStatus.WARNING
        assert result.message == "Problem found"
        assert result.recommendation == "Fix it"
        assert len(result.details) == 2

    def test_create_error(self):
        """Test creating error result."""
        result = CheckResult.error("Critical issue")
        assert result.status == CheckStatus.ERROR
        assert result.message == "Critical issue"

    def test_create_suggestion(self):
        """Test creating suggestion result."""
        result = CheckResult.suggestion("Quality improvement", recommendation="Consider this")
        assert result.status == CheckStatus.SUGGESTION
        assert result.message == "Quality improvement"
        assert result.recommendation == "Consider this"

    def test_is_problem(self):
        """Test is_problem method."""
        assert not CheckResult.success("OK").is_problem()
        assert not CheckResult.info("Info").is_problem()
        assert not CheckResult.suggestion("Suggestion").is_problem()  # Suggestions are not problems
        assert CheckResult.warning("Warning").is_problem()
        assert CheckResult.error("Error").is_problem()

    def test_is_actionable(self):
        """Test is_actionable method."""
        assert not CheckResult.success("OK").is_actionable()
        assert not CheckResult.info("Info").is_actionable()
        assert CheckResult.suggestion("Suggestion").is_actionable()
        assert CheckResult.warning("Warning").is_actionable()
        assert CheckResult.error("Error").is_actionable()

    def test_to_cache_dict(self):
        """Test serialization to cache dict."""
        result = CheckResult.warning("Test", recommendation="Fix it", details=["detail1"])
        data = result.to_cache_dict()

        assert data["status"] == "warning"
        assert data["message"] == "Test"
        assert data["recommendation"] == "Fix it"
        assert data["details"] == ["detail1"]
        assert data["validator"] == ""

    def test_from_cache_dict(self):
        """Test deserialization from cache dict."""
        data = {
            "status": "suggestion",
            "message": "Test suggestion",
            "recommendation": "Consider this",
            "details": None,
            "validator": "TestValidator",
        }
        result = CheckResult.from_cache_dict(data)

        assert result.status == CheckStatus.SUGGESTION
        assert result.message == "Test suggestion"
        assert result.recommendation == "Consider this"
        assert result.validator == "TestValidator"


class TestValidatorReport:
    """Test ValidatorReport class."""

    def test_passed_count(self):
        """Test counting passed checks."""
        report = ValidatorReport("Test")
        report.results = [
            CheckResult.success("OK 1"),
            CheckResult.success("OK 2"),
            CheckResult.warning("Warning"),
        ]
        assert report.passed_count == 2

    def test_info_count(self):
        """Test counting info messages."""
        report = ValidatorReport("Test")
        report.results = [
            CheckResult.info("Info 1"),
            CheckResult.info("Info 2"),
            CheckResult.success("OK"),
        ]
        assert report.info_count == 2

    def test_warning_count(self):
        """Test counting warnings."""
        report = ValidatorReport("Test")
        report.results = [
            CheckResult.warning("Warning 1"),
            CheckResult.warning("Warning 2"),
            CheckResult.error("Error"),
        ]
        assert report.warning_count == 2

    def test_suggestion_count(self):
        """Test counting suggestions."""
        report = ValidatorReport("Test")
        report.results = [
            CheckResult.suggestion("Suggestion 1"),
            CheckResult.suggestion("Suggestion 2"),
            CheckResult.success("OK"),
        ]
        assert report.suggestion_count == 2

    def test_error_count(self):
        """Test counting errors."""
        report = ValidatorReport("Test")
        report.results = [
            CheckResult.error("Error 1"),
            CheckResult.error("Error 2"),
        ]
        assert report.error_count == 2

    def test_has_problems(self):
        """Test has_problems property."""
        report = ValidatorReport("Test")
        report.results = [CheckResult.success("OK")]
        assert not report.has_problems

        report.results.append(CheckResult.warning("Warning"))
        assert report.has_problems

        # Suggestions are not problems
        report.results.append(CheckResult.suggestion("Suggestion"))
        assert report.has_problems  # Still has problems due to warning

    def test_status_emoji(self):
        """Test status emoji selection."""
        report = ValidatorReport("Test")

        # Only success
        report.results = [CheckResult.success("OK")]
        assert report.status_emoji == "✅"

        # Has info
        report.results = [CheckResult.info("Info")]
        assert report.status_emoji == "ℹ️"

        # Has warning
        report.results = [CheckResult.warning("Warning")]
        assert report.status_emoji == "⚠️"

        # Has error (highest priority)
        report.results = [
            CheckResult.success("OK"),
            CheckResult.warning("Warning"),
            CheckResult.error("Error"),
        ]
        assert report.status_emoji == "❌"


class TestHealthReport:
    """Test HealthReport class."""

    def test_total_counts(self):
        """Test total count properties."""
        report = HealthReport()

        vr1 = ValidatorReport("Validator1")
        vr1.results = [
            CheckResult.success("OK"),
            CheckResult.warning("Warning"),
        ]

        vr2 = ValidatorReport("Validator2")
        vr2.results = [
            CheckResult.info("Info"),
            CheckResult.error("Error"),
        ]

        report.validator_reports = [vr1, vr2]

        assert report.total_passed == 1
        assert report.total_info == 1
        assert report.total_warnings == 1
        assert report.total_errors == 1
        assert report.total_checks == 4

    def test_has_errors(self):
        """Test has_errors method."""
        report = HealthReport()
        vr = ValidatorReport("Test")

        vr.results = [CheckResult.success("OK")]
        report.validator_reports = [vr]
        assert not report.has_errors()

        vr.results.append(CheckResult.error("Error"))
        assert report.has_errors()

    def test_has_warnings(self):
        """Test has_warnings method."""
        report = HealthReport()
        vr = ValidatorReport("Test")

        vr.results = [CheckResult.success("OK")]
        report.validator_reports = [vr]
        assert not report.has_warnings()

        vr.results.append(CheckResult.warning("Warning"))
        assert report.has_warnings()

    def test_has_problems(self):
        """Test has_problems method."""
        report = HealthReport()
        vr = ValidatorReport("Test")

        vr.results = [CheckResult.success("OK")]
        report.validator_reports = [vr]
        assert not report.has_problems()

        vr.results.append(CheckResult.warning("Warning"))
        assert report.has_problems()

    def test_build_quality_score(self):
        """Test build quality score calculation (penalty-based)."""
        report = HealthReport()
        vr = ValidatorReport("Test")

        # Perfect score - no problems
        vr.results = [
            CheckResult.success("OK 1"),
            CheckResult.success("OK 2"),
        ]
        report.validator_reports = [vr]
        assert report.build_quality_score() == 100

        # No checks = 100% (nothing to fail)
        vr.results = []
        assert report.build_quality_score() == 100

        # 1 warning only = 95% (100 - 5)
        vr.results = [
            CheckResult.success("OK"),
            CheckResult.warning("Warning"),
        ]
        assert report.build_quality_score() == 95

        # 1 error only = 80% (100 - 20)
        vr.results = [
            CheckResult.success("OK"),
            CheckResult.error("Error"),
        ]
        assert report.build_quality_score() == 80

        # Mixed: 1 error + 1 warning = 75% (100 - 20 - 5)
        vr.results = [
            CheckResult.success("OK"),
            CheckResult.info("Info"),
            CheckResult.suggestion("Suggestion"),
            CheckResult.warning("Warning"),
            CheckResult.error("Error"),
        ]
        assert report.build_quality_score() == 75

        # 2 errors + 1 warning = 55% (100 - 40 - 5)
        vr.results = [
            CheckResult.warning("Warning"),
            CheckResult.error("Error 1"),
            CheckResult.error("Error 2"),
        ]
        assert report.build_quality_score() == 55

        # Many errors cap at 70 penalty, many warnings cap at 25
        vr.results = [
            CheckResult.warning("W1"),
            CheckResult.warning("W2"),
            CheckResult.warning("W3"),
            CheckResult.warning("W4"),
            CheckResult.warning("W5"),
            CheckResult.warning("W6"),  # 6 warnings = 25 cap
            CheckResult.error("E1"),
            CheckResult.error("E2"),
            CheckResult.error("E3"),
            CheckResult.error("E4"),
            CheckResult.error("E5"),  # 5 errors = 70 cap
        ]
        # 100 - 70 - 25 = 5 (floor at 0)
        assert report.build_quality_score() == 5

    def test_quality_rating(self):
        """Test quality rating labels (aligned with penalty-based scoring)."""
        report = HealthReport()
        vr = ValidatorReport("Test")
        report.validator_reports = [vr]

        # Excellent (90+): no errors, 0-2 warnings
        vr.results = [CheckResult.success("OK")] * 5
        assert report.quality_rating() == "Excellent"

        vr.results = [CheckResult.success("OK")] * 5 + [CheckResult.warning("W")]
        assert report.quality_rating() == "Excellent"  # 95%

        # Good (75-89): 1 error or 3-5 warnings
        vr.results = [CheckResult.success("OK")] * 5 + [CheckResult.error("E")]
        assert report.quality_rating() == "Good"  # 80%

        vr.results = [CheckResult.warning("W")] * 4
        assert report.quality_rating() == "Good"  # 80%

        # Fair (50-74): 2-3 errors or many warnings
        vr.results = [CheckResult.error("E1"), CheckResult.error("E2")]
        assert report.quality_rating() == "Fair"  # 60%

        # Needs Improvement (<50): 4+ errors
        vr.results = [
            CheckResult.error("E1"),
            CheckResult.error("E2"),
            CheckResult.error("E3"),
            CheckResult.error("E4"),
        ]
        assert report.quality_rating() == "Needs Improvement"  # 30%


class TestHealthReportFormatting:
    """Test health report console formatting."""

    def test_format_console_auto_mode_perfect(self):
        """Test auto mode with perfect build (should be quiet)."""
        report = HealthReport()
        vr = ValidatorReport("Test Validator")
        vr.results = [CheckResult.success("Everything is perfect")]
        report.validator_reports = [vr]

        output = report.format_console(mode="auto")

        # Should show quiet mode (one line)
        assert "All health checks passed" in output
        assert "quality: 100%" in output
        # Should not show validator names
        assert "Test Validator" not in output

    def test_format_console_auto_mode_with_warnings(self):
        """Test auto mode with warnings (should be normal)."""
        report = HealthReport()
        vr = ValidatorReport("Test Validator")
        vr.results = [
            CheckResult.success("OK"),
            CheckResult.warning("Found issue", recommendation="Fix it"),
        ]
        report.validator_reports = [vr]

        output = report.format_console(mode="auto")

        # Should show normal mode
        assert "Health Check Summary" in output
        assert "Test Validator" in output
        assert "Found issue" in output
        assert "Fix it" in output

    def test_format_quiet_mode(self):
        """Test quiet mode formatting."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [CheckResult.warning("Problem", recommendation="Fix")]
        report.validator_reports = [vr]

        output = report.format_console(mode="quiet")

        # Should show only problems
        assert "Validator" in output
        assert "Problem" in output
        assert "Fix" in output
        # Should not have header
        assert "Health Check Summary" not in output

    def test_format_normal_mode(self):
        """Test normal mode formatting."""
        report = HealthReport()

        vr1 = ValidatorReport("Good Validator")
        vr1.results = [CheckResult.success("All good")]

        vr2 = ValidatorReport("Bad Validator")
        vr2.results = [CheckResult.warning("Issue found")]

        report.validator_reports = [vr1, vr2]

        output = report.format_console(mode="normal")

        # Should show all validators
        assert "Health Check Summary" in output
        assert "Good Validator" in output
        assert "Bad Validator" in output
        assert "passed" in output
        assert "warning(s)" in output
        # Should show problem details
        assert "Issue found" in output

    def test_format_verbose_mode(self):
        """Test verbose mode formatting."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [
            CheckResult.success("Everything OK"),
            CheckResult.info("FYI message"),
            CheckResult.warning("Warning message"),
        ]
        report.validator_reports = [vr]

        output = report.format_console(mode="verbose")

        # Should show everything including successes
        assert "Health Check Report" in output
        assert "Everything OK" in output
        assert "FYI message" in output
        assert "Warning message" in output

    def test_format_info_messages_shown(self):
        """Test that INFO-only validators are filtered out (by design)."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [CheckResult.info("Important info")]
        report.validator_reports = [vr]

        # In normal mode, INFO-only validators are filtered out (writers don't need that noise)
        output = report.format_console(mode="normal")
        # Should not show the validator since it only has INFO
        assert "Validator" not in output

    def test_format_legacy_verbose_parameter(self):
        """Test that legacy verbose=True parameter works."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [CheckResult.success("OK")]
        report.validator_reports = [vr]

        # Legacy parameter should trigger verbose mode
        output = report.format_console(verbose=True)
        assert "Health Check Report" in output

    def test_format_details_truncation(self):
        """Test that details are truncated after 3 items."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [
            CheckResult.warning(
                "Many issues", details=["issue1", "issue2", "issue3", "issue4", "issue5"]
            )
        ]
        report.validator_reports = [vr]

        output = report.format_console(mode="normal")

        # Should show first 3
        assert "issue1" in output
        assert "issue2" in output
        assert "issue3" in output
        # Should show "and X more"
        assert "and 2 more" in output

    def test_format_summary_line(self):
        """Test summary line formatting."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [
            CheckResult.success("OK"),
            CheckResult.warning("Warning"),
            CheckResult.error("Error"),
        ]
        report.validator_reports = [vr]

        output = report.format_console(mode="normal")

        # Should have summary with error/warning counts
        # Note: Summary line shows "X error(s), Y warning(s)" format
        assert "Summary:" in output
        assert "1 error" in output
        assert "1 warning" in output
        assert "Build Quality:" in output


class TestHealthReportJSON:
    """Test JSON export functionality."""

    def test_format_json(self):
        """Test JSON formatting."""
        report = HealthReport()
        vr = ValidatorReport("Test Validator")
        vr.results = [CheckResult.success("OK"), CheckResult.warning("Warning")]
        report.validator_reports = [vr]

        json_data = report.format_json()

        assert isinstance(json_data, dict)
        assert "timestamp" in json_data
        assert "summary" in json_data
        assert "validators" in json_data

        # Check summary
        assert json_data["summary"]["passed"] == 1
        assert json_data["summary"]["warnings"] == 1
        assert json_data["summary"]["quality_score"] > 0

        # Check validators
        assert len(json_data["validators"]) == 1
        assert json_data["validators"][0]["name"] == "Test Validator"
