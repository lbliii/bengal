"""Kida Compatibility Layers.

This package provides compatibility adapters for migrating from other
template engines to Kida.

Available Adapters:
    - jinja: Parse Jinja2 syntax and produce Kida AST

Usage:
    from kida.compat.jinja import JinjaParser

    # Parse Jinja2 template, get Kida AST
    parser = JinjaParser(tokens, source=source)
    kida_ast = parser.parse()

    # Then compile and render with Kida's fast runtime
    compiler = Compiler(env)
    code = compiler.compile(kida_ast)

This allows benchmarking Kida's runtime against Jinja2's using
existing templates without rewriting them.
"""

from bengal.rendering.kida.compat.jinja import JinjaParser

__all__ = ["JinjaParser"]
