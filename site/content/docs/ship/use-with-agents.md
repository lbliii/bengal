---


title: Use with Agents
nav_title: Use with Agents
description: Distinguish site artifacts, hosted docs MCP, and the CLI MCP — and run Bengal as an MCP server while you author a site
weight: 38
icon: code
tags:
- ai
- mcp
- cli
keywords:
- mcp
- llms.txt
- cli mcp
- agent discovery
- milo gateway
aliases:
  - /docs/ship/use-with-agents/
---

# Use with Agents

Bengal talks to agents in three places. Mixing them up is the usual failure: a
published site's `llms.txt` is not the CLI, and the Connect to IDE button is not
`bengal --mcp`.

This page is for people **authoring** a Bengal site who want the CLI inside an
MCP client. For files agents read on a published site, see
[AI-Native Output](./ai-native-output/). For a button that installs a hosted
docs MCP, see [Connect to IDE](./connect-to-ide/).

## Three surfaces

| Surface | Audience | What Bengal provides |
|---------|----------|----------------------|
| Site artifacts (`llms.txt`, `agent.json`) | Agents **reading** a published site | Generated on every `bengal build` |
| Hosted docs MCP | Readers installing your docs in an IDE | The Connect to IDE button. Bengal does **not** provide that HTTP server |
| CLI MCP | People **authoring** a Bengal site | `bengal --mcp` — JSON-RPC on stdin/stdout |

## Run the CLI as an MCP server

`bengal` must be on your `PATH`, the same as any other CLI.

```bash
bengal --mcp
```

That process speaks [MCP](https://modelcontextprotocol.io/) over stdio (JSON-RPC
on stdin/stdout). Point your MCP client at this command. It exposes the
registered Bengal command tree — the same public CLI you already use, including
`bengal build` and `bengal serve`.

This is **not** an MCP server for your published documentation. It does not
replace a hosted Streamable HTTP endpoint, and it is not a Python entry-point
plugin. For that extension surface, see
[Writing Plugins](../../build-sites/extend/plugins/).

## Register with the Milo gateway

To register this CLI in the Milo gateway for AI agent discovery:

```bash
bengal --mcp-install
```

To remove it:

```bash
bengal --mcp-uninstall
```

These flags talk to the Milo gateway only. They do not install a hosted docs
MCP, and they do not change what `bengal build` writes into `public/`.

## CLI command catalog for agents

```bash
bengal --llms-txt
```

Prints an agent-readable catalog of the registered CLI. That stdout dump is not
the site-level `llms.txt` file produced by `bengal build` — see
[AI-Native Output](./ai-native-output/) for the published-site artifact.

## See Also

- [AI-Native Output](./ai-native-output/) — `llms.txt`, `agent.json`, and other
  files for agents reading a published site
- [Connect to IDE](./connect-to-ide/) — button for a hosted docs MCP (Bengal
  does not provide that server)
- [Writing Plugins](../../build-sites/extend/plugins/) — Python entry-point
  plugins; a different extension surface
- [Output Formats](./output-formats/) — JSON, LLM text, and other
  machine-readable outputs
