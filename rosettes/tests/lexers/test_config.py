"""Configuration format lexer tests (JSON, YAML, TOML)."""

from rosettes import tokenize


class TestJsonLexer:
    """JSON-specific tests."""

    def test_nested_object(self) -> None:
        """Tokenizes nested JSON."""
        code = '{"outer": {"inner": [1, 2, 3]}}'
        tokens = tokenize(code, "json")
        assert len(tokens) > 0
        types = {t.type.value for t in tokens}
        assert "s" in types
        assert "m" in types
        assert "p" in types

    def test_basic_types(self) -> None:
        """Tokenizes basic JSON types."""
        code = '{"str": "hello", "num": 42, "bool": true, "nil": null}'
        tokens = tokenize(code, "json")
        types = {t.type.value for t in tokens}
        assert "s" in types
        assert "m" in types
        assert "kc" in types
        assert "p" in types

    def test_arrays(self) -> None:
        """Tokenizes JSON arrays."""
        code = '["one", "two", "three"]'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 3

    def test_object_keys(self) -> None:
        """Tokenizes object keys correctly."""
        code = '{"name": "value", "count": 42}'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 3

    def test_float_numbers(self) -> None:
        """Tokenizes float numbers."""
        code = '{"price": 19.99, "rate": 0.05}'
        tokens = tokenize(code, "json")
        numbers = [t for t in tokens if t.type.value in ("m", "mf")]
        assert len(numbers) >= 2

    def test_scientific_notation(self) -> None:
        """Tokenizes scientific notation."""
        code = '{"big": 1.5e10, "small": 2.5e-5}'
        tokens = tokenize(code, "json")
        numbers = [t for t in tokens if t.type.value in ("m", "mf")]
        assert len(numbers) >= 2

    def test_negative_numbers(self) -> None:
        """Tokenizes negative numbers."""
        code = '{"temp": -20, "diff": -3.5}'
        tokens = tokenize(code, "json")
        values = [t.value for t in tokens]
        assert "-20" in values or ("-" in values and "20" in values)

    def test_escape_sequences(self) -> None:
        """Tokenizes escape sequences in strings."""
        code = '{"path": "C:\\\\Users\\\\name", "msg": "line1\\nline2"}'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 2

    def test_unicode_strings(self) -> None:
        """Tokenizes Unicode strings."""
        code = '{"emoji": "Hello 👋", "chinese": "你好"}'
        tokens = tokenize(code, "json")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 2

    def test_empty_structures(self) -> None:
        """Tokenizes empty objects and arrays."""
        code = '{"empty_obj": {}, "empty_arr": []}'
        tokens = tokenize(code, "json")
        punct = [t for t in tokens if t.type.value == "p"]
        assert len(punct) >= 6


class TestYamlLexer:
    """YAML-specific tests."""

    def test_anchor_alias(self) -> None:
        """Tokenizes anchors and aliases."""
        code = "defaults: &defaults\n  adapter: postgres\ndev:\n  <<: *defaults"
        tokens = tokenize(code, "yaml")
        values = [t.value for t in tokens]
        assert "&defaults" in values

    def test_multiline_indicator(self) -> None:
        """Tokenizes block scalar indicators."""
        code = "description: |\n  Multi\n  line"
        tokens = tokenize(code, "yaml")
        heredocs = [t for t in tokens if t.type.value == "sh"]
        assert len(heredocs) >= 1

    def test_key_value_pairs(self) -> None:
        """Tokenizes key-value pairs."""
        code = "name: John\nage: 30\nactive: true"
        tokens = tokenize(code, "yaml")
        attrs = [t for t in tokens if t.type.value == "na"]
        attr_values = {t.value for t in attrs}
        assert "name" in attr_values
        assert "age" in attr_values
        assert "active" in attr_values

    def test_nested_structure(self) -> None:
        """Tokenizes nested YAML."""
        code = "server:\n  host: localhost\n  port: 8080"
        tokens = tokenize(code, "yaml")
        attrs = [t for t in tokens if t.type.value == "na"]
        assert len(attrs) >= 3

    def test_list_items(self) -> None:
        """Tokenizes list items."""
        code = "items:\n  - first\n  - second\n  - third"
        tokens = tokenize(code, "yaml")
        values = [t.value for t in tokens]
        assert "-" in values

    def test_boolean_values(self) -> None:
        """Tokenizes boolean values."""
        code = "enabled: true\ndisabled: false\nyes_val: yes\nno_val: no"
        tokens = tokenize(code, "yaml")
        consts = [t for t in tokens if t.type.value == "kc"]
        assert len(consts) >= 2

    def test_null_values(self) -> None:
        """Tokenizes null values."""
        code = "empty: null\nalso_empty: ~"
        tokens = tokenize(code, "yaml")
        consts = [t for t in tokens if t.type.value == "kc"]
        assert len(consts) >= 1

    def test_quoted_strings(self) -> None:
        """Tokenizes quoted strings."""
        code = "message: 'Hello World'\npath: \"/usr/local/bin\""
        tokens = tokenize(code, "yaml")
        strings = [t for t in tokens if t.type.value in ("s", "s1", "s2")]
        assert len(strings) >= 2

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "# Configuration file\nname: app  # inline comment"
        tokens = tokenize(code, "yaml")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) >= 1

    def test_numbers(self) -> None:
        """Tokenizes numbers."""
        code = "port: 8080\nversion: 1.5\nhex: 0xFF"
        tokens = tokenize(code, "yaml")
        integers = [t for t in tokens if t.type.value == "mi"]
        floats = [t for t in tokens if t.type.value == "mf"]
        assert len(integers) >= 1
        assert len(floats) >= 1


class TestTomlLexer:
    """TOML-specific tests."""

    def test_array_of_tables(self) -> None:
        """Tokenizes array of tables."""
        code = "[[products]]\nname = 'hammer'"
        tokens = tokenize(code, "toml")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert any("products" in t.value for t in classes)

    def test_datetime(self) -> None:
        """Tokenizes datetime values."""
        code = "date = 2024-01-15T10:30:00Z"
        tokens = tokenize(code, "toml")
        dates = [t for t in tokens if t.type.value == "ld"]
        assert len(dates) >= 1

    def test_table_headers(self) -> None:
        """Tokenizes table headers."""
        code = "[package]\nname = 'my-app'\nversion = '1.0.0'"
        tokens = tokenize(code, "toml")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert any("package" in t.value for t in classes)

    def test_dotted_keys(self) -> None:
        """Tokenizes dotted keys."""
        code = "server.host = 'localhost'\nserver.port = 8080"
        tokens = tokenize(code, "toml")
        attrs = [t for t in tokens if t.type.value == "na"]
        assert len(attrs) >= 2

    def test_multiline_strings(self) -> None:
        """Tokenizes multiline strings."""
        code = 'text = """\nmulti\nline\n"""'
        tokens = tokenize(code, "toml")
        strings = [t for t in tokens if t.type.value in ("s", "s2", "sd")]
        assert len(strings) >= 1

    def test_arrays(self) -> None:
        """Tokenizes arrays."""
        code = "colors = ['red', 'green', 'blue']"
        tokens = tokenize(code, "toml")
        strings = [t for t in tokens if t.type.value == "s1"]
        assert len(strings) >= 3

    def test_inline_tables(self) -> None:
        """Tokenizes inline tables."""
        code = "point = { x = 1, y = 2 }"
        tokens = tokenize(code, "toml")
        values = [t.value for t in tokens]
        assert "{" in values
        assert "}" in values

    def test_boolean_values(self) -> None:
        """Tokenizes boolean values."""
        code = "enabled = true\ndisabled = false"
        tokens = tokenize(code, "toml")
        consts = [t for t in tokens if t.type.value == "kc"]
        assert len(consts) == 2

    def test_numbers(self) -> None:
        """Tokenizes various number formats."""
        code = "int = 42\nfloat = 3.14\nhex = 0xDEAD\nbin = 0b1010"
        tokens = tokenize(code, "toml")
        integers = [t for t in tokens if t.type.value == "mi"]
        floats = [t for t in tokens if t.type.value == "mf"]
        assert len(integers) >= 1
        assert len(floats) >= 1

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "# Configuration\nname = 'app'  # inline"
        tokens = tokenize(code, "toml")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) >= 1
