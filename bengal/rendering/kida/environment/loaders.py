"""Template loaders for Kida environment.

Loaders provide template source to the Environment. They implement
`get_source(name)` returning `(source, filename)`.

Built-in Loaders:
    - `FileSystemLoader`: Load from filesystem directories
    - `DictLoader`: Load from in-memory dictionary (testing/embedded)

Custom Loaders:
    Implement the Loader protocol:
    ```python
    class DatabaseLoader:
        def get_source(self, name: str) -> tuple[str, str | None]:
            row = db.query("SELECT source FROM templates WHERE name = ?", name)
            if not row:
                raise TemplateNotFoundError(f"Template '{name}' not found")
            return row.source, f"db://{name}"

        def list_templates(self) -> list[str]:
            return [r.name for r in db.query("SELECT name FROM templates")]
    ```

Thread-Safety:
    Loaders should be thread-safe for concurrent `get_source()` calls.
    Both built-in loaders are safe (FileSystemLoader reads files atomically,
    DictLoader uses immutable dict lookup).
"""

from __future__ import annotations

from pathlib import Path

from bengal.rendering.kida.environment.exceptions import TemplateNotFoundError


class FileSystemLoader:
    """Load templates from filesystem directories.

    Searches one or more directories for templates by name. The first matching
    file is returned. Supports arbitrary directory structures and file nesting.

    Attributes:
        _paths: List of Path objects to search
        _encoding: File encoding (default: utf-8)

    Methods:
        get_source(name): Return (source, filename) for template
        list_templates(): Return sorted list of all template names

    Search Order:
        Directories are searched in order. First match wins:
        ```python
        loader = FileSystemLoader(["themes/custom/", "themes/default/"])
        # Looks in themes/custom/ first, then themes/default/
        ```

    Example:
        >>> loader = FileSystemLoader("templates/")
        >>> source, filename = loader.get_source("pages/about.html")
        >>> print(filename)
        'templates/pages/about.html'

        >>> loader = FileSystemLoader(["site/", "shared/"])
        >>> loader.list_templates()
        ['base.html', 'components/card.html', 'pages/home.html']

    Raises:
        TemplateNotFoundError: If template not found in any search path
    """

    __slots__ = ("_paths", "_encoding")

    def __init__(
        self,
        paths: str | Path | list[str | Path],
        encoding: str = "utf-8",
    ):
        if isinstance(paths, (str, Path)):
            paths = [paths]
        self._paths = [Path(p) for p in paths]
        self._encoding = encoding

    def get_source(self, name: str) -> tuple[str, str]:
        """Load template source from filesystem."""
        for base in self._paths:
            path = base / name
            if path.is_file():
                return path.read_text(self._encoding), str(path)

        raise TemplateNotFoundError(
            f"Template '{name}' not found in: {', '.join(str(p) for p in self._paths)}"
        )

    def list_templates(self) -> list[str]:
        """List all templates in search paths."""
        templates = set()
        for base in self._paths:
            if base.is_dir():
                for path in base.rglob("*.html"):
                    templates.add(str(path.relative_to(base)))
                for path in base.rglob("*.xml"):
                    templates.add(str(path.relative_to(base)))
        return sorted(templates)


class DictLoader:
    """Load templates from an in-memory dictionary.

    Maps template names to source strings. Useful for testing, embedded
    templates, or dynamically generated templates.

    Attributes:
        _mapping: Dict mapping template name → source string

    Methods:
        get_source(name): Return (source, None) for template
        list_templates(): Return sorted list of template names

    Note:
        Returns `None` as filename since templates are not file-backed.
        Error messages will show `<template>` instead of a path.

    Example:
        >>> loader = DictLoader({
        ...     "base.html": "<html>{% block content %}{% end %}</html>",
        ...     "page.html": "{% extends 'base.html' %}{% block content %}Hi{% end %}",
        ... })
        >>> env = Environment(loader=loader)
        >>> env.get_template("page.html").render()
        '<html>Hi</html>'

    Testing:
        >>> loader = DictLoader({"test.html": "{{ x * 2 }}"})
        >>> env = Environment(loader=loader)
        >>> assert env.render("test.html", x=21) == "42"

    Raises:
        TemplateNotFoundError: If template name not in mapping
    """

    __slots__ = ("_mapping",)

    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def get_source(self, name: str) -> tuple[str, None]:
        if name not in self._mapping:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        return self._mapping[name], None

    def list_templates(self) -> list[str]:
        return sorted(self._mapping.keys())
