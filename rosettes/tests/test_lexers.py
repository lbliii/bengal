"""Tests for Rosettes lexers."""

import pytest

from rosettes import Token, TokenType, get_lexer, list_languages, supports_language, tokenize


class TestRegistry:
    """Tests for the lexer registry."""

    def test_get_lexer_python(self) -> None:
        """Can get Python lexer by name."""
        lexer = get_lexer("python")
        assert lexer.name == "python"

    def test_get_lexer_alias(self) -> None:
        """Can get lexer by alias."""
        py_lexer = get_lexer("python")
        alias_lexer = get_lexer("py")
        # Should be the same cached instance
        assert py_lexer is alias_lexer

    def test_get_lexer_unknown(self) -> None:
        """Unknown language raises LookupError."""
        with pytest.raises(LookupError, match="Unknown language"):
            get_lexer("nonexistent-language")

    def test_list_languages(self) -> None:
        """list_languages returns sorted list."""
        languages = list_languages()
        assert isinstance(languages, list)
        assert "python" in languages
        assert languages == sorted(languages)

    def test_supports_language(self) -> None:
        """supports_language checks availability."""
        assert supports_language("python") is True
        assert supports_language("py") is True
        assert supports_language("nonexistent") is False


class TestPythonLexer:
    """Tests for the Python lexer."""

    def test_keyword_def(self) -> None:
        """Tokenizes 'def' as KEYWORD_DECLARATION."""
        tokens = tokenize("def foo():", "python")
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION
        assert tokens[0].value == "def"

    def test_keyword_class(self) -> None:
        """Tokenizes 'class' as KEYWORD_DECLARATION."""
        tokens = tokenize("class Foo:", "python")
        assert tokens[0].type == TokenType.KEYWORD_DECLARATION
        assert tokens[0].value == "class"

    def test_keyword_constant(self) -> None:
        """Tokenizes True/False/None as KEYWORD_CONSTANT."""
        tokens = tokenize("True False None", "python")
        keywords = [t for t in tokens if t.type == TokenType.KEYWORD_CONSTANT]
        assert len(keywords) == 3
        assert {k.value for k in keywords} == {"True", "False", "None"}

    def test_keyword_namespace(self) -> None:
        """Tokenizes import/from as KEYWORD_NAMESPACE."""
        tokens = tokenize("from foo import bar", "python")
        namespace_kw = [t for t in tokens if t.type == TokenType.KEYWORD_NAMESPACE]
        assert len(namespace_kw) == 2
        assert namespace_kw[0].value == "from"
        assert namespace_kw[1].value == "import"

    def test_string_single(self) -> None:
        """Tokenizes single-quoted strings."""
        tokens = tokenize("'hello'", "python")
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "'hello'"

    def test_string_double(self) -> None:
        """Tokenizes double-quoted strings."""
        tokens = tokenize('"hello"', "python")
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == '"hello"'

    def test_docstring(self) -> None:
        """Tokenizes triple-quoted strings as STRING_DOC."""
        tokens = tokenize('"""docstring"""', "python")
        assert tokens[0].type == TokenType.STRING_DOC
        assert tokens[0].value == '"""docstring"""'

    def test_fstring(self) -> None:
        """Tokenizes f-strings."""
        tokens = tokenize('f"hello {name}"', "python")
        assert tokens[0].type == TokenType.STRING

    def test_raw_string(self) -> None:
        """Tokenizes raw strings."""
        tokens = tokenize(r'r"hello\n"', "python")
        assert tokens[0].type == TokenType.STRING

    def test_byte_string(self) -> None:
        """Tokenizes byte strings."""
        tokens = tokenize('b"hello"', "python")
        assert tokens[0].type == TokenType.STRING

    def test_comment(self) -> None:
        """Tokenizes comments."""
        tokens = tokenize("x = 1  # comment", "python")
        comments = [t for t in tokens if t.type == TokenType.COMMENT_SINGLE]
        assert len(comments) == 1
        assert "comment" in comments[0].value

    def test_decorator(self) -> None:
        """Tokenizes decorators."""
        tokens = tokenize("@property", "python")
        assert tokens[0].type == TokenType.NAME_DECORATOR
        assert tokens[0].value == "@property"

    def test_decorator_with_dots(self) -> None:
        """Tokenizes dotted decorators."""
        tokens = tokenize("@foo.bar.baz", "python")
        assert tokens[0].type == TokenType.NAME_DECORATOR

    def test_number_integer(self) -> None:
        """Tokenizes integers."""
        tokens = tokenize("42", "python")
        assert tokens[0].type == TokenType.NUMBER_INTEGER
        assert tokens[0].value == "42"

    def test_number_float(self) -> None:
        """Tokenizes floats."""
        tokens = tokenize("3.14", "python")
        assert tokens[0].type == TokenType.NUMBER_FLOAT

    def test_number_hex(self) -> None:
        """Tokenizes hex numbers."""
        tokens = tokenize("0xFF", "python")
        assert tokens[0].type == TokenType.NUMBER_HEX

    def test_number_octal(self) -> None:
        """Tokenizes octal numbers."""
        tokens = tokenize("0o755", "python")
        assert tokens[0].type == TokenType.NUMBER_OCT

    def test_number_binary(self) -> None:
        """Tokenizes binary numbers."""
        tokens = tokenize("0b1010", "python")
        assert tokens[0].type == TokenType.NUMBER_BIN

    def test_number_with_underscores(self) -> None:
        """Tokenizes numbers with underscores."""
        tokens = tokenize("1_000_000", "python")
        assert tokens[0].type == TokenType.NUMBER_INTEGER
        assert tokens[0].value == "1_000_000"

    def test_builtin(self) -> None:
        """Tokenizes builtins."""
        tokens = tokenize("print(len(x))", "python")
        builtins = [t for t in tokens if t.type == TokenType.NAME_BUILTIN]
        assert len(builtins) == 2
        assert {b.value for b in builtins} == {"print", "len"}

    def test_pseudo_builtin(self) -> None:
        """Tokenizes pseudo-builtins like self."""
        tokens = tokenize("self.x = 1", "python")
        pseudo = [t for t in tokens if t.type == TokenType.NAME_BUILTIN_PSEUDO]
        assert len(pseudo) == 1
        assert pseudo[0].value == "self"

    def test_exception(self) -> None:
        """Tokenizes exception names."""
        tokens = tokenize("raise ValueError", "python")
        exceptions = [t for t in tokens if t.type == TokenType.NAME_EXCEPTION]
        assert len(exceptions) == 1
        assert exceptions[0].value == "ValueError"

    def test_operator_walrus(self) -> None:
        """Tokenizes walrus operator."""
        tokens = tokenize("if (x := 1):", "python")
        operators = [t for t in tokens if t.type == TokenType.OPERATOR]
        values = {o.value for o in operators}
        assert ":=" in values

    def test_operator_arrow(self) -> None:
        """Tokenizes return type hint arrow."""
        tokens = tokenize("def f() -> int:", "python")
        operators = [t for t in tokens if t.type == TokenType.OPERATOR]
        values = {o.value for o in operators}
        assert "->" in values

    def test_punctuation(self) -> None:
        """Tokenizes punctuation."""
        tokens = tokenize("()", "python")
        punct = [t for t in tokens if t.type == TokenType.PUNCTUATION]
        assert len(punct) == 2

    def test_line_numbers(self) -> None:
        """Tokens have correct line numbers."""
        code = "x = 1\ny = 2\nz = 3"
        tokens = tokenize(code, "python")
        # Find the name tokens on each line
        names = [t for t in tokens if t.type == TokenType.NAME]
        assert names[0].line == 1  # x
        assert names[1].line == 2  # y
        assert names[2].line == 3  # z

    def test_column_numbers(self) -> None:
        """Tokens have correct column numbers."""
        code = "    x = 1"
        tokens = tokenize(code, "python")
        # Skip whitespace, find 'x'
        x_token = next(t for t in tokens if t.value == "x")
        assert x_token.column == 5  # 1-based, after 4 spaces


class TestThreadSafety:
    """Tests for thread-safety."""

    def test_concurrent_tokenization(self) -> None:
        """Tokenization works correctly under concurrent access."""
        from concurrent.futures import ThreadPoolExecutor

        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

        def tokenize_many(i: int) -> list[Token]:
            results = []
            for _ in range(100):
                tokens = tokenize(code, "python")
                results.extend(tokens)
            return results

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(tokenize_many, i) for i in range(8)]
            results = [f.result() for f in futures]

        # All threads should get consistent results
        first_len = len(results[0])
        for r in results:
            assert len(r) == first_len

    def test_concurrent_lexer_access(self) -> None:
        """get_lexer is thread-safe."""
        from concurrent.futures import ThreadPoolExecutor

        def get_many(_: int) -> None:
            for _ in range(100):
                lexer = get_lexer("python")
                assert lexer.name == "python"

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(get_many, i) for i in range(8)]
            for f in futures:
                f.result()  # Should not raise
