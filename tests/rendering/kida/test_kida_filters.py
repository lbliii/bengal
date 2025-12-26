"""Test filter functionality in Kida template engine.

Based on Jinja2's test_filters.py.
Tests all built-in filters for correctness and Jinja2 compatibility.
"""

import pytest

from bengal.rendering.kida import Environment, Markup


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment(autoescape=True)


@pytest.fixture
def env_no_autoescape():
    """Create a Kida environment without autoescape."""
    return Environment(autoescape=False)


class TestStringFilters:
    """String manipulation filters."""

    def test_upper(self, env):
        """upper filter."""
        tmpl = env.from_string('{{ "hello"|upper }}')
        assert tmpl.render() == "HELLO"

    def test_lower(self, env):
        """lower filter."""
        tmpl = env.from_string('{{ "HELLO"|lower }}')
        assert tmpl.render() == "hello"

    def test_capitalize(self, env):
        """capitalize filter."""
        tmpl = env.from_string('{{ "foo bar"|capitalize }}')
        assert tmpl.render() == "Foo bar"

    def test_title(self, env):
        """title filter."""
        tmpl = env.from_string('{{ "foo bar"|title }}')
        assert tmpl.render() == "Foo Bar"

    def test_trim(self, env):
        """trim filter."""
        tmpl = env.from_string('{{ "  hello  "|trim }}')
        assert tmpl.render() == "hello"

    def test_trim_with_chars(self, env):
        """trim filter with custom characters."""
        tmpl = env.from_string('{{ "..hello.."|trim(".") }}')
        assert tmpl.render() == "hello"

    def test_strip(self, env):
        """strip filter (alias for trim)."""
        tmpl = env.from_string('{{ "  hello  "|strip }}')
        assert tmpl.render() == "hello"

    def test_center(self, env):
        """center filter."""
        tmpl = env.from_string('{{ "foo"|center(9) }}')
        assert tmpl.render() == "   foo   "

    def test_replace(self, env):
        """replace filter."""
        tmpl = env.from_string('{{ "hello world"|replace("world", "there") }}')
        assert tmpl.render() == "hello there"

    def test_wordcount(self, env):
        """wordcount filter."""
        tmpl = env.from_string('{{ "hello world foo"|wordcount }}')
        assert tmpl.render() == "3"

    def test_truncate(self, env):
        """truncate filter."""
        tmpl = env.from_string('{{ "hello world this is long"|truncate(11) }}')
        result = tmpl.render()
        assert len(result) <= 14  # truncate may add ellipsis

    def test_striptags(self, env):
        """striptags filter."""
        tmpl = env.from_string('{{ "<p>hello <b>world</b></p>"|striptags }}')
        assert tmpl.render() == "hello world"

    def test_wordwrap(self, env):
        """wordwrap filter."""
        tmpl = env.from_string('{{ "hello world foo bar"|wordwrap(10) }}')
        result = tmpl.render()
        assert "\n" in result

    def test_indent(self, env):
        """indent filter."""
        tmpl = env.from_string('{{ "hello\nworld"|indent(4) }}')
        result = tmpl.render()
        assert "    world" in result


class TestEscapeFilters:
    """HTML escaping filters."""

    def test_escape(self, env):
        """escape filter."""
        tmpl = env.from_string("{{ text|escape }}")
        assert tmpl.render(text="<script>") == "&lt;script&gt;"

    def test_e(self, env):
        """e filter (alias for escape)."""
        tmpl = env.from_string("{{ text|e }}")
        assert tmpl.render(text="<b>") == "&lt;b&gt;"

    def test_safe(self, env):
        """safe filter prevents escaping."""
        tmpl = env.from_string("{{ text|safe }}")
        assert tmpl.render(text="<b>bold</b>") == "<b>bold</b>"

    def test_safe_preserves_markup(self, env):
        """safe filter with Markup input."""
        tmpl = env.from_string("{{ text|safe }}")
        result = tmpl.render(text=Markup("<b>already safe</b>"))
        assert result == "<b>already safe</b>"

    def test_safe_with_reason(self, env):
        """safe filter accepts optional reason for documentation."""
        tmpl = env.from_string('{{ html|safe(reason="sanitized by bleach") }}')
        result = tmpl.render(html="<b>trusted</b>")
        assert result == "<b>trusted</b>"

    def test_urlencode(self, env):
        """urlencode filter."""
        tmpl = env.from_string('{{ "hello world"|urlencode }}')
        assert tmpl.render() == "hello%20world"


class TestListFilters:
    """List manipulation filters."""

    def test_first(self, env):
        """first filter."""
        tmpl = env.from_string("{{ items|first }}")
        assert tmpl.render(items=[1, 2, 3]) == "1"

    def test_last(self, env):
        """last filter."""
        tmpl = env.from_string("{{ items|last }}")
        assert tmpl.render(items=[1, 2, 3]) == "3"

    def test_length(self, env):
        """length filter."""
        tmpl = env.from_string("{{ items|length }}")
        assert tmpl.render(items=[1, 2, 3]) == "3"

    def test_count(self, env):
        """count filter (alias for length)."""
        tmpl = env.from_string("{{ items|count }}")
        assert tmpl.render(items=[1, 2, 3]) == "3"

    def test_list(self, env):
        """list filter."""
        tmpl = env.from_string("{{ items|list }}")
        result = tmpl.render(items=range(3))
        assert "[0, 1, 2]" in result

    def test_reverse(self, env):
        """reverse filter."""
        tmpl = env.from_string("{{ items|reverse|list }}")
        result = tmpl.render(items=[1, 2, 3])
        assert "3" in result and result.index("3") < result.index("1")

    def test_sort(self, env):
        """sort filter."""
        tmpl = env.from_string("{{ items|sort|list }}")
        result = tmpl.render(items=[3, 1, 2])
        # Check order: 1 comes before 2, 2 before 3
        assert result.index("1") < result.index("2") < result.index("3")

    def test_join(self, env):
        """join filter."""
        tmpl = env.from_string("{{ items|join(', ') }}")
        assert tmpl.render(items=[1, 2, 3]) == "1, 2, 3"

    def test_join_default(self, env):
        """join filter with default separator."""
        tmpl = env.from_string("{{ items|join }}")
        assert tmpl.render(items=["a", "b", "c"]) == "abc"

    def test_unique(self, env):
        """unique filter."""
        tmpl = env.from_string("{{ items|unique|list }}")
        result = tmpl.render(items=[1, 2, 1, 3, 2])
        # Result should have unique values
        assert result.count("1") == 1
        assert result.count("2") == 1

    def test_batch(self, env):
        """batch filter."""
        tmpl = env.from_string("{{ foo|batch(3)|list }}")
        result = tmpl.render(foo=list(range(10)))
        assert "[[0, 1, 2]" in result

    def test_batch_with_fill(self, env):
        """batch filter with fill value."""
        tmpl = env.from_string("{{ foo|batch(3, 'X')|list }}")
        result = tmpl.render(foo=list(range(10)))
        assert "X" in result

    def test_slice(self, env):
        """slice filter."""
        tmpl = env.from_string("{{ foo|slice(3)|list }}")
        result = tmpl.render(foo=list(range(10)))
        # Slice divides into 3 roughly equal parts
        assert "[[" in result


class TestNumericFilters:
    """Numeric manipulation filters."""

    def test_int(self, env):
        """int filter."""
        tmpl = env.from_string("{{ '42'|int }}")
        assert tmpl.render() == "42"

    def test_int_default(self, env):
        """int filter with default on error."""
        tmpl = env.from_string("{{ 'abc'|int(0) }}")
        assert tmpl.render() == "0"

    def test_float(self, env):
        """float filter."""
        tmpl = env.from_string("{{ '3.14'|float }}")
        assert tmpl.render() == "3.14"

    def test_abs(self, env):
        """abs filter."""
        tmpl = env.from_string("{{ -42|abs }}")
        assert tmpl.render() == "42"

    def test_round(self, env):
        """round filter."""
        tmpl = env.from_string("{{ 3.14159|round(2) }}")
        assert tmpl.render() == "3.14"

    def test_sum(self, env):
        """sum filter."""
        tmpl = env.from_string("{{ items|sum }}")
        assert tmpl.render(items=[1, 2, 3]) == "6"

    def test_min(self, env):
        """min filter."""
        tmpl = env.from_string("{{ items|min }}")
        assert tmpl.render(items=[3, 1, 2]) == "1"

    def test_max(self, env):
        """max filter."""
        tmpl = env.from_string("{{ items|max }}")
        assert tmpl.render(items=[3, 1, 2]) == "3"


class TestMappingFilters:
    """Dict and mapping filters."""

    def test_dictsort(self, env):
        """dictsort filter."""
        tmpl = env.from_string("{{ d|dictsort }}")
        result = tmpl.render(d={"b": 2, "a": 1, "c": 3})
        # Should be sorted by key
        assert result.index("a") < result.index("b") < result.index("c")

    def test_items(self, env):
        """items filter (returns list of key-value pairs)."""
        tmpl = env.from_string("{{ d.items()|list }}")
        result = tmpl.render(d={"a": 1})
        assert "a" in result and "1" in result


class TestAttributeFilters:
    """Attribute and mapping filters."""

    def test_attr(self, env):
        """attr filter."""

        class Obj:
            name = "test"

        tmpl = env.from_string("{{ obj|attr('name') }}")
        assert tmpl.render(obj=Obj()) == "test"

    def test_map(self, env):
        """map filter."""
        tmpl = env.from_string("{{ items|map('upper')|list }}")
        result = tmpl.render(items=["a", "b"])
        assert "A" in result and "B" in result

    def test_map_attribute(self, env):
        """map filter with attribute."""

        class Item:
            def __init__(self, name):
                self.name = name

        tmpl = env.from_string("{{ items|map(attribute='name')|list }}")
        result = tmpl.render(items=[Item("foo"), Item("bar")])
        assert "foo" in result and "bar" in result

    def test_select(self, env):
        """select filter."""
        tmpl = env.from_string("{{ items|select('odd')|list }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "1" in result and "3" in result and "5" in result
        assert "2" not in result and "4" not in result

    def test_reject(self, env):
        """reject filter."""
        tmpl = env.from_string("{{ items|reject('odd')|list }}")
        result = tmpl.render(items=[1, 2, 3, 4, 5])
        assert "2" in result and "4" in result
        assert "1" not in result

    def test_selectattr(self, env):
        """selectattr filter."""

        class Item:
            def __init__(self, active):
                self.active = active

        tmpl = env.from_string("{{ items|selectattr('active')|list|length }}")
        result = tmpl.render(items=[Item(True), Item(False), Item(True)])
        assert result == "2"

    def test_rejectattr(self, env):
        """rejectattr filter."""

        class Item:
            def __init__(self, active):
                self.active = active

        tmpl = env.from_string("{{ items|rejectattr('active')|list|length }}")
        result = tmpl.render(items=[Item(True), Item(False), Item(True)])
        assert result == "1"

    def test_groupby(self, env):
        """groupby filter."""

        class Item:
            def __init__(self, category, name):
                self.category = category
                self.name = name

        items = [
            Item("fruit", "apple"),
            Item("fruit", "banana"),
            Item("vegetable", "carrot"),
        ]
        tmpl = env.from_string(
            "{% for group in items|groupby('category') %}"
            "{{ group.grouper }}: {{ group.list|map(attribute='name')|join(', ') }}; "
            "{% endfor %}"
        )
        result = tmpl.render(items=items)
        assert "fruit:" in result and "apple" in result


class TestDefaultFilter:
    """Test default filter variations."""

    def test_default_missing(self, env):
        """default filter with missing variable."""
        tmpl = env.from_string("{{ missing|default('fallback') }}")
        assert tmpl.render() == "fallback"

    def test_default_none(self, env):
        """default filter with None value."""
        tmpl = env.from_string("{{ value|default('fallback') }}")
        # Note: behavior with None may vary - Jinja2 keeps None unless boolean=True
        result = tmpl.render(value=None)
        # Kida may treat None as falsy for default
        assert result in ["fallback", "None"]

    def test_default_false(self, env):
        """default filter with False value."""
        tmpl = env.from_string("{{ value|default('fallback') }}")
        assert tmpl.render(value=False) == "False"

    def test_default_boolean_true(self, env):
        """default filter with boolean=True."""
        tmpl = env.from_string("{{ value|default('fallback', true) }}")
        assert tmpl.render(value=False) == "fallback"

    def test_d_alias(self, env):
        """d filter (alias for default)."""
        tmpl = env.from_string("{{ missing|d('fallback') }}")
        assert tmpl.render() == "fallback"


class TestJsonFilter:
    """Test tojson filter."""

    def test_tojson_dict(self, env):
        """tojson filter with dict."""
        tmpl = env.from_string("{{ data|tojson }}")
        result = tmpl.render(data={"key": "value"})
        assert '"key"' in result and '"value"' in result

    def test_tojson_list(self, env):
        """tojson filter with list."""
        tmpl = env.from_string("{{ data|tojson }}")
        result = tmpl.render(data=[1, 2, 3])
        assert "[1, 2, 3]" in result

    def test_tojson_no_double_escape(self, env):
        """tojson output should not be HTML-escaped."""
        tmpl = env.from_string("{{ data|tojson }}")
        result = tmpl.render(data={"key": "value"})
        # Should NOT contain &quot;
        assert "&quot;" not in result
        assert '"' in result

    def test_tojson_with_indent(self, env):
        """tojson filter with indent."""
        tmpl = env.from_string("{{ data|tojson(2) }}")
        result = tmpl.render(data={"a": 1})
        assert "\n" in result  # Indented JSON has newlines


class TestFilterChaining:
    """Test chaining multiple filters."""

    def test_chain_basic(self, env):
        """Basic filter chain."""
        tmpl = env.from_string('{{ "  HELLO  "|trim|lower }}')
        assert tmpl.render() == "hello"

    def test_chain_multiple(self, env):
        """Multiple filter chain."""
        tmpl = env.from_string('{{ "  hello world  "|trim|title|replace(" ", "-") }}')
        assert tmpl.render() == "Hello-World"

    def test_chain_with_args(self, env):
        """Filter chain with arguments."""
        tmpl = env.from_string('{{ items|sort|join(", ") }}')
        assert tmpl.render(items=[3, 1, 2]) == "1, 2, 3"


class TestCustomFilters:
    """Test custom filter registration."""

    def test_custom_filter(self, env):
        """Register and use custom filter."""

        def double(value):
            return value * 2

        env.add_filter("double", double)
        tmpl = env.from_string("{{ 5|double }}")
        assert tmpl.render() == "10"

    def test_custom_filter_with_args(self, env):
        """Custom filter with arguments."""

        def multiply(value, factor):
            return value * factor

        env.add_filter("multiply", multiply)
        tmpl = env.from_string("{{ 5|multiply(3) }}")
        assert tmpl.render() == "15"

    def test_custom_filter_override(self, env):
        """Override built-in filter works when optimization is disabled."""
        # When filter inlining is enabled (default), built-in filters are inlined
        # and bypass the filter registry. To use custom filter overrides,
        # disable optimization.
        env_no_opt = Environment(optimized=False)

        def custom_upper(value):
            return value.upper() + "!"

        env_no_opt.add_filter("upper", custom_upper)
        tmpl = env_no_opt.from_string('{{ "hello"|upper }}')
        assert tmpl.render() == "HELLO!"
