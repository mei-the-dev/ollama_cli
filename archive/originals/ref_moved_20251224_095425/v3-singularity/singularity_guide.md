# Singularity v3.0 - Complete Guide

**Continue.dev-inspired Coding Agent with Battle-tested Architecture**

---

## 🚀 What's New in v3.0

Singularity v3.0 is a complete rewrite inspired by Continue.dev's proven architecture, bringing you:

### Core Improvements

1. **Battle-tested Agent Loop**
   - Multi-step reasoning with explicit steps
   - Tool calling with approval workflow
   - Error recovery and graceful degradation
   - Streaming responses for real-time feedback

2. **Granular Permission System** (Continue.dev-style)
   - **always_allow**: Read-only operations (automatic)
   - **ask**: Write operations (require approval)
   - **never**: Blocked operations (safety)
   - Per-tool and category-based rules

3. **Smart Context Management**
   - File references with `@file:path/to/file`
   - Auto-context from workspace
   - Token-aware context window
   - Intelligent pruning

4. **Enhanced Tools**
   - Proper error handling
   - Timeout protection
   - Size limits and safety checks
   - Telemetry and metrics

---

## 📦 Installation

```bash
# Install Singularity v3.0
git clone https://github.com/yourusername/singularity
cd singularity

# Install dependencies
pip install -r requirements.txt

# Make executable
chmod +x singularity_v3.py mcp_server_v3.py
```

### Requirements

- Python 3.8+
- Ollama (for LLM)
- aiohttp, prompt_toolkit, rich

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a coding model
ollama pull qwen2.5-coder:14b
```

---

## 🎯 Quick Start

### Interactive Mode (TUI)

```bash
# Start interactive session
./singularity_v3.py

# Or with custom model
./singularity_v3.py --model codellama:13b
```

**Example interaction:**
```
singularity › @file:app.py Add error handling to the API endpoint

🤖 Step 1: Analyzing app.py...
   [Streaming response]
   
⚠️  Approval Required
Tool: write_file
Arguments: {"filepath": "app.py", "content": "..."}
Allow? (y/N): y

✅ write_file: {"size": 1234, "lines": 45}

🤖 Step 2: Added comprehensive error handling...
   TASK_COMPLETE
```

### Headless Mode

```bash
# Single prompt execution
./singularity_v3.py -p "Refactor utils.py to use async"

# With auto-approval (DANGEROUS - use carefully)
./singularity_v3.py -p "Fix all linting errors" --allow write_file
```

---

## 🔧 Configuration

### Permission Rules

Create `~/.singularity/permissions.json`:

```json
{
  "rules": {
    "read": "always_allow",
    "write": "ask",
    "execute": "ask"
  },
  "tools": {
    "read_file": "always_allow",
    "search_files": "always_allow",
    "write_file": "ask",
    "execute_bash": "ask"
  }
}
```

### Server Config

Create `~/.singularity/config.json`:

```json
{
  "model": "qwen2.5-coder:14b",
  "allow_sudo": false,
  "max_file_size": 10485760,
  "timeout": 30,
  "auto_format": true
}
```

---

## 🛠️ Available Tools

### Read Operations (Auto-approved)

**read_file**
```json
{"filepath": "path/to/file.py"}
```
- Reads file with encoding detection
- Parses AST for Python files
- Returns content, size, line count

**search_files**
```json
{"query": "TODO", "path": ".", "limit": 50}
```
- Smart codebase search
- Context lines around matches
- Respects gitignore

**analyze_file**
```json
{"filepath": "module.py"}
```
- Deep analysis with metrics
- Function/class extraction
- Complexity calculation

### Write Operations (Require Approval)

**write_file**
```json
{
  "filepath": "app.py",
  "content": "...",
  "auto_format": true,
  "create_backup": true
}
```
- Automatic backups
- Optional auto-formatting (black for Python)
- Size checks

**apply_diff**
```json
{
  "filepath": "file.py",
  "diff": "unified diff content",
  "dry_run": false
}
```
- Surgical code changes
- Preview before applying
- Safe backup creation

### Execute Operations (Require Approval)

**execute_bash**
```json
{
  "command": "pytest tests/",
  "timeout": 60,
  "stream": false
}
```
- Timeout protection
- Environment variable support
- Optional streaming output

**git_operation**
```json
{
  "operation": "commit",
  "args": ["-m", "feat: add feature"],
  "auto_add": true
}
```
- Smart git operations
- Auto-add before commit
- Branch protection

---

## 💡 Usage Patterns

### Pattern 1: Code Generation

```bash
singularity › Generate a FastAPI endpoint for user authentication with JWT

# Agent will:
# 1. Read existing code for context
# 2. Generate endpoint code
# 3. Ask approval to write file
# 4. Apply changes
```

### Pattern 2: Refactoring

```bash
singularity › @file:legacy.py Refactor to use async/await

# Agent will:
# 1. Analyze current code
# 2. Plan refactoring steps
# 3. Apply changes incrementally
# 4. Run tests to verify
```

### Pattern 3: Bug Fixing

```bash
singularity › Fix the NoneType error in utils.py line 45

# Agent will:
# 1. Read utils.py
# 2. Analyze the error context
# 3. Propose fix
# 4. Ask approval to apply
```

### Pattern 4: Documentation

```bash
singularity › Add comprehensive docstrings to @file:api.py

# Agent will:
# 1. Read and analyze functions
# 2. Generate docstrings
# 3. Update file with documentation
```

### Pattern 5: Testing

```bash
singularity › Generate unit tests for @file:calculator.py

# Agent will:
# 1. Analyze calculator.py
# 2. Generate test cases
# 3. Create test_calculator.py
```

---

## 🎨 Commands Reference

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/exit` | Exit Singularity |
| `/clear` | Clear context |
| `/allow <tool>` | Always allow tool |
| `/ask <tool>` | Require approval for tool |
| `/block <tool>` | Block tool completely |
| `/metrics` | Show execution metrics |

### Context Providers

| Provider | Example | Description |
|----------|---------|-------------|
| `@file:` | `@file:app.py` | Add file to context |
| `@dir:` | `@dir:src/` | Add directory (coming soon) |
| `@web:` | `@web:url` | Fetch web content (coming soon) |

---

## 🔒 Security Best Practices

### 1. **Use Permission Rules**

```bash
# Block dangerous operations
./singularity_v3.py
singularity › /block execute_bash
singularity › /block write_file

# Only allow safe operations
singularity › /allow read_file
singularity › /allow search_files
```

### 2. **Review Before Approval**

- Always review tool arguments carefully
- Check file paths and commands
- Verify no sensitive data exposure

### 3. **Use Backups**

- File backups are automatic
- Keep them for rollback
- Clean old backups periodically

### 4. **Headless Mode Safety**

```bash
# NEVER do this in production
./singularity_v3.py -p "Fix everything" --allow write_file

# Instead, run interactively
./singularity_v3.py
```

---

## 📊 Monitoring & Metrics

### View Metrics

```bash
singularity › /metrics
```

Shows:
- Total agent steps
- Tool calls made
- Approvals requested
- Errors encountered

### Server Health

```bash
curl http://localhost:PORT/health
```

Returns:
- Uptime
- Request rate
- Average latency
- Tool usage statistics

---

## 🐛 Troubleshooting

### Issue: Ollama Connection Failed

```bash
# Check Ollama is running
ollama list

# Start Ollama service
ollama serve
```

### Issue: Permission Denied

```bash
# Reset permissions
rm ~/.singularity/permissions.json

# Restart with defaults
./singularity_v3.py
```

### Issue: MCP Server Not Starting

```bash
# Check logs
tail -f ~/.singularity/logs/singularity_*.log

# Manual server start
./mcp_server_v3.py --host 127.0.0.1 --port 8765
```

### Issue: Tool Execution Timeout

Edit `~/.singularity/config.json`:
```json
{
  "timeout": 120
}
```

---

## 🚀 Advanced Usage

### Custom Tools

Add your own tools to `mcp_server_v3.py`:

```python
async def tool_my_custom_tool(self, args: Dict) -> ToolResult:
    """Your custom tool implementation"""
    try:
        result = do_something(args)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=result
        )
    except Exception as e:
        return ToolResult(
            status=ToolStatus.ERROR,
            error=str(e)
        )
```

### CI/CD Integration

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Singularity
        run: |
          ./singularity_v3.py -p "Review the changes in this PR" \
            --allow read_file --allow search_files
```

### API Integration

```python
import aiohttp

async def call_singularity_tool(tool_name, arguments):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8765/call",
            json={"name": tool_name, "arguments": arguments}
        ) as resp:
            return await resp.json()

# Example
result = await call_singularity_tool("read_file", {"filepath": "app.py"})
```

---

## 🌟 Key Differences from v2.0

| Feature | v2.0 | v3.0 |
|---------|------|------|
| Agent Loop | Basic | Multi-step with reasoning |
| Permissions | Simple allow/deny | Granular 3-tier system |
| Streaming | Limited | Full streaming support |
| Error Handling | Basic | Comprehensive with recovery |
| Metrics | None | Full telemetry |
| Tool Schema | Informal | Structured with validation |
| Context | Manual | Smart auto-context |

---

## 📚 Learn More

- [Continue.dev Documentation](https://docs.continue.dev/)
- [Agent Loop Patterns](https://docs.continue.dev/guides/agent-loop)
- [Permission System](https://docs.continue.dev/guides/permissions)

---

## 🤝 Contributing

We follow Continue.dev's contribution philosophy:

1. **Start Small** - Fix bugs, improve docs
2. **Test Thoroughly** - Add tests for new features
3. **Document Everything** - Update this guide
4. **Open PRs Early** - Get feedback fast

---

## 📝 License

Apache 2.0 - Same as Continue.dev

---

## 🎯 Roadmap

### v3.1 (Next)
- [ ] Web search integration
- [ ] Directory context provider
- [ ] Improved diff application
- [ ] Session persistence

### v3.2 (Future)
- [ ] Multi-agent workflows
- [ ] Custom rules system
- [ ] VSCode extension
- [ ] Cloud sync

---

**Built with inspiration from Continue.dev • Ship faster with Continuous AI**
