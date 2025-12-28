"""Hand-written Perl lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    HashCommentsMixin,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["PerlStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "if",
        "elsif",
        "else",
        "unless",
        "while",
        "until",
        "for",
        "foreach",
        "do",
        "sub",
        "my",
        "our",
        "local",
        "use",
        "require",
        "package",
        "return",
        "last",
        "next",
        "redo",
        "goto",
        "die",
        "warn",
        "print",
        "say",
        "given",
        "when",
        "default",
        "BEGIN",
        "END",
        "CHECK",
        "INIT",
        "UNITCHECK",
        "AUTOLOAD",
        "DESTROY",
        "try",
        "catch",
        "finally",
        "eq",
        "ne",
        "lt",
        "gt",
        "le",
        "ge",
        "cmp",
        "and",
        "or",
        "not",
        "xor",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "abs",
        "accept",
        "alarm",
        "atan2",
        "bind",
        "binmode",
        "bless",
        "caller",
        "chdir",
        "chmod",
        "chomp",
        "chop",
        "chown",
        "chr",
        "chroot",
        "close",
        "closedir",
        "connect",
        "cos",
        "crypt",
        "dbmclose",
        "dbmopen",
        "defined",
        "delete",
        "dump",
        "each",
        "endgrent",
        "endhostent",
        "endnetent",
        "endprotoent",
        "endpwent",
        "endservent",
        "eof",
        "eval",
        "exec",
        "exists",
        "exit",
        "exp",
        "fcntl",
        "fileno",
        "flock",
        "fork",
        "format",
        "formline",
        "getc",
        "getgrent",
        "getgrgid",
        "getgrnam",
        "gethostbyaddr",
        "gethostbyname",
        "gethostent",
        "getlogin",
        "getnetbyaddr",
        "getnetbyname",
        "getnetent",
        "getpeername",
        "getpgrp",
        "getppid",
        "getpriority",
        "getprotobyname",
        "getprotobynumber",
        "getprotoent",
        "getpwent",
        "getpwnam",
        "getpwuid",
        "getservbyname",
        "getservbyport",
        "getservent",
        "getsockname",
        "getsockopt",
        "glob",
        "gmtime",
        "grep",
        "hex",
        "import",
        "index",
        "int",
        "ioctl",
        "join",
        "keys",
        "kill",
        "lc",
        "lcfirst",
        "length",
        "link",
        "listen",
        "localtime",
        "log",
        "lstat",
        "map",
        "mkdir",
        "msgctl",
        "msgget",
        "msgrcv",
        "msgsnd",
        "oct",
        "open",
        "opendir",
        "ord",
        "pack",
        "pipe",
        "pop",
        "pos",
        "printf",
        "prototype",
        "push",
        "quotemeta",
        "rand",
        "read",
        "readdir",
        "readline",
        "readlink",
        "readpipe",
        "recv",
        "ref",
        "rename",
        "reset",
        "reverse",
        "rewinddir",
        "rindex",
        "rmdir",
        "scalar",
        "seek",
        "seekdir",
        "select",
        "semctl",
        "semget",
        "semop",
        "send",
        "setgrent",
        "sethostent",
        "setnetent",
        "setpgrp",
        "setpriority",
        "setprotoent",
        "setpwent",
        "setservent",
        "setsockopt",
        "shift",
        "shmctl",
        "shmget",
        "shmread",
        "shmwrite",
        "shutdown",
        "sin",
        "sleep",
        "socket",
        "socketpair",
        "sort",
        "splice",
        "split",
        "sprintf",
        "sqrt",
        "srand",
        "stat",
        "study",
        "substr",
        "symlink",
        "syscall",
        "sysopen",
        "sysread",
        "sysseek",
        "system",
        "syswrite",
        "tell",
        "telldir",
        "tie",
        "tied",
        "time",
        "times",
        "truncate",
        "uc",
        "ucfirst",
        "umask",
        "undef",
        "unlink",
        "unpack",
        "unshift",
        "untie",
        "utime",
        "values",
        "vec",
        "wait",
        "waitpid",
        "wantarray",
        "write",
    }
)


class PerlStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Perl lexer."""

    name = "perl"
    aliases = ("pl",)
    filenames = ("*.pl", "*.pm", "*.t")
    mimetypes = ("text/x-perl", "application/x-perl")

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in " \t":
                ws_start = pos
                while pos < length and code[pos] in " \t":
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[ws_start:pos], line, col)
                continue

            if char == "\n":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                line += 1
                line_start = pos
                continue

            # Shebang
            if pos == start and char == "#" and pos + 1 < length and code[pos + 1] == "!":
                shebang_start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_HASHBANG, code[shebang_start:pos], line, col)
                continue

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # POD documentation =pod ... =cut
            if (
                col == 1
                and char == "="
                and pos + 3 < length
                and code[pos + 1 : pos + 4]
                in ("pod", "hea", "ove", "ite", "bac", "beg", "end", "for", "enc")
            ):
                start = pos
                start_line = line
                while pos < length:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    if code[pos : pos + 5] == "\n=cut":
                        pos += 5
                        while pos < length and code[pos] != "\n":
                            pos += 1
                        break
                    pos += 1
                yield Token(TokenType.STRING_DOC, code[start:pos], start_line, 1)
                continue

            # Variables
            if char in "$@%*":
                start = pos
                pos += 1
                if pos < length:
                    if code[pos] in "$#!+&`'?^":
                        pos += 1
                    elif code[pos] == "{":
                        pos += 1
                        while pos < length and code[pos] != "}":
                            pos += 1
                        if pos < length:
                            pos += 1
                    elif code[pos].isalpha() or code[pos] == "_":
                        while pos < length and (code[pos].isalnum() or code[pos] in "_:"):
                            pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Strings
            if char in "'\"":
                start = pos
                quote = char
                pos += 1
                while pos < length and code[pos] != quote:
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

            # Backticks
            if char == "`":
                start = pos
                pos += 1
                while pos < length and code[pos] != "`":
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING_BACKTICK, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if code[pos] == "0" and pos + 1 < length:
                    next_char = code[pos + 1]
                    if next_char in "xX":
                        pos += 2
                        while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                        continue
                    if next_char in "bB":
                        pos += 2
                        while pos < length and code[pos] in "01_":
                            pos += 1
                        yield Token(TokenType.NUMBER_BIN, code[start:pos], line, col)
                        continue
                    if next_char in OCTAL_DIGITS:
                        while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_OCT, code[start:pos], line, col)
                        continue

                if char == ".":
                    pos += 1
                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_:"):
                    pos += 1
                word = code[start:pos]
                if word in ("sub", "my", "our", "local", "package"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("use", "require"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%^~.":
                start = pos
                if pos + 2 < length and code[pos : pos + 3] in ("=~", "!~", "<=>", "...", "**="):
                    pos += 3
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "++",
                    "--",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    ".=",
                    "**",
                    "->",
                    "=>",
                    "//",
                    "~~",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Regex (simplified detection)
            if char == "/" and pos > 0 and code[pos - 1] in "=~(,;":
                start = pos
                pos += 1
                while pos < length and code[pos] != "/":
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                    while pos < length and code[pos] in "gimsx":
                        pos += 1
                yield Token(TokenType.STRING_REGEX, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{}:;,":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
