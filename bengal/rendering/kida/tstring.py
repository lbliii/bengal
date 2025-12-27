"""Kida Template String support (PEP 750).

Provides the `k` tag for Python 3.14+ t-strings, allowing Kida-style
interpolation and filters within Python code.
"""

from __future__ import annotations

import string.templatelib

from bengal.rendering.kida.utils.html import html_escape


def k(template: string.templatelib.Template) -> str:
    """The `k` tag for Kida template strings.

    Example:
        >>> name = "World"
        >>> k(t"Hello {name}!")
        'Hello World!'

    Note: Currently supports simple interpolation. Future versions will
    integrate with the Kida compiler for filter support.
    """
    parts = []
    strings = template.strings
    interpolations = template.interpolations

    for i in range(len(strings)):
        parts.append(strings[i])
        if i < len(interpolations):
            val = interpolations[i].value
            # Auto-escape if it's not already Markup (Kida principle)
            if hasattr(val, "__html__"):
                parts.append(val.__html__())
            else:
                parts.append(html_escape(str(val)))

    return "".join(parts)
