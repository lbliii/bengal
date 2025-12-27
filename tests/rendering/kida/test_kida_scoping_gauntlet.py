"""The Scoping Gauntlet: Complex stress tests for Kida template engine.

Tests for deep structural unpacking, scoping cross-pollination,
nil-resilience, and recursive macros with pattern matching.
"""


class TestScopingGauntlet:
    """The Scoping Gauntlet: Stress testing Kida's architectural limits."""

    def test_structural_nesting_gauntlet(self, env):
        """Test deep nested structural unpacking in various tags."""
        template = env.from_string("""
        {% set (a, (b, c)), d = ([1, [2, 3]], 4) %}
        {% let (x, y), z = ([10, 20], 30) %}
        {% export (m, n) = (100, 200) %}

        Set: {{ a }}, {{ b }}, {{ c }}, {{ d }}
        Let: {{ x }}, {{ y }}, {{ z }}
        Export: {{ m }}, {{ n }}
        """)
        rendered = template.render()
        assert "Set: 1, 2, 3, 4" in rendered
        assert "Let: 10, 20, 30" in rendered
        assert "Export: 100, 200" in rendered

    def test_scoping_cross_pollination(self, env):
        """Test let, set, and export interaction inside patterns and with."""
        # A case that uses let, an inner loop that uses export
        template = env.from_string("""
        {% let outer = 1 %}
        {% with (site.meta ?? (none, none)) as a, b %}
            {% match a, b %}
                {% case 1, _ %}
                    {% set inner = 2 %}
                    {% for i in [1] %}
                        {% export inner = outer + i + inner %}
                    {% end %}
                    Result: {{ inner }}
                {% case _ %}None
            {% end %}
        {% end %}
        """)
        # site.meta is (1, 'test'), so case 1, _ matches.
        # outer(1) + i(1) + inner(2) = 4.
        # export inner should update the inner variable in the match case scope.
        assert "Result: 4" in template.render(site={"meta": (1, "test")})

    def test_nil_resilience_depth(self, env):
        """Test optional chaining and null coalescing with conditional with."""
        template = env.from_string("""
        {% with element?.metadata?.tags ?? [] as tags %}
            Tags: {% for t in tags %}{{ t }}{% if not loop.last %}, {% end %}{% end %}
        {% empty %}
            No tags found
        {% end %}
        """)
        # Case 1: Deep path exists
        assert "Tags: a, b" in template.render(element={"metadata": {"tags": ["a", "b"]}})
        # Case 2: Intermediate path missing
        assert "No tags found" in template.render(element={"metadata": None})
        # Case 3: Empty list (falsy) - WithConditional should skip
        assert "No tags found" in template.render(element={"metadata": {"tags": []}})

    def test_structural_unpacking_in_for(self, env):
        """Test nested tuple unpacking in for loops."""
        template = env.from_string("""
        {% for (id, (lat, lon)) in locations %}
            {{ id }}: {{ lat }} / {{ lon }}
        {% end %}
        """)
        locations = [("NYC", (40.71, -74.00)), ("LON", (51.50, -0.12))]
        rendered = template.render(locations=locations)
        assert "NYC: 40.71 / -74.0" in rendered
        assert "LON: 51.5 / -0.12" in rendered

    def test_with_multiple_subject_nil_resilience(self, env):
        """Test {% with a, b as x, y %} where one is missing."""
        template = env.from_string("""
        {% with site.logo, site.logo_text as logo, text %}
            Logo: {{ logo }}, Text: {{ text }}
        {% empty %}
            Missing branding
        {% end %}
        """)
        # Case 1: Both exist
        assert "Logo: logo.png, Text: Bengal" in template.render(
            site={"logo": "logo.png", "logo_text": "Bengal"}
        )
        # Case 2: One missing - WithConditional should skip if using truthy check on all
        assert "Missing branding" in template.render(site={"logo": None, "logo_text": "Bengal"})

    def test_recursive_pattern_macro(self, env):
        """Test recursive macro passing tuples for pattern matching."""
        template = env.from_string("""
        {%- def traverse(node) -%}
            {%- match node -%}
                {%- case "leaf", val -%}Leaf: {{ val }}
                {%- case "node", (left, right) -%}
                    Node: [{{ traverse(left) }} | {{ traverse(right) }}]
            {%- end -%}
        {%- enddef -%}
        {{ traverse(tree) }}
        """)
        tree = ("node", (("leaf", 1), ("node", (("leaf", 2), ("leaf", 3)))))
        rendered = template.render(tree=tree).strip()
        assert rendered == "Node: [Leaf: 1 | Node: [Leaf: 2 | Leaf: 3]]"

    def test_match_subject_side_effects(self, env):
        """Test that match subject is evaluated only once even with complex patterns."""

        # We use a stateful object to track calls, since macros render to strings
        class Tracker:
            def __init__(self):
                self.count = 0

            def get_val(self):
                self.count += 1
                return (1, 2)

        tracker = Tracker()
        template = env.from_string("""
        {% match tracker.get_val() %}
            {% case 3, 4 %}No
            {% case 1, 2 %}Yes: {{ tracker.count }}
            {% case _ %}Other
        {% end %}
        """)
        assert "Yes: 1" in template.render(tracker=tracker)
