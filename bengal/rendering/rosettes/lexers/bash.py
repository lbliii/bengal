"""Bash/Shell lexer for Rosettes.

Thread-safe regex-based tokenizer for shell scripts.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["BashLexer"]

# Shell keywords
_KEYWORDS = frozenset(
    (
        "if",
        "then",
        "else",
        "elif",
        "fi",
        "for",
        "while",
        "until",
        "do",
        "done",
        "case",
        "esac",
        "in",
        "function",
        "select",
        "time",
        "coproc",
    )
)

# Shell builtins
_BUILTINS = frozenset(
    (
        "alias",
        "bg",
        "bind",
        "break",
        "builtin",
        "caller",
        "cd",
        "command",
        "compgen",
        "complete",
        "compopt",
        "continue",
        "declare",
        "dirs",
        "disown",
        "echo",
        "enable",
        "eval",
        "exec",
        "exit",
        "export",
        "false",
        "fc",
        "fg",
        "getopts",
        "hash",
        "help",
        "history",
        "jobs",
        "kill",
        "let",
        "local",
        "logout",
        "mapfile",
        "popd",
        "printf",
        "pushd",
        "pwd",
        "read",
        "readarray",
        "readonly",
        "return",
        "set",
        "shift",
        "shopt",
        "source",
        "suspend",
        "test",
        "times",
        "trap",
        "true",
        "type",
        "typeset",
        "ulimit",
        "umask",
        "unalias",
        "unset",
        "wait",
    )
)

# Common external commands (highlighted as functions)
_COMMON_COMMANDS = frozenset(
    (
        # Version control
        "git",
        "svn",
        "hg",
        "gh",
        # Container/cloud
        "docker",
        "docker-compose",
        "podman",
        "kubectl",
        "helm",
        "terraform",
        "aws",
        "gcloud",
        "az",
        # Package managers
        "pip",
        "pip3",
        "pipx",
        "uv",
        "poetry",
        "pdm",
        "npm",
        "npx",
        "yarn",
        "pnpm",
        "bun",
        "deno",
        "cargo",
        "rustup",
        "go",
        "gem",
        "bundle",
        "composer",
        "apt",
        "apt-get",
        "yum",
        "dnf",
        "pacman",
        "brew",
        "snap",
        "flatpak",
        # Build tools
        "make",
        "cmake",
        "ninja",
        "meson",
        "gradle",
        "maven",
        "ant",
        # File utilities
        "ls",
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "cp",
        "mv",
        "rm",
        "mkdir",
        "rmdir",
        "touch",
        "chmod",
        "chown",
        "chgrp",
        "ln",
        "stat",
        "file",
        "tree",
        "find",
        "locate",
        "which",
        "whereis",
        "realpath",
        "basename",
        "dirname",
        # Text processing
        "grep",
        "egrep",
        "fgrep",
        "rg",
        "ag",
        "ack",
        "sed",
        "awk",
        "gawk",
        "cut",
        "sort",
        "uniq",
        "wc",
        "tr",
        "tee",
        "diff",
        "patch",
        "jq",
        "yq",
        "xargs",
        # Archive/compression
        "tar",
        "gzip",
        "gunzip",
        "bzip2",
        "xz",
        "zip",
        "unzip",
        "7z",
        # Network
        "curl",
        "wget",
        "ssh",
        "scp",
        "rsync",
        "sftp",
        "ftp",
        "ping",
        "nc",
        "netcat",
        "telnet",
        "nmap",
        "dig",
        "nslookup",
        "host",
        "ifconfig",
        "ip",
        "netstat",
        "ss",
        # Process management
        "ps",
        "top",
        "htop",
        "pgrep",
        "pkill",
        "killall",
        "nohup",
        "screen",
        "tmux",
        "systemctl",
        "service",
        "journalctl",
        # System info
        "date",
        "cal",
        "uptime",
        "whoami",
        "id",
        "uname",
        "hostname",
        "df",
        "du",
        "free",
        "lsof",
        "lsblk",
        "mount",
        "umount",
        "fdisk",
        # User management
        "sudo",
        "su",
        "passwd",
        "useradd",
        "userdel",
        "usermod",
        "groupadd",
        "groups",
        # Editors
        "vi",
        "vim",
        "nvim",
        "nano",
        "emacs",
        "code",
        # Programming language runtimes
        "python",
        "python3",
        "python2",
        "node",
        "ruby",
        "perl",
        "php",
        "java",
        "javac",
        "scala",
        "kotlin",
        "lua",
        "julia",
        "swift",
        "rustc",
        "gcc",
        "g++",
        "clang",
        "clang++",
        # Testing/linting
        "pytest",
        "mypy",
        "ruff",
        "black",
        "isort",
        "flake8",
        "pylint",
        "eslint",
        "prettier",
        "tsc",
        "jest",
        "mocha",
        "vitest",
        # Documentation
        "sphinx-build",
        "mkdocs",
        "hugo",
        "jekyll",
        # Misc tools
        "man",
        "info",
        "env",
        "printenv",
        "xdg-open",
        "open",
        "pbcopy",
        "pbpaste",
        "xclip",
        "clear",
        "reset",
        "watch",
        "time",
        # Bengal CLI
        "bengal",
    )
)

# Bengal subcommands (for bengal <subcommand>)
_BENGAL_SUBCOMMANDS = frozenset(
    (
        # Core commands
        "new",
        "init",
        "build",
        "serve",
        "clean",
        "validate",
        "fix",
        "explain",
        "perf",
        # Groups
        "site",
        "theme",
        "assets",
        "config",
        "collections",
        "sources",
        "graph",
        "health",
        "debug",
        "utils",
        "version",
        "project",
        "skeleton",
        "codemod",
        "engine",
        # Scaffold subcommands (under 'new')
        "page",
        "layout",
        "partial",
        # Graph subcommands
        "analyze",
        "report",
        "orphans",
        "pagerank",
        "bridges",
        "communities",
        "suggest",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify a word token."""
    word = match.group(0)
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word in _COMMON_COMMANDS:
        return TokenType.NAME_FUNCTION
    if word in _BENGAL_SUBCOMMANDS:
        return TokenType.NAME_ATTRIBUTE
    return TokenType.NAME


class BashLexer(PatternLexer):
    """Bash/Shell lexer.

    Handles Bash/sh/zsh syntax including variable expansion, here-documents,
    and command substitution markers.
    Thread-safe: all state is immutable.
    """

    name = "bash"
    aliases = ("sh", "shell", "zsh", "ksh")
    filenames = ("*.sh", "*.bash", "*.zsh", "*.ksh", ".bashrc", ".zshrc", ".profile")
    mimetypes = ("text/x-shellscript", "application/x-sh")

    rules = (
        # Shebang
        Rule(re.compile(r"^#!.*$", re.MULTILINE), TokenType.COMMENT_HASHBANG),
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Here-documents (simplified - just the markers)
        Rule(re.compile(r"<<-?'?(\w+)'?"), TokenType.STRING_HEREDOC),
        # Double-quoted strings (may contain variables)
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Single-quoted strings (literal)
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # ANSI-C quoting
        Rule(re.compile(r"\$'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Variable expansion
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$[0-9@#?$!*-]"), TokenType.NAME_VARIABLE),
        # Command substitution
        Rule(re.compile(r"\$\([^)]*\)"), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"`[^`]*`"), TokenType.STRING_BACKTICK),
        # Options: -o, --option (must come before operators)
        Rule(re.compile(r"--?[a-zA-Z][a-zA-Z0-9_-]*"), TokenType.NAME_ATTRIBUTE),
        # Numbers
        Rule(re.compile(r"\b\d+\b"), TokenType.NUMBER_INTEGER),
        # Keywords, builtins, and common commands (includes hyphenated names)
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_-]*\b"), _classify_word),
        # Operators
        Rule(re.compile(r"&&|\|\|"), TokenType.OPERATOR),
        Rule(re.compile(r"\|&|&>|>>|>|<|2>&1|&"), TokenType.OPERATOR),
        Rule(re.compile(r";;|;&|;;&"), TokenType.OPERATOR),  # Case terminators
        Rule(re.compile(r"[|!]"), TokenType.OPERATOR),
        # Comparison operators
        Rule(re.compile(r"-(?:eq|ne|lt|le|gt|ge|z|n|f|d|e|r|w|x|s)\b"), TokenType.OPERATOR_WORD),
        # Punctuation
        Rule(re.compile(r"[()[\]{};<>=]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Catch-all for any remaining text (paths, filenames, etc.)
        Rule(re.compile(r"[^\s\[\](){}|&;$\"'#<>=]+"), TokenType.TEXT),
    )
