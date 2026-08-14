"""Adapter for theme-library filter/global registration on a Kida environment."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.errors.codes import ErrorCode

if TYPE_CHECKING:
    from kida import Environment


class _ProviderEnvShim:
    """Adapter that lets library register_filters() calls set env.filters/globals.

    Detects collisions with Bengal built-ins and other providers.
    Implements the minimal template_filter()/template_global() decorator API
    that libraries like chirp_ui expect (Flask-style registration).
    """

    __slots__ = (
        "_builtin_filters",
        "_builtin_globals",
        "_env",
        "_filter_owners",
        "_global_owners",
        "_package",
    )

    def __init__(
        self,
        env: Environment,
        builtin_filters: frozenset[str],
        builtin_globals: frozenset[str],
        filter_owners: dict[str, str],
        global_owners: dict[str, str],
        package: str,
    ) -> None:
        self._env = env
        self._builtin_filters = builtin_filters
        self._builtin_globals = builtin_globals
        self._filter_owners = filter_owners
        self._global_owners = global_owners
        self._package = package

    def _check_collision(self, name: str, kind: str) -> None:
        from bengal.errors.context import ErrorDebugPayload
        from bengal.errors.exceptions import BengalConfigError

        builtins = self._builtin_filters if kind == "filter" else self._builtin_globals
        if name in builtins:
            msg = (
                f"Theme library '{self._package}': {kind} '{name}' collides with a Bengal built-in"
            )
            raise BengalConfigError(
                msg,
                code=ErrorCode.C003,
                suggestion=(
                    f"Rename the {kind} in '{self._package}' or remove the library "
                    "from the theme's libraries list."
                ),
                debug_payload=ErrorDebugPayload(
                    processing_item=f"theme-library:{self._package}",
                    processing_type="theme_library",
                    config_keys_accessed=["theme.libraries"],
                    relevant_config={
                        "library": self._package,
                        "kind": kind,
                        "name": name,
                        "collision": "bengal_builtin",
                    },
                    files_to_check=["themes/*/theme.toml", self._package],
                    grep_patterns=[f"libraries = .*{self._package}", f"{kind}.*{name}"],
                ),
            )
        owners = self._filter_owners if kind == "filter" else self._global_owners
        if name in owners:
            msg = (
                f"Theme library '{self._package}': {kind} '{name}' "
                f"collides with library '{owners[name]}'"
            )
            raise BengalConfigError(
                msg,
                code=ErrorCode.C003,
                suggestion=(
                    f"Rename the {kind} in either '{self._package}' or '{owners[name]}', "
                    "or remove one library from the theme's libraries list."
                ),
                debug_payload=ErrorDebugPayload(
                    processing_item=f"theme-library:{self._package}",
                    processing_type="theme_library",
                    config_keys_accessed=["theme.libraries"],
                    relevant_config={
                        "library": self._package,
                        "existing_library": owners[name],
                        "kind": kind,
                        "name": name,
                        "collision": "provider",
                    },
                    files_to_check=["themes/*/theme.toml", self._package, owners[name]],
                    grep_patterns=[f"libraries = .*{self._package}", f"{kind}.*{name}"],
                ),
            )

    def template_filter(self, name: str | None = None):
        """Decorator-style filter registration (Flask-compatible)."""

        def decorator(fn):
            filter_name = name or fn.__name__
            self._check_collision(filter_name, "filter")
            self._env.filters[filter_name] = fn
            self._filter_owners[filter_name] = self._package
            return fn

        return decorator

    def template_global(self, name: str | None = None):
        """Decorator-style global registration (Flask-compatible)."""

        def decorator(fn):
            global_name = name or fn.__name__
            self._check_collision(global_name, "global")
            self._env.globals[global_name] = fn
            self._global_owners[global_name] = self._package
            return fn

        return decorator

    def add_template_filter(self, fn, name: str | None = None) -> None:
        """Direct filter registration (non-decorator style)."""
        filter_name = name or fn.__name__
        self._check_collision(filter_name, "filter")
        self._env.filters[filter_name] = fn
        self._filter_owners[filter_name] = self._package

    def add_template_global(self, fn, name: str | None = None) -> None:
        """Direct global registration (non-decorator style)."""
        global_name = name or fn.__name__
        self._check_collision(global_name, "global")
        self._env.globals[global_name] = fn
        self._global_owners[global_name] = self._package
