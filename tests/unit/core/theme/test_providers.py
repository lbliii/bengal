"""
Tests for theme library provider resolution.

Covers:
- ThemeLibraryProvider dataclass
- resolve_provider() convention hook probing
- resolve_theme_providers() chain accumulation and deduplication
- Error handling for missing/broken packages
"""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import patch

import pytest

from bengal.core.theme.providers import (
    ThemeLibraryProvider,
    get_provider_asset_dirs,
    resolve_provider,
    resolve_theme_providers,
)


def _make_library_module(
    *,
    has_loader: bool = False,
    has_static_path: bool = False,
    has_register_filters: bool = False,
    loader_value: object = None,
    static_path_value: Path | None = None,
    library_contract: dict | None = None,
) -> types.ModuleType:
    """Create a fake library module with configurable convention hooks."""
    mod = types.ModuleType("fake_lib")
    if has_loader:
        mod.get_loader = lambda: loader_value  # type: ignore[attr-defined]
    if has_static_path:
        mod.static_path = lambda: static_path_value  # type: ignore[attr-defined]
    if has_register_filters:
        mod.register_filters = lambda app: None  # type: ignore[attr-defined]
    if library_contract is not None:
        mod.get_library_contract = lambda: library_contract  # type: ignore[attr-defined]
    return mod


class TestThemeLibraryProvider:
    """Tests for ThemeLibraryProvider dataclass."""

    def test_frozen(self):
        provider = ThemeLibraryProvider(
            package="test",
            loader=None,
            asset_root=None,
            asset_prefix="test",
            register_env=None,
        )
        with pytest.raises(AttributeError):
            provider.package = "changed"  # type: ignore[misc]

    def test_fields(self):
        root = Path("/fake/static")
        provider = ThemeLibraryProvider(
            package="chirp_ui",
            loader="fake_loader",
            asset_root=root,
            asset_prefix="chirp_ui",
            register_env=None,
        )
        assert provider.package == "chirp_ui"
        assert provider.loader == "fake_loader"
        assert provider.asset_root == root
        assert provider.asset_prefix == "chirp_ui"
        assert provider.register_env is None


class TestResolveProvider:
    """Tests for resolve_provider()."""

    def test_resolves_all_hooks(self):
        loader = object()
        static = Path("/fake/static")
        mod = _make_library_module(
            has_loader=True,
            has_static_path=True,
            has_register_filters=True,
            loader_value=loader,
            static_path_value=static,
        )
        with patch("bengal.core.theme.providers.importlib.import_module", return_value=mod):
            provider = resolve_provider("fake_lib")

        assert provider.package == "fake_lib"
        assert provider.loader is loader
        assert provider.asset_root == static
        assert provider.asset_prefix == "fake_lib"
        assert provider.register_env is not None

    def test_missing_hooks_are_none(self):
        mod = _make_library_module()
        with patch("bengal.core.theme.providers.importlib.import_module", return_value=mod):
            provider = resolve_provider("bare_lib")

        assert provider.loader is None
        assert provider.asset_root is None
        assert provider.register_env is None

    def test_import_failure_raises_config_error(self):
        from bengal.errors.exceptions import BengalConfigError

        with (
            patch(
                "bengal.core.theme.providers.importlib.import_module",
                side_effect=ImportError("No module named 'nonexistent'"),
            ),
            pytest.raises(BengalConfigError, match="not installed"),
        ):
            resolve_provider("nonexistent")

    def test_hook_failure_raises_config_error(self):
        from bengal.errors.exceptions import BengalConfigError

        mod = types.ModuleType("broken_lib")
        mod.get_loader = lambda: (_ for _ in ()).throw(RuntimeError("broken"))  # type: ignore[attr-defined]

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match=r"get_loader.*failed"),
        ):
            resolve_provider("broken_lib")

    def test_asset_prefix_normalizes_hyphens(self):
        mod = _make_library_module()
        with patch("bengal.core.theme.providers.importlib.import_module", return_value=mod):
            provider = resolve_provider("my-ui-kit")

        assert provider.asset_prefix == "my_ui_kit"

    def test_consumes_library_contract_assets(self, tmp_path):
        static = tmp_path / "static"
        static.mkdir()
        (static / "ui.css").write_text(".ui{}", encoding="utf-8")
        (static / "ui.js").write_text("window.ui=true", encoding="utf-8")
        (static / "tokens.css").write_text(":root{}", encoding="utf-8")
        mod = _make_library_module(
            library_contract={
                "asset_root": static,
                "assets": [
                    {"path": "ui.css", "mode": "link", "type": "css"},
                    {
                        "path": "ui.js",
                        "mode": "bundle",
                        "type": "javascript",
                        "output": "bundle.js",
                        "defer": True,
                        "module": True,
                        "attributes": {"crossorigin": "anonymous"},
                    },
                    {"path": "tokens.css", "mode": "none", "type": "css"},
                ],
                "runtime": ["ui-runtime"],
            }
        )

        with patch("bengal.core.theme.providers.importlib.import_module", return_value=mod):
            provider = resolve_provider("fake_ui")

        assert provider.asset_root == static
        assert provider.runtime == ("ui-runtime",)
        assert [asset.mode for asset in provider.assets] == ["link", "bundle", "none"]
        assert [asset.logical_path.as_posix() for asset in provider.assets] == [
            "fake_ui/ui.css",
            "fake_ui/bundle.js",
            "fake_ui/tokens.css",
        ]
        assert dict(provider.assets[1].tag_attrs) == {
            "crossorigin": "anonymous",
            "defer": True,
            "type": "module",
        }

    def test_invalid_library_contract_mode_raises_config_error(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "ui.css", "mode": "copy"}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="asset mode 'copy' is invalid"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_absolute_output_path(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "ui.css", "output": "/tmp/ui.css"}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="output must be relative"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_output_traversal(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "ui.css", "output": "../ui.css"}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match=r"output must not contain '\.\.'"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_source_traversal(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "../ui.css"}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match=r"path must not contain '\.\.'"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_non_path_asset_value(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [object()],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="path must be path-like"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_non_string_runtime_entries(self):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(library_contract={"runtime": ["loader", 3]})

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="runtime entries must be strings"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_bytes_runtime(self):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(library_contract={"runtime": b"loader"})

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="runtime must be a string"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_non_mapping_asset_attributes(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "ui.js", "attributes": ["defer"]}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="attributes must be a mapping"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_reserved_asset_attribute(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "ui.js", "attributes": {"src": "/bad.js"}}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="must not set 'src'"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_invalid_asset_attribute_value(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [{"path": "ui.css", "attributes": {"media": ["print"]}}],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="values must be strings or booleans"),
        ):
            resolve_provider("fake_ui")

    def test_library_contract_rejects_duplicate_non_bundle_outputs(self, tmp_path):
        from bengal.errors.exceptions import BengalConfigError

        mod = _make_library_module(
            library_contract={
                "asset_root": tmp_path,
                "assets": [
                    {"path": "ui.css", "output": "vendor.css", "mode": "link"},
                    {"path": "theme.css", "output": "vendor.css", "mode": "link"},
                ],
            }
        )

        with (
            patch("bengal.core.theme.providers.importlib.import_module", return_value=mod),
            pytest.raises(BengalConfigError, match="duplicate asset output"),
        ):
            resolve_provider("fake_ui")


class TestResolveThemeProviders:
    """Tests for resolve_theme_providers() chain accumulation."""

    def _write_theme_toml(self, tmp_path: Path, name: str, content: str) -> None:
        theme_dir = tmp_path / "themes" / name
        theme_dir.mkdir(parents=True, exist_ok=True)
        (theme_dir / "theme.toml").write_text(content)

    def test_empty_chain_returns_empty(self, tmp_path):
        providers = resolve_theme_providers(tmp_path, [])
        assert providers == ()

    def test_theme_without_libraries_returns_empty(self, tmp_path):
        self._write_theme_toml(tmp_path, "simple", 'name = "simple"')
        providers = resolve_theme_providers(tmp_path, ["simple"])
        assert providers == ()

    def test_single_theme_with_libraries(self, tmp_path):
        self._write_theme_toml(tmp_path, "themed", 'name = "themed"\nlibraries = ["fake_ui"]')
        mod = _make_library_module(has_loader=True, loader_value="loader")
        with patch("bengal.core.theme.providers.importlib.import_module", return_value=mod):
            providers = resolve_theme_providers(tmp_path, ["themed"])

        assert len(providers) == 1
        assert providers[0].package == "fake_ui"

    def test_child_wins_deduplication(self, tmp_path):
        """When both child and parent declare the same library, child wins."""
        self._write_theme_toml(
            tmp_path, "child", 'name = "child"\nextends = "parent"\nlibraries = ["shared_ui"]'
        )
        self._write_theme_toml(
            tmp_path, "parent", 'name = "parent"\nlibraries = ["shared_ui", "extra_ui"]'
        )

        call_count = {"shared_ui": 0, "extra_ui": 0}

        def mock_import(name):
            call_count[name] = call_count.get(name, 0) + 1
            return _make_library_module(has_loader=True, loader_value=f"loader_{name}")

        with patch("bengal.core.theme.providers.importlib.import_module", side_effect=mock_import):
            providers = resolve_theme_providers(tmp_path, ["child", "parent"])

        assert len(providers) == 2
        assert providers[0].package == "shared_ui"
        assert providers[1].package == "extra_ui"
        # shared_ui resolved only once (from child), not again from parent
        assert call_count["shared_ui"] == 1

    def test_multiple_libraries_per_theme(self, tmp_path):
        self._write_theme_toml(
            tmp_path, "rich", 'name = "rich"\nlibraries = ["lib_a", "lib_b", "lib_c"]'
        )
        mod = _make_library_module()
        with patch("bengal.core.theme.providers.importlib.import_module", return_value=mod):
            providers = resolve_theme_providers(tmp_path, ["rich"])

        assert len(providers) == 3
        assert [p.package for p in providers] == ["lib_a", "lib_b", "lib_c"]

    def test_returns_tuple(self, tmp_path):
        """Result is a tuple (immutable)."""
        providers = resolve_theme_providers(tmp_path, [])
        assert isinstance(providers, tuple)


class TestGetProviderAssetDirs:
    """Tests for get_provider_asset_dirs()."""

    def test_empty_providers(self):
        assert get_provider_asset_dirs(()) == []

    def test_provider_without_asset_root(self):
        p = ThemeLibraryProvider(
            package="no_assets",
            loader=None,
            asset_root=None,
            asset_prefix="no_assets",
            register_env=None,
        )
        assert get_provider_asset_dirs((p,)) == []

    def test_provider_with_existing_asset_root(self, tmp_path):
        asset_dir = tmp_path / "static"
        asset_dir.mkdir()
        p = ThemeLibraryProvider(
            package="has_assets",
            loader=None,
            asset_root=asset_dir,
            asset_prefix="has_assets",
            register_env=None,
        )
        result = get_provider_asset_dirs((p,))
        assert len(result) == 1
        assert result[0] == ("has_assets", asset_dir)

    def test_provider_with_missing_asset_root(self, tmp_path):
        """Provider with non-existent asset_root is skipped."""
        p = ThemeLibraryProvider(
            package="gone",
            loader=None,
            asset_root=tmp_path / "nonexistent",
            asset_prefix="gone",
            register_env=None,
        )
        assert get_provider_asset_dirs((p,)) == []

    def test_multiple_providers(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        providers = (
            ThemeLibraryProvider("a", None, dir_a, "a", None),
            ThemeLibraryProvider("b", None, None, "b", None),
            ThemeLibraryProvider("c", None, dir_b, "c", None),
        )
        result = get_provider_asset_dirs(providers)
        assert len(result) == 2
        assert result[0] == ("a", dir_a)
        assert result[1] == ("c", dir_b)


class TestProviderEnvShim:
    """Tests for _ProviderEnvShim collision detection."""

    def test_filter_collision_with_builtin(self):
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.errors.exceptions import BengalConfigError
        from bengal.rendering.engines.kida import _ProviderEnvShim

        env = Environment(loader=FileSystemLoader([]))
        env.filters["url"] = lambda x: x
        builtin_filters = frozenset(env.filters.keys())
        builtin_globals = frozenset(env.globals.keys())

        shim = _ProviderEnvShim(env, builtin_filters, builtin_globals, {}, {}, "test_lib")

        with pytest.raises(BengalConfigError, match="collides with a Bengal built-in"):
            shim.add_template_filter(lambda x: x, name="url")

    def test_filter_collision_between_providers(self):
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.errors.exceptions import BengalConfigError
        from bengal.rendering.engines.kida import _ProviderEnvShim

        env = Environment(loader=FileSystemLoader([]))
        filter_owners: dict[str, str] = {"shared_filter": "lib_a"}

        shim = _ProviderEnvShim(env, frozenset(), frozenset(), filter_owners, {}, "lib_b")

        with pytest.raises(BengalConfigError, match="collides with library 'lib_a'"):
            shim.add_template_filter(lambda x: x, name="shared_filter")

    def test_successful_filter_registration(self):
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.rendering.engines.kida import _ProviderEnvShim

        env = Environment(loader=FileSystemLoader([]))
        filter_owners: dict[str, str] = {}

        shim = _ProviderEnvShim(env, frozenset(), frozenset(), filter_owners, {}, "my_lib")
        shim.add_template_filter(lambda x: x.upper(), name="shout")

        assert "shout" in env.filters
        assert filter_owners["shout"] == "my_lib"

    def test_decorator_style_registration(self):
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.rendering.engines.kida import _ProviderEnvShim

        env = Environment(loader=FileSystemLoader([]))
        shim = _ProviderEnvShim(env, frozenset(), frozenset(), {}, {}, "my_lib")

        @shim.template_filter("yell")
        def yell(x):
            return x.upper()

        assert env.filters["yell"] is yell

    def test_global_collision_with_builtin(self):
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.errors.exceptions import BengalConfigError
        from bengal.rendering.engines.kida import _ProviderEnvShim

        env = Environment(loader=FileSystemLoader([]))
        env.globals["range"] = range
        builtin_globals = frozenset(env.globals.keys())

        shim = _ProviderEnvShim(env, frozenset(), builtin_globals, {}, {}, "bad_lib")

        with pytest.raises(BengalConfigError, match="collides with a Bengal built-in"):
            shim.add_template_global(lambda: 42, name="range")

    def test_same_name_filter_and_global_no_collision(self):
        """A filter and global with the same name should NOT collide."""
        from kida import Environment
        from kida.environment import FileSystemLoader

        from bengal.rendering.engines.kida import _ProviderEnvShim

        env = Environment(loader=FileSystemLoader([]))
        filter_owners: dict[str, str] = {}
        global_owners: dict[str, str] = {}

        shim = _ProviderEnvShim(
            env, frozenset(), frozenset(), filter_owners, global_owners, "lib_a"
        )
        shim.add_template_filter(lambda x: x, name="foo")
        shim.add_template_global(lambda: 42, name="foo")

        assert filter_owners["foo"] == "lib_a"
        assert global_owners["foo"] == "lib_a"
