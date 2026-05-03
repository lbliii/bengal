Route CLI progress, prompts, interrupt messages, and Milo compatibility output
through the shared `CLIOutput` bridge so CLI utility imports and output package
imports use the same renderer singleton.
