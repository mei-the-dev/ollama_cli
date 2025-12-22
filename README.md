# Omarchy — AI Code Agent

Omarchy is a local AI-powered coding assistant that uses a Model Context Protocol (MCP) server to provide code-aware tools such as `write_code`, `apply_edit`, `fetch_url`, and more.

Highlights
- Interactive artistic CLI with context providers: `@file`, `@web`, `@diff`, `@tree`
- Tools exposed via an MCP HTTP server for scripting and integrations
- Safety: `sudo` is opt-in (`~/.omarchy/config.json`) and `auto_apply` for file writes is opt-in

Quick start
1. Install (see `install_script.sh`)
2. Start the CLI: `omarchy`
3. Use `/mode code` and ask for code generation. To let the agent write files automatically, enable startup auto-apply.

Documentation
See `docs/USER_GUIDE.md` for full usage, configuration, and security guidance.