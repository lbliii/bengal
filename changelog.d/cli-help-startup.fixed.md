CLI help, bare command groups, `--version`, and ordinary single-command
execution now avoid full Milo parser construction. Bengal resolves only the
selected command schema unless a full-tree built-in mode such as `--llms-txt`,
completions, or MCP needs the entire command registry.
