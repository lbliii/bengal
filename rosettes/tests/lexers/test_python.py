"""Python lexer tests."""

from rosettes import tokenize


class TestPythonLexer:
    """Python-specific tests."""

    def test_function_definition(self) -> None:
        """Tokenizes function definitions."""
        code = "def hello(name: str) -> str:\n    return f'Hello {name}'"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "def" for t in keywords)

    def test_class_definition(self) -> None:
        """Tokenizes class definitions."""
        code = "class MyClass(BaseClass):\n    pass"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "class" for t in keywords)

    def test_decorators(self) -> None:
        """Tokenizes decorators."""
        code = "@property\n@staticmethod\ndef method(self): pass"
        tokens = tokenize(code, "python")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert any("@property" in t.value for t in decorators)
        assert any("@staticmethod" in t.value for t in decorators)

    def test_f_strings(self) -> None:
        """Tokenizes f-strings."""
        code = "name = 'World'\nmsg = f'Hello {name}!'"
        tokens = tokenize(code, "python")
        strings = [t for t in tokens if t.type.value == "s"]
        assert any("f'" in t.value or 'f"' in t.value for t in strings)

    def test_docstrings(self) -> None:
        """Tokenizes docstrings."""
        code = '"""This is a docstring."""'
        tokens = tokenize(code, "python")
        docs = [t for t in tokens if t.type.value == "sd"]
        assert len(docs) == 1

    def test_builtin_functions(self) -> None:
        """Tokenizes builtin functions."""
        code = "result = len(list(range(10)))"
        tokens = tokenize(code, "python")
        builtins = [t for t in tokens if t.type.value == "nb"]
        builtin_names = {t.value for t in builtins}
        assert "len" in builtin_names
        assert "list" in builtin_names
        assert "range" in builtin_names

    def test_keyword_constants(self) -> None:
        """Tokenizes True, False, None."""
        code = "x = True\ny = False\nz = None"
        tokens = tokenize(code, "python")
        consts = [t for t in tokens if t.type.value == "kc"]
        const_values = {t.value for t in consts}
        assert "True" in const_values
        assert "False" in const_values
        assert "None" in const_values

    def test_import_statements(self) -> None:
        """Tokenizes import statements."""
        code = "from typing import List, Dict\nimport os"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kn"]
        keyword_values = {t.value for t in keywords}
        assert "from" in keyword_values
        assert "import" in keyword_values

    def test_walrus_operator(self) -> None:
        """Tokenizes walrus operator."""
        code = "if (n := len(data)) > 10: pass"
        tokens = tokenize(code, "python")
        values = [t.value for t in tokens]
        assert ":=" in values

    def test_type_hints(self) -> None:
        """Tokenizes type hints with arrow."""
        code = "def process(data: list[int]) -> dict[str, int]: ..."
        tokens = tokenize(code, "python")
        values = [t.value for t in tokens]
        assert "->" in values

    def test_exception_names(self) -> None:
        """Tokenizes exception names."""
        code = "raise ValueError('invalid')"
        tokens = tokenize(code, "python")
        exceptions = [t for t in tokens if t.type.value == "ne"]
        assert any(t.value == "ValueError" for t in exceptions)

    def test_self_and_cls(self) -> None:
        """Tokenizes self and cls as pseudo-builtins."""
        code = "def method(self): return self.value"
        tokens = tokenize(code, "python")
        pseudo = [t for t in tokens if t.type.value == "bp"]
        assert any(t.value == "self" for t in pseudo)

    def test_numbers(self) -> None:
        """Tokenizes various number formats."""
        code = "a = 42\nb = 3.14\nc = 0xFF\nd = 0b1010\ne = 0o777"
        tokens = tokenize(code, "python")
        integers = [t for t in tokens if t.type.value == "mi"]
        floats = [t for t in tokens if t.type.value == "mf"]
        hex_nums = [t for t in tokens if t.type.value == "mh"]
        bin_nums = [t for t in tokens if t.type.value == "mb"]
        oct_nums = [t for t in tokens if t.type.value == "mo"]
        assert len(integers) >= 1
        assert len(floats) >= 1
        assert len(hex_nums) >= 1
        assert len(bin_nums) >= 1
        assert len(oct_nums) >= 1

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "x = 1  # This is a comment\ny = 2"
        tokens = tokenize(code, "python")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 1

    def test_lambda(self) -> None:
        """Tokenizes lambda expressions."""
        code = "fn = lambda x, y: x + y"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "lambda" for t in keywords)

    def test_async_await(self) -> None:
        """Tokenizes async/await."""
        code = "async def fetch():\n    result = await get_data()"
        tokens = tokenize(code, "python")
        keywords = [t for t in tokens if t.type.value == "k"]
        keyword_values = {t.value for t in keywords}
        assert "async" in keyword_values
        assert "await" in keyword_values
