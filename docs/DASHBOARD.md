# Singularity Command Center (Dashboard)

A modern TUI dashboard that monitors the Ollama model and the MCP server, inspects available tools, and provides an inference testing console.

Features
- Live health checks for Ollama (port 11434) and the local MCP Server (port 8080)
- Tool Inspector: fetches and displays the tool list and basic input schema
- Inference Lab: send prompts to the model and view streamed responses and simple token-rate metrics
- Lightweight CPU/RAM graphs for `ollama` and `python` processes

Quick start
1. Install optional TUI dependencies: `pip install textual aiohttp psutil`
2. Start Ollama: `ollama serve` (optional — the launcher can start it for you)
3. Start the MCP server: `python3 ~/.singularity/mcp_server.py` (or from this repo)
4. Run the dashboard: `python3 ref/singularity_dashboard.py` (or copy to `~/.singularity/` and run there)

Launcher (recommended)

You can use the included launcher script to start Ollama (optional), the MCP server, the CLI, and the dashboard in a single tmux session:

```bash
# Start everything (tmux required):
./scripts/launch_with_dashboard.sh

# Skip starting ollama (if you already ran it elsewhere):
SKIP_OLLAMA=1 ./scripts/launch_with_dashboard.sh
```

If `tmux` is not installed the launcher will start backgrounded processes and write logs to `./logs/`.

Notes and configuration
- The dashboard expects the MCP server at `http://localhost:8080/mcp` and Ollama at `http://localhost:11434` — set `SINGULARITY_MODEL` to change the default model used in the inference lab.
- The dashboard is intended for local development and observability only.

Tips
- If the MCP server is not reachable, the dashboard will show the MCP status as OFFLINE and not attempt tool inspection until it reconnects.
- To run the dashboard from anywhere, copy the file to `~/.singularity/singularity_dashboard.py` and make it executable.

Enjoy! ✨
