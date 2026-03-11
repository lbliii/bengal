---
title: Connect to IDE (Cursor MCP)
nav_title: Connect to IDE
description: Add a one-click "Connect to IDE" button so readers can add your docs as an MCP server in Cursor
weight: 37
---

# Connect to IDE (Cursor MCP)

Add a "Connect to IDE" button to your docs that opens Cursor and prompts readers to install your documentation as an [MCP](https://modelcontextprotocol.io/) server. One click adds your docs to their IDE for AI-assisted development.

## What It Does

When enabled, a **Connect to IDE** link appears in the action bar share menu (next to Copy URL, Open LLM text, etc.). Clicking it:

1. Opens Cursor (or prompts to install it)
2. Prompts to add your docs MCP server
3. One-click install — no manual `mcp.json` editing

The button uses Cursor's [MCP install deeplinks](https://cursor.com/docs/context/mcp/install-links) (`cursor://` scheme).

## Prerequisites

You must host a **Streamable HTTP MCP server** that serves your documentation. Bengal generates the button and deeplink — it does **not** provide the MCP server.

The MCP server should:

- Expose an endpoint (e.g. `https://docs.example.com/mcp`)
- Speak the [MCP Streamable HTTP transport](https://modelcontextprotocol.io/docs/concepts/transports)
- Serve your docs content as tools, resources, or prompts

## Enable in Bengal

Add to `bengal.toml` (or your config directory):

```toml
[connect_to_ide]
enabled = true
mcp_url = "https://docs.example.com/mcp"  # Your hosted MCP endpoint
server_name = "My Docs"  # Optional; shown in Cursor when installing (default: Docs)
```

:::{tip}
Use the full URL to your MCP endpoint. Bengal strips trailing slashes automatically.
:::

## Hosting an MCP Server

Bengal does not ship an MCP server. You have several options:

| Approach | Description |
|----------|-------------|
| **Build your own** | Use the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) or [FastMCP](https://github.com/jlowin/fastmcp) with `transport="streamable-http"`. Read your built site (e.g. `public/`) and expose it via tools/resources. |
| **Third-party service** | Some doc platforms offer MCP endpoints. If you use one, point `mcp_url` to their endpoint. |
| **Self-hosted proxy** | Run a small service that reads your static output and serves it via MCP. Deploy alongside your docs (e.g. same domain, `/mcp` path). |

For a minimal Python example, see the [MCP Streamable HTTP guide](https://modelcontextprotocol.io/docs/concepts/transports) and [FastMCP docs](https://github.com/jlowin/fastmcp#streamable-http).

## Where the Button Appears

The button is included in the default theme's **action bar** share dropdown, which appears on documentation pages. Themes can override or relocate it by customizing `partials/action-bar.html` or `partials/connect-to-ide.html`.

## Disable

The feature is **disabled by default**. Omit `connect_to_ide` from config, or set:

```toml
[connect_to_ide]
enabled = false
```

## See Also

- [SEO & Discovery](./seo.md) — Machine discovery, content signals, and related features
- [Output Formats](./output-formats.md) — JSON, LLM text, and other machine-readable outputs
- [Cursor MCP Install Links](https://cursor.com/docs/context/mcp/install-links) — Deeplink format reference
