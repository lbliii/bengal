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

    def test_is_problem(self):
        """Test is_problem method."""
        assert not CheckResult.success("OK").is_problem()
        assert not CheckResult.info("Info").is_problem()
        assert CheckResult.warning("Warning").is_problem()
        assert CheckResult.error("Error").is_problem()


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
        """Test build quality score calculation."""
        report = HealthReport()
        vr = ValidatorReport("Test")

        # Perfect score
        vr.results = [
            CheckResult.success("OK 1"),
            CheckResult.success("OK 2"),
        ]
        report.validator_reports = [vr]
        assert report.build_quality_score() == 100

        # Mixed results
        vr.results = [
            CheckResult.success("OK"),  # 1.0 point
            CheckResult.info("Info"),  # 0.8 points
            CheckResult.warning("Warning"),  # 0.5 points
            CheckResult.error("Error"),  # 0.0 points
        ]
        # Total: 2.3 / 4 = 57.5% = 57
        score = report.build_quality_score()
        assert 55 <= score <= 60  # Allow some rounding variance

    def test_quality_rating(self):
        """Test quality rating labels."""
        report = HealthReport()
        vr = ValidatorReport("Test")
        report.validator_reports = [vr]

        # Excellent (95+)
        vr.results = [CheckResult.success("OK")] * 20
        assert report.quality_rating() == "Excellent"

        # Good (85-94)
        vr.results = [CheckResult.success("OK")] * 9 + [CheckResult.warning("W")]
        rating = report.quality_rating()
        assert rating in ["Good", "Excellent"]

        # Fair (70-84)
        vr.results = [CheckResult.success("OK")] * 7 + [CheckResult.warning("W")] * 3
        rating = report.quality_rating()
        assert rating in ["Fair", "Good"]


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
        """Test that INFO messages are visible (regression test for bug)."""
        report = HealthReport()
        vr = ValidatorReport("Validator")
        vr.results = [CheckResult.info("Important info")]
        report.validator_reports = [vr]

        # In normal mode, should show INFO count
        output = report.format_console(mode="normal")
        assert "1 info" in output or "info" in output.lower()

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

        # Should have summary with counts
        assert "Summary:" in output
        assert "1 passed" in output
        assert "1 warning" in output
        assert "1 error" in output
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
