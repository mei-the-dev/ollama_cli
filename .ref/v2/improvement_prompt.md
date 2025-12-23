# Critical Review & Improvement Prompt for Singularity CLI + MCP Server

## 🔍 Current Issues Found

After reviewing the existing code and previous answers, I've identified these critical issues:

### **1. Hallucinations in Enhanced CLI (Previous Answer)**
- ❌ **Missing actual Ollama integration** - Used `curl` subprocess instead of proper async HTTP client
- ❌ **Incomplete command handlers** - Most commands print "coming soon" instead of working
- ❌ **No actual MCP server connection** - Agent class doesn't connect to the MCP server at all
- ❌ **Context providers not implemented** - `@file:`, `@web:` parsing exists but doesn't actually work
- ❌ **No streaming implementation** - Just simulated with chunks but no real Ollama streaming
- ❌ **Missing tool execution** - `handle_tool_calls` is a stub that sleeps 0.5s

### **2. Issues in Original CLI (singularity_cli.py)**
- ❌ **Agent doesn't start MCP server properly** - `start_mcp_server()` and `stop_mcp_server()` are empty stubs
- ❌ **No actual communication with MCP** - No HTTP calls to the MCP server
- ❌ **execute_with_animation is empty** - Just prints prompt, doesn't call Ollama
- ❌ **No tool integration** - Can't actually use write_code, read_code, etc.
- ❌ **Startup config prompts exist but don't work in practice**

### **3. Issues in MCP Servers**

**mcp_server.py:**
- ⚠️ **Inconsistent tool implementations** - Some return ToolResult, others return dict
- ⚠️ **Duplicate method definitions** - `analyze_codebase`, `search_files`, etc. defined twice
- ⚠️ **No actual server startup in __main__** - Server setup exists but URL never printed reliably
- ⚠️ **fetch_url not properly attached** - Defined outside class then attached awkwardly

**fast_mcp_server.py:**
- ✓ **Better structured** with consistent ToolResult returns
- ⚠️ **Aliases for compatibility** but still has multiple duplicate methods
- ⚠️ **Port selection is dynamic (port=0)** but parent process might not capture it

---

## 🎯 Your Mission: Make It Actually Work

Please review and fix the CLI and MCP server to create a **fully functional** system. Here's what needs to work:

### **Phase 1: Fix MCP Server Communication** ⭐ CRITICAL

**Task:** Make the CLI actually communicate with the MCP server

```python
# The CLI needs to:
1. Start the MCP server as a subprocess (mcp_server.py or fast_mcp_server.py)
2. Capture the actual port from server stdout ("MCP server listening on 127.0.0.1:XXXXX")
3. Store the URL (e.g., "http://127.0.0.1:XXXXX")
4. Make POST requests to /call endpoint with JSON: {"name": "tool_name", "arguments": {...}}
5. Parse the ToolResult responses
6. Actually stop the server process on exit
```

**Verification:** After this phase, running `singularity_cli.py --startup-check-only` should:
- Start the MCP server
- Print the URL it discovered
- Exit cleanly

---

### **Phase 2: Implement Real Ollama Integration** ⭐ CRITICAL

**Task:** Make the agent actually call Ollama and stream responses

```python
# The agent needs to:
1. Use aiohttp (not subprocess curl) to POST to http://localhost:11434/api/chat
2. Stream the response line-by-line
3. Parse JSON chunks and extract content
4. Detect tool calls in the response (if model returns them)
5. Update conversation history properly
6. Handle errors gracefully
```

**Verification:** After this phase, typing a prompt should show:
- Real streaming response from Ollama
- Proper markdown/code formatting
- Conversation history maintained

---

### **Phase 3: Connect Agent to MCP Tools** ⭐ CRITICAL

**Task:** Make the agent use MCP tools when needed

```python
# When Ollama response includes tool calls, the agent should:
1. Extract tool name and arguments from the response
2. Make HTTP POST to MCP server: {"name": "write_code", "arguments": {"filepath": "...", ...}}
3. Parse the ToolResult
4. Display the tool execution result to the user
5. Continue the conversation with tool results

# Example flow:
User: "create a hello.py file that prints hello world"
→ Agent calls Ollama
→ Ollama suggests: {"tool": "write_code", "args": {"filepath": "hello.py", "content": "print('hello world')"}}
→ Agent calls MCP /call endpoint
→ MCP executes write_code tool
→ Agent shows: "✓ Created hello.py"
```

**Verification:** Test with:
```bash
singularity
> create a test.py file with a hello world function
# Should actually create the file
```

---

### **Phase 4: Implement Context Providers**

**Task:** Make `@file:`, `@web:`, `@tree:`, `@git` actually work

```python
# When user types: "explain @file:main.py"
1. Parse the prompt and extract @file:main.py
2. Read main.py content
3. Inject into the prompt sent to Ollama as context
4. Same for @tree (run tree or custom impl)
5. Same for @git (run git status)
6. @web: should use MCP fetch_url tool or requests library
```

**Verification:**
```bash
singularity
> explain @file:mcp_server.py
# Should include actual file content in context and explain it
```

---

### **Phase 5: Fix Command Handlers**

**Task:** Make all /commands actually work (not print "coming soon")

Commands that MUST work:
- `/exec <cmd>` - Run shell command and show output (already async, should work)
- `/mode <name>` - Switch mode (should work, just verify)
- `/new` - Clear conversation history (should work)
- `/search <query>` - Use MCP search_files tool
- `/analyze [path]` - Use MCP analyze_codebase tool
- `/config show` - Show actual config from ~/.singularity/config.json

**Verification:** Each command should do something real, not just print a message.

---

### **Phase 6: Enhanced Autocomplete (Optional but Nice)**

**Task:** Make the autocomplete actually suggest real files from workspace

```python
# Current issue: SingularityCompleter._index_workspace() is called
# but completions don't always reflect real workspace files

Fix:
1. Ensure workspace indexing happens on startup
2. Make file completions show real files from the index
3. Add re-indexing when user navigates (@file: triggers re-index)
4. Show file metadata (size, last modified) in completion meta
```

---

### **Phase 7: MCP Server Cleanup**

**Task:** Clean up the MCP server code

```python
# Issues to fix:
1. Remove all duplicate method definitions (analyze_codebase defined twice, etc.)
2. Ensure ALL methods return ToolResult consistently
3. Remove the awkward fetch_url attachment pattern - define it properly in the class
4. Make sure __main__ prints port reliably for parent to capture
5. Add better error handling in each tool

# Consider consolidating:
- Keep fast_mcp_server.py as the main implementation (it's cleaner)
- Make mcp_server.py import and extend it if needed
- Or pick one and delete the other
```

---

## 📋 Testing Checklist

After implementing fixes, verify these work:

```bash
# Test 1: Server starts and CLI connects
python singularity_cli.py --startup-check-only
# Expected: "Startup check: MCP server at http://127.0.0.1:XXXXX"

# Test 2: Basic conversation works
python singularity_cli.py
> what is python?
# Expected: Real response from Ollama, streamed

# Test 3: File creation works
> create a test.txt file with content "hello"
# Expected: File actually created, agent uses write_code tool

# Test 4: File reading works
> read test.txt
# Expected: Agent uses read_code tool and shows content

# Test 5: Context providers work
> explain @file:test.txt
# Expected: File content included in prompt

# Test 6: Commands work
> /search TODO
# Expected: Searches workspace using MCP tool

# Test 7: Autocomplete shows real files
> create a script in <TAB>
# Expected: Shows actual workspace files

# Test 8: History persists
# Exit and restart
> <UP ARROW>
# Expected: Previous commands appear
```

---

## 🔧 Implementation Priority

**CRITICAL** (Must work for basic functionality):
1. ✅ MCP server starts and CLI captures URL
2. ✅ Ollama integration with real streaming
3. ✅ Tool execution through MCP

**HIGH** (Makes it actually useful):
4. ✅ Context providers (@file, @tree, @git)
5. ✅ Command handlers (/search, /analyze, /exec)

**MEDIUM** (Nice polish):
6. ✅ Autocomplete shows real workspace files
7. ✅ MCP server code cleanup

---

## 💡 Hints & Guidance

### Starting MCP Server Subprocess
```python
# Good pattern:
proc = await asyncio.create_subprocess_exec(
    sys.executable, str(mcp_server_path),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)

# Read stdout line by line until you see:
# "MCP server listening on 127.0.0.1:XXXXX"
# Then parse the port and construct URL
```

### Calling MCP Tools
```python
# Use aiohttp:
async with aiohttp.ClientSession() as session:
    async with session.post(
        f"{mcp_url}/call",
        json={"name": "write_code", "arguments": {...}}
    ) as resp:
        result = await resp.json()
        # result has: status, data, error, warnings, metadata
```

### Ollama Streaming
```python
# Use aiohttp streaming:
async with session.post(
    "http://localhost:11434/api/chat",
    json={"model": "...", "messages": [...], "stream": True}
) as resp:
    async for line in resp.content:
        if line:
            chunk = json.loads(line)
            yield chunk["message"]["content"]
```

---

## 🎯 Success Criteria

The improved system should:

✅ **Actually start and connect** - No more stub functions
✅ **Stream real responses** - From Ollama, not fake
✅ **Execute tools** - Files get created, code gets analyzed
✅ **Use context** - @file: actually includes file content
✅ **Handle errors gracefully** - Don't crash on failures
✅ **Feel responsive** - Async all the way through
✅ **Be production-ready** - No "coming soon" stubs

---

## 📝 Deliverables

Please provide:

1. **Fixed singularity_cli.py** - With working MCP connection, Ollama integration, and tool execution
2. **Cleaned up mcp_server.py** - No duplicates, consistent ToolResult returns
3. **Testing script** - Shell script that runs all 8 tests above
4. **Brief summary** - What you fixed and how to verify it works

---

## ⚠️ What NOT to Do

❌ Don't add more "coming soon" stubs
❌ Don't use subprocess curl - use aiohttp
❌ Don't print fake streaming - actually stream from Ollama
❌ Don't create new features until these core ones work
❌ Don't ignore the MCP server - the CLI needs it!

---

## 🚀 Ready?

Review the uploaded files:
- `singularity_cli.py` - Main CLI (needs MCP connection + Ollama)
- `mcp_server.py` - MCP server (needs cleanup + consistency)
- `fast_mcp_server.py` - Alternative MCP (consider using this as base)

Focus on **making it work** before making it pretty. The autocomplete and UI are already good - they just need to connect to working backend functionality.

Good luck! 🎯