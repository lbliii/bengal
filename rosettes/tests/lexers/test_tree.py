"""Tree/directory structure lexer tests."""

from rosettes import tokenize


class TestTreeLexer:
    """Tree lexer tests."""

    def test_directory_names(self) -> None:
        """Tokenizes directory names ending with /."""
        code = "config/\nsrc/"
        tokens = tokenize(code, "tree")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert len(classes) == 2
        assert any("config/" in t.value for t in classes)
        assert any("src/" in t.value for t in classes)

    def test_tree_structure_unicode(self) -> None:
        """Tokenizes Unicode box-drawing characters."""
        code = "├── ├ └ │ ─"
        tokens = tokenize(code, "tree")
        punct = [t for t in tokens if t.type.value == "p"]
        assert len(punct) >= 3

    def test_tree_structure_ascii(self) -> None:
        """Tokenizes ASCII tree characters."""
        code = "|-- +-- | `--"
        tokens = tokenize(code, "tree")
        punct = [t for t in tokens if t.type.value == "p"]
        assert len(punct) >= 2

    def test_config_files(self) -> None:
        """Tokenizes config files (yaml, toml, json, ini)."""
        code = "site.yaml\nconfig.toml\npackage.json\nsettings.ini"
        tokens = tokenize(code, "tree")
        attrs = [t for t in tokens if t.type.value == "na"]
        assert len(attrs) == 4

    def test_code_files(self) -> None:
        """Tokenizes code files (py, js, ts, rs, go)."""
        code = "main.py\napp.js\nindex.ts\nlib.rs\nmain.go"
        tokens = tokenize(code, "tree")
        funcs = [t for t in tokens if t.type.value == "nf"]
        assert len(funcs) == 5

    def test_doc_files(self) -> None:
        """Tokenizes documentation files (md, rst, txt, html)."""
        code = "README.md\nindex.rst\nnotes.txt\npage.html"
        tokens = tokenize(code, "tree")
        strings = [t for t in tokens if t.type.value == "s"]
        assert len(strings) == 4

    def test_hidden_files(self) -> None:
        """Tokenizes dotfiles."""
        code = ".gitignore\n.env\n.bashrc"
        tokens = tokenize(code, "tree")
        decorators = [t for t in tokens if t.type.value == "nd"]
        assert len(decorators) == 3

    def test_hidden_directories(self) -> None:
        """Tokenizes hidden directories."""
        code = ".git/\n.config/"
        tokens = tokenize(code, "tree")
        classes = [t for t in tokens if t.type.value == "nc"]
        assert len(classes) == 2

    def test_files_without_extension(self) -> None:
        """Tokenizes files without extensions."""
        code = "Makefile\nDockerfile\nLICENSE"
        tokens = tokenize(code, "tree")
        names = [t for t in tokens if t.type.value == "n"]
        assert len(names) == 3

    def test_complete_tree(self) -> None:
        """Tokenizes a complete directory tree structure."""
        code = """config/
├── _default/
│   ├── site.yaml
│   └── theme.yaml
└── environments/
    └── production.yaml"""
        tokens = tokenize(code, "tree")
        # Should have directories
        dirs = [t for t in tokens if t.type.value == "nc"]
        assert len(dirs) >= 3
        # Should have config files
        configs = [t for t in tokens if t.type.value == "na"]
        assert len(configs) == 3
        # Should have tree structure
        punct = [t for t in tokens if t.type.value == "p"]
        assert len(punct) >= 5

    def test_comments(self) -> None:
        """Tokenizes comments."""
        code = "src/  # source files\nconfig/  # configuration"
        tokens = tokenize(code, "tree")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert len(comments) == 2

    def test_ellipsis(self) -> None:
        """Tokenizes ellipsis for truncated content."""
        code = "src/\n├── ...\n└── main.py"
        tokens = tokenize(code, "tree")
        comments = [t for t in tokens if t.type.value == "c1"]
        assert any("..." in t.value for t in comments)

    def test_aliases(self) -> None:
        """Aliases resolve correctly."""
        for alias in ("tree", "directory", "filetree", "dirtree", "files"):
            tokens = tokenize("src/", alias)
            assert len(tokens) > 0
