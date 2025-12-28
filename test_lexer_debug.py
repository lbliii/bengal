#!/usr/bin/env python3
"""Debug script to test lexer with fenced code."""

from bengal.rendering.parsers.patitas.lexer import Lexer

# Test the exact input from the test
source = "```\ncode\n```"
print(f"Source: {repr(source)}")
print(f"Source length: {len(source)}")

lexer = Lexer(source)
print(f"Initial mode: {lexer._mode}")
print(f"Initial pos: {lexer._pos}")

tokens = []
max_iterations = 50
for i, token in enumerate(lexer.tokenize()):
    tokens.append(token)
    print(
        f"Token {i}: {token.type} = {repr(token.value[:50])} (pos={lexer._pos}, mode={lexer._mode})"
    )
    if i >= max_iterations:
        print(f"STOPPING - reached {max_iterations} iterations (likely infinite loop)")
        break

print(f"\nTotal tokens: {len(tokens)}")
if len(tokens) == 1 and tokens[0].type.name == "EOF":
    print("ERROR: Only got EOF token - lexer didn't process the input!")
