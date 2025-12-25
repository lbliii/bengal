"""Hand-written Bash/Shell lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HashCommentsMixin,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["BashStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "if",
        "then",
        "else",
        "elif",
        "fi",
        "case",
        "esac",
        "for",
        "select",
        "while",
        "until",
        "do",
        "done",
        "in",
        "function",
        "time",
        "coproc",
        "return",
        "exit",
        "break",
        "continue",
        "declare",
        "typeset",
        "local",
        "export",
        "readonly",
        "unset",
        "shift",
        "source",
        "alias",
        "unalias",
        "set",
        "shopt",
        "trap",
        "eval",
        "exec",
        "wait",
        "read",
        "echo",
        "printf",
        "test",
        "[",
        "[[",
        "]]",
        "]",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "cd",
        "pwd",
        "pushd",
        "popd",
        "dirs",
        "jobs",
        "fg",
        "bg",
        "kill",
        "disown",
        "suspend",
        "logout",
        "umask",
        "ulimit",
        "enable",
        "builtin",
        "command",
        "type",
        "hash",
        "help",
        "history",
        "fc",
        "bind",
        "complete",
        "compgen",
        "compopt",
        "mapfile",
        "readarray",
        "getopts",
        "let",
    }
)


class BashStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Bash/Shell lexer using composable mixins."""

    name = "bash"
    aliases = ("sh", "shell", "zsh")
    filenames = ("*.sh", "*.bash", "*.zsh", ".bashrc", ".zshrc", ".profile")
    mimetypes = ("application/x-sh", "text/x-shellscript")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in " \t":
                start = pos
                while pos < length and code[pos] in " \t":
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], line, col)
                continue

            if char == "\n":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                line += 1
                line_start = pos
                continue

            # Line continuation
            if char == "\\" and pos + 1 < length and code[pos + 1] == "\n":
                yield Token(TokenType.WHITESPACE, "\\\n", line, col)
                pos += 2
                line += 1
                line_start = pos
                continue

            # Comments (but not in strings)
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Shebang
            if pos == 0 and char == "#" and pos + 1 < length and code[pos + 1] == "!":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_HASHBANG, code[start:pos], line, col)
                continue

            # Double-quoted strings (with variable expansion)
            if char == '"':
                start = pos
                pos += 1
                while pos < length and code[pos] != '"':
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Single-quoted strings (literal)
            if char == "'":
                start = pos
                pos += 1
                while pos < length and code[pos] != "'":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # $'...' ANSI-C quoting
            if char == "$" and pos + 1 < length and code[pos + 1] == "'":
                start = pos
                pos += 2
                while pos < length and code[pos] != "'":
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Heredoc <<EOF or <<'EOF' or <<-EOF
            if char == "<" and pos + 1 < length and code[pos + 1] == "<":
                start = pos
                pos += 2
                if pos < length and code[pos] == "-":
                    pos += 1
                if pos < length and code[pos] == "<":  # <<<
                    pos += 1
                    yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                    continue
                # Get delimiter
                while pos < length and code[pos] in " \t":
                    pos += 1
                delim_start = pos
                quoted = False
                if pos < length and code[pos] in "\"'":
                    quoted = True
                    quote = code[pos]
                    pos += 1
                    while pos < length and code[pos] != quote:
                        pos += 1
                    if pos < length:
                        pos += 1
                else:
                    while pos < length and code[pos] not in " \t\n":
                        pos += 1
                yield Token(TokenType.STRING_HEREDOC, code[start:pos], line, col)
                continue

            # Variables $VAR, ${VAR}, $1, $$, etc.
            if char == "$":
                start = pos
                pos += 1
                if pos < length:
                    next_char = code[pos]
                    if next_char == "{":
                        # ${...}
                        brace_depth = 1
                        pos += 1
                        while pos < length and brace_depth > 0:
                            if code[pos] == "{":
                                brace_depth += 1
                            elif code[pos] == "}":
                                brace_depth -= 1
                            pos += 1
                    elif next_char == "(":
                        # $(...)
                        paren_depth = 1
                        pos += 1
                        while pos < length and paren_depth > 0:
                            if code[pos] == "(":
                                paren_depth += 1
                            elif code[pos] == ")":
                                paren_depth -= 1
                            pos += 1
                    elif next_char in "0123456789@#?$!*-_":
                        pos += 1
                    elif next_char.isalpha() or next_char == "_":
                        while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                            pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS:
                start = pos
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                yield Token(TokenType.NUMBER_INTEGER, code[start:pos], line, col)
                continue

            # Keywords and commands
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_-"):
                    pos += 1
                word = code[start:pos]
                if word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "|&;":
                start = pos
                if pos + 1 < length and code[pos + 1] == char:
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            if char in "<>":
                start = pos
                if pos + 1 < length and code[pos + 1] in "<>&":
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            if char in "!=-+*":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
