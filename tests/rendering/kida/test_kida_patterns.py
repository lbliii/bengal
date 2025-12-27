"""Advanced pattern matching tests for Kida template engine.

Tests for structural matching, multiple subjects, and guard conditions in {% match %}.
"""


class TestStructuralMatching:
    """Tests for structural pattern matching in {% match %}."""

    def test_match_tuple_subject(self, env):
        """Match with multiple expressions (implicit tuple)."""
        template = env.from_string("""
        {% match site.logo, site.logo_text %}
            {% case logo, _ if logo %}Logo: {{ logo }}
            {% case _, text if text %}Text: {{ text }}
            {% case _ %}None
        {% end %}
        """)
        # Case 1: Logo exists
        assert "Logo: logo.png" in template.render(site={"logo": "logo.png", "logo_text": "Bengal"})
        # Case 2: Only text exists
        assert "Text: Bengal" in template.render(site={"logo": None, "logo_text": "Bengal"})
        # Case 3: Neither exists
        assert "None" in template.render(site={"logo": None, "logo_text": None})

    def test_match_explicit_tuple_subject(self, env):
        """Match with explicit tuple subject."""
        template = env.from_string("""
        {% match (x, y) %}
            {% case 1, 1 %}Both One
            {% case 1, _ %}First One
            {% case _, 1 %}Second One
            {% case _ %}Other
        {% end %}
        """)
        assert "Both One" in template.render(x=1, y=1)
        assert "First One" in template.render(x=1, y=2)
        assert "Second One" in template.render(x=2, y=1)
        assert "Other" in template.render(x=2, y=2)

    def test_match_binding_patterns(self, env):
        """Patterns can bind values to names."""
        template = env.from_string("""
        {% match item %}
            {% case (x, y) %}Point: {{ x }},{{ y }}
            {% case x %}Value: {{ x }}
        {% end %}
        """)
        assert "Point: 10,20" in template.render(item=(10, 20))
        assert "Value: hello" in template.render(item="hello")

    def test_match_with_complex_guards(self, env):
        """Match cases with guard conditions."""
        template = env.from_string("""
        {% match x %}
            {% case n if n > 0 %}Positive: {{ n }}
            {% case n if n < 0 %}Negative: {{ n }}
            {% case _ %}Zero
        {% end %}
        """)
        assert "Positive: 42" in template.render(x=42)
        assert "Negative: -5" in template.render(x=-5)
        assert "Zero" in template.render(x=0)

    def test_nested_structural_matching(self, env):
        """Match with nested tuple patterns."""
        template = env.from_string("""
        {% match data %}
            {% case (id, (x, y)) %}ID {{ id }} at {{ x }},{{ y }}
            {% case _ %}Unknown
        {% end %}
        """)
        assert "ID 1 at 10,20" in template.render(data=(1, (10, 20)))
        assert "Unknown" in template.render(data=(1, 2))

    def test_match_list_subject(self, env):
        """Match works with list subjects too."""
        template = env.from_string("""
        {% match items %}
            {% case x, y %}Two: {{ x }}, {{ y }}
            {% case _ %}Other
        {% end %}
        """)
        assert "Two: a, b" in template.render(items=["a", "b"])

    def test_match_literal_in_pattern(self, env):
        """Mix literals and names in patterns."""
        template = env.from_string("""
        {% match action, value %}
            {% case "add", n %}Adding {{ n }}
            {% case "sub", n %}Subtracting {{ n }}
            {% case _ %}Unknown
        {% end %}
        """)
        assert "Adding 10" in template.render(action="add", value=10)
        assert "Subtracting 5" in template.render(action="sub", value=5)

    def test_match_runtime_builtins(self, env):
        """Ensure structural matching built-ins (_isinstance, _len) are available."""
        # This test ensures the fix for 'isinstance' not defined is working
        template = env.from_string("""
        {% match (1, 2) %}
            {% case a, b %}OK: {{ a }},{{ b }}
        {% end %}
        """)
        assert "OK: 1,2" in template.render()

    def test_match_with_walrus_short_circuit(self, env):
        """Ensure bindings are available in guards (via walrus operators)."""
        template = env.from_string("""
        {% match (10, 20) %}
            {% case x, y if x + y == 30 %}Sum is 30
            {% case _ %}Fail
        {% end %}
        """)
        assert "Sum is 30" in template.render()
