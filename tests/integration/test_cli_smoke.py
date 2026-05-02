"""Published CLI contract smoke tests.

Parser construction tests prove Bengal can describe commands. These tests go one
step further: each non-exempt advertised command gets at least one cheap runtime
invocation that enters the command body against a tiny site fixture.

The tests use ``run_cli`` which invokes Bengal via ``python -m bengal.cli``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests._testing.cli import run_cli


@dataclass(frozen=True)
class CLISmokeCase:
    args: tuple[str, ...]
    testroot: str | None = "test-basic"
    acceptable_exit_codes: tuple[int, ...] = (0,)
    timeout: int = 30


CLI_SMOKE_CASES = [
    CLISmokeCase(("--version",), None),
    CLISmokeCase(("build",)),
    CLISmokeCase(("clean", "--force")),
    CLISmokeCase(("check",), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("fix", "--dry-run"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("codemod", "--path", "content", "--dry-run", "--yes")),
    CLISmokeCase(("new", "site", "--name", "smoke-site", "--no-init")),
    CLISmokeCase(("new", "theme", "--name", "smoke-theme")),
    CLISmokeCase(("new", "page", "--name", "smoke-page")),
    CLISmokeCase(("new", "layout", "--name", "smoke-layout"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("new", "partial", "--name", "smoke-partial"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("new", "content-type", "--name", "smoke-type")),
    CLISmokeCase(("config", "show"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("config", "doctor"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("config", "diff", "--against", "production"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("config", "init", "--force")),
    CLISmokeCase(("config", "inspect"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("theme", "list")),
    CLISmokeCase(("theme", "info", "--slug", "default")),
    CLISmokeCase(("theme", "discover")),
    CLISmokeCase(
        ("theme", "swizzle", "--template-path", "base.html"), acceptable_exit_codes=(0, 1)
    ),
    CLISmokeCase(("theme", "validate", "--theme-path", "."), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("theme", "new", "--slug", "runtime-smoke")),
    CLISmokeCase(("theme", "debug")),
    CLISmokeCase(("theme", "directives")),
    CLISmokeCase(("theme", "test", "--content", "plain text", "--validate-only")),
    CLISmokeCase(("theme", "assets"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("content", "sources")),
    CLISmokeCase(("content", "fetch")),
    CLISmokeCase(("content", "collections")),
    CLISmokeCase(("content", "schemas"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("version", "list")),
    CLISmokeCase(("version", "info", "--version-id", "v1"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(
        ("version", "create", "--version-id", "v1", "--from-path", "content", "--dry-run")
    ),
    CLISmokeCase(
        ("version", "diff", "--old-version", "v1", "--new-version", "v2"),
        acceptable_exit_codes=(0, 1),
    ),
    CLISmokeCase(("i18n", "init", "--locale-codes", "es")),
    CLISmokeCase(("i18n", "extract"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("i18n", "compile"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("i18n", "sync"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("i18n", "status")),
    CLISmokeCase(("plugin", "list")),
    CLISmokeCase(("plugin", "info", "--name", "smoke"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("plugin", "validate"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("inspect", "page", "--page-path", "index"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("inspect", "links", "--internal-only"), acceptable_exit_codes=(0, 1)),
    CLISmokeCase(("inspect", "graph")),
    CLISmokeCase(("inspect", "perf")),
    CLISmokeCase(("debug", "incremental")),
    CLISmokeCase(("debug", "delta")),
    CLISmokeCase(("debug", "deps")),
    CLISmokeCase(("debug", "migrate")),
    CLISmokeCase(("debug", "sandbox", "--list-directives")),
    CLISmokeCase(("cache", "inputs")),
    CLISmokeCase(("cache", "hash")),
]


CLI_SMOKE_EXEMPTIONS = {
    "serve": "starts a long-running development server; server smoke tests own lifecycle checks",
    "upgrade": "checks PyPI and can run an installer; release tests cover installed-wheel startup",
    "theme.install": "installs packages from PyPI; networked installer behavior needs a dedicated test",
}


def _registered_command_keys() -> set[str]:
    from bengal.cli.milo_app import cli

    return {path for path, _command in cli.walk_commands()}


def _case_command_key(args: tuple[str, ...], registered: set[str]) -> str | None:
    if not args or args[0].startswith("-"):
        return None
    parts: list[str] = []
    match: str | None = None
    for arg in args:
        if arg.startswith("-"):
            break
        parts.append(arg)
        candidate = ".".join(parts)
        if candidate in registered:
            match = candidate
    return match


def test_cli_smoke_manifest_covers_registered_commands():
    """Every advertised leaf command needs runtime smoke or an explicit reason."""
    registered = _registered_command_keys()
    covered = {
        key
        for case in CLI_SMOKE_CASES
        if (key := _case_command_key(case.args, registered)) is not None
    }
    exempt = set(CLI_SMOKE_EXEMPTIONS)

    assert registered - covered - exempt == set()
    assert (covered | exempt) - registered == set()
    assert all(reason.strip() for reason in CLI_SMOKE_EXEMPTIONS.values())


@pytest.mark.bengal(testroot="test-basic")
class TestCLICommandSmoke:
    """Runtime smoke tests for published CLI commands."""

    @pytest.mark.parametrize(
        "case",
        CLI_SMOKE_CASES,
        ids=lambda case: ".".join(case.args).replace("--", "") or "root",
    )
    def test_published_cli_contract_runtime_smoke(self, site, case: CLISmokeCase):
        """Advertised commands must execute a runtime path, not only render help."""
        cwd = str(site.root_path) if case.testroot is not None else None
        result = run_cli(list(case.args), cwd=cwd, timeout=case.timeout)

        assert result.returncode in case.acceptable_exit_codes, (
            f"Unexpected exit code {result.returncode} for bengal {' '.join(case.args)}\n"
            f"stdout={result.stdout[-1000:]!r}\nstderr={result.stderr[-1000:]!r}"
        )

    def test_check_command_incremental_smoke(self, site):
        """Verify 'bengal check' works (checks fix for cache redefinition)."""
        # Run build first to ensure output and cache exist
        run_cli(["build"], cwd=str(site.root_path)).assert_ok()

        # Test full validation
        result = run_cli(["check"], cwd=str(site.root_path))
        result.assert_ok()

        # Test incremental validation (checks our fix in validate.py)
        result = run_cli(["check", "--incremental"], cwd=str(site.root_path))
        result.assert_ok()

    def test_cache_hash_command(self, site):
        """Verify 'bengal cache hash' executes, not just renders help."""
        result = run_cli(["cache", "hash"], cwd=str(site.root_path))

        result.assert_ok()
        cache_hash = result.stdout.strip().splitlines()[-1]
        assert len(cache_hash) == 16
        assert all(ch in "0123456789abcdef" for ch in cache_hash)

    def test_cache_hash_includes_absolute_autodoc_sources(self, tmp_path):
        """Absolute autodoc input paths must contribute to the runtime hash."""
        source_dir = tmp_path / "src" / "pkg"
        source_dir.mkdir(parents=True)
        source_file = source_dir / "__init__.py"
        source_file.write_text("VALUE = 1\n")

        site_root = tmp_path / "site"
        (site_root / "content").mkdir(parents=True)
        (site_root / "content" / "index.md").write_text("---\ntitle: Home\n---\n# Home\n")
        (site_root / "bengal.toml").write_text(
            "\n".join(
                [
                    "[site]",
                    'title = "Hash Site"',
                    "",
                    "[autodoc.python]",
                    "enabled = true",
                    f'source_dirs = ["{source_dir.as_posix()}"]',
                    "",
                ]
            )
        )

        result1 = run_cli(["cache", "hash"], cwd=str(site_root))
        result1.assert_ok()
        source_file.write_text("VALUE = 2\n")
        result2 = run_cli(["cache", "hash"], cwd=str(site_root))
        result2.assert_ok()

        assert result1.stdout.strip().splitlines()[-1] != result2.stdout.strip().splitlines()[-1]
