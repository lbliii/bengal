#!/usr/bin/env python3
"""Trace lexer execution step by step."""

from bengal.rendering.parsers.patitas.lexer import Lexer

source = "```\ncode\n```"
print(f"Source: {repr(source)}")
print(f"Source chars: {[c for c in source]}")
print()

lexer = Lexer(source)
print(
    f"Initial: pos={lexer._pos}, mode={lexer._mode}, fence_char={repr(lexer._fence_char)}, fence_count={lexer._fence_count}"
)
print()

token_count = 0
max_tokens = 20

try:
    for token in lexer.tokenize():
        token_count += 1
        print(f"Token {token_count}: {token.type.name} = {repr(token.value[:50])}")
        print(
            f"  After token: pos={lexer._pos}, mode={lexer._mode}, fence_char={repr(lexer._fence_char)}, fence_count={lexer._fence_count}"
        )
        print(
            f"  pos < len(source)? {lexer._pos < len(lexer._source)} (pos={lexer._pos}, len={len(lexer._source)})"
        )
        print()

        if token_count >= max_tokens:
            print(f"STOPPING - reached {max_tokens} tokens")
            break

        if lexer._pos >= len(lexer._source):
            print("Reached end of source")
            break
except KeyboardInterrupt:
    print("\nINTERRUPTED")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback

    traceback.print_exc()

print(f"\nTotal tokens: {token_count}")
