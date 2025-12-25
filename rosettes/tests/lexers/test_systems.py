"""Systems language lexer tests (Bash, C, C++, Rust, Go, SQL, etc.)."""

from rosettes import tokenize


class TestBashLexer:
    """Bash-specific tests."""

    def test_variable_expansion(self) -> None:
        """Tokenizes variable expansion."""
        code = "echo $HOME $USER"
        tokens = tokenize(code, "bash")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert len(vars) >= 2

    def test_shebang(self) -> None:
        """Tokenizes shebang."""
        code = "#!/bin/bash\necho hello"
        tokens = tokenize(code, "bash")
        shebangs = [t for t in tokens if t.type.value == "ch"]
        assert len(shebangs) == 1

    def test_command_substitution(self) -> None:
        """Tokenizes command substitution."""
        code = "files=$(ls -la)"
        tokens = tokenize(code, "bash")
        subs = [t for t in tokens if t.type.value == "si"]
        assert len(subs) >= 1

    def test_hyphenated_commands(self) -> None:
        """Tokenizes hyphenated command/argument names as single tokens."""
        code = "my-custom-script --option my-arg"
        tokens = tokenize(code, "bash")
        values = [t.value for t in tokens]
        assert "my-custom-script" in values
        assert "my-arg" in values

    def test_options_short_and_long(self) -> None:
        """Tokenizes short and long options."""
        code = "ls -la --color=auto"
        tokens = tokenize(code, "bash")
        attrs = [t for t in tokens if t.type.value == "na"]
        attr_values = [t.value for t in attrs]
        assert "-la" in attr_values
        assert "--color" in attr_values

    def test_builtin_commands(self) -> None:
        """Tokenizes builtin commands correctly."""
        code = "cd /path && echo hello && exit 0"
        tokens = tokenize(code, "bash")
        builtins = [t for t in tokens if t.type.value == "nb"]
        builtin_values = {t.value for t in builtins}
        assert "cd" in builtin_values
        assert "echo" in builtin_values
        assert "exit" in builtin_values

    def test_double_quoted_strings(self) -> None:
        """Tokenizes double-quoted strings."""
        code = 'echo "hello world"'
        tokens = tokenize(code, "bash")
        strings = [t for t in tokens if t.type.value == "s2"]
        assert len(strings) == 1
        assert '"hello world"' in strings[0].value

    def test_single_quoted_strings(self) -> None:
        """Tokenizes single-quoted strings."""
        code = "echo 'literal $VAR'"
        tokens = tokenize(code, "bash")
        strings = [t for t in tokens if t.type.value == "s1"]
        assert len(strings) == 1

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "# This is a comment\necho hello"
        tokens = tokenize(code, "bash")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 1

    def test_pipes_and_redirects(self) -> None:
        """Tokenizes pipes and redirects."""
        code = "cat file.txt | grep pattern > output.txt"
        tokens = tokenize(code, "bash")
        values = [t.value for t in tokens]
        assert "|" in values
        assert ">" in values


class TestRustLexer:
    """Rust-specific tests."""

    def test_lifetime(self) -> None:
        """Tokenizes lifetimes."""
        code = "fn foo<'a>(x: &'a str) -> &'a str { x }"
        tokens = tokenize(code, "rust")
        labels = [t for t in tokens if t.type.value == "nl"]
        assert any("'a" in t.value for t in labels)

    def test_attribute(self) -> None:
        """Tokenizes attributes."""
        code = "#[derive(Debug)]\nstruct Foo {}"
        tokens = tokenize(code, "rust")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert len(decorators) >= 1

    def test_macro(self) -> None:
        """Tokenizes macro calls."""
        code = 'println!("Hello, {}!", name);'
        tokens = tokenize(code, "rust")
        macros = [t for t in tokens if t.type.value == "fm"]
        assert any("println!" in t.value for t in macros)

    def test_raw_string(self) -> None:
        """Tokenizes raw strings."""
        code = 'r#"raw string with "quotes""#'
        tokens = tokenize(code, "rust")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1


class TestGoLexer:
    """Go-specific tests."""

    def test_goroutine(self) -> None:
        """Tokenizes go keyword."""
        code = "go func() { fmt.Println() }()"
        tokens = tokenize(code, "go")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value == "go" for t in keywords)

    def test_channel(self) -> None:
        """Tokenizes channel operations."""
        code = "ch := make(chan int)\nch <- 42"
        tokens = tokenize(code, "go")
        values = [t.value for t in tokens]
        assert "<-" in values

    def test_raw_string(self) -> None:
        """Tokenizes raw strings."""
        code = "`raw string`"
        tokens = tokenize(code, "go")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1

    def test_short_declaration(self) -> None:
        """Tokenizes short variable declaration."""
        code = "x := 42"
        tokens = tokenize(code, "go")
        values = [t.value for t in tokens]
        assert ":=" in values


class TestSqlLexer:
    """SQL-specific tests."""

    def test_select_query(self) -> None:
        """Tokenizes SELECT query."""
        code = "SELECT id, name FROM users WHERE active = 1;"
        tokens = tokenize(code, "sql")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value.upper() == "SELECT" for t in keywords)
        assert any(t.value.upper() == "FROM" for t in keywords)
        assert any(t.value.upper() == "WHERE" for t in keywords)

    def test_join_query(self) -> None:
        """Tokenizes JOIN query."""
        code = "SELECT * FROM orders INNER JOIN users ON orders.user_id = users.id"
        tokens = tokenize(code, "sql")
        keywords = [t for t in tokens if t.type.value == "k"]
        keyword_values = {t.value.upper() for t in keywords}
        assert "JOIN" in keyword_values
        assert "ON" in keyword_values

    def test_aggregate_functions(self) -> None:
        """Tokenizes aggregate functions."""
        code = "SELECT COUNT(*), AVG(price), SUM(quantity) FROM orders"
        tokens = tokenize(code, "sql")
        functions = [t for t in tokens if t.type.value == "nf"]
        func_names = {t.value.upper() for t in functions}
        assert "COUNT" in func_names
        assert "AVG" in func_names

    def test_placeholders(self) -> None:
        """Tokenizes query placeholders."""
        code = "SELECT * FROM users WHERE id = $1 AND name = :name"
        tokens = tokenize(code, "sql")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert len(vars) >= 2


class TestCLexer:
    """C-specific tests."""

    def test_preprocessor(self) -> None:
        """Tokenizes preprocessor directives."""
        code = "#include <stdio.h>\n#define MAX 100"
        tokens = tokenize(code, "c")
        preprocs = [t for t in tokens if t.type.value == "cp"]
        assert len(preprocs) >= 2

    def test_pointer(self) -> None:
        """Tokenizes pointer operations."""
        code = "int *ptr = &value;"
        tokens = tokenize(code, "c")
        types = [t for t in tokens if t.type.value == "kt"]
        assert any(t.value == "int" for t in types)

    def test_sizeof(self) -> None:
        """Tokenizes sizeof operator."""
        code = "size_t n = sizeof(int);"
        tokens = tokenize(code, "c")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value == "sizeof" for t in keywords)

    def test_struct(self) -> None:
        """Tokenizes struct definition."""
        code = "struct Point { int x; int y; };"
        tokens = tokenize(code, "c")
        decls = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "struct" for t in decls)


class TestCppLexer:
    """C++-specific tests."""

    def test_class(self) -> None:
        """Tokenizes class definition."""
        code = "class Foo : public Base { public: void bar(); };"
        tokens = tokenize(code, "cpp")
        decls = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "class" for t in decls)

    def test_template(self) -> None:
        """Tokenizes template."""
        code = "template<typename T>\nT max(T a, T b) { return a > b ? a : b; }"
        tokens = tokenize(code, "cpp")
        decls = [t for t in tokens if t.type.value == "kd"]
        assert any(t.value == "template" for t in decls)

    def test_lambda(self) -> None:
        """Tokenizes lambda expressions."""
        code = "auto f = [](int x) { return x * 2; };"
        tokens = tokenize(code, "cpp")
        keywords = [t for t in tokens if t.type.value in ("k", "kd")]
        assert any(t.value == "auto" for t in keywords)

    def test_raw_string(self) -> None:
        """Tokenizes raw string literals."""
        code = 'R"(raw string)"'
        tokens = tokenize(code, "cpp")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) >= 1


class TestJavaLexer:
    """Java-specific tests."""

    def test_annotation(self) -> None:
        """Tokenizes annotations."""
        code = "@Override\npublic void foo() {}"
        tokens = tokenize(code, "java")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert any("@Override" in t.value for t in decorators)

    def test_generic(self) -> None:
        """Tokenizes generics."""
        code = "List<String> items = new ArrayList<>();"
        tokens = tokenize(code, "java")
        types = [t for t in tokens if t.type.value in ("kt", "nc")]
        assert any(t.value == "List" for t in types)
        assert any(t.value == "String" for t in types)

    def test_javadoc(self) -> None:
        """Tokenizes Javadoc comments."""
        code = "/** Javadoc comment */\nclass Foo {}"
        tokens = tokenize(code, "java")
        docs = [t for t in tokens if t.type.value == "sd"]
        assert len(docs) >= 1

    def test_lambda(self) -> None:
        """Tokenizes lambda expressions."""
        code = "list.forEach(x -> System.out.println(x));"
        tokens = tokenize(code, "java")
        values = [t.value for t in tokens]
        assert "->" in values


class TestRubyLexer:
    """Ruby-specific tests."""

    def test_symbol(self) -> None:
        """Tokenizes symbols."""
        code = "hash = { :key => 'value' }"
        tokens = tokenize(code, "ruby")
        symbols = [t for t in tokens if t.type.value == "ss"]
        assert any(":key" in t.value for t in symbols)

    def test_instance_variable(self) -> None:
        """Tokenizes instance variables."""
        code = "@name = 'Ruby'"
        tokens = tokenize(code, "ruby")
        ivars = [t for t in tokens if t.type.value == "vi"]
        assert any("@name" in t.value for t in ivars)

    def test_block(self) -> None:
        """Tokenizes blocks."""
        code = "items.each do |item|\n  puts item\nend"
        tokens = tokenize(code, "ruby")
        keywords = [t for t in tokens if t.type.value == "k"]
        assert any(t.value == "do" for t in keywords)
        assert any(t.value == "end" for t in keywords)

    def test_heredoc(self) -> None:
        """Tokenizes heredocs."""
        code = "text = <<DOC\nmulti\nline\nDOC"
        tokens = tokenize(code, "ruby")
        assert len(tokens) > 0


class TestPhpLexer:
    """PHP-specific tests."""

    def test_variable(self) -> None:
        """Tokenizes PHP variables."""
        code = "<?php $name = 'PHP'; ?>"
        tokens = tokenize(code, "php")
        vars = [t for t in tokens if t.type.value == "nv"]
        assert any("$name" in t.value for t in vars)

    def test_heredoc(self) -> None:
        """Tokenizes heredocs."""
        code = "<<<EOT\nmulti\nline\nEOT;"
        tokens = tokenize(code, "php")
        assert len(tokens) > 0

    def test_arrow_function(self) -> None:
        """Tokenizes arrow functions."""
        code = "<?php $fn = fn($x) => $x * 2; ?>"
        tokens = tokenize(code, "php")
        values = [t.value for t in tokens]
        assert "=>" in values
        assert "fn" in values

    def test_namespace(self) -> None:
        """Tokenizes namespace."""
        code = "<?php namespace App\\Models; use App\\Base; ?>"
        tokens = tokenize(code, "php")
        ns_keywords = [t for t in tokens if t.type.value == "kn"]
        assert any(t.value == "namespace" for t in ns_keywords)
        assert any(t.value == "use" for t in ns_keywords)
