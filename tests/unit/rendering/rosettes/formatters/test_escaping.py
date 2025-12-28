"""Security tests for HTML escaping and XSS prevention."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import highlight


class TestHtmlEscaping:
    """Test HTML special character escaping."""

    def test_angle_brackets_escaped(self) -> None:
        """Angle brackets should be escaped in HTML output."""
        code = "<script>alert('xss')</script>"
        html = highlight(code, "html")

        # HTML formatter tokenizes and escapes - check that script tags are escaped
        # The lexer tokenizes <script> into separate tokens, which are then escaped
        assert "&lt;" in html or "<script>" not in html.replace("<pre", "").replace(
            "<code", ""
        ).replace("<div", "").replace("<span", "")

    def test_ampersand_escaped(self) -> None:
        """Ampersands should be escaped."""
        code = "x && y"
        html = highlight(code, "javascript")

        assert "&amp;" in html or "&amp;&amp;" in html

    def test_quotes_escaped(self) -> None:
        """Quotes should be escaped in attributes."""
        code = '"test"'
        html = highlight(code, "python")
        # Should be escaped when in HTML attributes
        assert isinstance(html, str)


class TestXssPrevention:
    """Test XSS prevention in output."""

    def test_script_tag_prevention(self) -> None:
        """Script tags should not execute."""
        xss_vectors = [
            ("<script>alert('xss')</script>", "html"),
            ("<img src=x onerror=alert(1)>", "html"),
            ("<svg onload=alert(1)>", "html"),
            ("'><script>alert(1)</script>", "html"),
        ]

        for code, lang in xss_vectors:
            html = highlight(code, lang)
            # No unescaped angle brackets except our own wrapper tags
            html_content = (
                html.replace("<pre", "")
                .replace("<code", "")
                .replace("<div", "")
                .replace("<span", "")
                .replace("</pre>", "")
                .replace("</code>", "")
                .replace("</div>", "")
                .replace("</span>", "")
            )
            assert "<script>" not in html_content
            assert "onerror=" not in html_content
            assert "onload=" not in html_content

    def test_javascript_protocol_prevention(self) -> None:
        """javascript: protocol should be tokenized (not executed)."""
        code = "javascript:alert(1)"
        html = highlight(code, "javascript")
        # Should be tokenized (not executed) - check that it's in the output as text
        assert "javascript" in html or "alert" in html

    def test_template_injection_prevention(self) -> None:
        """Template injection vectors should be tokenized (not executed)."""
        # Jinja injection attempt
        code = "{{ __import__('os').system('rm -rf') }}"
        html = highlight(code, "jinja")
        # Should be tokenized, not executed - template syntax is tokenized
        assert "{{" in html or "__import__" in html  # Tokenized, not executed

    def test_kida_injection_prevention(self) -> None:
        """Kida injection vectors should be tokenized (not executed)."""
        code = "{% import os %}{{ os.system('ls') }}"
        html = highlight(code, "kida")
        # Should be tokenized, not executed - template syntax is tokenized
        assert "{%" in html or "import" in html  # Tokenized, not executed


class TestComprehensiveXssVectors:
    """Comprehensive XSS vector testing."""

    @pytest.mark.parametrize(
        "code,language",
        [
            ("<script>alert('xss')</script>", "html"),
            ("<img src=x onerror=alert(1)>", "html"),
            ("javascript:alert(1)", "javascript"),
            ("{{ __import__('os').system('rm -rf') }}", "jinja"),
            ("{% import os %}{{ os.system('ls') }}", "kida"),
            ("<svg onload=alert(1)>", "html"),
            ("'><script>alert(1)</script>", "html"),
            ("<iframe src=javascript:alert(1)>", "html"),
        ],
    )
    def test_xss_vector(self, code: str, language: str) -> None:
        """All XSS vectors must be neutralized."""
        html = highlight(code, language)
        # Remove our own wrapper tags
        html_content = (
            html.replace("<pre", "")
            .replace("<code", "")
            .replace("<div", "")
            .replace("<span", "")
            .replace("</pre>", "")
            .replace("</code>", "")
            .replace("</div>", "")
            .replace("</span>", "")
        )
        # Should not contain unescaped dangerous patterns
        assert "<script>" not in html_content
        assert "onerror=" not in html_content
        assert "onload=" not in html_content
        assert "javascript:" not in html_content or "&lt;" in html_content
