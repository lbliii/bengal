"""
Tests for TemplateValidationService protocol and implementations.

Covers:
- Protocol conformance tests
- DefaultTemplateValidationService adapter tests
- Mock implementation tests for testing scenarios
- Engine-agnostic validation tests
- TemplateError conversion tests
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bengal.rendering.engines.errors import TemplateError
from bengal.services.validation import (
    DefaultTemplateValidationService,
    TemplateValidationService,
    _default_engine_factory,
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

    def test_validate_returns_integer(self):
        """validate() returns integer error count."""
        mock_engine = MagicMock()
        mock_validator = MagicMock(return_value=0)

        service = DefaultTemplateValidationService(
            engine_factory=lambda site: mock_engine,
            validator=mock_validator,
        )
        mock_site = MagicMock()

        result = service.validate(mock_site)

        assert isinstance(result, int)
        assert result == 0
        mock_validator.assert_called_once_with(mock_engine)

    def test_validate_propagates_error_count(self):
        """validate() returns error count from underlying validator."""
        mock_validator = MagicMock(return_value=5)

        service = DefaultTemplateValidationService(
            engine_factory=lambda site: MagicMock(),
            validator=mock_validator,
        )
        mock_site = MagicMock()

        result = service.validate(mock_site)

        assert result == 5

    def test_validate_creates_engine_with_site(self):
        """validate() passes site to engine factory."""
        captured_site = None

        def capturing_factory(site):
            nonlocal captured_site
            captured_site = site
            return MagicMock()

        service = DefaultTemplateValidationService(
            engine_factory=capturing_factory,
            validator=lambda engine: 0,
        )
        mock_site = MagicMock()
        mock_site.config = {"theme": "default"}

        service.validate(mock_site)

        assert captured_site is mock_site

    def test_validate_passes_engine_to_validator(self):
        """validate() passes created engine to validator."""
        mock_engine = MagicMock()
        captured_engine = None

        def capturing_validator(engine):
            nonlocal captured_engine
            captured_engine = engine
            return 0

        service = DefaultTemplateValidationService(
            engine_factory=lambda site: mock_engine,
            validator=capturing_validator,
        )
        mock_site = MagicMock()

        service.validate(mock_site)

        assert captured_engine is mock_engine

    def test_default_factories_are_callable(self):
        """Default engine_factory and validator are set to callable defaults."""
        service = DefaultTemplateValidationService()

        assert callable(service.engine_factory)
        assert callable(service.validator)


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

    def test_validation_returns_error_count(self, mock_site):
        """Test validation returns error count from validator."""
        mock_validator = MagicMock(return_value=2)

        service = DefaultTemplateValidationService(
            engine_factory=lambda site: MagicMock(),
            validator=mock_validator,
        )
        error_count = service.validate(mock_site)

        assert error_count == 2

    def test_validation_can_be_swapped(self, mock_site):
        """Test that validation service can be easily swapped."""

        # Original service with mock dependencies
        mock_validator = MagicMock(return_value=3)
        original = DefaultTemplateValidationService(
            engine_factory=lambda site: MagicMock(),
            validator=mock_validator,
        )

        # Custom no-op service for testing
        @dataclass
        class NoOpService:
            def validate(self, site: Any) -> int:
                return 0

        # Both satisfy the protocol and can be used interchangeably
        def validate_site(service: TemplateValidationService, site: Any) -> int:
            return service.validate(site)

        # Original service returns actual validation result
        assert validate_site(original, mock_site) == 3

        # Custom service bypasses validation
        custom = NoOpService()
        assert validate_site(custom, mock_site) == 0


class TestDefaultEngineFactory:
    """Tests for the default engine factory function.
    
    These tests ensure the factory uses the correct engine creation path,
    which would have caught Bug #2 (deprecated shim usage).
    """

    def test_factory_uses_create_engine(self, tmp_path):
        """Default factory should use create_engine(), not deprecated shim."""
        # Verify the factory function imports from the correct module
        import inspect
        source = inspect.getsource(_default_engine_factory)
        
        # Should use create_engine from bengal.rendering.engines
        assert "from bengal.rendering.engines import create_engine" in source
        # Should NOT use deprecated shim
        assert "from bengal.rendering.template_engine" not in source

    def test_factory_respects_engine_config(self, tmp_path):
        """Factory should create engine based on site config."""
        site = MagicMock()
        site.root_path = tmp_path
        site.theme = "default"
        site.output_dir = tmp_path / "public"
        site.menu = {}
        site.menu_localized = {}
        site.config = {
            "template_engine": "kida",
            "production": False,
            "development": {"auto_reload": False},
        }
        
        engine = _default_engine_factory(site)
        
        # Should create Kida engine when configured
        assert type(engine).__name__ == "KidaTemplateEngine"


class TestTemplateValidatorEngineAgnostic:
    """Tests ensuring TemplateValidator works with any engine.
    
    These tests would have caught Bug #1 (Jinja2-specific env.parse() call).
    """

    def test_validator_uses_engine_validate_method(self):
        """TemplateValidator should call engine.validate(), not env.parse()."""
        from bengal.health.validators.templates import TemplateValidator
        
        # Create mock engine with validate() method
        mock_engine = MagicMock()
        mock_engine.validate.return_value = []
        mock_engine.template_dirs = []
        
        validator = TemplateValidator(mock_engine)
        errors = validator.validate_all()
        
        # Should call engine.validate()
        mock_engine.validate.assert_called_once()
        assert errors == []

    def test_validator_converts_template_errors(self):
        """TemplateValidator should convert TemplateError to TemplateRenderError."""
        from bengal.health.validators.templates import TemplateValidator
        from bengal.rendering.errors import TemplateRenderError
        
        mock_engine = MagicMock()
        mock_engine.validate.return_value = [
            TemplateError(
                template="test.html",
                message="Syntax error on line 5",
                line=5,
                error_type="syntax",
            ),
        ]
        mock_engine.get_template_path.return_value = Path("/tmp/test.html")
        
        validator = TemplateValidator(mock_engine)
        errors = validator.validate_all()
        
        assert len(errors) == 1
        assert isinstance(errors[0], TemplateRenderError)
        assert errors[0].message == "Syntax error on line 5"
        assert errors[0].template_context.template_name == "test.html"
        assert errors[0].template_context.line_number == 5

    def test_validator_handles_multiple_errors(self):
        """TemplateValidator should handle multiple validation errors."""
        from bengal.health.validators.templates import TemplateValidator
        
        mock_engine = MagicMock()
        mock_engine.validate.return_value = [
            TemplateError(template="a.html", message="Error A", line=1, error_type="syntax"),
            TemplateError(template="b.html", message="Error B", line=2, error_type="undefined"),
            TemplateError(template="c.html", message="Error C", line=None, error_type="other"),
        ]
        mock_engine.get_template_path.return_value = None
        
        validator = TemplateValidator(mock_engine)
        errors = validator.validate_all()
        
        assert len(errors) == 3
        assert errors[0].template_context.template_name == "a.html"
        assert errors[1].template_context.template_name == "b.html"
        assert errors[2].template_context.template_name == "c.html"

    def test_validator_handles_none_line_number(self):
        """TemplateValidator should handle errors without line numbers."""
        from bengal.health.validators.templates import TemplateValidator
        
        mock_engine = MagicMock()
        mock_engine.validate.return_value = [
            TemplateError(template="test.html", message="Unknown error", line=None),
        ]
        mock_engine.get_template_path.return_value = None
        
        validator = TemplateValidator(mock_engine)
        errors = validator.validate_all()
        
        assert len(errors) == 1
        assert errors[0].template_context.line_number is None


class TestEngineProtocolCompliance:
    """Tests verifying engines implement required protocol for validation.
    
    These contract tests ensure any engine used with the validation service
    has the methods needed for validation to work.
    """

    @pytest.fixture
    def minimal_site(self, tmp_path):
        """Create minimal site fixture for engine creation."""
        site = MagicMock()
        site.root_path = tmp_path
        site.theme = "default"
        site.output_dir = tmp_path / "public"
        site.menu = {}
        site.menu_localized = {}
        site.config = {
            "production": False,
            "development": {"auto_reload": False},
        }
        return site

    def test_kida_engine_has_validate_method(self, minimal_site):
        """Kida engine must implement validate() method."""
        minimal_site.config["template_engine"] = "kida"
        
        from bengal.rendering.engines import create_engine
        engine = create_engine(minimal_site)
        
        assert hasattr(engine, "validate")
        assert callable(engine.validate)
        
        # validate() should return list of TemplateError
        result = engine.validate()
        assert isinstance(result, list)

    def test_jinja_engine_has_validate_method(self, minimal_site):
        """Jinja engine must implement validate() method."""
        minimal_site.config["template_engine"] = "jinja2"
        
        from bengal.rendering.engines import create_engine
        engine = create_engine(minimal_site)
        
        assert hasattr(engine, "validate")
        assert callable(engine.validate)
        
        # validate() should return list of TemplateError
        result = engine.validate()
        assert isinstance(result, list)

    def test_engines_have_get_template_path_method(self, minimal_site):
        """Engines must implement get_template_path() for error context."""
        for engine_name in ["kida", "jinja2"]:
            minimal_site.config["template_engine"] = engine_name
            
            from bengal.rendering.engines import create_engine
            engine = create_engine(minimal_site)
            
            assert hasattr(engine, "get_template_path"), f"{engine_name} missing get_template_path"
            assert callable(engine.get_template_path)
