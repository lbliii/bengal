"""CI guard: ``agent-plugin/`` manifests match Agent Plugins 1.0.0 (#782, #784).

Loads ``plugin.json`` and ``mcp.json`` from the repo and checks them against
vendored 1.0.0 schemas under ``tests/unit/docs/fixtures/agent-plugins/``.
Does not retrieve schemas while the test runs (spec §5.2 / §7.2.1).
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

# tests/unit/docs/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_ROOT = _REPO_ROOT / "agent-plugin"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "agent-plugins"

_PLUGIN_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
_MCP_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
_SCHEMA_VERSION = "1.0.0"

_PLUGIN_CLOSED_FIELDS = frozenset(
    {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "extensions",
    }
)
_MCP_CLOSED_FIELDS = frozenset({"$schema", "mcpServers"})
_STDIO_CLOSED_FIELDS = frozenset({"type", "command", "args", "env", "cwd"})
_PACK_STDIO_FIELDS = frozenset({"type", "command", "args"})

_SECRET_KEY_RE = re.compile(
    r"secret|password|passwd|token|api[_-]?key|authorization|credential",
    re.IGNORECASE,
)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must be a JSON object"
    return data


def _schema_version(schema_url: str) -> str:
    parts = schema_url.rstrip("/").split("/")
    assert len(parts) >= 2, f"unrecognized schema URL: {schema_url}"
    return parts[-2]


def _assert_closed_object(
    data: dict[str, Any],
    *,
    allowed: frozenset[str],
    required: frozenset[str],
    label: str,
) -> None:
    missing = required - data.keys()
    extra = data.keys() - allowed
    assert not missing, f"{label} missing required fields: {sorted(missing)}"
    assert not extra, f"{label} has unknown top-level fields: {sorted(extra)}"


def _assert_no_secret_keys(mapping: dict[str, Any], *, label: str) -> None:
    secrets = [key for key in mapping if _SECRET_KEY_RE.search(key)]
    assert not secrets, f"{label} must not embed secrets: {secrets}"


def _plugin_name_pattern(plugin_schema: dict[str, Any]) -> re.Pattern[str]:
    pattern = plugin_schema["properties"]["name"]["pattern"]
    assert isinstance(pattern, str)
    return re.compile(pattern)


def _assert_plugin_name(name: object, plugin_schema: dict[str, Any]) -> None:
    assert isinstance(name, str)
    assert 1 <= len(name) <= 64, f"plugin name length must be 1–64, got {len(name)}"
    name_re = _plugin_name_pattern(plugin_schema)
    assert name_re.fullmatch(name), f"plugin name fails spec §5.5: {name!r}"


def _assert_plugin_manifest(plugin: dict[str, Any], plugin_schema: dict[str, Any]) -> None:
    schema_allowed = frozenset(plugin_schema["properties"])
    assert schema_allowed == _PLUGIN_CLOSED_FIELDS
    _assert_closed_object(
        plugin,
        allowed=_PLUGIN_CLOSED_FIELDS,
        required=frozenset({"$schema", "name"}),
        label="plugin.json",
    )
    assert plugin["$schema"] == _PLUGIN_SCHEMA_ID
    assert plugin["$schema"] == plugin_schema["$id"]
    assert plugin["$schema"] == plugin_schema["properties"]["$schema"]["const"]
    assert _schema_version(plugin["$schema"]) == _SCHEMA_VERSION

    _assert_plugin_name(plugin["name"], plugin_schema)
    assert plugin["name"] == "bengal-agent"
    assert "extensions" not in plugin


def _assert_mcp_manifest(mcp: dict[str, Any], mcp_schema: dict[str, Any]) -> None:
    schema_allowed = frozenset(mcp_schema["properties"])
    assert schema_allowed == _MCP_CLOSED_FIELDS
    _assert_closed_object(
        mcp,
        allowed=_MCP_CLOSED_FIELDS,
        required=frozenset({"$schema", "mcpServers"}),
        label="mcp.json",
    )
    assert mcp["$schema"] == _MCP_SCHEMA_ID
    assert mcp["$schema"] == mcp_schema["$id"]
    assert mcp["$schema"] == mcp_schema["properties"]["$schema"]["const"]
    assert _schema_version(mcp["$schema"]) == _SCHEMA_VERSION

    servers = mcp["mcpServers"]
    assert isinstance(servers, dict)
    assert "bengal" in servers, "mcp.json must define the bengal stdio server"
    server = servers["bengal"]
    assert isinstance(server, dict)
    _assert_closed_object(
        server,
        allowed=_STDIO_CLOSED_FIELDS,
        required=frozenset({"type", "command"}),
        label="mcpServers.bengal",
    )
    extra_pack_fields = server.keys() - _PACK_STDIO_FIELDS
    assert not extra_pack_fields, (
        f"bengal stdio server must omit cwd/env (O1-B / no secrets): {sorted(extra_pack_fields)}"
    )
    assert server["type"] == "stdio"
    command = server["command"]
    assert isinstance(command, str)
    assert command == "bengal"
    assert " " not in command, "command must be one executable token (spec §7.2.1)"
    assert server.get("args") == ["--mcp"]
    assert "cwd" not in server
    assert "env" not in server
    assert "headers" not in server


def test_shipped_manifests_match_agent_plugins_1_0_0() -> None:
    plugin_schema = _load_json(_FIXTURES / "plugin.schema.json")
    mcp_schema = _load_json(_FIXTURES / "mcp.schema.json")
    plugin = _load_json(_PLUGIN_ROOT / "plugin.json")
    mcp = _load_json(_PLUGIN_ROOT / "mcp.json")

    _assert_plugin_manifest(plugin, plugin_schema)
    _assert_mcp_manifest(mcp, mcp_schema)
    assert _schema_version(plugin["$schema"]) == _schema_version(mcp["$schema"])


def test_invalid_plugin_name_is_rejected() -> None:
    plugin_schema = _load_json(_FIXTURES / "plugin.schema.json")
    with pytest.raises(AssertionError, match=r"spec §5\.5"):
        _assert_plugin_name("Bengal-Agent", plugin_schema)
    with pytest.raises(AssertionError, match=r"spec §5\.5"):
        _assert_plugin_name("has--double", plugin_schema)
    with pytest.raises(AssertionError, match="1–64"):
        _assert_plugin_name("a" * 65, plugin_schema)


def test_unknown_plugin_field_is_rejected() -> None:
    plugin_schema = _load_json(_FIXTURES / "plugin.schema.json")
    plugin = _load_json(_PLUGIN_ROOT / "plugin.json")
    plugin["mcpServers"] = {}
    with pytest.raises(AssertionError, match="unknown top-level fields"):
        _assert_plugin_manifest(plugin, plugin_schema)


def test_stdio_cwd_is_rejected() -> None:
    mcp_schema = _load_json(_FIXTURES / "mcp.schema.json")
    mcp = _load_json(_PLUGIN_ROOT / "mcp.json")
    mcp["mcpServers"]["bengal"]["cwd"] = "./"
    with pytest.raises(AssertionError, match="omit cwd/env"):
        _assert_mcp_manifest(mcp, mcp_schema)


def test_uv_run_command_is_rejected() -> None:
    mcp_schema = _load_json(_FIXTURES / "mcp.schema.json")
    mcp = _load_json(_PLUGIN_ROOT / "mcp.json")
    mcp["mcpServers"]["bengal"]["command"] = "uv run"
    with pytest.raises(AssertionError):
        _assert_mcp_manifest(mcp, mcp_schema)


def test_secret_keys_in_env_or_headers_are_rejected() -> None:
    _assert_no_secret_keys({}, label="empty")
    with pytest.raises(AssertionError, match="must not embed secrets"):
        _assert_no_secret_keys({"API_KEY": "x"}, label="env")
    with pytest.raises(AssertionError, match="must not embed secrets"):
        _assert_no_secret_keys({"Authorization": "Bearer x"}, label="headers")


def test_module_does_not_fetch_schemas() -> None:
    for line in Path(__file__).read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("import ", "from ")):
            assert "httpx" not in stripped
            assert "urllib" not in stripped
            assert "requests" not in stripped
            assert "aiohttp" not in stripped
    assert (_FIXTURES / "plugin.schema.json").is_file()
    assert (_FIXTURES / "mcp.schema.json").is_file()
