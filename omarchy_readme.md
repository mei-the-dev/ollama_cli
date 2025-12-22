# 🚀 Omarchy - AI Code Agent

**A powerful, beautiful CLI code agent powered by Ollama's Qwen2.5-Coder with MCP tools**

Omarchy brings the power of GitHub Copilot CLI to your local machine, with enhanced capabilities for planning, learning, and self-improvement - all running completely offline with your own Ollama instance.

```
   ██████  ███    ███  █████  ██████   ██████ ██   ██ ██    ██ 
  ██    ██ ████  ████ ██   ██ ██   ██ ██      ██   ██  ██  ██  
  ██    ██ ██ ████ ██ ███████ ██████  ██      ███████   ████   
  ██    ██ ██  ██  ██ ██   ██ ██   ██ ██      ██   ██    ██    
   ██████  ██      ██ ██   ██ ██   ██  ██████ ██   ██    ██    
   
         Powered by Qwen2.5-Coder 14B via Ollama
```

## ✨ Features

### 🎯 Core Capabilities
- **💬 Interactive Chat**: Natural conversation with your AI coding assistant
- **⚡ Code Generation**: Create complete, production-ready code
- **📋 Project Planning**: Break down complex tasks into actionable steps
- **📦 Batch Operations**: Generate multiple files and structures at once
- **🎓 Knowledge Persistence**: Learn and save information across sessions
- **🔍 Codebase Analysis**: Deep insights into your projects
- **🔧 Git Integration**: Full version control from the CLI
- **🌐 Documentation Search**: Find and learn from online resources

### 🎨 Beautiful Interface
- **ASCII Art Banner**: Gorgeous startup screen
- **Animated Progress**: Real-time thinking indicators
- **Syntax Highlighting**: Beautiful code display
- **Rich Formatting**: Tables, panels, and markdown rendering
- **Color Themes**: Customizable appearance

### 🛠️ MCP Tools Suite
The agent has access to 15+ powerful tools:

1. **write_code** - Generate and save code files with auto-backup
2. **read_code** - Analyze existing code
3. **execute_code** - Run and test code safely
4. **search_docs** - Find documentation online
5. **git_operation** - Complete git workflow
6. **create_plan** - Project planning and task breakdown
7. **update_plan** - Track progress on plans
8. **save_knowledge** - Persistent learning system
9. **query_knowledge** - Search your knowledge base
10. **batch_generate** - Multi-file generation
11. **analyze_codebase** - Code structure analysis
12. **add_tool** - Self-improvement: add new capabilities
13. **test_code** - Automated testing
14. **And more...**

### 🔄 Self-Improvement
Omarchy can expand its own capabilities:
- Add new tools dynamically
- Learn from interactions
- Improve over time
- Adapt to your workflow

## 📦 Installation

### Quick Install

```bash
# Download and run the installer
curl -fsSL https://raw.githubusercontent.com/your-repo/omarchy/main/install.sh | bash

# Or manual installation:
git clone https://github.com/your-repo/omarchy.git
cd omarchy
chmod +x install.sh
./install.sh
```

### Requirements
- Python 3.8+
- Ollama
- 8GB+ RAM (for the 14B model)
- 10GB disk space

### What Gets Installed
```
~/.omarchy/
├── mcp_server.py       # MCP tool server
├── omarchy.py          # Main CLI
├── config.json         # Configuration
├── knowledge/          # Knowledge base
├── plans/              # Saved plans
├── tools/              # Custom tools
└── sessions/           # Conversation history
```

## 🚀 Quick Start

### Basic Usage

```bash
# Start interactive mode
omarchy

# Direct prompt
omarchy "explain how React hooks work"

# Specific mode
omarchy --mode code "create a REST API with FastAPI"
```

### Interactive Commands

Once in Omarchy:

```
/mode <name>    - Switch modes (chat, code, plan, batch, learn, analyze)
/new            - Start new conversation
/plan           - View current plan
/save           - Save session
/load           - Load previous session
/exec <cmd>     - Execute shell command
/git <op>       - Perform git operation
/help           - Show help
/exit           - Exit Omarchy
```

## 🎯 Usage Modes

### 💬 Chat Mode (Default)
Natural conversation with the agent:
```bash
omarchy
> How do I implement authentication in Express.js?
> What are the best practices for error handling?
> Explain the difference between Promise and async/await
```

### ⚡ Code Mode
Optimized for code generation:
```bash
omarchy --mode code
> Create a Python script to scrape weather data
> Build a React component for a todo list
> Generate a Dockerfile for a Node.js app
```

### 📋 Plan Mode
Break down complex projects:
```bash
omarchy --mode plan
> Build a full-stack blog application
> Create a microservices architecture
> Implement a CI/CD pipeline
```

The agent will create a detailed plan with:
- Actionable steps
- Dependencies
- Time estimates
- Progress tracking

### 📦 Batch Mode
Generate multiple files at once:
```bash
omarchy --mode batch
> Create CRUD operations for User, Product, and Order models
> Generate API endpoints for a blog (posts, comments, users)
> Set up project structure for a React app with Redux
```

### 🎓 Learn Mode
Research and save knowledge:
```bash
omarchy --mode learn
> Research GraphQL best practices
> Learn about Kubernetes deployment strategies
> Study Python async patterns
```

Knowledge is saved to `~/.omarchy/knowledge/` and can be queried later.

### 🔍 Analyze Mode
Deep codebase analysis:
```bash
cd your-project
omarchy --mode analyze
> Review security vulnerabilities
> Find performance bottlenecks
> Suggest refactoring opportunities
> Check code quality and consistency
```

## 💡 Examples

### Example 1: Build a REST API
```bash
omarchy --mode code "Create a FastAPI REST API for a todo application with:
- User authentication (JWT)
- CRUD operations for todos
- SQLAlchemy models
- Proper error handling
- API documentation"
```

### Example 2: Debug Code
```bash
omarchy "I'm getting this error when running my script:
TypeError: 'NoneType' object is not iterable

Here's my code:
$(cat myfile.py)

What's wrong and how do I fix it?"
```

### Example 3: Learn and Apply
```bash
# Learn
omarchy --mode learn "Research Docker multi-stage builds"

# Later, apply knowledge
omarchy --mode code "Create a Dockerfile using multi-stage builds for my Python app"
```

### Example 4: Project Planning
```bash
omarchy --mode plan "Create a real-time chat application with:
- WebSocket support
- User authentication
- Message history
- Typing indicators
- React frontend
- Node.js backend"

# View the plan
/plan

# Track progress
> Completed: Setup project structure
> Completed: Implement authentication
```

### Example 5: Git Workflow
```bash
omarchy
> Review my changes and suggest a commit message

/git status
/git add .
/git commit -m "feat: add user authentication"
/git push
```

## ⚙️ Configuration

Edit `~/.omarchy/config.json`:

```json
{
  "model": "qwen2.5-coder:14b-instruct-q4_K_M",
  "ollama_host": "http://localhost:11434",
  "default_mode": "chat",
  "auto_save_sessions": true,
  "knowledge_base_enabled": true,
  "git_integration": true,
  "theme": "monokai",
  "max_history": 50,
  "streaming": true,
  "animations": true
}
```

### Available Themes
- `monokai` (default)
- `dracula`
- `nord`
- `solarized-dark`
- `solarized-light`

## 🔧 Advanced Features

### Knowledge Base

Build a persistent knowledge base:

```bash
# Save knowledge
omarchy --mode learn "Research Rust ownership and borrowing"

# Query later
omarchy "What did I learn about Rust ownership?"

# Browse knowledge base
cat ~/.omarchy/knowledge/*.json | jq .
```

### Plan Tracking

Create and track complex plans:

```python
# The agent creates structured plans
{
  "id": "plan_20231215_143022",
  "goal": "Build chat application",
  "items": [
    {
      "id": "1",
      "description": "Setup project structure",
      "status": "complete",
      "dependencies": []
    },
    {
      "id": "2",
      "description": "Implement WebSocket server",
      "status": "in_progress",
      "dependencies": ["1"]
    }
  ]
}
```

### Custom Tools

Add your own tools to extend Omarchy:

```python
# Create a new tool
omarchy
> Add a tool called "deploy" that deploys code to my server using SSH

# The agent will:
# 1. Write the tool code
# 2. Add it to the MCP server
# 3. Make it available immediately
```

### Session Management

```bash
# Auto-save is enabled by default
# Sessions are saved to ~/.omarchy/sessions/

# Load previous session
omarchy
/load

# Save current session
/save session-name
```

## 🎭 How It Works

### Architecture

```
┌─────────────────┐
│   Omarchy CLI   │  Beautiful interface with animations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ollama Server  │  Qwen2.5-Coder 14B model
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MCP Server    │  15+ tools for code operations
└─────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  File System, Git, Knowledge DB │
└─────────────────────────────────┘
```

### Tool Execution Flow

1. User enters prompt
2. CLI sends to Ollama with available tools
3. Model decides which tools to use
4. MCP server executes tools
5. Results returned to model
6. Model generates response
7. Beautiful output displayed

## 🐛 Troubleshooting

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Check if it's running
curl http://localhost:11434/api/tags
```

### Model Not Found
```bash
# Pull the correct model
ollama pull qwen2.5-coder:14b-instruct-q4_K_M

# List available models
ollama list
```

### Permission Errors
```bash
chmod +x ~/.omarchy/omarchy.py
chmod +x ~/.omarchy/mcp_server.py
```

### Slow Performance
- Ensure you have 8GB+ RAM available
- Close other applications
- Consider using a smaller model variant
- Check CPU usage: `top` or `htop`

### Reset Everything
```bash
# Remove all data
rm -rf ~/.omarchy

# Reinstall
curl -fsSL https://install.omarchy.com | bash
```

## 🤝 Contributing

Omarchy is designed to self-improve! You can:

1. **Add new tools** via the CLI itself
2. **Share knowledge** exports with others
3. **Create custom modes** for your workflow
4. **Report issues** and suggest features

## 📝 License

MIT License - feel free to use, modify, and distribute!

## 🙏 Credits

- **Ollama** - Local LLM runtime
- **Qwen2.5-Coder** - Powerful code generation model
- **Rich** - Beautiful terminal formatting
- **MCP** - Model Context Protocol

## 🔮 Roadmap

- [ ] Plugin system for custom tools
- [ ] Web interface option
- [ ] Team collaboration features
- [ ] Cloud sync for knowledge base
- [ ] Integration with IDEs (VSCode, JetBrains)
- [ ] Voice input support
- [ ] Multi-model support
- [ ] Docker container deployment

---

**Made with ❤️ for developers who want powerful AI assistance without the cloud**

Start coding smarter today: `omarchy`