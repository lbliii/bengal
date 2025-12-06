    def test_button_with_icon(self, parser):
        """Test button with icon."""
        markdown = """:::{button} /test/
    :icon: rocket
    Launch
    :::"""
        result = parser.parse(markdown, {})
        # Check for SVG icon or unicode fallback
        assert "rocket" in result or "🚀" in result or "<svg" in result
        assert "button-icon" in result

    def test_button_all_options(self, parser):
        """Test button with all options."""
        markdown = """:::{button} /signup/
    :color: primary
    :style: pill
    :size: large
    :icon: rocket
    
    Sign Up Free
    :::"""
        result = parser.parse(markdown, {})
        assert "button-primary" in result
        assert "button-pill" in result
        assert "button-lg" in result
        # Check for SVG icon or unicode fallback
        assert "rocket" in result or "🚀" in result or "<svg" in result
        assert "Sign Up Free" in result

    def test_button_invalid_color_fallback(self, parser):
