"""
Tests for TemplateValidationService protocol and implementations.

Covers:
- Protocol conformance tests
- DefaultTemplateValidationService adapter tests
- Mock implementation tests for testing scenarios
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bengal.services.validation import (
    DefaultTemplateValidationService,
    TemplateValidationService,
)


class TestTemplateValidationServiceProtocol:
    """Tests for TemplateValidationService protocol conformance."""

    def test_protocol_defines_validate_method(self):
        """Protocol requires validate(site) -> int signature."""
        # Protocol should define validate method
        assert hasattr(TemplateValidationService, "validate")

    def test_default_service_conforms_to_protocol(self):
        """DefaultTemplateValidationService implements the protocol."""
        service = DefaultTemplateValidationService()
        # Should have validate method matching protocol signature
        assert hasattr(service, "validate")
        assert callable(service.validate)

    def test_custom_implementation_conforms_to_protocol(self):
        """Custom implementations can satisfy the protocol."""

        @dataclass
        class CustomValidationService:
            """Custom validation service that always passes."""

            def validate(self, site: Any) -> int:
                return 0  # No errors

        service = CustomValidationService()
        # Should satisfy protocol requirements
        assert hasattr(service, "validate")
        result = service.validate(None)
        assert isinstance(result, int)
        assert result == 0


class TestDefaultTemplateValidationService:
    """Tests for DefaultTemplateValidationService adapter."""

    def test_default_strict_is_false(self):
        """Default strict mode is False."""
        service = DefaultTemplateValidationService()
        assert service.strict is False

    def test_strict_can_be_set(self):
        """Strict mode can be configured."""
        service = DefaultTemplateValidationService(strict=True)
        assert service.strict is True

    def test_validate_returns_integer(self):
        """validate() returns integer error count."""
        service = DefaultTemplateValidationService()

        # Mock the imports within validate() - patch where they're looked up
        with (
            patch("bengal.rendering.template_engine.TemplateEngine") as MockEngine,
            patch("bengal.health.validators.templates.validate_templates") as mock_validate,
        ):
            mock_validate.return_value = 0
            mock_site = MagicMock()

            result = service.validate(mock_site)

            assert isinstance(result, int)
            assert result == 0
            MockEngine.assert_called_once_with(mock_site)
            mock_validate.assert_called_once()

    def test_validate_propagates_error_count(self):
        """validate() returns error count from underlying validator."""
        service = DefaultTemplateValidationService()

        with (
            patch("bengal.rendering.template_engine.TemplateEngine"),
            patch("bengal.health.validators.templates.validate_templates") as mock_validate,
        ):
            mock_validate.return_value = 5  # 5 errors
            mock_site = MagicMock()

            result = service.validate(mock_site)

            assert result == 5

    def test_validate_creates_template_engine_with_site(self):
        """validate() creates TemplateEngine with provided site."""
        service = DefaultTemplateValidationService()

        with (
            patch("bengal.rendering.template_engine.TemplateEngine") as MockEngine,
            patch("bengal.health.validators.templates.validate_templates"),
        ):
            mock_site = MagicMock()
            mock_site.config = {"theme": "default"}

            service.validate(mock_site)

            MockEngine.assert_called_once_with(mock_site)

    def test_validate_passes_engine_to_validator(self):
        """validate() passes created engine to validate_templates."""
        service = DefaultTemplateValidationService()

        with (
            patch("bengal.rendering.template_engine.TemplateEngine") as MockEngine,
            patch("bengal.health.validators.templates.validate_templates") as mock_validate,
        ):
            mock_engine_instance = MagicMock()
            MockEngine.return_value = mock_engine_instance
            mock_site = MagicMock()

            service.validate(mock_site)

            mock_validate.assert_called_once_with(mock_engine_instance)


class TestMockValidationService:
    """Tests for mock validation services used in testing scenarios."""

    def test_always_pass_service(self):
        """Mock service that always reports no errors."""

        @dataclass
        class AlwaysPassService:
            def validate(self, site: Any) -> int:
                return 0

        service = AlwaysPassService()
        assert service.validate(MagicMock()) == 0

    def test_always_fail_service(self):
        """Mock service that always reports errors."""

        @dataclass
        class AlwaysFailService:
            error_count: int = 1

            def validate(self, site: Any) -> int:
                return self.error_count

        service = AlwaysFailService(error_count=3)
        assert service.validate(MagicMock()) == 3

    def test_conditional_service(self):
        """Mock service that conditionally reports errors based on site state."""

        @dataclass
        class ConditionalService:
            def validate(self, site: Any) -> int:
                # Check for specific condition
                if hasattr(site, "pages") and len(site.pages) == 0:
                    return 1  # Error: no pages
                return 0

        service = ConditionalService()

        # Site with pages - no errors
        site_with_pages = MagicMock()
        site_with_pages.pages = [MagicMock()]
        assert service.validate(site_with_pages) == 0

        # Site without pages - one error
        site_no_pages = MagicMock()
        site_no_pages.pages = []
        assert service.validate(site_no_pages) == 1

    def test_recording_service(self):
        """Mock service that records validation calls for testing."""

        @dataclass
        class RecordingService:
            calls: list = None

            def __post_init__(self):
                if self.calls is None:
                    self.calls = []

            def validate(self, site: Any) -> int:
                self.calls.append(site)
                return 0

        service = RecordingService()
        mock_site1 = MagicMock()
        mock_site2 = MagicMock()

        service.validate(mock_site1)
        service.validate(mock_site2)

        assert len(service.calls) == 2
        assert service.calls[0] is mock_site1
        assert service.calls[1] is mock_site2


class TestValidationServiceIntegration:
    """Integration tests for validation service behavior."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for validation."""
        site = MagicMock()
        site.root_path = tmp_path
        site.config = {"strict_mode": False}
        site.pages = []
        site.sections = []
        site.theme = "default"
        return site

    def test_validation_with_strict_mode(self, mock_site):
        """Test validation behavior with strict mode."""
        mock_site.config["strict_mode"] = True

        with (
            patch("bengal.rendering.template_engine.TemplateEngine"),
            patch("bengal.health.validators.templates.validate_templates") as mock_validate,
        ):
            mock_validate.return_value = 2  # 2 errors

            service = DefaultTemplateValidationService(strict=True)
            error_count = service.validate(mock_site)

            # Should return error count regardless of strict mode
            # (strict mode handling is at CLI level, not service level)
            assert error_count == 2

    def test_validation_can_be_swapped(self, mock_site):
        """Test that validation service can be easily swapped."""

        # Original service
        original = DefaultTemplateValidationService()

        # Custom no-op service for testing
        @dataclass
        class NoOpService:
            def validate(self, site: Any) -> int:
                return 0

        # Both satisfy the protocol and can be used interchangeably
        def validate_site(service: TemplateValidationService, site: Any) -> int:
            return service.validate(site)

        with (
            patch("bengal.rendering.template_engine.TemplateEngine"),
            patch("bengal.health.validators.templates.validate_templates", return_value=3),
        ):
            # Original service returns actual validation result
            assert validate_site(original, mock_site) == 3

        # Custom service bypasses validation
        custom = NoOpService()
        assert validate_site(custom, mock_site) == 0
