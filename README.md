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

Dashboard
- A lightweight TUI dashboard is available at `ref/omarchy_dashboard.py` (or copy to `~/.omarchy/omarchy_dashboard.py`). See `docs/DASHBOARD.md` for usage and quick start tips.
- Use the launcher script `./scripts/launch_with_dashboard.sh` to start Ollama (optional), the MCP server, the CLI and the dashboard together (uses `tmux` when available).