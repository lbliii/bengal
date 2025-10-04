"""
Unit tests for template validation system.
"""

import pytest
from pathlib import Path
from jinja2 import Environment

from bengal.rendering.validator import TemplateValidator, validate_templates


class MockTemplateEngine:
    """Mock template engine for testing."""
    
    def __init__(self, template_dirs=None):
        self.template_dirs = template_dirs or []
        self.env = Environment()
        self.env.filters['markdown'] = lambda x: x
        self.env.filters['dateformat'] = lambda x, y: x
    
    def _find_template_path(self, template_name):
        """Find template path."""
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                return template_path
        return None


class TestTemplateValidator:
    """Tests for TemplateValidator."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        mock_engine = MockTemplateEngine()
        validator = TemplateValidator(mock_engine)
        
        assert validator.template_engine == mock_engine
        assert validator.env == mock_engine.env
    
    def test_validate_all_empty_dirs(self):
        """Test validation with no template directories."""
        mock_engine = MockTemplateEngine(template_dirs=[])
        validator = TemplateValidator(mock_engine)
        
        errors = validator.validate_all()
        assert errors == []
    
    def test_validate_all_nonexistent_dir(self):
        """Test validation with non-existent directory."""
        mock_engine = MockTemplateEngine(
            template_dirs=[Path("/nonexistent/path")]
        )
        validator = TemplateValidator(mock_engine)
        
        errors = validator.validate_all()
        assert errors == []
    
    def test_validate_syntax_valid_template(self, tmp_path):
        """Test syntax validation of valid template."""
        # Create a valid template
        template_file = tmp_path / "valid.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }}</title>
</head>
<body>
    {% if page.content %}
        {{ page.content }}
    {% endif %}
</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_syntax("valid.html", template_file)
        assert len(errors) == 0
    
    def test_validate_syntax_invalid_template(self, tmp_path):
        """Test syntax validation of invalid template."""
        # Create an invalid template (missing endif)
        template_file = tmp_path / "invalid.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<body>
    {% if page.content %}
        {{ page.content }}
    {# Missing endif #}
</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_syntax("invalid.html", template_file)
        assert len(errors) == 1
        assert errors[0].error_type == 'syntax'
    
    def test_validate_includes_all_exist(self, tmp_path):
        """Test include validation when all includes exist."""
        # Create base template
        base_template = tmp_path / "base.html"
        base_template.write_text("<html><body>{% block content %}{% endblock %}</body></html>")
        
        # Create partial template
        partial_template = tmp_path / "partial.html"
        partial_template.write_text("<div>Partial content</div>")
        
        # Create template with include
        template_file = tmp_path / "page.html"
        template_file.write_text("""
{% extends "base.html" %}
{% block content %}
    {% include "partial.html" %}
{% endblock %}
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_includes("page.html", template_file)
        assert len(errors) == 0
    
    def test_validate_includes_missing(self, tmp_path):
        """Test include validation when include is missing."""
        # Create template with missing include
        template_file = tmp_path / "page.html"
        template_file.write_text("""
<html>
<body>
    {% include "nonexistent.html" %}
</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_includes("page.html", template_file)
        assert len(errors) == 1
        assert "nonexistent.html" in errors[0].message
        assert errors[0].suggestion is not None
    
    def test_validate_all_integration(self, tmp_path):
        """Test full validation of template directory."""
        # Create templates
        valid_template = tmp_path / "valid.html"
        valid_template.write_text("""
<!DOCTYPE html>
<html>
<body>{% if page.title %}{{ page.title }}{% endif %}</body>
</html>
""")
        
        invalid_template = tmp_path / "invalid.html"
        invalid_template.write_text("""
<!DOCTYPE html>
<html>
<body>{% if page.title %}{{ page.title }}</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator.validate_all()
        
        # Should find error in invalid.html
        assert len(errors) >= 1
        error_files = [e.template_context.template_name for e in errors]
        assert "invalid.html" in error_files
    
    def test_validate_multiple_includes(self, tmp_path):
        """Test validation of template with multiple includes."""
        # Create partials
        (tmp_path / "header.html").write_text("<header>Header</header>")
        (tmp_path / "footer.html").write_text("<footer>Footer</footer>")
        
        # Create template with multiple includes
        template_file = tmp_path / "page.html"
        template_file.write_text("""
<html>
<body>
    {% include "header.html" %}
    <main>Content</main>
    {% include "footer.html" %}
    {% include "missing.html" %}
</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_includes("page.html", template_file)
        
        # Should only find error for missing.html
        assert len(errors) == 1
        assert "missing.html" in errors[0].message


class TestValidateTemplatesFunction:
    """Tests for validate_templates helper function."""
    
    def test_validate_templates_no_errors(self, tmp_path, capsys):
        """Test validate_templates with valid templates."""
        # Create valid template
        template_file = tmp_path / "valid.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<body>{% if page.title %}{{ page.title }}{% endif %}</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        
        error_count = validate_templates(mock_engine)
        
        assert error_count == 0
        
        captured = capsys.readouterr()
        assert "Validating templates" in captured.out
        assert "All templates valid" in captured.out
    
    def test_validate_templates_with_errors(self, tmp_path, capsys):
        """Test validate_templates with invalid templates."""
        # Create invalid template
        template_file = tmp_path / "invalid.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<body>{% if page.title %}{{ page.title }}</body>
</html>
""")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        
        error_count = validate_templates(mock_engine)
        
        assert error_count >= 1
        
        captured = capsys.readouterr()
        assert "Validating templates" in captured.out
        assert "Found" in captured.out
        assert "error" in captured.out


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_template_file(self, tmp_path):
        """Test validation of empty template file."""
        template_file = tmp_path / "empty.html"
        template_file.write_text("")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_syntax("empty.html", template_file)
        assert len(errors) == 0
    
    def test_template_with_no_includes(self, tmp_path):
        """Test validation of template with no includes."""
        template_file = tmp_path / "no_includes.html"
        template_file.write_text("<html><body>Static content</body></html>")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_includes("no_includes.html", template_file)
        assert len(errors) == 0
    
    def test_template_with_comments_only(self, tmp_path):
        """Test validation of template with only comments."""
        template_file = tmp_path / "comments.html"
        template_file.write_text("{# This is a comment #}\n{# Another comment #}")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator._validate_syntax("comments.html", template_file)
        assert len(errors) == 0
    
    def test_nested_template_directory(self, tmp_path):
        """Test validation with nested template directories."""
        # Create nested structure
        partials_dir = tmp_path / "partials"
        partials_dir.mkdir()
        
        template_file = partials_dir / "nested.html"
        template_file.write_text("<div>Nested template</div>")
        
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
        validator = TemplateValidator(mock_engine)
        
        errors = validator.validate_all()
        assert isinstance(errors, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

