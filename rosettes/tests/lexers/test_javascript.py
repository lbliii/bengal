"""JavaScript and TypeScript lexer tests."""

from rosettes import tokenize


class TestJavaScriptLexer:
    """JavaScript-specific tests."""

    def test_arrow_function(self) -> None:
        """Tokenizes arrow functions."""
        tokens = tokenize("const f = (x) => x * 2;", "javascript")
        values = [t.value for t in tokens]
        assert "=>" in values

    def test_template_literal(self) -> None:
        """Tokenizes template literals."""
        tokens = tokenize("`hello ${name}`", "javascript")
        assert any(t.value.startswith("`") for t in tokens)

    def test_bigint(self) -> None:
        """Tokenizes BigInt literals."""
        tokens = tokenize("const big = 123n;", "javascript")
        assert any(t.value == "123n" for t in tokens)

    def test_nullish_coalescing(self) -> None:
        """Tokenizes nullish coalescing operator."""
        tokens = tokenize("const x = a ?? b;", "javascript")
        values = [t.value for t in tokens]
        assert "??" in values

    def test_const_let_var(self) -> None:
        """Tokenizes variable declarations."""
        code = "const a = 1;\nlet b = 2;\nvar c = 3;"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value == "kd"]
        keyword_values = {t.value for t in keywords}
        assert "const" in keyword_values
        assert "let" in keyword_values
        assert "var" in keyword_values

    def test_function_declaration(self) -> None:
        """Tokenizes function declarations."""
        code = "function greet(name) { return 'Hello ' + name; }"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "function" for t in keywords)

    def test_class_syntax(self) -> None:
        """Tokenizes class syntax."""
        code = "class MyClass extends Base { constructor() { super(); } }"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value in ("k", "kd")]
        keyword_values = {t.value for t in keywords}
        assert "class" in keyword_values
        assert "extends" in keyword_values

    def test_async_await(self) -> None:
        """Tokenizes async/await."""
        code = "async function fetch() { const data = await getData(); }"
        tokens = tokenize(code, "javascript")
        keywords = [t for t in tokens if t.type.value == "k"]
        keyword_values = {t.value for t in keywords}
        assert "async" in keyword_values
        assert "await" in keyword_values

    def test_destructuring(self) -> None:
        """Tokenizes destructuring syntax."""
        code = "const { a, b } = obj;\nconst [x, y] = arr;"
        tokens = tokenize(code, "javascript")
        punct = [t for t in tokens if t.type.value == "p"]
        assert len(punct) >= 4

    def test_spread_operator(self) -> None:
        """Tokenizes spread operator."""
        code = "const arr = [...items, newItem];"
        tokens = tokenize(code, "javascript")
        values = [t.value for t in tokens]
        assert "..." in values

    def test_optional_chaining(self) -> None:
        """Tokenizes optional chaining."""
        code = "const value = obj?.prop?.nested;"
        tokens = tokenize(code, "javascript")
        values = [t.value for t in tokens]
        # Optional chaining may be tokenized as ? and . separately
        assert "?" in values and "." in values

    def test_regex_literal(self) -> None:
        """Tokenizes regex literals."""
        code = "const pattern = /^hello.*$/gi;"
        tokens = tokenize(code, "javascript")
        strings = [t for t in tokens if t.type.value == "sr"]
        assert len(strings) >= 1

    def test_single_line_comments(self) -> None:
        """Tokenizes single-line comments."""
        code = "const x = 1; // comment"
        tokens = tokenize(code, "javascript")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 1

    def test_multi_line_comments(self) -> None:
        """Tokenizes multi-line comments."""
        code = "/* multi\nline\ncomment */\nconst x = 1;"
        tokens = tokenize(code, "javascript")
        comments = [t for t in tokens if t.type.value == "cm"]
        assert len(comments) == 1


class TestTypeScriptLexer:
    """TypeScript-specific tests."""

    def test_type_annotation(self) -> None:
        """Tokenizes type annotations."""
        tokens = tokenize("const x: number = 1;", "typescript")
        types = [t for t in tokens if t.type.value == "kt"]
        assert any(t.value == "number" for t in types)

    def test_interface(self) -> None:
        """Tokenizes interface declarations."""
        tokens = tokenize("interface User { name: string; }", "typescript")
        keywords = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "interface" for t in keywords)

    def test_decorator(self) -> None:
        """Tokenizes decorators."""
        tokens = tokenize("@Component class Foo {}", "typescript")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert any("@Component" in t.value for t in decorators)
